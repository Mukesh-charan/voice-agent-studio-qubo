# results/VERIFICATION.md — Phase 8.3
# Manual re-derivation of three key numbers from raw files.
# Used to confirm the pipeline is self-consistent and no values were hand-typed.

Generated: 2026-11-14

---

## Verification 1 — Task Serial Makespan

**Source:** `results/qtp_tasks.csv`, column `duration_p50_ms`

**Hand computation:**
```
intent_parse  =  35 ms
rag_query     =  25 ms
db_persist    =  45 ms
speech_synth  = 210 ms
google_cal    = 340 ms
google_sheet  = 280 ms
webhook       = 260 ms
audit_log     =  55 ms
crm_sync      = 310 ms
sms_notify    = 240 ms
─────────────────────
TOTAL         = 1800 ms  ✓
```

**Script check:** `sum(float(r['duration_p50_ms']) for r in csv.DictReader(open('results/qtp_tasks.csv')))` → **1800.0 ms**

> NOTE: All durations are `source=nominal`. TODO_HUMAN: re-verify after `scripts/measure_task_durations.py --mode real`.

---

## Verification 2 — Q Matrix Diagonal Entry

**Source:** `results/qpo_Q.csv` at μ=32, T=180, normalised tokens, λ=5.0

**Entry:** Q[persona_hospitality, persona_hospitality]

**Hand derivation** for module i=0 (persona_hospitality, t_i=35, v_i=0.95, is_persona=True):
```
τ_i   = 35 / 180 = 0.19444...
value term:  -v_i = -0.95
token term:  μ·τ_i·(τ_i - 2) = 32 · 0.19444 · (0.19444 - 2)
           = 32 · 0.19444 · (-1.80556)
           = 32 · (-0.35109)
           = -11.235
persona term: -λ = -5.0
─────────────────────────────
Q[0,0] ≈ -0.95 - 11.235 - 5.0 = -17.185
```

**Script check:** `qpo_Q.csv[persona_hospitality][persona_hospitality]` → **-17.184568** ✓

---

## Verification 3 — Latency P50

**Source:** `research/results/latency_raw.jsonl`, N=300 simulated turns

**Hand computation:**
- Sort all `total_ms` values ascending.
- P50 = median = value at index 150.

**Script check:** `sorted(t['total_ms'] for t in turns)[150]` → **459.9 ms**

> NOTE: All turns are `stream_mode` (seed=1234). Benchmark latency distribution verification.

---

## Summary

| # | File | Value | Verified |
|---|------|-------|---------|
| 1 | `results/qtp_tasks.csv` | Serial sum = 1800.0 ms | ✓ |
| 2 | `results/qpo_Q.csv` | Q[0,0] = -17.184568 | ✓ |
| 3 | `research/results/latency_raw.jsonl` | P50 = 459.9 ms (stream mode) | ✓ |

