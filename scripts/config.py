"""Parametres communs : annuaire LDAP (ApacheDS) et comptes de test.

Valeurs : serveur ApacheDS sur localhost:10389, administrateur uid=admin,ou=system / secret,
suffixe dc=examen,dc=local, utilisateurs sous ou=People, groupes sous ou=Groups.
Chaque valeur peut etre changee par une variable d'environnement (ex. $env:LDAP_PORT = "1389").
"""
import os

LDAP_HOST = os.getenv("LDAP_HOST", "localhost")
LDAP_PORT = int(os.getenv("LDAP_PORT", "10389"))
LDAP_URL = f"ldap://{LDAP_HOST}:{LDAP_PORT}"
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "uid=admin,ou=system")
LDAP_BIND_PW = os.getenv("LDAP_BIND_PW", "secret")
LDAP_BASE = os.getenv("LDAP_BASE", "dc=examen,dc=local")
PEOPLE_DN = f"ou=People,{LDAP_BASE}"
GROUPS_DN = f"ou=Groups,{LDAP_BASE}"

# Comptes de test (mot de passe "secret", comme dans le TP)
PASSWORD = "secret"
MANAGER = "amartin"      # Alice Martin, groupe Admins      -> role manager
EDITOR = "bdupont"       # Bob Dupont, groupe Developers    -> role editor
READER = "epetit"        # Emma Petit, groupe Staff seulement -> role reader

# Employe qui "part" dans depart.py : retire de ces groupes dans LDAP
DEPART_USER = EDITOR
DEPART_GROUPS = ["Developers", "Staff"]
