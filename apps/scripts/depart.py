"""Protocole de depart d'un employe : on retire bdupont (Bob Dupont) de ses groupes dans LDAP
(Developers et Staff), puis on desactive son compte (Keycloak), et on MESURE le delai avant que
chaque acces tombe.

Usage : python apps/scripts/depart.py [--timeout 240]
Pre-requis : API, Keycloak et annuaire LDAP lances.
Resultat : affichage + docs/resultats/depart.md
"""
import argparse
import time

import requests
from ldap3 import MODIFY_ADD, MODIFY_DELETE, Connection, Server

from common import KC, REALM, RESULTS, call, decode, login, refresh, tokens
from config import (DEPART_GROUPS, DEPART_USER, GROUPS_DN, LDAP_BIND_DN, LDAP_BIND_PW, LDAP_HOST,
                    LDAP_PORT, PEOPLE_DN)

ADMIN = f"{KC}/admin/realms/{REALM}"
USER_DN = f"uid={DEPART_USER},{PEOPLE_DN}"


def admin_headers():
    r = requests.post(f"{KC}/realms/master/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"},
        timeout=10)
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def set_enabled(username: str, enabled: bool):
    h = admin_headers()
    users = requests.get(f"{ADMIN}/users", params={"username": username, "exact": "true"},
                         headers=h, timeout=10).json()
    if not users:
        return
    rep = requests.get(f"{ADMIN}/users/{users[0]['id']}", headers=h, timeout=10).json()
    rep["enabled"] = enabled
    requests.put(f"{ADMIN}/users/{users[0]['id']}", json=rep, headers=h, timeout=10).raise_for_status()


def ldap_groups(op: str):
    """Ajoute ('add') ou retire ('delete') l'employe de ses groupes LDAP. Retourne (succes, message)."""
    conn = Connection(Server(LDAP_HOST, port=LDAP_PORT), user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=True)
    action = MODIFY_ADD if op == "add" else MODIFY_DELETE
    ok, msgs = True, []
    for g in DEPART_GROUPS:
        res = conn.modify(f"cn={g},{GROUPS_DN}", {"member": [(action, [USER_DN])]})
        ok = ok and res
        msgs.append(f"{g}: {conn.result.get('description')}")
    conn.unbind()
    return ok, "; ".join(msgs)


def reset():
    ldap_groups("add")           # si deja membre, erreur ignoree
    set_enabled(DEPART_USER, True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=240, help="duree max d'observation (s) apres desactivation")
    args = ap.parse_args()

    print("Remise a l'etat initial...")
    reset()
    t = tokens(DEPART_USER)
    access, refresh_tok = t["access_token"], t["refresh_token"]
    exp_in = decode(access)["exp"] - time.time()
    print(f"{DEPART_USER} connecte. groups={decode(access).get('groups')}, access token valide ~{exp_in:.0f}s")
    call("POST", "/_reset")

    print("\n== Etat de reference (avant depart) ==")
    for mode in ("local", "introspect"):
        print(f"  POST /docs ({mode}) :", call("POST", "/docs", access, mode, json={"title": "x"}).status_code)

    print(f"\n== Etape 1 : retrait de {DEPART_USER} des groupes {DEPART_GROUPS} dans LDAP ==")
    t_group = time.monotonic()
    ok, msg = ldap_groups("delete")
    if not ok:
        raise SystemExit("retrait des groupes LDAP impossible : " + msg)
    delay_new_roles = None
    new = access
    while time.monotonic() - t_group < 30:
        new = tokens(DEPART_USER)["access_token"]
        if not (decode(new).get("groups") or []):
            delay_new_roles = time.monotonic() - t_group
            break
        time.sleep(1)
    if delay_new_roles is None:
        print("  Nouveau jeton sans groupe : JAMAIS en 30 s -> Keycloak garde l'appartenance en cache "
              "(relancer setup_keycloak.py avec --ldap-cache NO_CACHE)")
    else:
        print(f"  Nouveau jeton sans groupe apres : {delay_new_roles:.1f} s")
    print("  POST /docs avec le NOUVEAU jeton :", call("POST", "/docs", new, "local", json={"title": "y"}).status_code, "(403 attendu)")
    for mode in ("local", "introspect"):
        code = call("POST", "/docs", access, mode, json={"title": "z"}).status_code
        print(f"  POST /docs avec l'ANCIEN jeton ({mode}) : {code}  "
              f"<- {'jeton lu tel quel : les groupes y sont encore' if mode == 'local' else 'Keycloak recalcule les droits a chaque appel'}")

    print("\n== Etape 2 : desactivation du compte ==")
    set_enabled(DEPART_USER, False)
    t0 = time.monotonic()
    pending = {
        "nouvelle connexion": lambda: login(DEPART_USER).status_code != 200,
        "refresh token": None,   # gere a part (rotation)
        "access token, validation locale": lambda: call("GET", "/docs", access, "local").status_code == 401,
        "access token, introspection": lambda: call("GET", "/docs", access, "introspect").status_code == 401,
    }
    delays = {}
    cur_refresh = refresh_tok
    while len(delays) < len(pending) and time.monotonic() - t0 < args.timeout:
        for name, test in pending.items():
            if name in delays:
                continue
            if name == "refresh token":
                r = refresh(cur_refresh)
                if r.status_code == 200:
                    cur_refresh = r.json()["refresh_token"]   # rotation : il faut utiliser le nouveau
                    blocked = False
                else:
                    blocked = True
            else:
                blocked = test()
            if blocked:
                delays[name] = time.monotonic() - t0
        time.sleep(1)

    lines = ["| Element | Delai apres desactivation |", "|---|---|"]
    for name in pending:
        lines.append(f"| {name} | " + (f"{delays[name]:.1f} s" if name in delays else f"> {args.timeout} s (toujours valide)") + " |")
    table = "\n".join(lines)
    print("\n" + table)

    group_line = ("non propage en 30 s (cache Keycloak)" if delay_new_roles is None
                  else f"{delay_new_roles:.1f} s")
    out = f"Retrait des groupes LDAP -> nouveau jeton sans groupe : {group_line}\n\n" + table
    (RESULTS / "depart.md").write_text(out, encoding="utf-8")
    print(f"\nEcrit dans {RESULTS / 'depart.md'}")
    print("Remise a l'etat initial...")
    reset()


if __name__ == "__main__":
    main()
