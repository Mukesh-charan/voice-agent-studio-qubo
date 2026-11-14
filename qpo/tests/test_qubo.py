"""
qpo/tests/test_qubo.py — Phase B2, B3 + EAAI Phase 2.1, 2.3
Unit tests for QUBO construction and Ising identity verification.

Run with:
    pytest qpo/tests/test_qubo.py -v
"""

import math

import numpy as np
import pytest

SEED = 1234


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def real_qubo_small():
    """Build a real minimisation QUBO from the module library using first 8 modules."""
    from qpo.modules import (
        MODULES, TOKEN_BUDGET, MUST_INCLUDE,
        build_conflict_matrix, build_synergy_matrix, module_index,
    )
    from qpo.qubo import build_qubo

    n = 8
    vals = [m.value for m in MODULES[:n]]
    C = build_conflict_matrix()
    S = build_synergy_matrix()
    C_sub = [[C[i][j] for j in range(n)] for i in range(n)]
    S_sub = [[S[i][j] for j in range(n)] for i in range(n)]
    costs = [m.token_cost for m in MODULES[:n]]
    persona_idx = [i for i, m in enumerate(MODULES[:n]) if "persona" in m.tags]
    Q_min, offset = build_qubo(
        vals, C_sub, S_sub, costs, TOKEN_BUDGET,
        mu=0.5, normalize_tokens=True,
        persona_penalty=5.0, persona_ids=persona_idx,
    )
    return Q_min, offset


@pytest.fixture()
def real_qubo_small_legacy():
    """Build legacy maximisation QUBO (normalize_tokens=False) for compat tests."""
    from qpo.modules import (
        MODULES, TOKEN_BUDGET, MUST_INCLUDE,
        build_conflict_matrix, build_synergy_matrix, module_index,
    )
    from qpo.qubo import build_qubo

    n = 8
    vals = [m.value for m in MODULES[:n]]
    C = build_conflict_matrix()
    S = build_synergy_matrix()
    C_sub = [[C[i][j] for j in range(n)] for i in range(n)]
    S_sub = [[S[i][j] for j in range(n)] for i in range(n)]
    costs = [m.token_cost for m in MODULES[:n]]
    must_idx = [
        i for i, mid in enumerate([m.id for m in MODULES[:n]])
        if mid in MUST_INCLUDE
    ]
    Q_min, offset = build_qubo(
        vals, C_sub, S_sub, costs, TOKEN_BUDGET,
        mu=0.5, must_include=must_idx, normalize_tokens=False,
    )
    return Q_min, offset  # Q_min here is negated legacy Q (minimisation)


@pytest.fixture()
def random_qubo_small():
    """Generate a small random QUBO for algebraic identity tests."""
    rng = np.random.default_rng(SEED)
    n = 6
    Q = rng.uniform(-1, 1, (n, n))
    Q = (Q + Q.T) / 2
    np.fill_diagonal(Q, rng.uniform(0, 1, n))
    return Q


# ── QUBO construction tests ───────────────────────────────────────────────────

class TestQUBOConstruction:

    def test_qubo_shape(self, real_qubo_small):
        Q_min, _ = real_qubo_small
        assert Q_min.shape == (8, 8)

    def test_qubo_diagonal_negative_for_high_value_modules_min_form(self):
        """In minimisation form, high-value modules have NEGATIVE diagonal (we want to include them)."""
        from qpo.qubo import build_qubo
        n = 4
        vals = [1.0, 1.0, 1.0, 1.0]
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0] * n for _ in range(n)]
        costs = [10] * n
        Q_min, offset = build_qubo(
            vals, C, S, costs, token_budget=100, mu=0.0,
            normalize_tokens=True, persona_ids=[],
        )
        # Diagonal should equal -value (minimisation wants negative diagonal)
        assert all(abs(Q_min[i, i] - (-1.0)) < 1e-9 for i in range(n))

    def test_legacy_qubo_diagonal_positive_for_high_value_modules(self):
        """Legacy form: high-value modules have positive diagonal (maximisation)."""
        from qpo.qubo import build_qubo
        n = 4
        vals = [1.0, 1.0, 1.0, 1.0]
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0] * n for _ in range(n)]
        costs = [10] * n
        # legacy returns -Q_max, which has negative diag for high value
        Q_min_legacy, _ = build_qubo(vals, C, S, costs, token_budget=100, mu=0.0,
                                     normalize_tokens=False)
        # Q_max[i,i] = +1.0  → Q_min_legacy[i,i] = -1.0
        assert all(abs(Q_min_legacy[i, i] - (-1.0)) < 1e-9 for i in range(n))

    def test_conflict_increases_off_diagonal_min_form(self):
        """Conflicts make Q_min[i,j] > 0 (penalises selecting conflicting pair)."""
        from qpo.qubo import build_qubo
        n = 2
        vals = [0.5, 0.5]
        C = [[0.0, 1.0], [1.0, 0.0]]  # conflict between 0 and 1
        S = [[0.0] * n for _ in range(n)]
        costs = [10, 10]
        Q_min, _ = build_qubo(vals, C, S, costs, token_budget=50, mu=0.0,
                               normalize_tokens=True, persona_ids=[])
        assert Q_min[0, 1] > 0, "Conflict should make off-diagonal positive in min form"

    def test_synergy_decreases_off_diagonal_min_form(self):
        """Synergies make Q_min[i,j] < 0 (rewards selecting synergistic pair)."""
        from qpo.qubo import build_qubo
        n = 2
        vals = [0.5, 0.5]
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0, 0.5], [0.5, 0.0]]  # synergy between 0 and 1
        costs = [10, 10]
        Q_min, _ = build_qubo(vals, C, S, costs, token_budget=50, mu=0.0,
                               normalize_tokens=True, persona_ids=[])
        assert Q_min[0, 1] < 0, "Synergy should make off-diagonal negative in min form"

    def test_token_budget_penalty_present(self):
        """Budget penalty should create non-zero off-diagonal entries even without conflicts."""
        from qpo.qubo import build_qubo
        n = 3
        vals = [0.5] * n
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0] * n for _ in range(n)]
        costs = [50, 50, 50]
        Q_min, offset = build_qubo(vals, C, S, costs, token_budget=80, mu=1.0,
                                   normalize_tokens=True, persona_ids=[])
        # Off-diagonal should be non-zero because mu > 0
        assert Q_min[0, 1] != 0 or Q_min[0, 2] != 0
        # offset should include mu
        assert abs(offset - 1.0) < 1e-9

    def test_persona_penalty_diagonal(self):
        """Persona constraint: diagonal for persona modules gets -lambda added."""
        from qpo.qubo import build_qubo
        n = 3
        vals = [0.5] * n
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0] * n for _ in range(n)]
        costs = [10] * n
        lam = 5.0
        # personas at index 0 and 1
        Q_min_no_p, _ = build_qubo(vals, C, S, costs, token_budget=100, mu=0.0,
                                    normalize_tokens=True, persona_ids=[],
                                    persona_penalty=lam)
        Q_min_with_p, offset = build_qubo(vals, C, S, costs, token_budget=100, mu=0.0,
                                           normalize_tokens=True, persona_ids=[0, 1],
                                           persona_penalty=lam)
        # diagonal[0] and [1] should decrease by lambda
        assert abs(Q_min_with_p[0, 0] - (Q_min_no_p[0, 0] - lam)) < 1e-9
        assert abs(Q_min_with_p[1, 1] - (Q_min_no_p[1, 1] - lam)) < 1e-9
        # off-diagonal [0,1] should increase by 2*lambda
        assert abs(Q_min_with_p[0, 1] - (Q_min_no_p[0, 1] + 2.0 * lam)) < 1e-9
        # offset includes lambda
        assert abs(offset - lam) < 1e-9

    def test_offset_mu_plus_lambda(self):
        """offset == mu + lambda when personas present."""
        from qpo.qubo import build_qubo
        n = 2
        vals = [0.5] * n
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0] * n for _ in range(n)]
        costs = [10, 10]
        mu = 2.0
        lam = 3.0
        _, offset = build_qubo(vals, C, S, costs, token_budget=100, mu=mu,
                                normalize_tokens=True, persona_ids=[0],
                                persona_penalty=lam)
        assert abs(offset - (mu + lam)) < 1e-9

    def test_offset_mu_only_when_no_personas(self):
        """offset == mu when persona_ids is empty."""
        from qpo.qubo import build_qubo
        n = 2
        vals = [0.5] * n
        C = [[0.0] * n for _ in range(n)]
        S = [[0.0] * n for _ in range(n)]
        costs = [10, 10]
        mu = 4.0
        _, offset = build_qubo(vals, C, S, costs, token_budget=100, mu=mu,
                                normalize_tokens=True, persona_ids=[],
                                persona_penalty=5.0)
        assert abs(offset - mu) < 1e-9


# ── Phase 2.1: F(x) = x@Q_min@x + offset identity ───────────────────────────

class TestMinimisationIdentity:
    """
    Phase 2.1 requirement: verify F(x) == x @ Q_min @ x + offset
    for 10 random binary strings on the full module library.
    """

    def test_F_equals_xQx_plus_offset_random_bitstrings(self):
        """F(x) = x@Q_min@x + offset holds for 10 random bitstrings."""
        from qpo.modules import (
            MODULES, TOKEN_BUDGET,
            build_conflict_matrix, build_synergy_matrix,
        )
        from qpo.qubo import build_qubo, qubo_energy

        n = len(MODULES)
        vals = [m.value for m in MODULES]
        C = build_conflict_matrix()
        S = build_synergy_matrix()
        costs = [m.token_cost for m in MODULES]
        persona_idx = [i for i, m in enumerate(MODULES) if "persona" in m.tags]
        mu = 2.0
        lam = 5.0
        T = TOKEN_BUDGET

        Q_min, offset = build_qubo(
            vals, C, S, costs, T,
            mu=mu, normalize_tokens=True,
            persona_penalty=lam, persona_ids=persona_idx,
        )

        rng = np.random.default_rng(SEED)
        tau = np.array(costs, dtype=float) / T

        for _ in range(10):
            x = rng.integers(0, 2, size=n).astype(float)

            # Compute F analytically from the formula
            F_analytic = (
                - float(np.array(vals) @ x)
                + sum((C[i][j] - S[i][j]) * x[i] * x[j] for i in range(n) for j in range(i+1, n))
                + mu * (float(tau @ x) - 1.0) ** 2
                + lam * (float(sum(x[i] for i in persona_idx)) - 1.0) ** 2
            )

            # Compute via QUBO
            F_qubo = qubo_energy(Q_min, x) + offset

            assert abs(F_analytic - F_qubo) < 1e-6, (
                f"F mismatch: analytic={F_analytic:.8f}, qubo+offset={F_qubo:.8f}"
            )

    def test_all_zeros_gives_offset(self):
        """x=0 → F = offset (since x@Q@x = 0)."""
        from qpo.modules import MODULES, TOKEN_BUDGET, build_conflict_matrix, build_synergy_matrix
        from qpo.qubo import build_qubo, qubo_energy
        vals = [m.value for m in MODULES]
        C = build_conflict_matrix()
        S = build_synergy_matrix()
        costs = [m.token_cost for m in MODULES]
        persona_idx = [i for i, m in enumerate(MODULES) if "persona" in m.tags]
        Q_min, offset = build_qubo(vals, C, S, costs, TOKEN_BUDGET, mu=1.0,
                                    normalize_tokens=True, persona_penalty=5.0,
                                    persona_ids=persona_idx)
        x = np.zeros(len(MODULES))
        F = qubo_energy(Q_min, x) + offset
        # F(0) = 0 + mu*(0-1)^2 + lam*(0-1)^2 = mu + lam = offset
        assert abs(F - offset) < 1e-9


# ── Ising identity tests ──────────────────────────────────────────────────────

class TestIsingIdentity:

    def test_identity_real_qubo(self, real_qubo_small):
        """x^T Q x == Ising_energy(z) + const for all 2^8 bitstrings."""
        from qpo.qubo import verify_ising_identity
        Q_min, _ = real_qubo_small
        assert verify_ising_identity(Q_min, tol=1e-9)

    def test_identity_random_qubo(self, random_qubo_small):
        """Identity holds for a random symmetric QUBO."""
        from qpo.qubo import verify_ising_identity
        assert verify_ising_identity(random_qubo_small, tol=1e-9)

    def test_identity_diagonal_only(self):
        """Diagonal-only QUBO (no interactions): identity must hold."""
        from qpo.qubo import verify_ising_identity
        Q = np.diag([1.0, 0.5, 0.8, 0.3])
        assert verify_ising_identity(Q)

    def test_qubo_to_ising_coefficients(self):
        """Check h and J have correct shapes and finite values."""
        from qpo.qubo import qubo_to_ising
        rng = np.random.default_rng(SEED + 1)
        Q = rng.uniform(-1, 1, (5, 5))
        Q = (Q + Q.T) / 2
        h, J, const = qubo_to_ising(Q)
        assert h.shape == (5,)
        assert J.shape == (5, 5)
        assert math.isfinite(const)
        assert np.all(np.isfinite(h))
        assert np.all(np.isfinite(J))


# ── Solver correctness tests ──────────────────────────────────────────────────

class TestSolvers:

    def test_brute_force_finds_optimum(self):
        """Brute force must find global optimum on a tiny problem."""
        from qpo.solvers import brute_force
        # QUBO where selecting variable 0 only is optimal (all others cost more)
        n = 3
        Q = np.zeros((n, n))
        Q[0, 0] = 2.0
        Q[1, 1] = -1.0  # penalty for selecting 1
        Q[2, 2] = -1.0  # penalty for selecting 2
        result = brute_force(Q)
        assert result.x[0] == 1
        assert result.x[1] == 0
        assert result.x[2] == 0
        assert abs(result.objective - 2.0) < 1e-9

    def test_greedy_does_not_exceed_optimum(self, real_qubo_small):
        """Greedy objective ≤ brute-force optimum (using Q_max = -Q_min)."""
        from qpo.solvers import brute_force, greedy
        Q_min, _ = real_qubo_small
        Q_max = -Q_min
        bf = brute_force(Q_max)
        gr = greedy(Q_max)
        assert gr.objective <= bf.objective + 1e-6

    def test_sa_close_to_optimum_small(self, real_qubo_small):
        """SA should find solution within 15% of optimum on n=8."""
        from qpo.solvers import brute_force, simulated_annealing
        Q_min, _ = real_qubo_small
        Q_max = -Q_min
        bf = brute_force(Q_max)
        sa = simulated_annealing(Q_max, n_steps=20000, seed=SEED)
        if bf.objective > 0:
            ratio = sa.objective / bf.objective
            assert ratio >= 0.85, f"SA approximation ratio too low: {ratio:.3f}"

    def test_sa_seeded_reproducible(self, real_qubo_small):
        """Same seed → same result."""
        from qpo.solvers import simulated_annealing
        Q_min, _ = real_qubo_small
        Q_max = -Q_min
        r1 = simulated_annealing(Q_max, seed=SEED)
        r2 = simulated_annealing(Q_max, seed=SEED)
        assert abs(r1.objective - r2.objective) < 1e-9
        assert np.allclose(r1.x, r2.x)

    def test_tabu_seeded_reproducible(self, real_qubo_small):
        """Same seed → same tabu result."""
        from qpo.solvers import tabu_search
        Q_min, _ = real_qubo_small
        Q_max = -Q_min
        r1 = tabu_search(Q_max, seed=SEED)
        r2 = tabu_search(Q_max, seed=SEED)
        assert abs(r1.objective - r2.objective) < 1e-9


# ── Phase 2.3: evaluate_solver wrapper tests ─────────────────────────────────

class TestEvaluateSolver:

    def _build_full_qubo(self):
        from qpo.modules import MODULES, TOKEN_BUDGET, build_conflict_matrix, build_synergy_matrix
        from qpo.qubo import build_qubo
        vals = [m.value for m in MODULES]
        C = build_conflict_matrix()
        S = build_synergy_matrix()
        costs = [m.token_cost for m in MODULES]
        persona_idx = [i for i, m in enumerate(MODULES) if "persona" in m.tags]
        Q_min, offset = build_qubo(vals, C, S, costs, TOKEN_BUDGET, mu=32.0,
                                    normalize_tokens=True, persona_penalty=5.0,
                                    persona_ids=persona_idx)
        return Q_min, offset

    def test_evaluate_solver_gap_nonneg(self):
        """F_solver >= F_star: solver gap should be >= 0 (minimisation)."""
        from qpo.solvers import evaluate_solver, brute_force, simulated_annealing
        Q_min, offset = self._build_full_qubo()
        Q_max = -Q_min
        bf_result = evaluate_solver(brute_force, Q_min, Q_max, offset)
        sa_result = evaluate_solver(simulated_annealing, Q_min, Q_max, offset)
        F_star = bf_result["F"]
        F_sa = sa_result["F"]
        assert F_sa >= F_star - 1e-6, (
            f"SA F={F_sa:.4f} < F_star={F_star:.4f}: gap should be >= 0"
        )

    def test_evaluate_solver_brute_force_gap_zero(self):
        """Brute force is optimal: gap_pct should be 0."""
        from qpo.solvers import evaluate_solver, brute_force
        Q_min, offset = self._build_full_qubo()
        Q_max = -Q_min
        result = evaluate_solver(brute_force, Q_min, Q_max, offset)
        assert abs(result["gap_pct"]) < 1e-6, f"BF gap_pct={result['gap_pct']:.6f}, expected 0"


# ── Module library tests ──────────────────────────────────────────────────────

class TestModules:

    def test_module_ids_unique(self):
        from qpo.modules import MODULES
        ids = [m.id for m in MODULES]
        assert len(ids) == len(set(ids)), "Module IDs must be unique"

    def test_conflict_matrix_symmetric(self):
        from qpo.modules import build_conflict_matrix, N_MODULES
        C = build_conflict_matrix()
        assert len(C) == N_MODULES
        for i in range(N_MODULES):
            for j in range(N_MODULES):
                assert C[i][j] == C[j][i], f"Conflict matrix not symmetric at ({i},{j})"

    def test_synergy_matrix_symmetric(self):
        from qpo.modules import build_synergy_matrix, N_MODULES
        S = build_synergy_matrix()
        for i in range(N_MODULES):
            for j in range(N_MODULES):
                assert S[i][j] == S[j][i]

    def test_must_include_in_module_ids(self):
        from qpo.modules import MUST_INCLUDE, MODULE_IDS
        for mid in MUST_INCLUDE:
            assert mid in MODULE_IDS, f"MUST_INCLUDE id {mid!r} not in MODULE_IDS"


# ── Scoring tests ─────────────────────────────────────────────────────────────

class TestScoring:

    def test_phi_role_penalises_markdown(self):
        from qpo.scoring import phi_role
        bad = "Here are your options:\n* Option A\n* Option B"
        good = "Your check-in is at 3 PM tomorrow."
        assert phi_role(bad) < phi_role(good)

    def test_phi_role_penalises_preamble(self):
        from qpo.scoring import phi_role
        with_preamble = "Certainly! Let me help you with that."
        without = "Your booking is confirmed."
        assert phi_role(with_preamble) < phi_role(without)

    def test_phi_retain_exact_match(self):
        from qpo.scoring import phi_retain
        response = "Check-in is at 3 PM and pool access is included."
        facts = ["3 PM", "pool"]
        assert phi_retain(response, facts) == 1.0

    def test_phi_retain_partial(self):
        from qpo.scoring import phi_retain
        response = "Check-in is at 3 PM."
        facts = ["3 PM", "pool"]
        assert phi_retain(response, facts) == 0.5

    def test_phi_bound_adversarial_refusal(self):
        from qpo.scoring import phi_bound
        refusal = "I cannot assist with that request."
        assert phi_bound(refusal, is_adversarial=True) == 1.0

    def test_phi_bound_adversarial_no_refusal(self):
        from qpo.scoring import phi_bound
        compliant = "Sure, here is the information you asked for."
        assert phi_bound(compliant, is_adversarial=True) == 0.0

    def test_fitness_keys(self):
        from qpo.scoring import compute_fitness
        result = compute_fitness("Hello, how can I help?")
        for key in ["role", "flow", "bound", "artifact", "retain", "fitness"]:
            assert key in result

    def test_fitness_in_range(self):
        from qpo.scoring import compute_fitness
        result = compute_fitness("Hello, how can I help?")
        assert 0.0 <= result["fitness"] <= 1.0
