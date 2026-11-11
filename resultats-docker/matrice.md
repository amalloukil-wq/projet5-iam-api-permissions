### Mode de validation : local

| Profil | GET /docs | POST /docs | DELETE /docs/1 (doc de amartin) | DELETE /docs/2 (doc de bdupont) |
|---|---|---|---|---|
| amartin (groupe Admins = manager) | 200 | 201 | 200 | 200 |
| bdupont (groupe Developers = editor) | 200 | 201 | 403 | 200 |
| epetit (groupe Staff = reader) | 200 | 403 | 403 | 403 |
| tache planifiee (client credentials) | 200 | 403 | 403 | 403 |
| amartin via client 'other' (mauvaise aud) | 401 | 401 | 401 | 401 |
| jeton falsifie | 401 | 401 | 401 | 401 |
| sans jeton | 401 | 401 | 401 | 401 |

### Mode de validation : introspect

| Profil | GET /docs | POST /docs | DELETE /docs/1 (doc de amartin) | DELETE /docs/2 (doc de bdupont) |
|---|---|---|---|---|
| amartin (groupe Admins = manager) | 200 | 201 | 200 | 200 |
| bdupont (groupe Developers = editor) | 200 | 201 | 403 | 200 |
| epetit (groupe Staff = reader) | 200 | 403 | 403 | 403 |
| tache planifiee (client credentials) | 200 | 403 | 403 | 403 |
| amartin via client 'other' (mauvaise aud) | 401 | 401 | 401 | 401 |
| jeton falsifie | 401 | 401 | 401 | 401 |
| sans jeton | 401 | 401 | 401 | 401 |
