"""Fonctions communes aux scripts de test."""
import base64
import json
import os
from pathlib import Path

import requests

from config import EDITOR, MANAGER, PASSWORD, READER

# Adresses modifiables par variables d'environnement (utile dans Docker : KC_URL=http://keycloak:8080)
KC = os.getenv("KC_URL", "http://localhost:8080")
REALM = "examen"
API = os.getenv("API_URL", "http://localhost:8000")
TOKEN_URL = f"{KC}/realms/{REALM}/protocol/openid-connect/token"
USERS = {MANAGER: PASSWORD, EDITOR: PASSWORD, READER: PASSWORD}
RESULTS = Path(__file__).resolve().parent.parent / "resultats"
RESULTS.mkdir(exist_ok=True)


def decode(token: str) -> dict:
    p = token.split(".")[1]
    p += "=" * (-len(p) % 4)
    return json.loads(base64.urlsafe_b64decode(p))


def login(user: str, client: str = "webapp"):
    """Retourne la reponse brute (pour pouvoir tester les echecs)."""
    return requests.post(TOKEN_URL, data={
        "grant_type": "password", "client_id": client, "username": user,
        "password": USERS[user], "scope": "openid"}, timeout=10)


def tokens(user: str, client: str = "webapp") -> dict:
    r = login(user, client)
    r.raise_for_status()
    return r.json()


def service_token() -> str:
    r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials"},
                      auth=("batch", "batch-secret"), timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def refresh(refresh_token: str, client: str = "webapp"):
    return requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token", "client_id": client, "refresh_token": refresh_token}, timeout=10)


def call(method: str, path: str, token: str | None = None, mode: str = "local", **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.request(method, f"{API}{path}", headers=headers, params={"mode": mode},
                            timeout=10, **kw)
