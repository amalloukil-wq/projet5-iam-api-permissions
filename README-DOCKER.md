# Lancer le projet avec Docker (une seule commande)

Tout le projet tourne dans des conteneurs : annuaire LDAP, base PostgreSQL, Keycloak, API Spring Boot (Java 25) et application Angular. Aucun autre outil n'est à installer.

## Pré-requis
- **Docker Desktop** (ou Docker Engine + le plugin Compose), démarré.
- Les ports **8080, 8000, 4200, 1389 et 5434** doivent être libres sur la machine.
- Une connexion internet pour la première construction (téléchargement des images et des dépendances).

## 1. Démarrer

### Option A : avec les images fournies (rapide, recommandé)
Le fichier `examen-images-1.0.tar.gz` contient les trois images du projet (`examen-backend`, `examen-frontend`, `examen-tools`), déjà construites. Dans le dossier du projet :
```
docker load -i examen-images-1.0.tar.gz
docker compose up -d --no-build
```
Vérification de l'archive (facultatif), son empreinte SHA-256 est dans `examen-images-1.0.tar.gz.sha256` :
```
Get-FileHash examen-images-1.0.tar.gz -Algorithm SHA256      # PowerShell
sha256sum examen-images-1.0.tar.gz                           # Linux / macOS
```
Docker télécharge seulement les images officielles de PostgreSQL, OpenLDAP et Keycloak (connexion internet nécessaire la première fois).

### Option B : construire les images depuis les sources
```
docker compose up -d --build
```
La première fois, la construction prend plusieurs minutes (Maven et npm téléchargent leurs dépendances). Ensuite, le démarrage est rapide.

Le service `setup` configure Keycloak tout seul (realm, clients, scopes, fédération LDAP, groupes), puis s'arrête. Pour vérifier qu'il a réussi :
```
docker compose logs setup
```
La fin doit contenir `5 imported users` et `groups = ['Admins', 'Staff']`.

## 2. Utiliser l'application
| Adresse | Contenu | Identifiants |
|---|---|---|
| http://localhost:4200 | l'application Angular | `amartin`, `bdupont` ou `epetit` / mot de passe `secret` |
| http://localhost:8080 | console Keycloak, realm `examen` | `admin` / `admin` |
| http://localhost:8000/metrics | l'API | |

| Compte | Groupe LDAP | Rôle dans l'API |
|---|---|---|
| amartin | Admins | manager (tout) |
| bdupont | Developers | editor (écrit, supprime ses documents) |
| epetit | Staff | reader (lit seulement) |

## 3. Lancer les tests
Les tests tournent dans un conteneur dédié, qui écrit ses résultats dans `resultats/` :
```
docker compose run --rm tools python scripts/tests_matrix.py
docker compose run --rm tools python scripts/bench.py
docker compose run --rm tools python scripts/revocation.py
docker compose run --rm tools python scripts/depart.py
```
- `tests_matrix.py` : matrice 200/201/401/403, attendu **56/56 conformes**.
- `bench.py` : validation locale du jeton contre introspection (temps de réponse, appels à Keycloak).
- `revocation.py` : effet de la révocation (RFC 7009).
- `depart.py` : protocole de départ de l'employé bdupont (2 à 3 minutes), avec les délais mesurés.

**Rejouer le départ pas à pas, dans l'application.** Connecter `bdupont` sur http://localhost:4200, puis lancer ces commandes l'une après l'autre en regardant ce qui change (jeton local contre introspection, renouvellement, nouvelle connexion) :
```
docker compose run --rm tools python scripts/depart_manuel.py retirer       # retire bdupont de ses groupes LDAP
docker compose run --rm tools python scripts/depart_manuel.py desactiver    # désactive son compte Keycloak
docker compose run --rm tools python scripts/depart_manuel.py restaurer     # remet tout en état
```
Astuce : le jeton dure 2 minutes ; pour avoir le temps de manipuler, lancer d'abord
`docker compose run --rm tools python scripts/setup_keycloak.py --access-lifespan 600` (10 minutes), puis la même commande sans option pour revenir à 2 minutes.

Ajouter un utilisateur (identifiant, prénom, nom, groupe, mot de passe) :
```
docker compose run --rm tools python scripts/ajouter_utilisateur.py fmoreau Farid Moreau Developers secret
```

## 4. Voir l'annuaire
L'annuaire est accessible sur `ldap://localhost:1389`, suffixe `dc=examen,dc=local`, administrateur `cn=admin,dc=examen,dc=local` / `admin`. On peut s'y connecter avec Apache Directory Studio (hôte `localhost`, port `1389`).

## 5. Arrêter et nettoyer
```
docker compose down        # arrête tout, conserve la base PostgreSQL
docker compose down -v     # arrête tout et efface aussi les données
```

## Remarques
- Dans Docker, l'annuaire est **OpenLDAP** avec les mêmes fichiers LDIF que l'ApacheDS du projet (mêmes employés, mêmes groupes, même suffixe). Le reste du projet ne voit aucune différence.
- Les jetons portent `iss = http://localhost:8080` (adresse du navigateur) ; les conteneurs joignent Keycloak par `http://keycloak:8080`. L'API gère cette différence avec les variables `APP_KC_URL` et `APP_KC_INTERNAL_URL`.
- Les routes `/_reset` et `/metrics` et le paramètre `?mode=` de l'API sont réservés à la démonstration.

## Dépannage
| Symptôme | Cause probable | Solution |
|---|---|---|
| `port is already allocated` | un autre programme utilise un port | le fermer, ou changer le port à gauche dans `docker-compose.yml` |
| Connexion impossible, 401 partout | le service `setup` n'a pas fini | `docker compose logs setup`, puis `docker compose up -d setup` |
| `groups` vide | l'annuaire n'était pas prêt | `docker compose restart ldap`, puis `docker compose up -d setup` |
| L'application affiche « reseau » | l'API n'est pas démarrée | `docker compose logs backend` |
| Un test échoue juste après le démarrage | Keycloak ou l'API terminent leur démarrage | attendre une minute et relancer la commande |
