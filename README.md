# Projet 5 : API à permissions et départ d'un employé

Keycloak (OIDC / OAuth 2.0) + **annuaire LDAP ApacheDS (Apache Directory Studio)** + **API Spring Boot 4.1 (Java 25)** + **frontend Angular** + **PostgreSQL**. Tout tourne en local, sans Docker.

```
Angular (Code + PKCE) --> Keycloak --> ApacheDS (examen : utilisateurs, groupes)
Angular --Bearer--> API Spring Boot --> PostgreSQL (documents)
                       |-- JWKS ou introspection --> Keycloak
```

## L'annuaire LDAP (serveur ApacheDS `Examen`)

| Paramètre | Valeur |
|---|---|
| Serveur | ApacheDS (serveur intégré d'Apache Directory Studio 2.0.0-M17), `localhost:10389`, sans chiffrement |
| Administrateur | `uid=admin,ou=system` / `secret` |
| Suffixe | `dc=examen,dc=local` (partition `examen`) |
| Utilisateurs | `ou=People,dc=examen,dc=local` : amartin, bdupont, cdurand, dbernard, epetit (mot de passe `secret`) |
| Groupes | `ou=Groups,dc=examen,dc=local` : Admins (amartin), Developers (bdupont, cdurand), Staff (les 5) |

Dans Studio : créer le serveur ApacheDS `Examen` (*LDAP Servers* > *New Server* > *ApacheDS 2.0.0*), puis sa partition (*Open Configuration* > *Partitions* > *Add* : ID `examen`, suffixe `dc=examen,dc=local`, enregistrer, *Stop* puis *Run*), puis importez les 3 fichiers du dossier `ldap/` dans cet ordre :
```
ldapadd -x -H ldap://localhost:10389 -D "uid=admin,ou=system" -w secret -f ldap/base.ldif
ldapadd -x -H ldap://localhost:10389 -D "uid=admin,ou=system" -w secret -f ldap/users.ldif
ldapadd -x -H ldap://localhost:10389 -D "uid=admin,ou=system" -w secret -f ldap/groups.ldif
```
(ou dans Studio : clic droit sur la partition > *Import* > *LDIF Import*). **Plus simple : `python scripts/preparer_ldap.py`** charge les 3 fichiers dans l'ordre (sans `ldap-utils`, et sans danger si on le relance). Vérifier : `python scripts/voir_ldap.py`.

**ApacheDS de Studio avec Java 25** : le TP exigeait Java 11 ; avec Java 25 le serveur s'arrêtait juste après « En cours ». `.\demarrage\reparer-studio-java25.ps1` corrige cela (option `--add-exports` pour Java, fichier de clés fourni à ApacheDS, LDAPS/StartTLS désactivés) puis relance Studio. À lancer **une fois après avoir créé le serveur** dans Studio, avant *Run* ; à relancer si le serveur s'arrête de nouveau après une modification de sa configuration (ex. ajout de la partition). Studio doit toujours être lancé par ce script (il fournit l'option Java au serveur).

**ApacheDS dans WSL (Ubuntu)** : Keycloak et les scripts tournent sous Windows et joignent `localhost:10389` grâce à la redirection de ports de WSL ; lancer `python scripts/voir_ldap.py` pour le vérifier. **Annuaire de secours** : si ApacheDS n'est pas disponible, `.\demarrage\lancer-ldap-secours.ps1` démarre un annuaire en Java avec exactement les mêmes paramètres et données (le reste du projet ne voit aucune différence ; les modifications sont perdues à l'arrêt). Ne pas lancer les deux en même temps.

## Comptes de test (mot de passe `secret` pour tous)

| Utilisateur | Groupe LDAP | Rôle dans l'API |
|---|---|---|
| amartin (Alice Martin, CEO) | Admins (+ Staff) | manager |
| bdupont (Bob Dupont, Lead Developer) | Developers (+ Staff) | editor |
| epetit (Emma Petit, Support Engineer) | Staff | reader |

## 1. Outils (une seule fois)

```powershell
.\demarrage\installer-outils.ps1
```
Installe **une seule version de Java, la 25** (backend Spring Boot 4.1, Keycloak 26.6 et annuaire de secours), Node 22 (Angular), Python 3.12 (scripts), PostgreSQL 16 (port 5433, base `docs`), Maven et Keycloak 26.6.0 (Keycloak 25 ne tourne pas sur Java 25, d'où la version 26.6). Seul le **serveur ApacheDS intégré à Studio M17** demande Java 11 d'après le TP : s'il ne démarre pas avec Java 25, utiliser l'annuaire de secours. Des fenêtres d'autorisation administrateur apparaissent : cliquer sur **Oui**. Si le réseau coupe, relancer le script (il reprend où il s'est arrêté). Ensuite, **fermer et rouvrir PowerShell**. Apache Directory Studio se télécharge sur directory.apache.org (vous l'avez déjà utilisé au TP).

Java 25 est installé sous la forme d'« Amazon Corretto 25 », une distribution gratuite d'OpenJDK (équivalente à Temurin, mais téléchargeable même quand GitHub est bloqué). Ce n'est pas le logiciel Eclipse.

## 2. Préparer Python (une seule fois)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Lancer (4 fenêtres, à laisser ouvertes)

| Étape | Commande | Prêt quand |
|---|---|---|
| 1 | Studio : onglet *LDAP Servers* > serveur `Examen` > clic droit > **Run** | état *Started* |
| 2 | `.\demarrage\lancer-keycloak.ps1` | Keycloak répond sur http://localhost:8080 (~1 min) |
| 3 | `python scripts/setup_keycloak.py` puis `.\demarrage\lancer-backend.ps1` | `Started ApiApplication` |
| 4 | `.\demarrage\lancer-frontend.ps1` | http://localhost:4200 (la 1re fois, génère Angular : internet requis) |

PostgreSQL tourne tout seul (service Windows). L'annuaire doit être démarré **avant** `setup_keycloak.py`.

## 4. Tester

- Navigateur : http://localhost:4200 → `amartin`, `bdupont` ou `epetit` (mot de passe `secret`).
- Scripts (avec le venv activé) :
```powershell
python scripts/tests_matrix.py     # matrice 200/201/401/403 (56 cas)
python scripts/bench.py            # local vs introspection
python scripts/revocation.py       # RFC 7009
python scripts/depart.py           # départ de bdupont : retrait des groupes + désactivation, délais mesurés (~2-4 min)
python scripts/depart_manuel.py retirer       # départ pas à pas : retire bdupont de ses groupes (puis : desactiver, restaurer)
python scripts/gerer_utilisateur.py amal desactiver   # desactiver / reactiver / supprimer un utilisateur quelconque
python scripts/voir_ldap.py        # contenu de l'annuaire (pour les captures)
python scripts/ajouter_utilisateur.py fmoreau Farid Moreau Developers secret   # nouvel utilisateur (uid prénom nom groupe mot_de_passe)
```
Les résultats sont écrits dans `resultats/*.md`, à copier dans `rapport.md`.

Ajouter un utilisateur peut aussi se faire dans Studio (comme au TP : *New Entry* sous `ou=People`, puis ajouter son DN dans `member` du groupe). Il peut se connecter tout de suite ; si c'est un **nouveau groupe**, cliquer sur *Sync LDAP groups to Keycloak* (Keycloak > User federation > ldap > Mappers > groupes-ldap) et ajouter son rôle dans `GROUP_TO_ROLE` (`backend/.../AuthService.java`).

Console Keycloak : http://localhost:8080 (admin / admin), realm `examen`.
Contenu de PostgreSQL :
```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -p 5433 -U docs -d docs -c "select * from docs;"
```
(mot de passe : `docs`).

## Modèle d'autorisation

| Route | Scope | Rôles (groupe LDAP) | Propriété |
|---|---|---|---|
| GET /docs | docs:read | reader (Staff), editor (Developers), manager (Admins), service (batch) | |
| POST /docs | docs:write | editor, manager | |
| DELETE /docs/{id} | docs:delete | editor, manager | editor : ses documents seulement |

Clients Keycloak : `webapp` (Code + PKCE), `batch` (Client Credentials, `docs:read` seulement), `api` (introspection), `other` (sans audience, teste `aud`).

Fichiers clés : `backend/src/main/java/exam/api/AuthService.java` (validation du jeton, scope, rôle), `DocController.java` (routes), `frontend/overrides/src/app/auth.service.ts` (PKCE), `scripts/config.py` (paramètres LDAP et comptes de test).

## À savoir

- **Cache Keycloak** : `setup_keycloak.py` règle la fédération LDAP en `NO_CACHE`. Avec `--ldap-cache DEFAULT`, Keycloak garde les groupes en cache et un retrait de groupe dans LDAP n'est plus vu par les nouveaux jetons (à reproduire et expliquer dans le rapport).
- **`groupOfNames` exige au moins un `member`** : on ne peut pas retirer le dernier membre d'un groupe (ex. amartin de Admins). Le script de départ utilise donc bdupont (Developers a 2 membres, Staff 5).
- Les routes `/_reset`, `/metrics` et le paramètre `?mode=` de l'API sont réservés à la démonstration.
- Autre annuaire ou autres identifiants : variables d'environnement `LDAP_HOST`, `LDAP_PORT`, `LDAP_BIND_DN`, `LDAP_BIND_PW`, `LDAP_BASE` (lues par `scripts/config.py`) et option `--ldap-url` de `setup_keycloak.py`.

## Dépannage

- `groups` vide dans le jeton : vérifier l'annuaire avec `python scripts/voir_ldap.py`, puis relancer `python scripts/setup_keycloak.py`.
- `voir_ldap.py` ne se connecte pas : ApacheDS n'est pas à l'état *Started*, ou la partition `examen` n'existe pas (voir plus haut).
- Le frontend affiche « reseau » : l'API n'est pas démarrée.
- Erreur PostgreSQL : le service `postgresql-x64-16` doit être démarré (port 5433).
- Script bloqué par la politique d'exécution : `Set-ExecutionPolicy -Scope Process Bypass` puis relancer.
