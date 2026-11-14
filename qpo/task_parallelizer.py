"""
qpo/task_parallelizer.py — Quantum/QUBO Task Parallelization (QTP) Engine.

Formulates concurrent live-call operations (Local DB Capture, Google Sheets Sync,
Google Calendar Event, Webhook Dispatch, and Confirmation Speech Synthesis)
into a Resource-Constrained Task Scheduling QUBO.

Solves the optimal concurrency DAG using QAOA quantum simulation or
fast Simulated Annealing / Tabu Search, then executes non-conflicting tasks
simultaneously via asyncio.gather().

Phase 1 EAAI fixes applied:
  1.2 — QuantumScheduleResult gains wave_makespan_ms, critical_path_ms,
         speech_onset_ms + compute_dag_metrics() helper.
  1.3 — QuboTaskScheduler (renamed) adds execute_dag(), schedule_topological(),
         schedule_greedy(), schedule_cpsat() baselines.
  1.4 — build_task_scheduling_qubo() gains concurrency_cap, gpu_tasks,
         google_api_cap capacity constraints.
  1.6 — Class/function renames; old names kept as deprecated aliases.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

import numpy as np


# ── Task Specification ────────────────────────────────────────────────────────

@dataclass
class TaskDefinition:
    """Definition of an operational unit in a voice call workflow."""
    task_id: str
    name: str
    estimated_duration_ms: float
    depends_on: list[str] = field(default_factory=list)
    can_parallel_with: list[str] = field(default_factory=list)
    task_type: str = ""                      # e.g. "nlp", "tts", "google_api"
    coroutine_func: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)


@dataclass
class ParallelStage:
    stage_idx: int
    tasks: list[TaskDefinition] = field(default_factory=list)


@dataclass
class QuboScheduleResult:
    """
    Result of a QUBO/quantum task scheduling pass.

    Fields
    ------
    wave_makespan_ms
        Makespan of the scheduled wave plan (sum of per-stage max durations).
        Replaces the former ``theoretical_parallel_ms``.
    critical_path_ms
        Length of the longest dependency chain through the DAG (computed by DP).
    speech_onset_ms
        Wall-clock time until the first TTS audio chunk can start
        (= finish time of the last dependency of the TTS task).
    theoretical_parallel_ms
        **Deprecated** alias for ``wave_makespan_ms``; kept for back-compat.
    """
    stages: list[ParallelStage]
    objective: float
    solver_used: str
    quantum_hardware_used: bool
    wall_time_s: float
    theoretical_serial_ms: float
    # New canonical fields (Phase 1.2)
    wave_makespan_ms: float = 0.0
    critical_path_ms: float = 0.0
    speech_onset_ms: float = 0.0
    theoretical_speedup: float = 1.0
    metadata: dict = field(default_factory=dict)

    # Deprecated alias — do not use in new code
    @property
    def theoretical_parallel_ms(self) -> float:  # noqa: D401
        """Deprecated: use wave_makespan_ms."""
        return self.wave_makespan_ms

    @theoretical_parallel_ms.setter
    def theoretical_parallel_ms(self, value: float) -> None:
        self.wave_makespan_ms = value


# Deprecated alias for the dataclass itself (Phase 1.6)
QuantumScheduleResult = QuboScheduleResult


# ── DAG Metrics (Phase 1.2) ───────────────────────────────────────────────────

def compute_dag_metrics(
    tasks: list[TaskDefinition],
    stage_assignment: dict[str, int],
) -> dict:
    """
    Compute DAG-level scheduling metrics.

    Parameters
    ----------
    tasks:
        Full list of task definitions (must include estimated_duration_ms and
        depends_on).
    stage_assignment:
        Mapping {task_id -> stage_index} produced by the scheduler.

    Returns
    -------
    dict with keys:
        wave_makespan_ms   — sum of per-stage max durations
        critical_path_ms   — longest dependency chain (DP over DAG)
        speech_onset_ms    — finish time of TTS task's last dependency
        serial_ms          — sum of all task durations
    """
    dur: dict[str, float] = {t.task_id: t.estimated_duration_ms for t in tasks}
    deps: dict[str, list[str]] = {t.task_id: list(t.depends_on) for t in tasks}

    # --- wave_makespan_ms: sum of max duration per stage ---
    stages_max: dict[int, float] = defaultdict(float)
    for t in tasks:
        s = stage_assignment.get(t.task_id, 0)
        stages_max[s] = max(stages_max[s], t.estimated_duration_ms)
    wave_makespan_ms = sum(stages_max.values())

    # --- critical_path_ms: DP (finish_time[v] = dur[v] + max(finish[u]) for u in deps) ---
    finish: dict[str, float] = {}

    def _finish(tid: str) -> float:
        if tid in finish:
            return finish[tid]
        pred_max = max((_finish(d) for d in deps.get(tid, []) if d in dur), default=0.0)
        finish[tid] = dur.get(tid, 0.0) + pred_max
        return finish[tid]

    for t in tasks:
        _finish(t.task_id)
    critical_path_ms = max(finish.values(), default=0.0)

    # --- speech_onset_ms: finish time of last dep of the TTS task ---
    tts_task = next((t for t in tasks if t.task_type == "tts" or t.task_id == "speech_synth"), None)
    if tts_task and tts_task.depends_on:
        speech_onset_ms = max(
            (_finish(d) for d in tts_task.depends_on if d in dur), default=0.0
        )
    else:
        speech_onset_ms = 0.0

    serial_ms = sum(t.estimated_duration_ms for t in tasks)

    return {
        "wave_makespan_ms": round(wave_makespan_ms, 3),
        "critical_path_ms": round(critical_path_ms, 3),
        "speech_onset_ms": round(speech_onset_ms, 3),
        "serial_ms": round(serial_ms, 3),
    }


# ── QUBO Construction for Task Parallelization ───────────────────────────────

def build_task_scheduling_qubo(
    tasks: list[TaskDefinition],
    n_stages: int = 2,
    penalty_onehot: float = 25.0,
    penalty_precedence: float = 40.0,
    reward_concurrency: float = 10.0,
    # Phase 1.4 — capacity constraints
    concurrency_cap: int = 4,
    gpu_tasks: list[str] = None,
    google_api_cap: int = 2,
) -> tuple[np.ndarray, list[tuple[str, int]]]:
    """
    Constructs a QUBO matrix Q for scheduling N tasks across K execution stages.

    Binary variable x_{i, k} = 1 iff Task i is scheduled in Stage k.
    Objective: Minimise makespan while enforcing:
      1. Every task runs in exactly one stage (one-hot per task).
      2. If task j depends on task i, stage(j) >= stage(i) + 1.
      3. Non-conflicting I/O tasks are rewarded for sharing the same parallel stage.
      4. Earlier stages penalised less to promote eager execution.
      5. (Phase 1.4) At most ``concurrency_cap`` tasks per stage (slack-bit penalty).
      6. (Phase 1.4) GPU tasks must not share a stage (pairwise penalty).
      7. (Phase 1.4) At most ``google_api_cap`` google_api tasks per stage.
    """
    if gpu_tasks is None:
        gpu_tasks = []

    n_tasks = len(tasks)
    n_vars = n_tasks * n_stages
    task_idx_map = {t.task_id: i for i, t in enumerate(tasks)}

    var_map: list[tuple[str, int]] = []
    for i in range(n_tasks):
        for k in range(n_stages):
            var_map.append((tasks[i].task_id, k))

    def var_index(t_idx: int, s_idx: int) -> int:
        return t_idx * n_stages + s_idx

    Q = np.zeros((n_vars, n_vars), dtype=float)

    # 1. One-hot per task: (sum_k x_{i,k} - 1)^2
    for i in range(n_tasks):
        for k in range(n_stages):
            idx = var_index(i, k)
            Q[idx, idx] += -penalty_onehot
            # Eager bias: slight preference for earlier stages
            Q[idx, idx] += 0.2 * k * (tasks[i].estimated_duration_ms / 50.0)

        for k in range(n_stages):
            for l in range(k + 1, n_stages):
                idx_k = var_index(i, k)
                idx_l = var_index(i, l)
                Q[idx_k, idx_l] += 2.0 * penalty_onehot

    # 2. Precedence constraints: If j depends on i, stage(j) must be > stage(i)
    for j_idx, task_j in enumerate(tasks):
        for dep_id in task_j.depends_on:
            if dep_id not in task_idx_map:
                continue
            i_idx = task_idx_map[dep_id]

            for k in range(n_stages):
                for m in range(k + 1):  # m <= k violates dependency
                    idx_i = var_index(i_idx, k)
                    idx_j = var_index(j_idx, m)
                    if idx_i == idx_j:
                        continue
                    low, high = min(idx_i, idx_j), max(idx_i, idx_j)
                    Q[low, high] += penalty_precedence

    # 3. Concurrency synergy reward
    for i in range(n_tasks):
        for j in range(i + 1, n_tasks):
            t_i = tasks[i]
            t_j = tasks[j]

            is_parallel_safe = (
                t_j.task_id in t_i.can_parallel_with
                or t_i.task_id in t_j.can_parallel_with
                or (not t_i.depends_on and not t_j.depends_on and t_i.task_id != t_j.task_id)
            )
            if t_i.task_id in t_j.depends_on or t_j.task_id in t_i.depends_on:
                is_parallel_safe = False

            if is_parallel_safe:
                for k in range(n_stages):
                    idx_i = var_index(i, k)
                    idx_j = var_index(j, k)
                    low, high = min(idx_i, idx_j), max(idx_i, idx_j)
                    Q[low, high] -= reward_concurrency

    # 4. (Phase 1.4) Concurrency cap: penalise pairs within same stage when
    #    total tasks in that stage would exceed concurrency_cap.
    #    Simple pairwise approach: add penalty for every (i, j, k) triple
    #    beyond the cap threshold.  We approximate by penalising all pairs
    #    whose combined stage assignment exceeds cap/N ratio.
    cap_penalty = penalty_onehot * 0.5
    if concurrency_cap < n_tasks:
        for k in range(n_stages):
            for i in range(n_tasks):
                for j in range(i + 1, n_tasks):
                    # Penalise sharing a stage if it increases density
                    idx_i = var_index(i, k)
                    idx_j = var_index(j, k)
                    low, high = min(idx_i, idx_j), max(idx_i, idx_j)
                    # Only add extra penalty when tasks per stage > cap
                    if n_tasks / n_stages > concurrency_cap:
                        Q[low, high] += cap_penalty / n_tasks

    # 5. (Phase 1.4) GPU tasks: pairwise penalty within same stage
    gpu_penalty = penalty_precedence * 0.8
    gpu_indices = [task_idx_map[tid] for tid in gpu_tasks if tid in task_idx_map]
    for gi in range(len(gpu_indices)):
        for gj in range(gi + 1, len(gpu_indices)):
            for k in range(n_stages):
                idx_i = var_index(gpu_indices[gi], k)
                idx_j = var_index(gpu_indices[gj], k)
                low, high = min(idx_i, idx_j), max(idx_i, idx_j)
                Q[low, high] += gpu_penalty

    # 6. (Phase 1.4) Google API cap: at most google_api_cap tasks per stage
    gapi_indices = [
        task_idx_map[t.task_id]
        for t in tasks
        if t.task_type == "google_api" and t.task_id in task_idx_map
    ]
    gapi_penalty = penalty_onehot * 0.6
    if len(gapi_indices) > google_api_cap:
        for gi in range(len(gapi_indices)):
            for gj in range(gi + 1, len(gapi_indices)):
                for k in range(n_stages):
                    idx_i = var_index(gapi_indices[gi], k)
                    idx_j = var_index(gapi_indices[gj], k)
                    low, high = min(idx_i, idx_j), max(idx_i, idx_j)
                    Q[low, high] += gapi_penalty

    return Q, var_map


# ── QUBO Task Scheduler (Phase 1.6 rename) ───────────────────────────────────

class QuboTaskScheduler:
    """
    Schedules and parallelizes operational tasks during active voice calls
    using QAOA quantum simulation or fast Simulated Annealing on QUBO.

    Also provides classical baseline schedulers:
      - schedule_topological(): Kahn-layer DAG scheduling via asyncio.gather per layer.
      - schedule_greedy():      Longest-duration-first list scheduling.
      - schedule_cpsat():       CP-SAT optimal (requires ortools; skipped if absent).
      - execute_dag():          Event-driven execution respecting exact DAG dependencies.
    """

    def __init__(self, use_quantum: bool = False):
        self.use_quantum = use_quantum

    # ── QUBO / QAOA schedule ─────────────────────────────────────────────────

    def schedule(
        self,
        tasks: list[TaskDefinition],
        n_stages: int = 2,
        timeout: float = 2.0,
    ) -> QuboScheduleResult:
        t0 = time.perf_counter()

        if not tasks:
            return QuboScheduleResult(
                stages=[],
                objective=0.0,
                solver_used="empty",
                quantum_hardware_used=False,
                wall_time_s=0.0,
                theoretical_serial_ms=0.0,
                wave_makespan_ms=0.0,
                critical_path_ms=0.0,
                speech_onset_ms=0.0,
                theoretical_speedup=1.0,
            )

        # 1. Build Scheduling QUBO
        Q, var_map = build_task_scheduling_qubo(tasks, n_stages=n_stages)
        n_vars = len(var_map)
        Q_max = -Q

        solver_name = "simulated_annealing"
        quantum_used = False

        if self.use_quantum and n_vars <= 16:
            try:
                from qpo.solvers import qaoa
                res = qaoa(Q_max, p=1, shots=256, maxiter=20)
                if res.objective != float("-inf") and "error" not in res.metadata:
                    sol_x = res.x
                    solver_name = res.solver
                    quantum_used = True
                else:
                    from qpo.solvers import simulated_annealing
                    res = simulated_annealing(Q_max, n_steps=2000)
                    sol_x = res.x
                    solver_name = "qaoa_fallback_sa"
            except Exception:
                from qpo.solvers import simulated_annealing
                res = simulated_annealing(Q_max, n_steps=2000)
                sol_x = res.x
                solver_name = "classical_sa"
        else:
            from qpo.solvers import simulated_annealing
            res = simulated_annealing(Q_max, n_steps=2000)
            sol_x = res.x
            solver_name = "simulated_annealing"

        elapsed = time.perf_counter() - t0

        # 2. Decode assignments
        stages_dict: dict[int, list[TaskDefinition]] = {k: [] for k in range(n_stages)}

        for i, task in enumerate(tasks):
            stage_vals = []
            for k in range(n_stages):
                var_idx = i * n_stages + k
                val = sol_x[var_idx] if var_idx < len(sol_x) else 0.0
                stage_vals.append(val)

            chosen_stage = int(np.argmax(stage_vals)) if any(v > 0 for v in stage_vals) else 0

            # Dependency invariant
            max_dep_stage = -1
            for dep_id in task.depends_on:
                for s_k, s_tasks in stages_dict.items():
                    if any(st.task_id == dep_id for st in s_tasks):
                        max_dep_stage = max(max_dep_stage, s_k)

            if max_dep_stage >= chosen_stage:
                chosen_stage = min(n_stages - 1, max_dep_stage + 1)

            stages_dict[chosen_stage].append(task)

        # 3. Format output
        scheduled_stages: list[ParallelStage] = []
        for k in range(n_stages):
            if stages_dict[k]:
                scheduled_stages.append(ParallelStage(stage_idx=k, tasks=stages_dict[k]))

        # 4. Compute DAG metrics
        stage_assignment = {t.task_id: k for k, tl in stages_dict.items() for t in tl}
        metrics = compute_dag_metrics(tasks, stage_assignment)

        serial_ms = metrics["serial_ms"]
        wave_ms = metrics["wave_makespan_ms"]
        speedup = (serial_ms / wave_ms) if wave_ms > 0 else 1.0

        return QuboScheduleResult(
            stages=scheduled_stages,
            objective=float(res.objective),
            solver_used=solver_name,
            quantum_hardware_used=quantum_used,
            wall_time_s=elapsed,
            theoretical_serial_ms=serial_ms,
            wave_makespan_ms=wave_ms,
            critical_path_ms=metrics["critical_path_ms"],
            speech_onset_ms=metrics["speech_onset_ms"],
            theoretical_speedup=round(speedup, 2),
            metadata={
                "n_tasks": len(tasks),
                "n_stages": len(scheduled_stages),
            },
        )

    # ── Classical baseline: topological (Kahn layer) ─────────────────────────

    def schedule_topological(
        self, tasks: list[TaskDefinition]
    ) -> list[list[TaskDefinition]]:
        """
        Kahn-level layering: group tasks into BFS layers where all predecessors
        of a task are in earlier layers.  Returns a list of layers, each layer
        being a list of TaskDefinition objects that can run concurrently.
        """
        in_degree: dict[str, int] = {t.task_id: 0 for t in tasks}
        adj: dict[str, list[str]] = defaultdict(list)

        task_map = {t.task_id: t for t in tasks}

        for t in tasks:
            for dep in t.depends_on:
                if dep in in_degree:
                    in_degree[t.task_id] += 1
                    adj[dep].append(t.task_id)

        queue: deque[str] = deque(tid for tid, deg in in_degree.items() if deg == 0)
        layers: list[list[TaskDefinition]] = []

        while queue:
            layer_size = len(queue)
            layer: list[TaskDefinition] = []
            for _ in range(layer_size):
                tid = queue.popleft()
                layer.append(task_map[tid])
                for child in adj[tid]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)
            layers.append(layer)

        return layers

    async def run_topological(
        self, tasks: list[TaskDefinition]
    ) -> dict[str, Any]:
        """Execute the topological layers: asyncio.gather per layer."""
        layers = self.schedule_topological(tasks)
        results: dict[str, Any] = {}
        for layer in layers:
            coros = []
            tids = []
            for t in layer:
                if t.coroutine_func is not None:
                    coros.append(t.coroutine_func(*t.args, **t.kwargs))
                    tids.append(t.task_id)
            if coros:
                raw = await asyncio.gather(*coros, return_exceptions=True)
                for tid, out in zip(tids, raw):
                    results[tid] = out
        return results

    # ── Classical baseline: greedy list scheduling ───────────────────────────

    def schedule_greedy(
        self, tasks: list[TaskDefinition], n_workers: int = 4
    ) -> list[tuple[str, float, float]]:
        """
        Longest-duration-first (LDF) list scheduling on ``n_workers`` parallel
        workers.

        Algorithm
        ---------
        1. Build a topological order of the DAG.
        2. At each scheduling step, collect all *ready* tasks — tasks whose
           dependencies have all been assigned a finish time.
        3. Among the ready tasks, pick the one with the greatest
           ``estimated_duration_ms`` (longest job first) to minimise idle gaps
           on the critical path.
        4. Assign it to the worker whose current finish time is earliest
           (classic list-scheduling heuristic).
        5. Repeat until all tasks are scheduled.

        Returns a list of (task_id, start_ms, finish_ms) triples in scheduling
        order.  The final makespan is ``max(finish_ms)``.
        """
        task_map = {t.task_id: t for t in tasks}
        finish_time: dict[str, float] = {}
        worker_free: list[float] = [0.0] * n_workers
        schedule_order: list[tuple[str, float, float]] = []
        remaining = set(task_map.keys())

        while remaining:
            # Collect ready tasks (all deps finished)
            ready = [
                tid for tid in remaining
                if all(d in finish_time for d in task_map[tid].depends_on
                       if d in task_map)
            ]
            if not ready:
                # Should not happen in a valid DAG; break to avoid infinite loop
                break
            # Sort by duration descending (longest first)
            ready.sort(key=lambda tid: task_map[tid].estimated_duration_ms, reverse=True)
            chosen = ready[0]
            task = task_map[chosen]

            # Earliest worker
            earliest_worker = int(np.argmin(worker_free))
            dep_ready = max(
                (finish_time[d] for d in task.depends_on if d in finish_time),
                default=0.0,
            )
            start = max(worker_free[earliest_worker], dep_ready)
            finish = start + task.estimated_duration_ms

            worker_free[earliest_worker] = finish
            finish_time[chosen] = finish
            schedule_order.append((chosen, round(start, 3), round(finish, 3)))
            remaining.remove(chosen)

        return schedule_order

    # ── CP-SAT optimal baseline (Phase 1.3) ──────────────────────────────────

    def schedule_cpsat(
        self,
        tasks: list[TaskDefinition],
        horizon_ms: float = 10_000.0,
    ) -> Optional[list[tuple[str, float, float]]]:
        """
        Optimal makespan scheduling via Google OR-Tools CP-SAT.

        Requires ``ortools`` (``pip install ortools``).  Returns ``None``
        gracefully if ortools is not installed.

        Returns a list of (task_id, start_ms, finish_ms) sorted by start time,
        or ``None`` if ortools is unavailable or infeasible.
        """
        try:
            from ortools.sat.python import cp_model  # type: ignore
        except ImportError:
            return None

        model = cp_model.CpModel()
        horizon = int(horizon_ms)
        task_map = {t.task_id: t for t in tasks}

        intervals: dict[str, Any] = {}
        starts: dict[str, Any] = {}
        ends: dict[str, Any] = {}

        for t in tasks:
            dur = int(t.estimated_duration_ms)
            start = model.NewIntVar(0, horizon, f"start_{t.task_id}")
            end = model.NewIntVar(0, horizon, f"end_{t.task_id}")
            interval = model.NewIntervalVar(start, dur, end, f"interval_{t.task_id}")
            starts[t.task_id] = start
            ends[t.task_id] = end
            intervals[t.task_id] = interval

        # Precedence constraints
        for t in tasks:
            for dep in t.depends_on:
                if dep in task_map:
                    model.Add(starts[t.task_id] >= ends[dep])

        # Minimise makespan
        makespan = model.NewIntVar(0, horizon, "makespan")
        model.AddMaxEquality(makespan, list(ends.values()))
        model.Minimize(makespan)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            result = []
            for t in tasks:
                s = solver.Value(starts[t.task_id])
                e = solver.Value(ends[t.task_id])
                result.append((t.task_id, float(s), float(e)))
            result.sort(key=lambda x: x[1])
            return result
        return None

    # ── Event-driven DAG execution (Phase 1.3) ───────────────────────────────

    async def execute_dag(
        self, tasks: list[TaskDefinition]
    ) -> dict[str, Any]:
        """
        Execute tasks as soon as all their dependencies finish, using
        asyncio.Event objects — one per task.  This is the most precise
        possible parallel execution: each task starts the instant its last
        dependency completes, without waiting for a full wave/layer boundary.

        Returns a dict of {task_id: result_or_exception}.
        """
        events: dict[str, asyncio.Event] = {t.task_id: asyncio.Event() for t in tasks}
        results: dict[str, Any] = {}
        task_map = {t.task_id: t for t in tasks}

        async def _run(t: TaskDefinition) -> None:
            # Wait for all dependencies
            for dep_id in t.depends_on:
                if dep_id in events:
                    await events[dep_id].wait()

            # Execute coroutine if provided
            if t.coroutine_func is not None:
                try:
                    out = await t.coroutine_func(*t.args, **t.kwargs)
                    results[t.task_id] = out
                except Exception as exc:
                    results[t.task_id] = exc
            else:
                results[t.task_id] = None

            # Signal dependents
            events[t.task_id].set()

        await asyncio.gather(*(_run(t) for t in tasks))
        return results

    # ── QUBO execute (unchanged from original) ────────────────────────────────

    async def execute(
        self,
        schedule_result: QuboScheduleResult,
    ) -> dict[str, Any]:
        """
        Executes scheduled stages sequentially, running all tasks within
        each stage concurrently via asyncio.gather().
        """
        execution_results: dict[str, Any] = {}
        stage_timings: list[dict] = []

        for stage in schedule_result.stages:
            st_t0 = time.perf_counter()
            coros = []
            task_ids = []

            for task in stage.tasks:
                if task.coroutine_func is not None:
                    coros.append(task.coroutine_func(*task.args, **task.kwargs))
                    task_ids.append(task.task_id)

            if coros:
                raw_outputs = await asyncio.gather(*coros, return_exceptions=True)
                for tid, out in zip(task_ids, raw_outputs):
                    if isinstance(out, Exception):
                        execution_results[tid] = {"status": "error", "error": str(out)}
                    else:
                        execution_results[tid] = out

            st_elapsed = (time.perf_counter() - st_t0) * 1000.0
            stage_timings.append({
                "stage_idx": stage.stage_idx,
                "tasks": [t.task_id for t in stage.tasks],
                "duration_ms": round(st_elapsed, 2),
            })

        return {
            "results": execution_results,
            "timings": stage_timings,
            "speedup": schedule_result.theoretical_speedup,
            "solver": schedule_result.solver_used,
        }


# Phase 1.6 deprecated alias
QuantumTaskParallelizer = QuboTaskScheduler


# ── High-Level Parallel Booking Dispatcher ───────────────────────────────────

async def dispatch_parallel_booking(
    agent: dict,
    call_uid: Optional[str],
    booking_args: dict,
    messages: list,
    hooks: dict[str, Any],
    caller_phone: str = "",
    use_quantum: bool = False,
) -> dict[str, Any]:
    """
    Parallel Booking Dispatcher.

    Instead of a blocking serial queue:
      Listen -> Transcribe -> DB Insert -> Google Sheets -> Google Calendar
              -> Webhook -> LLM -> TTS
    this builds an optimal concurrency wave:
      - Wave 0: Local SQLite DB ACID capture + Eager TTS pre-synthesis
      - Wave 1 (Concurrent): Google Calendar + Google Sheets + Webhook
    Returns booking data, pre-rendered speech audio, and execution telemetry.
    """
    t0 = time.perf_counter()
    agent_id = agent.get("id", 1)

    # 1. Fill caller phone if missing
    if not booking_args.get("phone") and caller_phone and caller_phone != "unknown":
        booking_args["phone"] = caller_phone

    # 2. Local DB Validation & Persistence
    db_save_fn = hooks.get("validate_and_save_booking")
    booking_holder: dict[str, Any] = {"is_valid": False, "booking": None, "err_msg": ""}

    async def _task_db_save() -> dict:
        if not db_save_fn:
            return {"status": "skipped", "reason": "no db_save_fn"}
        is_valid, booking, err_msg = db_save_fn(agent_id, call_uid, booking_args, agent, messages=messages)
        booking_holder["is_valid"] = is_valid
        booking_holder["booking"] = booking
        booking_holder["err_msg"] = err_msg
        return {"status": "success" if is_valid else "rejected", "booking": booking, "error": err_msg}

    # 3. Google Suite Sync
    auto_sync_fn = hooks.get("auto_sync_booking_to_google")

    async def _task_google_sync() -> dict:
        if not auto_sync_fn or not booking_holder.get("booking"):
            return {"status": "skipped"}
        try:
            await auto_sync_fn(agent, booking_holder["booking"])
            return {"status": "synced"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    # 4. Webhook Dispatch
    fire_webhook_fn = hooks.get("fire_webhook")
    booking_payload_fn = hooks.get("booking_payload")

    async def _task_webhook() -> dict:
        hook_url = (agent.get("booking_webhook") or "").strip()
        if not hook_url or not fire_webhook_fn or not booking_holder.get("booking"):
            return {"status": "skipped"}
        try:
            b = booking_holder["booking"]
            payload = booking_payload_fn(agent, b) if booking_payload_fn else b
            await fire_webhook_fn(hook_url, payload)
            return {"status": "delivered"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    # 5. Confirmation Voice Speech Synthesis
    synth_fn = hooks.get("synthesize_speech_bytes")
    guest_name = booking_args.get("name") or "there"
    guest_dt = booking_args.get("datetime") or "your requested time"
    confirmation_text = f"You're all set, {guest_name}! Your booking for {guest_dt} is confirmed."

    async def _task_speech_synth() -> dict:
        if not synth_fn:
            return {"status": "skipped", "text": confirmation_text}
        try:
            voice = agent.get("voice_name") or "zira"
            rate = float(agent.get("rate") or 1.0)
            wav_bytes = await synth_fn(confirmation_text, voice=voice, rate=rate)
            return {"status": "synthesized", "wav_bytes": wav_bytes, "text": confirmation_text}
        except Exception as e:
            return {"status": "failed", "error": str(e), "text": confirmation_text}

    # 6. Define Tasks
    tasks = [
        TaskDefinition(
            task_id="db_save",
            name="ACID SQLite Transaction",
            estimated_duration_ms=45.0,
            depends_on=[],
            can_parallel_with=["speech_synth"],
            coroutine_func=_task_db_save,
        ),
        TaskDefinition(
            task_id="speech_synth",
            name="Confirmation Voice Synthesis (TTS)",
            estimated_duration_ms=210.0,
            depends_on=[],
            can_parallel_with=["db_save", "google_sync", "webhook"],
            coroutine_func=_task_speech_synth,
        ),
        TaskDefinition(
            task_id="google_sync",
            name="Google Sheets & Calendar Sync",
            estimated_duration_ms=350.0,
            depends_on=["db_save"],
            can_parallel_with=["webhook", "speech_synth"],
            coroutine_func=_task_google_sync,
        ),
        TaskDefinition(
            task_id="webhook",
            name="External Outbound Webhook",
            estimated_duration_ms=280.0,
            depends_on=["db_save"],
            can_parallel_with=["google_sync", "speech_synth"],
            coroutine_func=_task_webhook,
        ),
    ]

    # 7. Schedule & Execute
    scheduler = QuboTaskScheduler(use_quantum=use_quantum)
    schedule_plan = scheduler.schedule(tasks, n_stages=2, timeout=2.0)
    exec_outcome = await scheduler.execute(schedule_plan)

    total_wall_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "is_valid": booking_holder["is_valid"],
        "booking": booking_holder["booking"],
        "err_msg": booking_holder["err_msg"],
        "reply_text": confirmation_text,
        "reply_wav_bytes": exec_outcome["results"].get("speech_synth", {}).get("wav_bytes"),
        "telemetry": {
            "wall_time_ms": round(total_wall_ms, 2),
            "theoretical_speedup": schedule_plan.theoretical_speedup,
            "solver_used": schedule_plan.solver_used,
            "quantum_hardware_used": schedule_plan.quantum_hardware_used,
            "stages_executed": len(schedule_plan.stages),
            "timings": exec_outcome["timings"],
        },
    }


# Phase 1.6 deprecated alias
dispatch_quantum_parallel_booking = dispatch_parallel_booking
