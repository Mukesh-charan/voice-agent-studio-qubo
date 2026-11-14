import os
import sys
from pathlib import Path
import asyncio
import pytest

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Phase 1.6 — import new canonical names
from qpo.task_parallelizer import (
    QuboTaskScheduler,
    QuboScheduleResult,
    TaskDefinition,
    dispatch_parallel_booking,
    compute_dag_metrics,
    # deprecated aliases — also tested below
    QuantumTaskParallelizer,
    QuantumScheduleResult,
    dispatch_quantum_parallel_booking,
)


# ── Helper: standard 10-task workload (from task_table) ─────────────────────

def _make_10_tasks() -> list[TaskDefinition]:
    return [
        TaskDefinition("intent_parse",  "Intent & Slot Extraction",          35.0,  [],               task_type="nlp"),
        TaskDefinition("rag_query",     "BM25 Knowledge Query",              25.0,  [],               task_type="retrieval"),
        TaskDefinition("db_persist",    "SQLite ACID Booking Commit",        45.0,  ["intent_parse"], task_type="db"),
        TaskDefinition("speech_synth",  "Voice Synthesis (Piper/Edge)",     210.0,  ["intent_parse"], task_type="tts"),
        TaskDefinition("google_cal",    "Google Calendar Event API",        340.0,  ["db_persist"],   task_type="google_api"),
        TaskDefinition("google_sheet",  "Google Sheets Row Append",         280.0,  ["db_persist"],   task_type="google_api"),
        TaskDefinition("webhook",       "Outbound Webhook Dispatch",        260.0,  ["db_persist"],   task_type="webhook"),
        TaskDefinition("audit_log",     "Call Journal & Metrics Ingestion",  55.0,  ["db_persist"],   task_type="db"),
        TaskDefinition("crm_sync",      "Enterprise CRM Contact Update",    310.0,  ["db_persist"],   task_type="crm"),
        TaskDefinition("sms_notify",    "Twilio SMS Guest Confirmation",    240.0,  ["db_persist"],   task_type="sms"),
    ]


# ── Phase 1.1 — task_table loads correctly ──────────────────────────────────

def test_task_table_loads():
    """TASKS list has exactly 10 entries, each a TaskDefinition."""
    from qpo.task_table import TASKS
    assert len(TASKS) == 10
    for t in TASKS:
        assert isinstance(t, TaskDefinition)
        assert t.task_id
        assert t.estimated_duration_ms > 0

    ids = [t.task_id for t in TASKS]
    assert "intent_parse" in ids
    assert "speech_synth" in ids
    assert "db_persist" in ids


def test_task_table_speech_synth_depends_on_intent_parse_only():
    """speech_synth must depend only on intent_parse (not db_persist)."""
    from qpo.task_table import TASKS
    ss = next(t for t in TASKS if t.task_id == "speech_synth")
    assert ss.depends_on == ["intent_parse"], (
        f"speech_synth.depends_on should be ['intent_parse'], got {ss.depends_on}"
    )


# ── Phase 1.2 — DAG metrics ──────────────────────────────────────────────────

def test_dag_metrics_invariants():
    """
    critical_path_ms <= wave_makespan_ms <= serial_ms
    sum(durations) == serial_ms
    """
    tasks = _make_10_tasks()
    serial_ms = sum(t.estimated_duration_ms for t in tasks)

    scheduler = QuboTaskScheduler()
    result = scheduler.schedule(tasks, n_stages=3)

    assert abs(result.theoretical_serial_ms - serial_ms) < 1e-6, (
        f"serial_ms mismatch: {result.theoretical_serial_ms} vs {serial_ms}"
    )
    assert result.critical_path_ms <= result.wave_makespan_ms + 1e-6, (
        f"critical_path_ms ({result.critical_path_ms}) > wave_makespan_ms ({result.wave_makespan_ms})"
    )
    assert result.wave_makespan_ms <= result.theoretical_serial_ms + 1e-6, (
        f"wave_makespan_ms ({result.wave_makespan_ms}) > serial_ms ({result.theoretical_serial_ms})"
    )


def test_dag_metrics_serial_sum():
    """sum of durations == theoretical_serial_ms."""
    tasks = _make_10_tasks()
    expected_serial = sum(t.estimated_duration_ms for t in tasks)
    scheduler = QuboTaskScheduler()
    result = scheduler.schedule(tasks, n_stages=3)
    assert abs(result.theoretical_serial_ms - expected_serial) < 1e-6


def test_compute_dag_metrics_critical_path():
    """
    For the 10-task workload, the critical path must be at least
    intent_parse + db_persist + google_cal = 35 + 45 + 340 = 420 ms.
    """
    tasks = _make_10_tasks()
    stage_assignment = {t.task_id: 0 for t in tasks}
    metrics = compute_dag_metrics(tasks, stage_assignment)
    # Critical path: intent_parse(35) -> db_persist(45) -> google_cal(340) = 420
    assert metrics["critical_path_ms"] >= 420.0, (
        f"Expected critical_path_ms >= 420, got {metrics['critical_path_ms']}"
    )


def test_speech_onset_ms():
    """speech_onset_ms == finish time of intent_parse (35 ms) for 10-task workload."""
    tasks = _make_10_tasks()
    stage_assignment = {t.task_id: 0 for t in tasks}
    metrics = compute_dag_metrics(tasks, stage_assignment)
    # speech_synth depends on intent_parse (35 ms), so onset = 35 ms
    assert abs(metrics["speech_onset_ms"] - 35.0) < 1e-6, (
        f"speech_onset_ms should be 35.0, got {metrics['speech_onset_ms']}"
    )


# ── Phase 1.3 — Baselines ────────────────────────────────────────────────────

def test_schedule_topological_layers():
    """Topological layers must be non-empty and respect precedence."""
    tasks = _make_10_tasks()
    scheduler = QuboTaskScheduler()
    layers = scheduler.schedule_topological(tasks)
    assert len(layers) >= 2
    seen = set()
    for layer in layers:
        for t in layer:
            for dep in t.depends_on:
                if dep in {tt.task_id for tt in tasks}:
                    assert dep in seen, f"{dep} not finished before {t.task_id}"
        seen.update(tt.task_id for tt in layer)


def test_schedule_greedy_covers_all_tasks():
    """Greedy schedule must include all 10 tasks exactly once."""
    tasks = _make_10_tasks()
    scheduler = QuboTaskScheduler()
    schedule = scheduler.schedule_greedy(tasks, n_workers=4)
    assert len(schedule) == 10
    sched_ids = {s[0] for s in schedule}
    assert sched_ids == {t.task_id for t in tasks}


def test_schedule_greedy_respects_deps():
    """In greedy schedule, each task starts after its dependencies finish."""
    tasks = _make_10_tasks()
    scheduler = QuboTaskScheduler()
    schedule = scheduler.schedule_greedy(tasks, n_workers=4)
    finish = {tid: fin for tid, _, fin in schedule}
    for tid, start, fin in schedule:
        task = next(t for t in tasks if t.task_id == tid)
        for dep in task.depends_on:
            if dep in finish:
                assert start >= finish[dep] - 1e-6, (
                    f"{tid} starts at {start} but dep {dep} finishes at {finish[dep]}"
                )


def test_schedule_cpsat_returns_or_none():
    """CP-SAT returns a valid schedule or None (if ortools not installed)."""
    tasks = _make_10_tasks()
    scheduler = QuboTaskScheduler()
    result = scheduler.schedule_cpsat(tasks)
    if result is not None:
        assert len(result) == 10
        ids = {r[0] for r in result}
        assert ids == {t.task_id for t in tasks}


@pytest.mark.asyncio
async def test_execute_dag_runs_all():
    """execute_dag fires all tasks and respects event-driven ordering."""
    order: list[str] = []

    async def _make_coro(tid: str):
        async def _coro():
            await asyncio.sleep(0.001)
            order.append(tid)
        return _coro

    tasks = [
        TaskDefinition("a", "A", 10.0, coroutine_func=await _make_coro("a")),
        TaskDefinition("b", "B", 10.0, depends_on=["a"], coroutine_func=await _make_coro("b")),
        TaskDefinition("c", "C", 10.0, depends_on=["a"], coroutine_func=await _make_coro("c")),
    ]
    scheduler = QuboTaskScheduler()
    results = await scheduler.execute_dag(tasks)
    assert "a" in order
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")


# ── Phase 1.6 — deprecated alias tests ──────────────────────────────────────

def test_deprecated_alias_QuantumTaskParallelizer():
    """QuantumTaskParallelizer is an alias for QuboTaskScheduler."""
    assert QuantumTaskParallelizer is QuboTaskScheduler


def test_deprecated_alias_QuantumScheduleResult():
    """QuantumScheduleResult is an alias for QuboScheduleResult."""
    assert QuantumScheduleResult is QuboScheduleResult


def test_deprecated_alias_dispatch():
    """dispatch_quantum_parallel_booking is an alias for dispatch_parallel_booking."""
    assert dispatch_quantum_parallel_booking is dispatch_parallel_booking


# ── Original QUBO + dispatch tests (preserved, updated to new names) ─────────

def test_qtp_scheduling_qubo():
    """Verify QUBO formulation and speedup calculation for concurrent call tasks."""
    qtp = QuboTaskScheduler(use_quantum=False)
    tasks = [
        TaskDefinition("db",     "DB Insert",        50.0),
        TaskDefinition("tts",    "TTS Synthesis",   200.0, can_parallel_with=["db"]),
        TaskDefinition("gcal",   "Google Calendar", 300.0, depends_on=["db"]),
        TaskDefinition("gsheet", "Google Sheet",    250.0, depends_on=["db"], can_parallel_with=["gcal"]),
    ]

    res = qtp.schedule(tasks, n_stages=2)
    assert len(res.stages) >= 1
    assert res.theoretical_speedup > 1.0
    assert res.solver_used in ["simulated_annealing", "tabu_search", "qaoa_fallback_sa"]
    # Phase 1.2 fields populated
    assert res.wave_makespan_ms > 0.0
    assert res.critical_path_ms > 0.0
    # deprecated alias still works
    assert res.theoretical_parallel_ms == res.wave_makespan_ms
    print(f"Test QTP Schedule Speedup: {res.theoretical_speedup}x across {len(res.stages)} stages")


@pytest.mark.asyncio
async def test_dispatch_quantum_parallel_booking():
    """Verify end-to-end parallel execution via dispatch_parallel_booking (and alias)."""
    saved_flag = False
    gcal_flag = False
    synth_flag = False

    def mock_save(agent_id, call_uid, args, agent, messages=None):
        nonlocal saved_flag
        saved_flag = True
        return True, {"id": 99, "name": args.get("name"), "datetime": args.get("datetime")}, ""

    async def mock_google(agent, booking):
        nonlocal gcal_flag
        await asyncio.sleep(0.01)
        gcal_flag = True

    async def mock_synth(text, voice="zira", rate=1.0):
        nonlocal synth_flag
        synth_flag = True
        return b"RIFF_FAKE_WAV_BYTES"

    hooks = {
        "validate_and_save_booking": mock_save,
        "auto_sync_booking_to_google": mock_google,
        "synthesize_speech_bytes": mock_synth,
    }

    agent = {"id": 1, "name": "Test Receptionist", "google_auto_sync_calendar": True}
    booking_args = {"name": "Sanjjey Arumugam", "datetime": "Tomorrow 3pm", "user_confirmed": True}

    res = await dispatch_parallel_booking(
        agent=agent,
        call_uid="test_call_123",
        booking_args=booking_args,
        messages=[],
        hooks=hooks,
        caller_phone="+1234567890",
    )

    assert res["is_valid"] is True
    assert res["booking"]["name"] == "Sanjjey Arumugam"
    assert saved_flag is True
    assert gcal_flag is True
    assert synth_flag is True
    assert res["reply_wav_bytes"] == b"RIFF_FAKE_WAV_BYTES"
    assert res["telemetry"]["theoretical_speedup"] > 1.0

    # Also verify deprecated alias works
    saved_flag = gcal_flag = synth_flag = False
    res2 = await dispatch_quantum_parallel_booking(
        agent=agent,
        call_uid="test_call_456",
        booking_args={"name": "Test User", "datetime": "Friday 5pm", "user_confirmed": True},
        messages=[],
        hooks=hooks,
        caller_phone="+9876543210",
    )
    assert res2["is_valid"] is True
    print("Test Dispatch Parallel Booking: PASSED", res["telemetry"])
