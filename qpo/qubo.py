"""
qpo/qubo.py — Phase B1, B2 + EAAI Phase 2.1
Builds the QUBO matrix Q for modular prompt assembly and converts it to
Ising (h, J, const) with a verified bijection.

MINIMISATION FORM (Phase 2.1):
    F(x) = -Σ v_i x_i + Σ_{i<j}(C_ij - S_ij) x_i x_j
           + μ(Σ τ_i x_i - 1)² + λ(Σ_{i∈persona} x_i - 1)²

    where τ_i = t_i / T  (normalised token fraction, if normalize_tokens=True)

    Expanding squares (using x_i²=x_i for binary x):
      Token diagonal:  μ·τ_i·(τ_i - 2)        for each i
      Token off-diag:  +2μ·τ_i·τ_j             for i<j
      Persona diag:    -λ·x_i                  for each persona i
      Persona off-diag: +2λ                    for each persona pair i<j
      Constant offset: μ + λ  (dropped from Q, returned separately)

    fitness = -F  (maximised when F is minimised)

LEGACY MAXIMISATION FORM (backwards compat, normalize_tokens=False):
    Objective (maximise, so QUBO is negated for minimisation):
        F(x) = Σ_i v_i x_i
              - Σ_{i<j} c_ij x_i x_j      # conflict penalties
              + Σ_{i<j} s_ij x_i x_j      # synergy bonuses
              - mu * (Σ_i t_i x_i - T)^2  # token-budget soft penalty

The QUBO matrix Q encodes this as  x^T Q x  (upper-triangular convention).

Ising conversion uses x_i = (1 - z_i) / 2 (z_i ∈ {-1, +1}).
Verified by unit test: for all 2^n bitstrings (n ≤ 12),
    x^T Q x == Ising_energy(z) + const   (to 1e-9 tolerance)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


SEED = 1234


# ── QUBO builder (Phase 2.1 — minimisation form) ─────────────────────────────

def build_qubo(
    values: list[float],
    conflicts: list[list[float]],
    synergies: list[list[float]],
    token_costs: list[int],
    token_budget: int,
    mu: float = 0.5,
    must_include: Optional[list[int]] = None,
    must_include_bias: float = 10.0,
    normalize_tokens: bool = True,
    persona_penalty: float = 5.0,
    persona_ids: list[int] = [],
) -> tuple[np.ndarray, float]:
    """
    Build the QUBO matrix Q_min (n×n, upper-triangular) for the MINIMISATION form.

    **F is MINIMISED.**  fitness = -F.

    When normalize_tokens=True (default, Phase 2.1):
        τ_i = t_i / T  (normalised token fractions)

        F(x) = -Σ v_i x_i + Σ_{i<j}(C_ij-S_ij) x_i x_j
               + μ(Σ τ_i x_i - 1)² + λ(Σ_{i∈persona} x_i - 1)²

        Q_min encodes only the variable parts; offset = μ + λ is returned.

    When normalize_tokens=False (legacy compat):
        Uses raw token counts.  Returns (Q_legacy, 0.0) where Q_legacy is
        the MAXIMISATION Q (same as old build_qubo, negated to get min form).
        In this mode persona_penalty / persona_ids are ignored.

    Args:
        values:            module base values v_i
        conflicts:         c_ij conflict matrix (penalty when both selected)
        synergies:         s_ij synergy matrix (bonus when both selected)
        token_costs:       t_i token cost per module
        token_budget:      T soft target token budget
        mu:                weight on the quadratic token penalty term
        must_include:      list of module indices with large positive bias
                           (only applied in legacy mode; phase 2.1 uses persona_ids)
        must_include_bias: additional value added to diagonal for must-include
        normalize_tokens:  if True, normalise token costs by T (new minimisation form)
        persona_penalty:   λ — penalty weight for one-hot persona constraint
        persona_ids:       indices of persona modules (one-hot constraint)

    Returns:
        (Q_min, offset) where:
            Q_min  — (n, n) numpy array, upper-triangular, minimisation convention
            offset — constant term μ + λ (add to x@Q_min@x to get true F)

    Note: To use existing maximisation solvers, pass Q_max = -Q_min to them.
    """
    n = len(values)

    if not normalize_tokens:
        # ── Legacy maximisation form (backwards compat) ───────────────────────
        Q = np.zeros((n, n), dtype=float)
        for i in range(n):
            Q[i, i] += values[i]
        if must_include:
            for i in must_include:
                Q[i, i] += must_include_bias
        for i in range(n):
            for j in range(i + 1, n):
                if conflicts[i][j] != 0:
                    Q[i, j] -= conflicts[i][j]
        for i in range(n):
            for j in range(i + 1, n):
                if synergies[i][j] != 0:
                    Q[i, j] += synergies[i][j]
        t = np.array(token_costs, dtype=float)
        for i in range(n):
            Q[i, i] += -mu * t[i] ** 2 + 2 * mu * token_budget * t[i]
        for i in range(n):
            for j in range(i + 1, n):
                Q[i, j] -= 2 * mu * t[i] * t[j]
        # Return negated as minimisation form, offset=0
        return -Q, 0.0

    # ── New minimisation form (Phase 2.1) ─────────────────────────────────────
    Q_min = np.zeros((n, n), dtype=float)

    # 1. Value terms: -Σ v_i x_i  → diagonal -v_i
    for i in range(n):
        Q_min[i, i] -= values[i]

    # 2. Conflict / synergy interaction terms: (C_ij - S_ij) x_i x_j
    for i in range(n):
        for j in range(i + 1, n):
            cs = conflicts[i][j] - synergies[i][j]
            if cs != 0:
                Q_min[i, j] += cs

    # 3. Token budget penalty: μ(Σ τ_i x_i - 1)²
    #    Expand: μ·Σ τ_i² x_i - 2μ·Σ τ_i x_i + μ
    #    Since x_i²=x_i: diagonal += μ·τ_i²  - 2μ·τ_i = μ·τ_i·(τ_i - 2)
    #    Off-diagonal (i<j): += 2μ·τ_i·τ_j
    #    Constant: +μ  (returned in offset)
    tau = np.array(token_costs, dtype=float) / float(token_budget)
    for i in range(n):
        Q_min[i, i] += mu * tau[i] * (tau[i] - 2.0)
    for i in range(n):
        for j in range(i + 1, n):
            Q_min[i, j] += 2.0 * mu * tau[i] * tau[j]

    # 4. Persona one-hot penalty: λ(Σ_{i∈persona} x_i - 1)²
    #    Expand: λ·Σ x_i² - 2λ·Σ x_i + λ + 2λ·Σ_{i<j} x_i x_j
    #    Since x_i²=x_i: diagonal[i] += λ·(1 - 2) = -λ  for each persona i
    #    Off-diagonal (i<j, both persona): += 2λ
    #    Constant: +λ  (returned in offset)
    lam = persona_penalty
    _persona_set = list(persona_ids)
    for i in _persona_set:
        Q_min[i, i] -= lam
    for idx_a in range(len(_persona_set)):
        for idx_b in range(idx_a + 1, len(_persona_set)):
            i, j = _persona_set[idx_a], _persona_set[idx_b]
            if i > j:
                i, j = j, i
            Q_min[i, j] += 2.0 * lam

    # Constant offset = μ + λ·(1 if personas exist else 0)
    offset = mu + (lam if _persona_set else 0.0)

    return Q_min, offset


def qubo_energy(Q: np.ndarray, x: np.ndarray) -> float:
    """Evaluate the QUBO objective x^T Q x for a binary vector x."""
    return float(x @ Q @ x)


# ── QUBO → Ising conversion (B2, corrected) ──────────────────────────────────

def qubo_to_ising(Q: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Convert a QUBO matrix Q (upper-triangular) to Ising (h, J, const).

    Q is upper-triangular: x^T Q x = Σ_i Q[i,i]*x_i + Σ_{i<j} Q[i,j]*x_i*x_j

    Substitution:  x_i = (1 - z_i) / 2,  z_i ∈ {-1, +1}

    Diagonal term (x_i^2 = x_i for binary x_i):
        Q[i,i] * x_i = Q[i,i] * (1-z_i)/2
        Contributes:  Q[i,i]/2  to const,  -Q[i,i]/2  to h_i

    Off-diagonal term:
        Q[i,j] * x_i*x_j = Q[i,j] * (1-z_i)(1-z_j)/4
                          = Q[i,j]/4 * (1 - z_i - z_j + z_i z_j)
        Contributes:  Q[i,j]/4  to const,
                     -Q[i,j]/4  to h_i AND h_j,
                     +Q[i,j]/4  to J[i,j]

    Ising energy convention: E(z) = Σ_i h_i z_i + Σ_{i<j} J_ij z_i z_j

    Resulting coefficients (for upper-triangular input Q):
        h_i   = -Q[i,i]/2 - Σ_{j>i} Q[i,j]/4 - Σ_{j<i} Q[j,i]/4
        J_ij  = Q[i,j]/4        (i < j, upper triangle)
        const = Σ_i Q[i,i]/2 + Σ_{i<j} Q[i,j]/4

    Verification: x^T Q x = E(z) + const  ∀ x ∈ {0,1}^n
    """
    n = Q.shape[0]
    # Project to upper-triangular: combine lower triangle into upper.
    # For off-diagonal pairs (i<j): effective Q_ij = Q[i,j] + Q[j,i]
    # Diagonal stays as-is (Q[i,i]).
    Q_up = np.zeros((n, n), dtype=float)
    for i in range(n):
        Q_up[i, i] = Q[i, i]
        for j in range(i + 1, n):
            Q_up[i, j] = Q[i, j] + Q[j, i]

    h = np.zeros(n, dtype=float)
    J = np.zeros((n, n), dtype=float)

    # Diagonal contribution: Q_up[i,i] * x_i = Q_up[i,i] * (1-z_i)/2
    for i in range(n):
        h[i] -= Q_up[i, i] / 2.0

    # Off-diagonal contribution (upper triangle)
    for i in range(n):
        for j in range(i + 1, n):
            if Q_up[i, j] != 0:
                h[i] -= Q_up[i, j] / 4.0
                h[j] -= Q_up[i, j] / 4.0
                J[i, j] = Q_up[i, j] / 4.0

    # Constant
    const = 0.0
    for i in range(n):
        const += Q_up[i, i] / 2.0
    for i in range(n):
        for j in range(i + 1, n):
            const += Q_up[i, j] / 4.0

    return h, J, const




def ising_energy(h: np.ndarray, J: np.ndarray, z: np.ndarray) -> float:
    """
    Compute Ising energy: E(z) = Σ_i h_i z_i + Σ_{i<j} J[i,j] z_i z_j
    z ∈ {-1, +1}^n
    """
    n = len(z)
    linear = float(h @ z)
    quad = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            quad += J[i, j] * z[i] * z[j]
    return linear + quad



def verify_ising_identity(Q: np.ndarray, tol: float = 1e-9) -> bool:
    """
    Brute-force verification: for all 2^n bitstrings (n ≤ 12),
    assert x^T Q x == Ising_energy(z) + const to within tol.

    Returns True if identity holds for all bitstrings, raises AssertionError otherwise.
    """
    n = Q.shape[0]
    assert n <= 12, f"Too many variables for brute-force verification: n={n}"
    h, J, const = qubo_to_ising(Q)

    for bits in range(2 ** n):
        x = np.array([(bits >> i) & 1 for i in range(n)], dtype=float)
        z = 1 - 2 * x  # x_i=0 -> z_i=1, x_i=1 -> z_i=-1

        qubo_val = qubo_energy(Q, x)
        ising_val = ising_energy(h, J, z) + const

        assert abs(qubo_val - ising_val) < tol, (
            f"Ising identity FAILED at bits={bits:0{n}b}: "
            f"QUBO={qubo_val:.6f}, Ising+const={ising_val:.6f}"
        )
    return True


# ── Quick self-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from qpo.modules import (
        MODULES, N_MODULES, TOKEN_BUDGET, MUST_INCLUDE,
        build_conflict_matrix, build_synergy_matrix, module_index,
    )

    values = [m.value for m in MODULES]
    conflicts = build_conflict_matrix()
    synergies = build_synergy_matrix()
    token_costs = [m.token_cost for m in MODULES]
    must_idx = [module_index(mid) for mid in MUST_INCLUDE]
    persona_idx = [i for i, m in enumerate(MODULES) if "persona" in m.tags]

    Q_min, offset = build_qubo(
        values, conflicts, synergies, token_costs, TOKEN_BUDGET,
        mu=32.0, normalize_tokens=True,
        persona_penalty=5.0, persona_ids=persona_idx,
    )

    print(f"QUBO shape: {Q_min.shape}")
    print(f"Diagonal range: [{Q_min.diagonal().min():.3f}, {Q_min.diagonal().max():.3f}]")
    print(f"Offset: {offset:.3f}")

    # Verify Ising identity on a small sub-problem (first 8 modules)
    Q_small = Q_min[:8, :8]
    ok = verify_ising_identity(Q_small)
    print(f"Ising identity verification (n=8): {'PASS' if ok else 'FAIL'}")
    print("QUBO builder self-test complete.")
    sys.exit(0)
