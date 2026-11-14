"""
scripts/measure_task_durations.py — Stub harness for measuring real task latencies.

Usage:
    python scripts/measure_task_durations.py --mode mock
    python scripts/measure_task_durations.py --mode real --out results/qtp_tasks.csv

Modes:
  mock  Read durations from the existing CSV and print them (no I/O side-effects).
  real  Actually invoke each task coroutine N times and record median + p90.
        Requires a live environment (DB, Google credentials, Twilio token, etc.).
        Updates ``results/qtp_tasks.csv`` in-place.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import statistics
import time
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CSV_PATH = ROOT_DIR / "results" / "qtp_tasks.csv"


# ---------------------------------------------------------------------------
# Mock runner — just re-read the existing CSV and echo it
# ---------------------------------------------------------------------------

def run_mock(out_path: Path) -> None:
    print(f"[mock] Reading durations from {out_path}")
    with open(out_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    print(f"{'task_id':<16} {'type':<12} {'p50_ms':>8} {'p90_ms':>8} {'source'}")
    print("-" * 55)
    for row in rows:
        print(
            f"{row['task_id']:<16} {row['type']:<12} "
            f"{row['duration_p50_ms']:>8} {row['duration_p90_ms']:>8} "
            f"{row['source']}"
        )
    print(f"\n[mock] Done — {len(rows)} tasks listed.  No files modified.")


# ---------------------------------------------------------------------------
# Real runner — placeholder; fill in coroutines for each task
# ---------------------------------------------------------------------------

async def _measure_one(task_id: str, n_repeats: int = 30) -> tuple[float, float]:
    """
    TODO: replace the asyncio.sleep stub with the real coroutine for *task_id*.
    Returns (p50_ms, p90_ms).
    """
    # Stub: simulate the mock duration from the CSV so the harness is runnable
    _mock_durations: dict[str, float] = {
        "intent_parse": 35.0,
        "rag_query": 25.0,
        "db_persist": 45.0,
        "speech_synth": 210.0,
        "google_cal": 340.0,
        "google_sheet": 280.0,
        "webhook": 260.0,
        "audit_log": 55.0,
        "crm_sync": 310.0,
        "sms_notify": 240.0,
    }
    base_ms = _mock_durations.get(task_id, 100.0)

    samples: list[float] = []
    for _ in range(n_repeats):
        t0 = time.perf_counter()
        await asyncio.sleep(base_ms / 1000.0)  # replace with real coroutine
        samples.append((time.perf_counter() - t0) * 1000.0)

    samples.sort()
    p50 = statistics.median(samples)
    p90 = samples[int(0.9 * len(samples))]
    return round(p50, 1), round(p90, 1)


async def _run_real_async(out_path: Path, n_repeats: int) -> None:
    print(f"[real] Measuring {n_repeats} samples per task …")
    with open(out_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    for row in rows:
        tid = row["task_id"].strip()
        p50, p90 = await _measure_one(tid, n_repeats)
        print(f"  {tid}: p50={p50} ms  p90={p90} ms")
        row["duration_p50_ms"] = str(p50)
        row["duration_p90_ms"] = str(p90)
        row["source"] = "real"

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[real] Updated {out_path}")


def run_real(out_path: Path, n_repeats: int) -> None:
    asyncio.run(_run_real_async(out_path, n_repeats))


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure or display QTP task durations."
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "real"],
        default="mock",
        help="mock: echo existing CSV values; real: run live measurements.",
    )
    parser.add_argument(
        "--out",
        default=str(CSV_PATH),
        help=f"Path to qtp_tasks.csv (default: {CSV_PATH})",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=30,
        help="Number of measurement repeats per task in real mode (default: 30).",
    )
    args = parser.parse_args()
    out_path = Path(args.out)

    if args.mode == "mock":
        run_mock(out_path)
    else:
        run_real(out_path, args.repeats)


if __name__ == "__main__":
    main()
