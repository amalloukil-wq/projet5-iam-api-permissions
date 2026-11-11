"""Gere un utilisateur existant : desactiver, reactiver ou supprimer.

Usage : python scripts/gerer_utilisateur.py <identifiant> <action>
  desactiver   desactive le compte dans Keycloak (l'employe reste dans l'annuaire)
  reactiver    reactive le compte
  supprimer    retire l'employe de ses groupes, le supprime de l'annuaire LDAP, puis de Keycloak

Exemples :
  python scripts/gerer_utilisateur.py amal desactiver
  python scripts/gerer_utilisateur.py amal reactiver
  python scripts/gerer_utilisateur.py amal supprimer

Avec Docker : docker compose run --rm tools python scripts/gerer_utilisateur.py amal desactiver
"""
import os
import sys

import requests
from ldap3 import MODIFY_DELETE, Connection, Server

from config import GROUPS_DN, LDAP_BIND_DN, LDAP_BIND_PW, LDAP_HOST, LDAP_PORT, PEOPLE_DN

KC = os.getenv("KC_URL", "http://localhost:8080")
ADMIN = f"{KC}/admin/realms/examen"
ACTIONS = {"desactiver", "reactiver", "supprimer"}

if len(sys.argv) != 3 or sys.argv[2] not in ACTIONS:
    raise SystemExit(__doc__)
uid, action = sys.argv[1], sys.argv[2]
dn = f"uid={uid},{PEOPLE_DN}"


def kc_headers():
    r = requests.post(f"{KC}/realms/master/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"}, timeout=10)
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def kc_user(h):
    """Fiche Keycloak de l'utilisateur (Keycloak l'importe depuis l'annuaire si besoin)."""
    r = requests.get(f"{ADMIN}/users", params={"username": uid, "exact": "true"}, headers=h, timeout=15)
    r.raise_for_status()
    return r.json()[0] if r.json() else None


def ldap_connexion():
    return Connection(Server(LDAP_HOST, port=LDAP_PORT), user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=True)


if action in ("desactiver", "reactiver"):
    h = kc_headers()
    u = kc_user(h)
    if not u:
        raise SystemExit(f"Utilisateur '{uid}' introuvable (existe-t-il dans l'annuaire ?).")
    u = requests.get(f"{ADMIN}/users/{u['id']}", headers=h, timeout=15).json()
    u["enabled"] = (action == "reactiver")
    requests.put(f"{ADMIN}/users/{u['id']}", json=u, headers=h, timeout=15).raise_for_status()
    print(f"OK : le compte {uid} est {'reactive' if u['enabled'] else 'desactive'} dans Keycloak")

else:  # supprimer
    conn = ldap_connexion()
    if not conn.search(dn, "(objectClass=*)", search_scope="BASE"):
        raise SystemExit(f"Utilisateur '{uid}' introuvable dans l'annuaire ({dn}).")
    conn.search(GROUPS_DN, f"(member={dn})", attributes=["cn"])
    for g in list(conn.entries):
        ok = conn.modify(g.entry_dn, {"member": [(MODIFY_DELETE, [dn])]})
        print(f"{'OK ' if ok else 'ECHEC'} retire du groupe {g.cn}" +
              ("" if ok else f" : {conn.result['description']} (un groupe doit garder au moins un membre)"))
        if not ok:
            raise SystemExit("Suppression arretee : l'utilisateur est le dernier membre d'un groupe.")
    if not conn.delete(dn):
        raise SystemExit(f"Suppression LDAP impossible : {conn.result['description']}")
    print(f"OK : {dn} supprime de l'annuaire")
    conn.unbind()
    h = kc_headers()
    u = kc_user(h)
    if u:
        r = requests.delete(f"{ADMIN}/users/{u['id']}", headers=h, timeout=15)
        print(f"{'OK' if r.status_code in (200, 204) else 'ATTENTION'} : fiche Keycloak supprimee (code {r.status_code})")
    else:
        print("OK : aucune fiche Keycloak a supprimer")
