| Action | Endpoint /revoke | Refresh ensuite | Access (local) | Access (introspection) |
|---|---|---|---|---|
| Revocation du refresh token | endpoint -> 200 | refresh -> 400 | access local -> 200 | access introspection -> 401 |
| Revocation de l'access token | endpoint -> 200 | refresh -> 200 | access local -> 200 | access introspection -> 401 |