"""Affiche le contenu de l'annuaire LDAP (utilisateurs et groupes) pour les captures d'ecran.

Usage : python apps/scripts/voir_ldap.py
Pre-requis : l'annuaire ApacheDS du TP tourne sur ldap://localhost:10389.
"""
from ldap3 import Connection, Server

from config import GROUPS_DN, LDAP_BASE, LDAP_BIND_DN, LDAP_BIND_PW, LDAP_HOST, LDAP_PORT, LDAP_URL, PEOPLE_DN

try:
    conn = Connection(Server(LDAP_HOST, port=LDAP_PORT), user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=True)
except Exception as e:
    raise SystemExit(f"Connexion impossible a {LDAP_URL} : {e}\nL'annuaire (ApacheDS) est-il demarre ?")

print(f"Annuaire LDAP : {LDAP_URL}   base : {LDAP_BASE}\n")

print("UTILISATEURS (ou=People)")
conn.search(PEOPLE_DN, "(objectClass=inetOrgPerson)", attributes=["uid", "cn", "title", "mail"])
for e in sorted(conn.entries, key=lambda x: str(x.uid)):
    print(f"  {e.entry_dn}")
    print(f"      uid={e.uid}  nom={e.cn}  titre={e.title}  mail={e.mail}")

print("\nGROUPES (ou=Groups)")
conn.search(GROUPS_DN, "(objectClass=groupOfNames)", attributes=["cn", "member"])
for e in sorted(conn.entries, key=lambda x: str(x.cn)):
    membres = [m.split(",")[0].replace("uid=", "").replace("cn=", "") for m in e.member.values]
    print(f"  {e.cn}  ->  {', '.join(membres)}")
conn.unbind()
