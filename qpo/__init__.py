# qpo/__init__.py
"""
QPO: Quantum Prompt Optimization package.

Sub-modules:
  modules   — prompt module library, conflict/synergy matrices
  scoring   — shared fitness evaluation (Phi_role, Phi_flow, Phi_bound, Phi_artifact, Phi_retain)
  qubo      — QUBO matrix builder + QUBO/Ising conversion with identity verification
  solvers   — brute_force, greedy, simulated_annealing, tabu_search, numpy_eigensolver, qaoa
  assemble  — binary vector -> prompt string
  optimizer — ScheduleOptimizer interface + ClassicalOptimizer + QAOAOptimizer adapters
  run_all   — end-to-end scaling study script
"""

from qpo.modules import MODULES, N_MODULES, PromptModule, get_module
from qpo.scoring import compute_fitness, score_module_selection
from qpo.qubo import build_qubo, qubo_to_ising, verify_ising_identity
from qpo.assemble import assemble_prompt, assemble_from_ids
from qpo.optimizer import (
    ScheduleOptimizer, ClassicalOptimizer, QAOAOptimizer,
    SchedulingProblem, SchedulingSolution,
    scores_to_qubo, validate_solution,
)

# Phase 1.6 — new canonical names
from qpo.task_parallelizer import (
    QuboTaskScheduler,
    QuboScheduleResult,
    TaskDefinition,
    ParallelStage,
    dispatch_parallel_booking,
    compute_dag_metrics,
    build_task_scheduling_qubo,
    # Deprecated aliases (kept for back-compat)
    QuantumTaskParallelizer,
    QuantumScheduleResult,
    dispatch_quantum_parallel_booking,
)

__all__ = [
    # QPO core
    "MODULES", "N_MODULES", "PromptModule", "get_module",
    "compute_fitness", "score_module_selection",
    "build_qubo", "qubo_to_ising", "verify_ising_identity",
    "assemble_prompt", "assemble_from_ids",
    "ScheduleOptimizer", "ClassicalOptimizer", "QAOAOptimizer",
    "SchedulingProblem", "SchedulingSolution",
    "scores_to_qubo", "validate_solution",
    # QTP — new names (Phase 1.6)
    "QuboTaskScheduler", "QuboScheduleResult",
    "TaskDefinition", "ParallelStage",
    "dispatch_parallel_booking",
    "compute_dag_metrics", "build_task_scheduling_qubo",
    # QTP — deprecated aliases
    "QuantumTaskParallelizer", "QuantumScheduleResult",
    "dispatch_quantum_parallel_booking",
]
