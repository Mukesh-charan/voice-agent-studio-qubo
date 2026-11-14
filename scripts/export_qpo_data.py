"""
scripts/export_qpo_data.py — Phase 2.4
Exports the full module table and Q matrix to results/ for paper reproducibility.

Usage:
    python scripts/export_qpo_data.py

Outputs:
    results/qpo_modules.csv  — full module table (id, tokens, value, tags, is_persona)
    results/qpo_Q.csv        — Q matrix at mu=32, T=180, normalised tokens
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "results"
MU = 32.0
T = 180
PERSONA_PENALTY = 5.0


def export_modules_csv() -> None:
    from qpo.modules import MODULES
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "qpo_modules.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "tokens", "value", "tags", "is_persona"])
        writer.writeheader()
        for m in MODULES:
            writer.writerow({
                "id": m.id,
                "tokens": m.token_cost,
                "value": m.value,
                "tags": "|".join(m.tags),
                "is_persona": "persona" in m.tags,
            })
    print(f"[export] Written {path}  ({len(MODULES)} modules)")


def export_Q_csv() -> None:
    import numpy as np
    from qpo.modules import MODULES, build_conflict_matrix, build_synergy_matrix, MODULE_IDS
    from qpo.qubo import build_qubo

    vals = [m.value for m in MODULES]
    C = build_conflict_matrix()
    S = build_synergy_matrix()
    costs = [m.token_cost for m in MODULES]
    persona_idx = [i for i, m in enumerate(MODULES) if "persona" in m.tags]

    Q_min, offset = build_qubo(
        vals, C, S, costs, T,
        mu=MU, normalize_tokens=True,
        persona_penalty=PERSONA_PENALTY,
        persona_ids=persona_idx,
    )

    n = len(MODULES)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "qpo_Q.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header: blank corner + module ids
        writer.writerow([""] + MODULE_IDS)
        for i in range(n):
            row = [MODULE_IDS[i]] + [f"{Q_min[i, j]:.6f}" for j in range(n)]
            writer.writerow(row)
    print(f"[export] Written {path}  shape=({n},{n})  mu={MU}  T={T}  offset={offset:.4f}")


if __name__ == "__main__":
    export_modules_csv()
    export_Q_csv()
    print("[export] Done.")
