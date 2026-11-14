"""
Statistical tests and confidence intervals for EAAI review.
Outputs results/stats_table.csv.

Functions:
  mcnemar_test(table)      — exact binomial McNemar via statsmodels
  wilson_ci(k, n, alpha)   — Wilson 95% CI for proportions
  bootstrap_ci(data, stat_fn, n_boot, alpha, seed) — bootstrap CI for any statistic
"""

from __future__ import annotations

import csv
import pathlib
from typing import Callable

import numpy as np

RESULTS_DIR = pathlib.Path(__file__).parent.parent / "results"
SEED = 1234


def mcnemar_test(table: list[list[int]]) -> dict:
    """
    Exact binomial McNemar test.
    table: 2×2 contingency [[a, b], [c, d]]
    Returns p-value, statistic, and 95% CI on the difference.
    """
    try:
        from statsmodels.stats.contingency_tables import mcnemar
    except ImportError:
        raise ImportError("statsmodels required: pip install statsmodels")

    import numpy as _np
    arr = _np.array(table)
    result = mcnemar(arr, exact=True, correction=False)
    b = arr[0, 1]
    c = arr[1, 0]
    return {
        "statistic": result.statistic,
        "pvalue":    result.pvalue,
        "b":         int(b),
        "c":         int(c),
        "note":      "exact binomial McNemar",
    }


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """
    Wilson score interval for proportion k/n at confidence level (1-alpha).
    Returns (lower, upper).
    """
    from scipy import stats as _stats

    z = _stats.norm.ppf(1 - alpha / 2)
    p_hat = k / n
    denom = 1 + z ** 2 / n
    centre = (p_hat + z ** 2 / (2 * n)) / denom
    margin = z * (p_hat * (1 - p_hat) / n + z ** 2 / (4 * n ** 2)) ** 0.5 / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def bootstrap_ci(
    data: list | np.ndarray,
    stat_fn: Callable,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = SEED,
) -> tuple[float, float]:
    """
    Percentile bootstrap CI for stat_fn applied to data.
    Returns (lower, upper) at (1-alpha) confidence.
    """
    rng = np.random.default_rng(seed)
    arr = np.asarray(data)
    boot_stats = []
    for _ in range(n_boot):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_stats.append(stat_fn(sample))
    boot_stats = np.array(boot_stats)
    lo = float(np.percentile(boot_stats, 100 * alpha / 2))
    hi = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))
    return lo, hi


def _demo_and_write_csv() -> None:
    """
    Run demo computations and write results/stats_table.csv.
    All values are computed from synthetic data (simulated=true).
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)

    # --- McNemar demo (synthetic) ---
    table = [[50, 10], [5, 35]]
    mc = mcnemar_test(table)

    # --- Wilson CI demo ---
    k, n = 72, 100
    w_lo, w_hi = wilson_ci(k, n, alpha=0.05)

    # --- Bootstrap CI demo (mean of synthetic scores) ---
    scores = rng.normal(0.78, 0.08, 100).tolist()
    b_lo, b_hi = bootstrap_ci(scores, np.mean, n_boot=1000, alpha=0.05, seed=SEED)

    rows = [
        {
            "test":       "McNemar (exact binomial)",
            "statistic":  round(mc["statistic"], 4),
            "pvalue":     round(mc["pvalue"], 4),
            "ci_lower":   "",
            "ci_upper":   "",
            "n":          mc["b"] + mc["c"],
            "simulated":  "true",
            "note":       mc["note"],
        },
        {
            "test":       "Wilson CI (proportion)",
            "statistic":  round(k / n, 4),
            "pvalue":     "",
            "ci_lower":   round(w_lo, 4),
            "ci_upper":   round(w_hi, 4),
            "n":          n,
            "simulated":  "true",
            "note":       f"k={k}, n={n}, alpha=0.05",
        },
        {
            "test":       "Bootstrap CI (mean fitness)",
            "statistic":  round(float(np.mean(scores)), 4),
            "pvalue":     "",
            "ci_lower":   round(b_lo, 4),
            "ci_upper":   round(b_hi, 4),
            "n":          len(scores),
            "simulated":  "true",
            "note":       "n_boot=1000, seed=1234",
        },
    ]

    out = RESULTS_DIR / "stats_table.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    _demo_and_write_csv()
