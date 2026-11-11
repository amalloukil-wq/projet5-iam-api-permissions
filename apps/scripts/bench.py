"""Compare validation locale et introspection : temps de reponse et appels a Keycloak.

Usage : python apps/scripts/bench.py [--n 100]
Resultat : affichage + docs/resultats/bench.md
"""
import argparse
import statistics
import time

import requests

from common import API, RESULTS, call, tokens
from config import MANAGER

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=100)
n = ap.parse_args().n

token = tokens(MANAGER)["access_token"]
lines = ["| Mode | Appels API | Appels a Keycloak | Moyenne (ms) | Mediane (ms) | p95 (ms) |", "|---|---|---|---|---|---|"]
for mode in ("local", "introspect"):
    call("GET", "/docs", token, mode)   # echauffement (charge le JWKS)
    before = requests.get(f"{API}/metrics").json()
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        assert call("GET", "/docs", token, mode).status_code == 200
        times.append((time.perf_counter() - t0) * 1000)
    after = requests.get(f"{API}/metrics").json()
    kc_calls = (after["jwks_fetches"] - before["jwks_fetches"]) + (after["introspection_calls"] - before["introspection_calls"])
    times.sort()
    lines.append(f"| {mode} | {n} | {kc_calls} | {statistics.mean(times):.1f} | "
                 f"{statistics.median(times):.1f} | {times[int(0.95 * n) - 1]:.1f} |")

text = "\n".join(lines)
print(text)
(RESULTS / "bench.md").write_text(text, encoding="utf-8")
print(f"\nEcrit dans {RESULTS / 'bench.md'}")
