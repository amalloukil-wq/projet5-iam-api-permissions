# Projet 5 IAM : API à permissions fines et départ d'un employé

Keycloak + annuaire LDAP + API Spring Boot (Java 25) + application Angular (Code + PKCE) + PostgreSQL, le tout en Docker.

## Lancer

```
docker compose up -d --build
```

Puis ouvrir http://localhost:4200 (compte `amartin`, mot de passe `secret`). Console Keycloak : http://localhost:8080 (`admin` / `admin`).

## Contenu

- docker-compose.yml : annuaire LDAP (OpenLDAP), base PostgreSQL, Keycloak, API, application, outils de test
- ldif/ : annuaire (utilisateurs et groupes)
- apps/ : API Spring Boot (backend/), application Angular (frontend/), scripts Python de configuration, de test et de mesure (scripts/), lancement local sans Docker (demarrage/)
- docs/ : rapport PDF, énoncé, guides, résultats des mesures

## Comptes de test

| Compte | Groupe LDAP | Rôle dans l'API |
|---|---|---|
| amartin | Admins | manager (tout) |
| bdupont | Developers | editor (écrit, supprime ses documents) |
| epetit | Staff | reader (lit seulement) |

## Tests

```
docker compose run --rm tools python scripts/tests_matrix.py
docker compose run --rm tools python scripts/depart.py
```

La matrice doit donner 56/56. `depart.py` mesure ce qu'il reste d'accès à un employé après son départ. Les autres commandes sont décrites dans docs/README-DOCKER.md (Docker) et docs/LANCER-EN-LOCAL.md (sans Docker, avec ApacheDS).

Les mots de passe du dépôt sont des mots de passe de démonstration, à ne jamais réutiliser.
