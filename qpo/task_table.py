"""
qpo/task_table.py — Canonical 10-task workload definition for QTP benchmarks.

Loads the single source-of-truth task table from results/qtp_tasks.csv and
exposes a ``TASKS`` list of :class:`TaskDefinition` instances.

The CSV is generated once (source=mock) using the duration values from
``scripts/bench_qtp.py``'s ``workload_templates``.  Real hardware measurements
should update the CSV; the code here just reads it.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from qpo.task_parallelizer import TaskDefinition

_CSV_PATH = Path(__file__).parent.parent / "results" / "qtp_tasks.csv"


def _load_tasks(csv_path: Path = _CSV_PATH) -> List[TaskDefinition]:
    """Parse *qtp_tasks.csv* into a list of :class:`TaskDefinition` objects."""
    tasks: List[TaskDefinition] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            depends_on: list[str] = (
                [d.strip() for d in row["depends_on"].split(",") if d.strip()]
                if row.get("depends_on", "").strip()
                else []
            )
            tasks.append(
                TaskDefinition(
                    task_id=row["task_id"].strip(),
                    name=row["name"].strip(),
                    estimated_duration_ms=float(row["duration_p50_ms"]),
                    depends_on=depends_on,
                )
            )
    return tasks


#: Canonical 10-task voice-agent workload loaded from results/qtp_tasks.csv.
TASKS: List[TaskDefinition] = _load_tasks()

__all__ = ["TASKS", "_load_tasks"]
