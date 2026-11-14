"""
scripts/derive_qubo_from_data.py — Phase 2.5 (STUB)
Derives QUBO parameters (values v_i, conflict C_ij, synergy S_ij)
from empirical conversation-turn data.

Schema for research/data/dev_turns.jsonl (one JSON object per line):
{
  "turn_id": str,          // unique turn identifier
  "domain": str,           // "hospitality" | "clinic" | ...
  "modules_active": [str], // list of module IDs active in this turn
  "response": str,         // assistant response text
  "phi_role": float,       // 0–1, graded by human / LLM judge
  "phi_flow": float,       // 0–1
  "phi_bound": float,      // 0–1
  "phi_artifact": float,   // 0–1
  "phi_retain": float,     // 0–1
  "fitness": float         // composite score, 0–1
}

TODO_HUMAN items are written to results/PENDING_MEASUREMENTS.md.

Cache mechanism:
  LLM responses are cached to .cache/llm_responses/ as JSON files keyed by
  SHA-256(prompt) so repeated runs don't re-query the LLM.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "research" / "data" / "dev_turns.jsonl"
CACHE_DIR = ROOT / ".cache" / "llm_responses"
RESULTS_DIR = ROOT / "results"
PENDING_PATH = RESULTS_DIR / "PENDING_MEASUREMENTS.md"

PENDING_CONTENT = """# Pending Measurements — TODO_HUMAN

## Status: PENDING

The file `research/data/dev_turns.jsonl` does not yet exist.
Real QUBO parameter derivation requires empirical conversation-turn data.

### What is needed

Collect graded conversation turns matching the schema in
`scripts/derive_qubo_from_data.py` (docstring) and save them to:

    research/data/dev_turns.jsonl

Each line must be a JSON object with keys:
- `turn_id`, `domain`, `modules_active` (list of module IDs)
- `phi_role`, `phi_flow`, `phi_bound`, `phi_artifact`, `phi_retain`, `fitness`

### Why it matters

Currently `v_i`, `C_ij`, `S_ij` values in `qpo/modules.py` are hand-crafted
heuristics. Data-driven derivation would:
1. Fit `v_i` = mean fitness when module i is active.
2. Fit `C_ij` = negative co-selection correlation penalty.
3. Fit `S_ij` = positive co-selection correlation bonus.

### Suggested collection protocol

1. Run the voice agent on 200+ real or synthetic booking/clinic turns
   with all 16 module combinations sampled from a D-optimal design.
2. Grade each turn with the phi scorers (or LLM judge).
3. Run `python scripts/derive_qubo_from_data.py` to fit parameters.

### Estimated effort

~2–4 hours of data collection + 30 min of script run time.
"""


def _cache_path(prompt: str) -> Path:
    h = hashlib.sha256(prompt.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def _cached_llm_call(prompt: str, mock_response: str = "") -> str:
    """Return cached LLM response or mock_response if not cached."""
    cp = _cache_path(prompt)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))["response"]
    # Cache miss: in a real implementation, call the LLM API here.
    # For now, write mock_response to cache and return it.
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps({"prompt_hash": cp.stem, "response": mock_response}), encoding="utf-8")
    return mock_response


def load_dev_turns() -> list[dict]:
    """Load dev_turns.jsonl; return [] if not found."""
    if not DATA_PATH.exists():
        return []
    turns = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    turns.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return turns


def write_pending_measurements() -> None:
    """Write PENDING_MEASUREMENTS.md noting data collection is needed."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_PATH.write_text(PENDING_CONTENT, encoding="utf-8")
    print(f"[derive] Written {PENDING_PATH}")


def derive_parameters(turns: list[dict]) -> dict:
    """
    Derive QUBO parameters from empirical data.
    Returns dict with keys: values, conflicts, synergies (all indexed by module id).
    """
    from qpo.modules import MODULE_IDS
    n = len(MODULE_IDS)
    idx = {mid: i for i, mid in enumerate(MODULE_IDS)}

    fitness_sum = [0.0] * n
    fitness_count = [0] * n
    co_sum = [[0.0] * n for _ in range(n)]
    co_count = [[0] * n for _ in range(n)]

    for t in turns:
        active = [idx[m] for m in t.get("modules_active", []) if m in idx]
        f = float(t.get("fitness", 0.0))
        for i in active:
            fitness_sum[i] += f
            fitness_count[i] += 1
        for a in range(len(active)):
            for b in range(a + 1, len(active)):
                i, j = active[a], active[b]
                co_sum[i][j] += f
                co_count[i][j] += 1
                co_sum[j][i] += f
                co_count[j][i] += 1

    values = [
        fitness_sum[i] / fitness_count[i] if fitness_count[i] > 0 else 0.5
        for i in range(n)
    ]
    # Synergy: co-fitness above average → positive; below → negative (conflict)
    avg = sum(values) / n if n > 0 else 0.5
    synergies = [[0.0] * n for _ in range(n)]
    conflicts = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if co_count[i][j] > 0:
                co_f = co_sum[i][j] / co_count[i][j]
                delta = co_f - avg
                if delta > 0:
                    synergies[i][j] = synergies[j][i] = delta
                else:
                    conflicts[i][j] = conflicts[j][i] = -delta

    return {"values": values, "conflicts": conflicts, "synergies": synergies}


def main() -> None:
    # Ensure research/data/ directory exists
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    turns = load_dev_turns()
    if not turns:
        print(f"[derive] No data at {DATA_PATH} — writing PENDING_MEASUREMENTS.md")
        write_pending_measurements()
        return

    print(f"[derive] Loaded {len(turns)} turns from {DATA_PATH}")
    params = derive_parameters(turns)
    print(f"[derive] Derived parameters:")
    print(f"  values range: [{min(params['values']):.3f}, {max(params['values']):.3f}]")
    print("[derive] Done. Update qpo/modules.py with derived values manually.")


if __name__ == "__main__":
    main()
