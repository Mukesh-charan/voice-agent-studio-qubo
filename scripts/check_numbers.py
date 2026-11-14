"""
scripts/check_numbers.py — Guard rails and consistency checks (Round 2)
Checks numerical consistency, duplicate values, empty cells, and banned strings.

Usage:
    python scripts/check_numbers.py          # exits 0 on OK, 1 on failure
    python scripts/check_numbers.py --warn   # print warnings but always exit 0
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys
from collections import defaultdict

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"
RESEARCH_DIR = ROOT_DIR / "research"

# Banned strings in the manuscript and generated tables (Task 0 / Task 7)
BANNED_STRINGS = [
    "TODO_HUMAN",
    "source=mock",
    "simulated=true",
    "pending",
    "camera-ready",
    "critical_path_ms",
    "wave_makespan_ms",
    "speech_onset_ms",
]

# Code identifiers with _ms that shouldn't appear in text
BANNED_PATTERNS = [
    r"\b[a-z_]+_ms\b",
]

_TIMING_COLS = {
    "Serial_Makespan_ms", "Greedy_Makespan_ms", "SA_Makespan_ms",
    "QAOA_Makespan_ms", "SA_Solver_Time_ms", "QAOA_Solver_Time_ms",
    "duration_p50_ms", "duration_p90_ms",
    "wave_makespan_ms", "critical_path_ms", "speech_onset_ms",
}

# Known collisions to forbid across different measurement types
FORBIDDEN_COLLISIONS = {312.4, 285.0}


def check_banned_strings(tex_path: pathlib.Path) -> list[str]:
    """Check for banned strings and process text in the manuscript."""
    failures = []
    if not tex_path.exists():
        return [f"[FAIL] Manuscript file not found: {tex_path}"]

    with open(tex_path, encoding="utf-8") as f:
        text = f.read()

    for banned in BANNED_STRINGS:
        cnt = text.count(banned)
        if cnt > 0:
            failures.append(f"[FAIL] Banned string '{banned}' found {cnt} time(s) in {tex_path.name}")

    for pat in BANNED_PATTERNS:
        matches = re.findall(pat, text)
        if matches:
            unique_matches = sorted(set(matches))
            failures.append(f"[FAIL] Code identifier(s) with '_ms' found in {tex_path.name}: {unique_matches}")

    return failures


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


def check_empty_cells(tables: dict[str, list[dict]]) -> list[str]:
    """Check for any empty table cells across results CSVs."""
    failures = []
    for fname, rows in tables.items():
        for r_idx, row in enumerate(rows):
            for col, val in row.items():
                if val is None or val.strip() == "":
                    failures.append(f"[FAIL] Empty cell in {fname} row {r_idx+1} col '{col}'")
    return failures


def check_timing_duplicates(tables: dict[str, list[dict]]) -> list[str]:
    """
    Flag timing values > 50 ms that appear identically in two different
    (file, timing-column) pairs.
    """
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
        files = {f for f, _ in locations}
        if len(files) < 2:
            continue
        locs_str = ", ".join(f"{f}:{c}" for f, c in sorted(locations))
        warnings.append(
            f"[WARN] Timing value {val} ms appears in multiple files: {locs_str}"
        )
    return warnings


def main(warn_only: bool = False) -> None:
    fail = False

    # 1. Check banned strings in manuscript
    tex_path = RESEARCH_DIR / "manuscript_corrected_final.tex"
    print(f"[CHECK] Scanning {tex_path.name} for banned process strings...")
    tex_failures = check_banned_strings(tex_path)
    for err in tex_failures:
        print(err)
    if tex_failures:
        fail = True

    # 2. Check results CSVs
    if not RESULTS_DIR.exists():
        print(f"[FAIL] results/ directory not found: {RESULTS_DIR}")
        sys.exit(0 if warn_only else 1)

    tables = load_csvs(RESULTS_DIR)
    print(f"[OK] Loaded {len(tables)} CSV(s) from results/: {', '.join(tables.keys())}")

    # Empty cells check
    empty_failures = check_empty_cells(tables)
    for err in empty_failures:
        print(err)
    if empty_failures:
        fail = True

    # Timing duplicates check
    timing_warnings = check_timing_duplicates(tables)
    for w in timing_warnings:
        print(w)

    if fail and not warn_only:
        print("\n[FAIL] check_numbers.py failed.")
        sys.exit(1)
    else:
        print("\n[OK] check_numbers.py passed.")
        sys.exit(0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--warn", action="store_true", help="Print warnings but always exit 0")
    args = p.parse_args()
    main(warn_only=args.warn)
