"""Revocation RFC 7009 : que devient chaque jeton apres revocation ?

Usage : python apps/scripts/revocation.py
Resultat : affichage + docs/resultats/revocation.md
"""
import requests

from common import KC, REALM, RESULTS, call, refresh, tokens
from config import EDITOR

REVOKE = f"{KC}/realms/{REALM}/protocol/openid-connect/revoke"


def revoke(token, hint):
    return requests.post(REVOKE, data={"client_id": "webapp", "token": token,
                                       "token_type_hint": hint}, timeout=10).status_code


rows = []

# Cas 1 : revocation du refresh token
t = tokens(EDITOR)
code = revoke(t["refresh_token"], "refresh_token")
rows.append(("Revocation du refresh token", f"endpoint -> {code}",
             f"refresh -> {refresh(t['refresh_token']).status_code}",
             f"access local -> {call('GET', '/docs', t['access_token'], 'local').status_code}",
             f"access introspection -> {call('GET', '/docs', t['access_token'], 'introspect').status_code}"))

# Cas 2 : revocation de l'access token
t = tokens(EDITOR)
code = revoke(t["access_token"], "access_token")
rows.append(("Revocation de l'access token", f"endpoint -> {code}",
             f"refresh -> {refresh(t['refresh_token']).status_code}",
             f"access local -> {call('GET', '/docs', t['access_token'], 'local').status_code}",
             f"access introspection -> {call('GET', '/docs', t['access_token'], 'introspect').status_code}"))

lines = ["| Action | Endpoint /revoke | Refresh ensuite | Access (local) | Access (introspection) |",
         "|---|---|---|---|---|"] + ["| " + " | ".join(r) + " |" for r in rows]
text = "\n".join(lines)
print(text)
(RESULTS / "revocation.md").write_text(text, encoding="utf-8")
print(f"\nEcrit dans {RESULTS / 'revocation.md'}")
