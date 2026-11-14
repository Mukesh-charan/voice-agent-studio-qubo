"""
Unit tests for latency harness — verify that percentiles are computed from totals,
NOT by summing component-level percentiles.
"""

from __future__ import annotations

import json
import pathlib
import sys
import unittest

# Allow running from repo root
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from scripts.bench_v2v_acoustic import simulate_turns, compute_percentiles
import numpy as np


class TestPercentileMethod(unittest.TestCase):
    """
    Key invariant: P50/P90/P99 must be computed from the distribution of
    per-turn total_ms, NOT from summing each component's percentile.
    """

    def test_percentile_of_totals_not_sum_of_percentiles(self):
        records = simulate_turns(300, seed=1234)
        totals = np.array([r["total_ms"] for r in records])

        # Correct: percentile of totals
        correct_p50 = float(np.percentile(totals, 50))

        # Wrong (strawman): sum per-component P50s
        asr_p50 = float(np.percentile([r["asr_done"] - r["vad_endpoint"] for r in records], 50))
        llm_p50 = float(np.percentile([r["llm_first_token"] - r["asr_done"] for r in records], 50))
        tts_p50 = float(np.percentile([r["tts_first_chunk"] - r["llm_first_token"] for r in records], 50))
        play_p50 = float(np.percentile([r["playback_start"] - r["tts_first_chunk"] for r in records], 50))
        wrong_p50 = asr_p50 + llm_p50 + tts_p50 + play_p50

        # They must differ (sum-of-percentiles overestimates)
        self.assertAlmostEqual(correct_p50, compute_percentiles(records)["p50_ms"], places=5,
                               msg="compute_percentiles must return percentile of totals")
        self.assertNotAlmostEqual(correct_p50, wrong_p50, places=0,
                                  msg="sum-of-component-p50s should differ from p50-of-totals")
        # sum of percentiles is >= true P50 (by Jensen / correlation)
        # This is a known statistical fact; assert it holds in simulation
        self.assertGreaterEqual(wrong_p50, correct_p50 * 0.95,
                                msg="sum-of-percentiles should be >= p50-of-totals (or close)")

    def test_all_turns_have_required_fields(self):
        records = simulate_turns(10, seed=1234)
        required = {"turn_id", "vad_endpoint", "asr_done", "llm_first_token",
                    "tts_first_chunk", "playback_start", "total_ms", "mode", "simulated"}
        for r in records:
            self.assertEqual(required, set(r.keys()) & required)

    def test_simulated_flag_is_true(self):
        records = simulate_turns(5, seed=1234)
        for r in records:
            self.assertTrue(r["simulated"], "Every simulated record must have simulated=true")

    def test_monotonic_pipeline(self):
        records = simulate_turns(50, seed=1234)
        for r in records:
            self.assertLessEqual(r["vad_endpoint"], r["asr_done"])
            self.assertLessEqual(r["asr_done"], r["llm_first_token"])
            self.assertLessEqual(r["llm_first_token"], r["tts_first_chunk"])
            self.assertLessEqual(r["tts_first_chunk"], r["playback_start"])


if __name__ == "__main__":
    unittest.main()
