"""Charge les donnees du TP (ldif/base.ldif, users.ldif, groups.ldif) dans l'annuaire ApacheDS.

Equivalent des trois commandes ldapadd du TP, sans avoir besoin d'ldap-utils ni de l'assistant
d'import de Studio. Sans danger si on le relance : une entree deja presente est simplement ignoree.

Pre-requis : dans Studio, le serveur ApacheDS est demarre (Started) ET la partition
  ID `examen`, suffixe `dc=examen,dc=local` existe (voir README, etapes 1 a 3).
Usage : python apps/scripts/preparer_ldap.py
"""
import sys
from pathlib import Path

from ldap3 import Connection, Server

from config import LDAP_BASE, LDAP_BIND_DN, LDAP_BIND_PW, LDAP_HOST, LDAP_PORT, LDAP_URL

LDIF_DIR = Path(__file__).resolve().parents[2] / "ldif"   # racine du depot / ldif
FILES = ["base.ldif", "users.ldif", "groups.ldif"]      # dans cet ordre : OU, puis utilisateurs, puis groupes


def parse_ldif(path: Path):
    """Lit un fichier LDIF simple (entrees separees par une ligne vide). Retourne [(dn, {attribut: [valeurs]})]."""
    entries, current = [], []
    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        if line.startswith("#"):
            continue
        if line.strip():
            current.append(line)
            continue
        if current:
            dn, attrs = None, {}
            for l in current:
                key, _, value = l.partition(":")
                value = value.strip()
                if key.lower() == "dn":
                    dn = value
                else:
                    attrs.setdefault(key, []).append(value)
            entries.append((dn, attrs))
            current = []
    return entries


def main():
    try:
        conn = Connection(Server(LDAP_HOST, port=LDAP_PORT), user=LDAP_BIND_DN, password=LDAP_BIND_PW, auto_bind=True)
    except Exception as e:
        sys.exit(f"Connexion impossible a {LDAP_URL} avec {LDAP_BIND_DN} : {e}\n"
                 "-> Dans Studio, le serveur est-il a l'etat Started ? (clic droit sur le serveur > Run)")

    if not conn.search(LDAP_BASE, "(objectClass=*)", search_scope="BASE"):
        sys.exit(f"La partition {LDAP_BASE} n'existe pas encore.\n"
                 "-> Studio : clic droit sur le serveur > Open Configuration > Partitions > Add\n"
                 f"   ID: examen ; Suffix: {LDAP_BASE} ; Ctrl+S ; puis Stop et Run du serveur. Relancez ce script ensuite.")

    ajoutes = ignores = erreurs = 0
    for name in FILES:
        for dn, attrs in parse_ldif(LDIF_DIR / name):
            classes = attrs.pop("objectClass")
            if conn.add(dn, classes, attrs):
                ajoutes += 1
                print(f"  + {dn}")
            elif conn.result["description"] == "entryAlreadyExists":
                ignores += 1
                print(f"  = {dn} (deja present)")
            else:
                erreurs += 1
                print(f"  ! {dn} -> {conn.result['description']} : {conn.result.get('message', '')}")
    conn.unbind()

    print(f"\n{ajoutes} entree(s) ajoutee(s), {ignores} deja presente(s), {erreurs} erreur(s).")
    if erreurs:
        sys.exit(1)
    print("Verifier le contenu : python apps/scripts/voir_ldap.py")


if __name__ == "__main__":
    main()
