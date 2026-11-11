# Démonstration (environ 8 minutes)

Chiffres de référence (vos mesures du jour, à remplacer si vous relancez les scripts) : matrice **56/56**, jeton local **23,3 ms** contre introspection **36,6 ms**, après désactivation du compte : connexion **2,0 s**, refresh **4,1 s**, introspection **4,1 s**, validation locale **108,9 s**.

## Avant d'entrer dans la salle (dans cet ordre)
1. `.\demarrage\reparer-studio-java25.ps1` : ouvre Studio. Puis clic droit sur le serveur > **Exécuter**, attendre *Démarré*.
2. Si l'annuaire est vide : `python scripts/preparer_ldap.py`.
3. `.\demarrage\lancer-keycloak.ps1` (fenêtre 1), attendre ~1 min.
4. `python scripts/setup_keycloak.py` (la configuration doit finir par `groups = ['Staff', 'Admins']`).
5. `.\demarrage\lancer-backend.ps1` (fenêtre 2), puis `.\demarrage\lancer-frontend.ps1` (fenêtre 3).
6. Ouvrir dans le navigateur : http://localhost:4200 et http://localhost:8080. Garder Studio et un terminal (venv activé) prêts.
7. Lancer `python scripts/depart.py` **une fois** avant, pour avoir `resultats/depart.md` frais sous la main.

## Déroulé

### 1. Le problème (30 s)
**Dire :** « Quand un employé quitte l'entreprise, son jeton JWT reste accepté par l'API tant qu'il n'a pas expiré. J'ai construit une API à permissions fines, puis j'ai mesuré ce qu'il reste d'accès après un départ. »

### 2. L'architecture (30 s)
**Montrer :** le schéma du README.
**Dire :** « L'annuaire ApacheDS contient les employés et les groupes. Keycloak vérifie le mot de passe dans l'annuaire et délivre un jeton. L'application Angular utilise Code + PKCE. L'API Spring Boot valide le jeton et applique les droits. Les documents sont dans PostgreSQL. »

### 3. L'annuaire dans Studio (45 s)
**Montrer :** `dc=examen,dc=local` > `ou=People` > `uid=bdupont` ; puis `ou=Groups` > `cn=Developers`.
**Dire :** « Cinq employés, trois groupes. bdupont est dans Developers et Staff. Le groupe est ce qui détermine son rôle dans l'API : Admins devient manager, Developers devient editor, Staff devient reader. »

### 4. Keycloak (45 s)
**Montrer :** realm `examen` > *User federation* > `ldap`, puis *Clients* et *Client scopes*.
**Dire :** « Keycloak est relié à l'annuaire. J'ai trois scopes, docs:read, docs:write et docs:delete, et quatre clients : l'application web, une tâche planifiée, l'API et un client de test. »

### 5. Les permissions en direct (2 min)
Sur http://localhost:4200 :
1. **Sans jeton** : bouton « GET /docs sans jeton » → **401**. *« Je ne sais pas qui vous êtes. »*
2. **Se connecter** en `amartin` / `secret`. Dérouler les *claims* : `groups`, `scope`, `aud`. *« Elle est manager. »* → GET /docs **200**, POST /docs **201**.
3. Déconnexion, puis connexion en `epetit` / `secret` (groupe Staff). → POST /docs **403**, « rôle insuffisant ». *« Je sais qui vous êtes, mais vous n'avez pas le droit. C'est la différence entre 401 et 403. »*
4. Basculer le menu sur **introspection** et refaire un appel : même résultat. *« Deux façons de valider le jeton. »*

### 6. Le départ d'un employé (2 min)
**Montrer :** le tableau de `resultats/depart.md` (ou lancer `python scripts/depart.py` en parlant).
**Dire :** « bdupont quitte l'entreprise. Je le retire de ses groupes dans l'annuaire, puis je désactive son compte. »

| Élément | Délai | Explication |
|---|---|---|
| Nouvelle connexion | ~2 s | Keycloak vérifie le compte à chaque connexion |
| Refresh token | ~4 s | un compte désactivé ne peut plus renouveler |
| Jeton, **introspection** | ~4 s | l'API demande à Keycloak, qui répond « inactif » |
| Jeton, **validation locale** | ~109 s | l'API ne contacte personne : le jeton vit jusqu'à son expiration |

**Conclure :** « Le jeton local garde l'accès presque deux minutes après le départ. L'introspection le coupe en quelques secondes. »

**Variante en direct (très parlante).** Connecter `bdupont` dans l'application, puis lancer dans un terminal :
1. `python scripts/depart_manuel.py retirer` : ancien jeton, mode local, POST /docs → **201** ; mode introspection → **403**.
2. `python scripts/depart_manuel.py desactiver` : mode local → **201** (le compte est désactivé, mais le jeton est encore lu tel quel) ; introspection → **401 « jeton inactif »** ; bouton « Renouveler » → **refusé, « User disabled »** ; nouvelle connexion → **« Account is disabled »**.
3. `python scripts/depart_manuel.py restaurer` pour tout remettre.
Conseil : allonger le jeton pour avoir le temps de manipuler : `python scripts/setup_keycloak.py --access-lifespan 600` (revenir ensuite à 2 minutes avec la même commande sans option).

### 7. Comparaison et recommandation (45 s)
**Montrer :** `resultats/bench.md`.
**Dire :** « La validation locale est plus rapide (23 ms contre 37 ms) et n'appelle jamais Keycloak. L'introspection fait un appel par requête, mais coupe presque tout de suite. »

| Niveau de risque | Durée du jeton | Mode |
|---|---|---|
| Faible (lecture publique) | 15 min | local |
| Moyen (données internes) | 5 min | local |
| Élevé (RH, finance, suppression) | 1 à 2 min | introspection |

**Phrase de fin :** « La durée du jeton est le compromis : plus il est court, moins l'exposition est grande, mais plus on sollicite Keycloak. »

## Si le professeur demande…

**« Ajoutez un utilisateur. »**
- Studio : clic droit sur `ou=People` > *New Entry* > `inetOrgPerson`, RDN `uid=…`, `cn`, `sn`, `givenName`, `mail`, `userPassword` ; puis ajouter son DN dans `member` du groupe voulu.
- Ou en 5 secondes : `python scripts/ajouter_utilisateur.py fmoreau Farid Moreau Developers secret`.
- Il peut se connecter tout de suite avec le rôle de son groupe.

**« Ajoutez un nouveau groupe. »**
Créer le groupe dans l'annuaire (au moins un `member`) ; Keycloak > *User federation* > `ldap` > *Mappers* > `groupes-ldap` > *Action* > *Sync LDAP groups to Keycloak* ; ajouter le rôle dans `GROUP_TO_ROLE` (fichier `AuthService.java`) ; relancer le backend.

**« Pourquoi ne pas retirer le dernier membre d'un groupe ? »**
Un `groupOfNames` doit avoir au moins un `member` (règle du schéma LDAP). Pour le départ, j'ai donc choisi bdupont : son groupe Developers a deux membres.

**« Pourquoi la désactivation est-elle plus rapide que l'expiration ? »**
La désactivation agit côté Keycloak : connexion, refresh et introspection passent par lui. Mais la validation locale ne le consulte pas, donc rien ne la prévient.

**« Un piège rencontré ? »**
Oui : avec le réglage par défaut de Keycloak, après un appel d'introspection, Keycloak garde l'utilisateur et ses groupes en cache. Retirer un groupe dans l'annuaire n'était alors plus vu par les nouveaux jetons. Correction : `cachePolicy = NO_CACHE` (une requête LDAP par jeton) ; désactiver le compte invalide aussi ce cache.

**« Pourquoi Java 25 avec ApacheDS ? »**
Le TP utilisait Java 11. ApacheDS 2.0.0.AM26 plantait sous Java 25 (accès à une classe interne protégée, et génération de certificat impossible). J'ai fourni l'option Java nécessaire et un fichier de clés ; le chiffrement LDAPS n'est pas utilisé dans cet exercice local.

## Si quelque chose ne marche pas pendant la démonstration
| Symptôme | Cause probable | Solution |
|---|---|---|
| Connexion impossible, 401 partout | Keycloak a perdu sa configuration | `python scripts/setup_keycloak.py` |
| `groups` vide | annuaire vide ou arrêté | `python scripts/voir_ldap.py`, puis `preparer_ldap.py` |
| Le serveur Studio s'arrête | configuration réécrite | `.\demarrage\reparer-studio-java25.ps1`, puis *Exécuter* |
| La page affiche « reseau » | backend arrêté | `.\demarrage\lancer-backend.ps1` |
