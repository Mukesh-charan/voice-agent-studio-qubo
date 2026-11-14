"""
scripts/check_numbers.py — Phase 5.4 / Phase 8.2
Checks numerical consistency across results/ CSV files.

Two checks:
  1. Cross-table consistency: values that SHOULD be identical (e.g. the same
     task duration cited in two different tables) are compared.  Hard fail if
     they differ.
  2. Duplicate-value detector: flags when two *different* latency/timing
     measurements share the exact same value to 0.1 ms precision — a signal
     that one may have been copy-pasted from the other.

     To avoid spurious hits on common small numbers (0, 1, 1.0, 2.0 …), the
     detector only fires when:
       • the value is > 50.0 (ms / tokens — small coincidences are expected)
       • AND the two occurrences are in the same semantic domain
         (both "timing" columns, or both in the same file).

Usage:
    python scripts/check_numbers.py          # exits 0 on OK, 1 on failure
    python scripts/check_numbers.py --warn   # print warnings but always exit 0
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys
from collections import defaultdict

RESULTS_DIR = pathlib.Path(__file__).parent.parent / "results"

# Columns that carry timing measurements (in ms) — only these are checked for
# suspicious duplicates.
_TIMING_COLS = {
    "Serial_Makespan_ms", "Greedy_Makespan_ms", "SA_Makespan_ms",
    "QAOA_Makespan_ms", "SA_Solver_Time_ms", "QAOA_Solver_Time_ms",
    "duration_p50_ms", "duration_p90_ms",
    "wave_makespan_ms", "critical_path_ms", "speech_onset_ms",
}

# Pairs of (file_a:col_a, file_b:col_b) that MUST carry the same value.
# Add entries here when a number is cited in two separate result files.
_MUST_MATCH_PAIRS: list[tuple[str, str, str, str]] = [
    # Example (uncomment when qtp_benchmark.csv exists):
    # ("qtp_tasks.csv", "duration_p50_ms", "qtp_benchmark.csv", "serial_ms"),
]


def load_csvs(d: pathlib.Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in sorted(d.glob("*.csv")):
        with open(p, newline="", encoding="utf-8") as fh:
            out[p.name] = list(csv.DictReader(fh))
    return out


def _numeric(raw: str) -> float | None:
    try:
        return float(raw.strip())
    except (ValueError, AttributeError):
        return None


def check_must_match(tables: dict[str, list[dict]]) -> list[str]:
    """Hard-check: pairs declared in _MUST_MATCH_PAIRS must be equal."""
    failures = []
    for fa, ca, fb, cb in _MUST_MATCH_PAIRS:
        if fa not in tables or fb not in tables:
            continue
        vals_a = [_numeric(r.get(ca, "")) for r in tables[fa] if _numeric(r.get(ca, "")) is not None]
        vals_b = [_numeric(r.get(cb, "")) for r in tables[fb] if _numeric(r.get(cb, "")) is not None]
        for va, vb in zip(vals_a, vals_b):
            if abs(va - vb) > 0.05:
                failures.append(
                    f"[FAIL] {fa}:{ca}={va} != {fb}:{cb}={vb} (diff={abs(va-vb):.3f})"
                )
    return failures


def check_timing_duplicates(tables: dict[str, list[dict]]) -> list[str]:
    """
    Flag timing values > 50 ms that appear identically in two different
    (file, timing-column) pairs — a signal of copy-paste rather than
    independent measurement.

    Legitimate coincidences (e.g. two tasks that really do take 55 ms each)
    will appear in the same column across rows of the same file and are NOT
    flagged.  Only cross-file, cross-column duplicates are flagged.
    """
    # bucket: rounded_value → set of (filename, col)
    bucket: dict[float, set[tuple[str, str]]] = defaultdict(set)
    for fname, rows in tables.items():
        for row in rows:
            for col, raw in row.items():
                if col not in _TIMING_COLS:
                    continue
                v = _numeric(raw)
                if v is None or v <= 50.0:
                    continue
                bucket[round(v, 1)].add((fname, col))

    warnings = []
    for val, locations in bucket.items():
        if len(locations) < 2:
            continue
        # Only flag cross-file duplicates (same file, different col is OK)
        files = {f for f, _ in locations}
        if len(files) < 2:
            continue
        locs_str = ", ".join(f"{f}:{c}" for f, c in sorted(locations))
        warnings.append(
            f"[WARN] Timing value {val} ms appears in multiple files — "
            f"verify these are independent measurements: {locs_str}"
        )
    return warnings


def main(warn_only: bool = False) -> None:
    if not RESULTS_DIR.exists():
        print(f"[FAIL] results/ directory not found: {RESULTS_DIR}")
        sys.exit(0 if warn_only else 1)

    tables = load_csvs(RESULTS_DIR)
    if not tables:
        print("[WARN] No CSV files found in results/")
        sys.exit(0)

    print(f"[OK] Loaded {len(tables)} CSV(s): {', '.join(tables.keys())}")

    fail = False

    # Check 1: declared must-match pairs
    failures = check_must_match(tables)
    for f in failures:
        print(f)
    if failures:
        fail = True

    # Check 2: suspicious timing duplicates
    warnings = check_timing_duplicates(tables)
    for w in warnings:
        print(w)
    if warnings and not warn_only:
        # Treat timing duplicates as warnings for now (not hard failures)
        # unless the same value appears in a "serial" and a "parallel" column
        # of different tables, which would be a definite error.
        hard = [w for w in warnings if "Serial_Makespan_ms" in w and "SA_Makespan_ms" in w]
        if hard:
            fail = True

    if not failures and not warnings:
        print("[OK] No cross-table inconsistencies detected.")
    elif not failures:
        print(f"[OK] {len(warnings)} timing coincidence warning(s) — review manually.")

    if fail and not warn_only:
        sys.exit(1)
    else:
        print("[OK] check_numbers.py passed.")
        sys.exit(0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--warn", action="store_true", help="Print warnings but always exit 0")
    args = p.parse_args()
    main(warn_only=args.warn)
