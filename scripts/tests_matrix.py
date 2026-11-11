"""Matrice de tests : pour chaque profil et chaque route, le code HTTP obtenu (200/201/401/403).

Usage : python scripts/tests_matrix.py     (API lancee sur le port 8000)
Resultat : affichage console + resultats/matrice.md
"""
from common import RESULTS, call, service_token, tokens
from config import EDITOR, MANAGER, READER

# Documents de depart : le 1 appartient a amartin, le 2 a bdupont
CASES = [("GET", "/docs", None), ("POST", "/docs", {"title": "test"}),
         ("DELETE", "/docs/1", None), ("DELETE", "/docs/2", None)]
HEADERS = ["GET /docs", "POST /docs", f"DELETE /docs/1 (doc de {MANAGER})", f"DELETE /docs/2 (doc de {EDITOR})"]

# profil -> (token, codes attendus)
profiles = {
    f"{MANAGER} (groupe Admins = manager)": (tokens(MANAGER)["access_token"], [200, 201, 200, 200]),
    f"{EDITOR} (groupe Developers = editor)": (tokens(EDITOR)["access_token"], [200, 201, 403, 200]),
    f"{READER} (groupe Staff = reader)": (tokens(READER)["access_token"], [200, 403, 403, 403]),
    "tache planifiee (client credentials)": (service_token(), [200, 403, 403, 403]),
    f"{MANAGER} via client 'other' (mauvaise aud)": (tokens(MANAGER, "other")["access_token"], [401] * 4),
    "jeton falsifie": ("abc.def.ghi", [401] * 4),
    "sans jeton": (None, [401] * 4),
}

lines = []
total = ko = 0
for mode in ("local", "introspect"):
    lines += [f"### Mode de validation : {mode}", "",
              "| Profil | " + " | ".join(HEADERS) + " |", "|---|" + "---|" * len(HEADERS)]
    for name, (tok, expected) in profiles.items():
        call("POST", "/_reset")
        row = []
        for (method, path, body), exp in zip(CASES, expected):
            code = call(method, path, tok, mode, json=body).status_code
            total += 1
            if code != exp:
                ko += 1
            row.append(str(code) if code == exp else f"{code} (attendu {exp})")
        lines.append(f"| {name} | " + " | ".join(row) + " |")
    lines.append("")

text = "\n".join(lines)
print(text)
print(f"\n{total - ko}/{total} resultats conformes aux attentes.")
(RESULTS / "matrice.md").write_text(text, encoding="utf-8")
print(f"Ecrit dans {RESULTS / 'matrice.md'}")
