"""Ajoute un utilisateur dans l'annuaire LDAP, l'ajoute a un groupe existant, puis synchronise Keycloak.

Usage : python scripts/ajouter_utilisateur.py <uid> <prenom> <nom> <groupe> <mot_de_passe>
Exemple : python scripts/ajouter_utilisateur.py fmoreau Farid Moreau Developers secret

Groupes existants : Admins (manager), Developers (editor), Staff (reader).
Equivalent de ce qu'on fait dans Apache Directory Studio (New Entry + member du groupe).
"""
import os
import sys

import requests
from ldap3 import MODIFY_ADD, Connection, Server

from config import GROUPS_DN, LDAP_BIND_DN, LDAP_BIND_PW, LDAP_HOST, LDAP_PORT, PEOPLE_DN

KC = os.getenv("KC_URL", "http://localhost:8080")
REALM = "examen"

if len(sys.argv) != 6:
    raise SystemExit(__doc__)
uid, prenom, nom, groupe, mdp = sys.argv[1:]
dn = f"uid={uid},{PEOPLE_DN}"
group_dn = f"cn={groupe},{GROUPS_DN}"

# --- 1. LDAP ---
try:
    conn = Connection(Server(LDAP_HOST, port=LDAP_PORT), user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=True)
except Exception as e:
    raise SystemExit(f"Connexion LDAP impossible (annuaire lance ?) : {e}")

if not conn.search(group_dn, "(objectClass=groupOfNames)"):
    raise SystemExit(f"Le groupe '{groupe}' n'existe pas (Admins, Developers ou Staff).")
if not conn.add(dn, "inetOrgPerson", {"uid": uid, "cn": f"{prenom} {nom}", "sn": nom, "givenName": prenom,
                                      "displayName": f"{prenom} {nom}", "mail": f"{uid}@examen.local",
                                      "userPassword": mdp}):
    raise SystemExit(f"Ajout impossible : {conn.result['description']} (l'utilisateur existe deja ?)")
conn.modify(group_dn, {"member": [(MODIFY_ADD, [dn])]})
print(f"LDAP : {dn} cree et ajoute au groupe {groupe}")
conn.unbind()

# --- 2. Keycloak : synchronisation ---
r = requests.post(f"{KC}/realms/master/protocol/openid-connect/token", data={
    "grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": "admin"}, timeout=10)
r.raise_for_status()
h = {"Authorization": "Bearer " + r.json()["access_token"]}
A = f"{KC}/admin/realms/{REALM}"

realm_id = requests.get(A, headers=h, timeout=10).json()["id"]
ldap = requests.get(f"{A}/components", headers=h, timeout=10,
                    params={"parent": realm_id, "type": "org.keycloak.storage.UserStorageProvider"}).json()
ldap_id = next(c["id"] for c in ldap if c["name"] == "ldap")
mappers = requests.get(f"{A}/components", headers=h, timeout=10,
                       params={"parent": ldap_id, "type": "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"}).json()
gm_id = next(m["id"] for m in mappers if m["name"] == "groupes-ldap")

requests.post(f"{A}/user-storage/{ldap_id}/mappers/{gm_id}/sync", params={"direction": "fedToKeycloak"},
              headers=h, timeout=60).raise_for_status()
s = requests.post(f"{A}/user-storage/{ldap_id}/sync", params={"action": "triggerFullSync"},
                  headers=h, timeout=60)
s.raise_for_status()
print("Keycloak : synchronisation faite ->", s.json().get("status"))
print(f"\n{uid} peut se connecter (mot de passe : {mdp}) avec le groupe {groupe}.")
