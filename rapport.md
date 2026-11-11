# Projet 5 — API à permissions et départ d'un employé

**Nom :** …  **Date :** …  **Durée :** 2 h

## 1. Contexte et objectif
Un JWT reste accepté par une API après la fin de la session. Ce projet construit une API à permissions fines, puis **mesure** ce qu'il reste d'accès à un employé après son départ.

## 2. Architecture
```
Application web Angular (Code + PKCE) --code, jetons--> Keycloak --utilisateurs, groupes--> ApacheDS (LDAP)
Tâche planifiée (Client Credentials) --jeton de service--> Keycloak
Application / tâche --access token--> API Spring Boot --JWKS ou introspection--> Keycloak
API Spring Boot --> PostgreSQL (documents)
```
Composants : Keycloak 25 (realm `examen`), annuaire LDAP (ApacheDS / Apache Directory Studio, suffixe `dc=examen,dc=local`, `localhost:10389`), API Spring Boot 4.1 (Java 25) avec PostgreSQL 16, frontend Angular (dernière version). Python sert uniquement aux scripts de configuration et de mesure.
*(Insérer captures : console Keycloak, `voir_ldap.py`.)*

## 3. Modèle d'autorisation
- **Scopes du client** : `docs:read`, `docs:write`, `docs:delete` ; `webapp` les a tous, `batch` n'a que `docs:read`.
- **Rôles venant des groupes LDAP** : Admins → manager, Developers → editor, Staff → reader (claim `groups` du jeton, converti en rôle par l'API).
- **Propriété de la ressource** : un `editor` ne supprime que ses propres documents ; un `manager` peut tout supprimer.

| Route | Scope | Rôles | Propriété |
|---|---|---|---|
| GET /docs | docs:read | reader, editor, manager, service | — |
| POST /docs | docs:write | editor, manager | — |
| DELETE /docs/{id} | docs:delete | editor, manager | editor : propriétaire seulement |

*(Capture : clients et scopes dans Keycloak ; jeton décodé dans l'interface Angular.)*

## 4. L'API (Spring Boot + PostgreSQL) et le frontend Angular
Validations : signature (JWKS), `iss`, `aud` = `api-examen`, `exp`, scope, rôle. Deux modes, choisis par `?mode=` :
- **local** : JWT vérifié avec la clé publique, aucun appel réseau ;
- **introspect** : RFC 7662, Keycloak dit si le jeton est encore actif.

Flux : `webapp` (Authorization Code + PKCE S256), `batch` (Client Credentials).
*(Captures : écran de connexion Keycloak, interface Angular avec le journal 200/401/403, contenu de la table `docs` dans PostgreSQL.)*

## 5. Durée des jetons et révocation
- Access token : 120 s (`--access-lifespan`), refresh token avec **rotation** (`revokeRefreshToken`, réutilisation interdite).
- Révocation RFC 7009 : endpoint `/protocol/openid-connect/revoke`.

Résultats de `scripts/revocation.py` :
*(coller `resultats/revocation.md`, puis commenter : quel jeton est réellement invalidé, et à quel endroit ?)*

## 6. Matrice de tests
*(coller `resultats/matrice.md`)*
Commentaire : 401 = jeton absent/invalide/mauvaise audience (identité non établie) ; 403 = identité connue mais scope, rôle ou propriété insuffisant.

## 7. Protocole de départ
Employé qui part : bdupont (Bob Dupont, Lead Developer). Étapes : (1) retrait de ses groupes `Developers` et `Staff` dans LDAP ; (2) désactivation du compte dans Keycloak.

*(coller `resultats/depart.md`)*

| Élément | Délai mesuré | Explication |
|---|---|---|
| Nouvelle connexion | … | Keycloak vérifie l'état du compte à chaque login |
| Refresh token | … | le compte désactivé ne peut plus renouveler |
| Access token, validation locale | … (≈ durée de vie restante) | l'API ne contacte pas Keycloak : le jeton vit jusqu'à `exp` |
| Access token, introspection | … | Keycloak voit le compte désactivé |

Constats à vérifier avec vos mesures :
- Le retrait du groupe ne change pas l'ancien jeton en validation locale (il contient encore ses groupes) ; en introspection, Keycloak recalcule les droits et refuse tout de suite ; un nouveau jeton perd le rôle presque instantanément.
- **Piège du cache Keycloak** : avec `cachePolicy = DEFAULT` sur la fédération LDAP, après un appel d'introspection, Keycloak garde l'utilisateur et ses groupes en cache : le retrait du groupe dans LDAP n'est plus vu par les nouveaux jetons. Correction : `cachePolicy = NO_CACHE` (option `--ldap-cache`), au prix d'une requête LDAP par jeton. Désactiver le compte invalide ce cache immédiatement.

## 8. Comparaison des modes
*(coller `resultats/bench.md`)*

| Critère | Local | Introspection |
|---|---|---|
| Délai de révocation | jusqu'à la durée de vie du jeton | immédiat (ou presque) |
| Appels à Keycloak | 1 (JWKS, mis en cache) | 1 par requête |
| Temps de réponse | … ms | … ms |
| Dépendance à Keycloak | faible | forte (point de défaillance) |

## 9. Recommandation chiffrée
| Niveau de risque | Exemple | Durée access token | Mode |
|---|---|---|---|
| Faible | lecture de données publiques | 15 min | local |
| Moyen | données internes | 5 min | local |
| Élevé | RH, finance, suppression | 1–2 min | introspection (ou local + liste de révocation) |

Justification à chiffrer avec vos mesures : fenêtre d'exposition maximale = durée de vie du jeton en mode local ; coût de l'introspection = (temps_introspect − temps_local) ms par requête.

## 10. Limites et conclusion
- Direct grant utilisé uniquement pour automatiser les tests ; le flux de production est Code + PKCE.
- Documents stockés dans PostgreSQL ; endpoints `/_reset`, `/metrics` et paramètre `?mode=` réservés à la démonstration.
- `groupOfNames` exige au moins un membre : on ne peut pas retirer le dernier membre d'un groupe (d'où le choix de bdupont pour le départ, car Developers a deux membres).
- Conclusion : …
