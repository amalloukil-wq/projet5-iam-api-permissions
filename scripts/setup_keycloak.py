"""Configure Keycloak automatiquement (realm, clients, scopes, federation LDAP, groupes).

Usage : python scripts/setup_keycloak.py [--access-lifespan 120] [--ldap-cache NO_CACHE|DEFAULT]
Le script est rejouable : il supprime et recree le realm 'examen'.
"""
import argparse
import os
import sys
import time

import requests

from config import GROUPS_DN, LDAP_BIND_DN, LDAP_BIND_PW, LDAP_URL, MANAGER, PASSWORD, PEOPLE_DN

KC = os.getenv("KC_URL", "http://localhost:8080")
REALM = "examen"

_tok = {"v": None, "t": 0}


def headers():
    if time.time() - _tok["t"] > 40:
        r = requests.post(
            f"{KC}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli",
                  "username": "admin", "password": "admin"}, timeout=10)
        r.raise_for_status()
        _tok["v"], _tok["t"] = r.json()["access_token"], time.time()
    return {"Authorization": "Bearer " + _tok["v"]}


def api(method, path, ok=(200, 201, 204), **kw):
    r = requests.request(method, f"{KC}/admin/realms{path}", headers=headers(), timeout=60, **kw)
    if r.status_code not in ok:
        print(f"ERREUR {method} {path} -> {r.status_code}\n{r.text}")
        sys.exit(1)
    return r


def created_id(resp):
    return resp.headers["Location"].rstrip("/").split("/")[-1]


def wait_keycloak():
    print("Attente de Keycloak (jusqu'a 3 min)...")
    for _ in range(90):
        try:
            if requests.get(f"{KC}/realms/master", timeout=3).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    sys.exit("Keycloak ne repond pas sur http://localhost:8080")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--access-lifespan", type=int, default=120, help="duree de l'access token en secondes")
    ap.add_argument("--ldap-url", default=LDAP_URL, help="URL de l'annuaire LDAP vue par Keycloak (TP : ApacheDS, port 10389)")
    ap.add_argument("--ldap-cache", default="NO_CACHE", choices=["NO_CACHE", "DEFAULT"],
                    help="NO_CACHE : groupes LDAP relus a chaque jeton ; DEFAULT : cache Keycloak (retrait de groupe non vu)")
    args = ap.parse_args()

    wait_keycloak()

    print("1. Realm")
    api("DELETE", f"/{REALM}", ok=(204, 404))
    api("POST", "", json={
        "realm": REALM, "enabled": True, "sslRequired": "none",
        "accessTokenLifespan": args.access_lifespan,
        "ssoSessionIdleTimeout": 1800, "ssoSessionMaxLifespan": 36000,
        "revokeRefreshToken": True,      # rotation du refresh token
        "refreshTokenMaxReuse": 0,
    })
    realm_id = api("GET", f"/{REALM}").json()["id"]

    print("2. Clients")
    web = {"enabled": True, "publicClient": True, "standardFlowEnabled": True,
           "directAccessGrantsEnabled": True,   # direct grant : uniquement pour automatiser les tests
           "redirectUris": ["http://localhost:4200/*", "http://localhost:8081/*", "https://oauth.pstmn.io/v1/callback"],
           "webOrigins": ["+"]}
    clients = {
        "webapp": {**web, "clientId": "webapp", "attributes": {"pkce.code.challenge.method": "S256"}},
        "other": {**web, "clientId": "other"},   # client SANS audience api-examen (test du controle aud)
        "batch": {"clientId": "batch", "enabled": True, "publicClient": False, "secret": "batch-secret",
                  "serviceAccountsEnabled": True, "standardFlowEnabled": False,
                  "directAccessGrantsEnabled": False},
        "api": {"clientId": "api", "enabled": True, "publicClient": False, "secret": "api-secret",
                "standardFlowEnabled": False, "directAccessGrantsEnabled": False},
    }
    cid = {}
    for name, rep in clients.items():
        cid[name] = created_id(api("POST", f"/{REALM}/clients", json=rep))

    groups_mapper = {"name": "groups", "protocol": "openid-connect",
                     "protocolMapper": "oidc-group-membership-mapper",
                     "config": {"claim.name": "groups", "full.path": "false", "access.token.claim": "true",
                                "id.token.claim": "true", "userinfo.token.claim": "true"}}
    aud_mapper = {"name": "aud-api-examen", "protocol": "openid-connect",
                  "protocolMapper": "oidc-audience-mapper",
                  "config": {"included.custom.audience": "api-examen", "access.token.claim": "true",
                             "id.token.claim": "false"}}
    for name in ("webapp", "other", "batch"):
        api("POST", f"/{REALM}/clients/{cid[name]}/protocol-mappers/models", json=groups_mapper)
    for name in ("webapp", "batch"):
        api("POST", f"/{REALM}/clients/{cid[name]}/protocol-mappers/models", json=aud_mapper)

    print("3. Scopes du client (docs:read / docs:write / docs:delete)")
    for s in ("docs:read", "docs:write", "docs:delete"):
        api("POST", f"/{REALM}/client-scopes", json={
            "name": s, "protocol": "openid-connect",
            "attributes": {"include.in.token.scope": "true", "display.on.consent.screen": "false"}})
    sid = {s["name"]: s["id"] for s in api("GET", f"/{REALM}/client-scopes").json()}
    grants = {"webapp": ["docs:read", "docs:write", "docs:delete"],
              "other": ["docs:read"],
              "batch": ["docs:read"]}          # le job planifie ne peut que lire
    for client, scopes in grants.items():
        for s in scopes:
            api("PUT", f"/{REALM}/clients/{cid[client]}/default-client-scopes/{sid[s]}")

    print("4. Federation LDAP")
    ldap_cfg = {
        "enabled": ["true"], "priority": ["0"], "editMode": ["UNSYNCED"], "vendor": ["other"],
        "usernameLDAPAttribute": ["uid"], "rdnLDAPAttribute": ["uid"], "uuidLDAPAttribute": ["entryUUID"],
        "userObjectClasses": ["inetOrgPerson"], "connectionUrl": [args.ldap_url],
        "usersDn": [PEOPLE_DN], "authType": ["simple"],
        "bindDn": [LDAP_BIND_DN], "bindCredential": [LDAP_BIND_PW],
        "searchScope": ["1"], "validatePasswordPolicy": ["false"], "importEnabled": ["true"],
        "syncRegistrations": ["false"], "pagination": ["true"], "connectionPooling": ["true"],
        "cachePolicy": [args.ldap_cache], "fullSyncPeriod": ["-1"], "changedSyncPeriod": ["-1"],
    }
    ldap_id = created_id(api("POST", f"/{REALM}/components", json={
        "name": "ldap", "providerId": "ldap", "providerType": "org.keycloak.storage.UserStorageProvider",
        "parentId": realm_id, "config": ldap_cfg}))

    mapper_type = "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"

    def attr_mapper(name, model, ldap_attr, mandatory="false"):
        api("POST", f"/{REALM}/components", json={
            "name": name, "providerId": "user-attribute-ldap-mapper", "providerType": mapper_type,
            "parentId": ldap_id, "config": {
                "user.model.attribute": [model], "ldap.attribute": [ldap_attr], "read.only": ["true"],
                "always.read.value.from.ldap": ["false"], "is.mandatory.in.ldap": [mandatory]}})

    attr_mapper("username", "username", "uid", "true")
    attr_mapper("email", "email", "mail")
    attr_mapper("first name", "firstName", "givenName", "true")
    attr_mapper("last name", "lastName", "sn", "true")

    gm_id = created_id(api("POST", f"/{REALM}/components", json={
        "name": "groupes-ldap", "providerId": "group-ldap-mapper", "providerType": mapper_type,
        "parentId": ldap_id, "config": {
            "groups.dn": [GROUPS_DN], "group.name.ldap.attribute": ["cn"],
            "group.object.classes": ["groupOfNames"], "preserve.group.inheritance": ["false"],
            "ignore.missing.groups": ["true"], "membership.ldap.attribute": ["member"],
            "membership.attribute.type": ["DN"], "membership.user.ldap.attribute": ["uid"],
            "groups.ldap.filter": [""], "mode": ["LDAP_ONLY"],
            "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
            "mapped.group.attributes": [""], "drop.non.existing.groups.during.sync": ["false"]}}))

    print("5. Synchronisation des groupes et des utilisateurs depuis LDAP")
    api("POST", f"/{REALM}/user-storage/{ldap_id}/mappers/{gm_id}/sync?direction=fedToKeycloak")
    r = api("POST", f"/{REALM}/user-storage/{ldap_id}/sync?action=triggerFullSync")
    print("   ", r.text.strip())

    print(f"6. Verification : connexion de {MANAGER}")
    r = requests.post(f"{KC}/realms/{REALM}/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": "webapp", "username": MANAGER,
        "password": PASSWORD, "scope": "openid"}, timeout=15)
    if r.status_code != 200:
        sys.exit(f"Connexion {MANAGER} impossible : {r.status_code} {r.text}")
    from common import decode
    claims = decode(r.json()["access_token"])
    print("    groups =", claims.get("groups"), "| scope =", claims.get("scope"), "| aud =", claims.get("aud"))
    if "Admins" not in (claims.get("groups") or []):
        print("ATTENTION : le claim 'groups' ne contient pas 'Admins'. Verifiez la federation LDAP dans la console Keycloak.")
    print("\nOK. Console Keycloak : http://localhost:8080 (admin/admin), realm 'examen'.")


if __name__ == "__main__":
    main()
