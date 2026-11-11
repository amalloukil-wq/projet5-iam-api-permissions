# Configurer Keycloak avec l'interface (sans le script)

Tout se fait dans la console d'administration : **http://localhost:8080** → *Administration Console* → `admin` / `admin`.
Les noms de menus sont ceux de Keycloak 26 ; un libellé peut varier légèrement d'une version à l'autre.

Pré-requis : l'annuaire LDAP (ApacheDS du TP) est **démarré** et contient les données de `ldap/*.ldif`.

---

## Étape 1 : créer le realm
1. En haut à gauche, cliquer sur le menu déroulant (« Keycloak » / `master`) → **Create realm**.
2. *Realm name* : `examen` → **Create**.
3. Vérifier que le menu affiche bien `examen` avant de continuer (tout le reste se fait dans ce realm).

## Étape 2 : connecter l'annuaire LDAP
Menu **User federation** → **Add LDAP provider** (ou « Add new provider » → *ldap*).

| Champ | Valeur |
|---|---|
| UI display name | `ldap` |
| Vendor | `Other` |
| Connection URL | `ldap://localhost:10389` → cliquer **Test connection** |
| Bind type | `simple` |
| Bind DN | `uid=admin,ou=system` |
| Bind credentials | `secret` → cliquer **Test authentication** |
| Edit mode | `UNSYNCED` |
| Users DN | `ou=People,dc=examen,dc=local` |
| Username LDAP attribute | `uid` |
| RDN LDAP attribute | `uid` |
| UUID LDAP attribute | `entryUUID` |
| User object classes | `inetOrgPerson` |
| Search scope | `One Level` |
| Import users | `On` |
| Sync Registrations | `Off` |
| Cache policy (section *Cache settings*) | `NO_CACHE` |

Cliquer **Save**. Les deux tests (connexion et authentification) doivent afficher un message de succès.

> **Pourquoi `NO_CACHE` ?** Sinon Keycloak garde les groupes en cache et un retrait de groupe dans LDAP n'est plus vu par les nouveaux jetons (constat important du rapport).

### Mappers (onglet *Mappers* du fournisseur `ldap`)
1. Ouvrir le mapper **first name** : changer *LDAP attribute* en `givenName` → **Save**.
2. Vérifier que **last name** utilise `sn`, **email** utilise `mail`, **username** utilise `uid`.
3. Cliquer **Add mapper** :

| Champ | Valeur |
|---|---|
| Name | `groupes-ldap` |
| Mapper type | `group-ldap-mapper` |
| LDAP Groups DN | `ou=Groups,dc=examen,dc=local` |
| Group name LDAP attribute | `cn` |
| Group object classes | `groupOfNames` |
| Preserve group inheritance | `Off` |
| Membership LDAP attribute | `member` |
| Membership attribute type | `DN` |
| Membership user LDAP attribute | `uid` |
| Mode | `LDAP_ONLY` |
| User groups retrieve strategy | `LOAD_GROUPS_BY_MEMBER_ATTRIBUTE` |
| Drop non-existing groups during sync | `Off` |

4. **Save**, puis en haut à droite menu **Action** → **Sync LDAP groups to Keycloak**.
5. Retourner sur le fournisseur `ldap` → menu **Action** → **Sync all users**.

Vérifier : menus **Users** (amartin, bdupont… présents) et **Groups** (Admins, Developers, Staff).

## Étape 3 : créer les scopes
Menu **Client scopes** → **Create client scope**, trois fois :

| Name | Type | Protocol | Include in token scope | Display on consent screen |
|---|---|---|---|---|
| `docs:read` | `None` | OpenID Connect | `On` | `Off` |
| `docs:write` | `None` | OpenID Connect | `On` | `Off` |
| `docs:delete` | `None` | OpenID Connect | `On` | `Off` |

## Étape 4 : créer les clients

### 4.1 `webapp` (application Angular, Code + PKCE)
1. **Clients** → **Create client** : *Client type* `OpenID Connect`, *Client ID* `webapp` → **Next**.
2. *Client authentication* `Off` ; *Authorization* `Off` ; cocher **Standard flow** (et **Direct access grants** si vous voulez lancer les scripts de test) → **Next**.
3. *Valid redirect URIs* : `http://localhost:4200/*` ; *Web origins* : `+` → **Save**.
4. Onglet **Advanced** → *Advanced settings* → *Proof Key for Code Exchange Code Challenge Method* : `S256` → **Save**.
5. Onglet **Client scopes** → **Add client scope** → cocher `docs:read`, `docs:write`, `docs:delete` → *Add* → **Default**.
6. Onglet **Client scopes** → cliquer `webapp-dedicated` → **Configure a new mapper** :
   - **Group Membership** : *Name* `groups`, *Token Claim Name* `groups`, *Full group path* `Off`, *Add to ID token*, *Add to access token*, *Add to userinfo* `On` → **Save**.
   - **Audience** : *Name* `aud-api-examen`, *Included Custom Audience* `api-examen`, *Add to ID token* `Off`, *Add to access token* `On` → **Save**.

### 4.2 `batch` (tâche planifiée, Client Credentials)
1. **Create client** : *Client ID* `batch` → **Next** → *Client authentication* `On`, décocher *Standard flow*, cocher **Service accounts roles** → **Save**.
2. Onglet **Client scopes** : ajouter **uniquement** `docs:read` (Default).
3. `batch-dedicated` : ajouter les mêmes mappers **Group Membership** et **Audience** qu'au 4.1.
4. Onglet **Credentials** : noter le *Client secret*.

### 4.3 `api` (le backend, pour l'introspection)
**Create client** : *Client ID* `api` → *Client authentication* `On`, décocher *Standard flow* → **Save**. Onglet **Credentials** : noter le *Client secret*.

### 4.4 `other` (sert à tester le contrôle de l'audience)
Comme `webapp` (public, Standard flow, redirect `http://localhost:4200/*`), mais ajouter seulement le scope `docs:read` et **ne pas** ajouter le mapper Audience.

## Étape 5 : durée et rotation des jetons
Menu **Realm settings** → onglet **Tokens** :
- *Access Token Lifespan* : `2 minutes` ;
- *Revoke Refresh Token* : `On` (rotation du refresh token) ; *Refresh Token Max Reuse* : `0` → **Save**.

## Étape 6 : tester
- Ouvrir http://localhost:4200, se connecter avec `amartin` / `secret` : la page doit afficher le groupe `Admins` et les scopes.
- Dans Keycloak : **Sessions** montre la connexion ; **Users** → amartin → onglet **Groups**.

---

## Attention aux secrets des clients
Le backend et les scripts attendent `api-secret` (client `api`) et `batch-secret` (client `batch`). Keycloak ne permet pas de choisir un secret dans l'interface : il en génère un. Si vous configurez tout à la main, reportez les secrets notés aux étapes 4.2 et 4.3 dans :
- `backend/src/main/resources/application.properties` → `app.api-client-secret` (secret du client `api`), puis redémarrer le backend ;
- `scripts/common.py` → ligne `auth=("batch", "batch-secret")` (secret du client `batch`).

## Ajouter un utilisateur avec l'interface
Dans **Apache Directory Studio** (comme au TP) : clic droit sur `ou=People,dc=examen,dc=local` → *New Entry* → `inetOrgPerson`, RDN `uid=…`, attributs `cn`, `sn`, `givenName`, `mail`, `userPassword` ; puis ouvrir le groupe voulu sous `ou=Groups` et ajouter son DN complet à l'attribut `member`. L'utilisateur peut se connecter tout de suite. Pour un **nouveau groupe** : dans Keycloak, *User federation* → `ldap` → *Mappers* → `groupes-ldap` → *Action* → *Sync LDAP groups to Keycloak*, et ajouter son rôle dans `GROUP_TO_ROLE` (`backend/.../AuthService.java`).
