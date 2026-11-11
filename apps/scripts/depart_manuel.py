"""Les etapes du depart de l'employe, UNE PAR UNE, pour la demonstration a la main.

Pendant que l'employe (bdupont) est connecte dans l'application, on lance ces commandes dans un terminal
et on regarde ce qui change dans l'application.

Usage : python apps/scripts/depart_manuel.py <etape>
  retirer      etape 1 : retire bdupont de ses groupes (Developers et Staff) dans l'annuaire LDAP
  desactiver   etape 2 : desactive son compte dans Keycloak
  restaurer    remet tout en etat (groupes et compte)

Avec Docker :  docker compose run --rm tools python scripts/depart_manuel.py retirer
"""
import sys

from depart import DEPART_GROUPS, DEPART_USER, ldap_groups, reset, set_enabled

ETAPES = {"retirer", "desactiver", "restaurer"}
if len(sys.argv) != 2 or sys.argv[1] not in ETAPES:
    raise SystemExit(__doc__)

etape = sys.argv[1]
if etape == "retirer":
    ok, msg = ldap_groups("delete")
    print(f"{'OK' if ok else 'ECHEC'} : {DEPART_USER} retire des groupes {DEPART_GROUPS} ({msg})")
elif etape == "desactiver":
    set_enabled(DEPART_USER, False)
    print(f"OK : le compte {DEPART_USER} est desactive dans Keycloak")
else:
    reset()
    print(f"OK : {DEPART_USER} remis dans ses groupes et compte reactive")
