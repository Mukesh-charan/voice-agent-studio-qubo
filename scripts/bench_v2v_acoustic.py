"""
Voice-to-voice latency measurement harness.
Logs per-turn timestamps: vad_endpoint, asr_done, llm_first_token, tts_first_chunk, playback_start.
Writes one JSON line per turn to research/results/latency_raw.jsonl.

Usage:
  python scripts/bench_v2v_acoustic.py --mode stream [--turns 300]
  python scripts/bench_v2v_acoustic.py --mode acoustic [--turns 300]  # TODO_HUMAN: needs audio loopback

In 'stream' mode: measures time-to-first-audio-chunk (TTFC) from VAD endpoint.
In 'acoustic' mode: measures true voice-to-voice using loopback recording (TODO_HUMAN).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import numpy as np

SEED = 1234
RESULTS_DIR = pathlib.Path(__file__).parent.parent / "research" / "results"


# ── Realistic component latency distributions (ms) ───────────────────────────
# Based on published benchmarks for similar pipeline components.
# All numbers are SIMULATED (simulated: true); not from hardware measurement.

_COMPONENT_MEANS = {
    "asr_ms":            85.0,   # Whisper-base ASR, typical short utterance
    "llm_first_token_ms": 320.0,  # Qwen2.5-7B INT4-GPTQ, first token
    "tts_first_chunk_ms": 45.0,   # Piper TTS first audio chunk
    "playback_start_ms":   8.0,   # audio device open + first buffer
}

_COMPONENT_STDS = {
    "asr_ms":            18.0,
    "llm_first_token_ms": 55.0,
    "tts_first_chunk_ms": 10.0,
    "playback_start_ms":   3.0,
}


def simulate_turns(n_turns: int, seed: int = SEED) -> list[dict]:
    """
    Simulate per-turn component timestamps with realistic jitter.
    Returns list of dicts; each dict is one JSONL record.
    All records carry simulated=true.
    """
    rng = np.random.default_rng(seed)
    records = []
    for turn_id in range(n_turns):
        # vad_endpoint is the reference zero point (cumulative wall-clock not relevant here)
        vad_endpoint = 0.0

        asr_done = vad_endpoint + max(
            20.0,
            rng.normal(_COMPONENT_MEANS["asr_ms"], _COMPONENT_STDS["asr_ms"]),
        )
        llm_first_token = asr_done + max(
            100.0,
            rng.normal(_COMPONENT_MEANS["llm_first_token_ms"], _COMPONENT_STDS["llm_first_token_ms"]),
        )
        tts_first_chunk = llm_first_token + max(
            15.0,
            rng.normal(_COMPONENT_MEANS["tts_first_chunk_ms"], _COMPONENT_STDS["tts_first_chunk_ms"]),
        )
        playback_start = tts_first_chunk + max(
            2.0,
            rng.normal(_COMPONENT_MEANS["playback_start_ms"], _COMPONENT_STDS["playback_start_ms"]),
        )

        total_ms = playback_start - vad_endpoint

        records.append({
            "turn_id":        turn_id,
            "vad_endpoint":   round(vad_endpoint, 3),
            "asr_done":       round(asr_done, 3),
            "llm_first_token": round(llm_first_token, 3),
            "tts_first_chunk": round(tts_first_chunk, 3),
            "playback_start": round(playback_start, 3),
            "total_ms":       round(total_ms, 3),
            "mode":           "stream",
            "simulated":      True,
        })
    return records


def compute_percentiles(records: list[dict]) -> dict:
    """
    Compute P50/P90/P99 from per-turn total_ms values.
    IMPORTANT: percentiles are taken of the total_ms distribution,
    NOT by summing component-level percentiles (which would overestimate).
    """
    totals = np.array([r["total_ms"] for r in records])
    return {
        "p50_ms": float(np.percentile(totals, 50)),
        "p90_ms": float(np.percentile(totals, 90)),
        "p99_ms": float(np.percentile(totals, 99)),
        "n_turns": len(totals),
        "method":  "percentile_of_totals",  # NOT sum_of_percentiles
    }


def run_stream(n_turns: int) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "latency_raw.jsonl"

    records = simulate_turns(n_turns, seed=SEED)

    with open(out_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")

    stats = compute_percentiles(records)
    print(f"Wrote {n_turns} simulated turns → {out_path}")
    print(f"  P50={stats['p50_ms']:.1f}ms  P90={stats['p90_ms']:.1f}ms  P99={stats['p99_ms']:.1f}ms")
    print("  (all data is simulated; simulated=true in every record)")


def run_acoustic(n_turns: int) -> None:
    # TODO_HUMAN: implement acoustic loopback latency measurement.
    # Requires:
    #   1. A virtual audio loopback device (e.g., VB-Cable on Windows, JACK on Linux).
    #   2. Record microphone input after TTS playback starts.
    #   3. Detect voice onset in recording via VAD (e.g., silero-vad).
    #   4. Compute true voice-to-voice round-trip latency.
    # See results/PENDING_MEASUREMENTS.md item 1.
    print("ERROR: --mode acoustic is not yet implemented.")
    print("See results/PENDING_MEASUREMENTS.md for required setup.")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice-to-voice latency harness")
    parser.add_argument("--mode", choices=["stream", "acoustic"], default="stream",
                        help="'stream': simulated component timestamps; 'acoustic': TODO_HUMAN loopback")
    parser.add_argument("--turns", type=int, default=300,
                        help="Number of turns to simulate (stream mode) or measure (acoustic mode)")
    args = parser.parse_args()

    if args.mode == "stream":
        run_stream(args.turns)
    else:
        run_acoustic(args.turns)


if __name__ == "__main__":
    main()
