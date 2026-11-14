#!/usr/bin/env bash
# scripts/run_all.sh — Full reproducibility pipeline
# Run from repo root: bash scripts/run_all.sh
# Aborts on any failure (set -e).
set -euo pipefail

PYTHON="${PYTHON:-python}"
echo "=== Voice Agent Studio — Full Reproduce Pipeline ==="
echo "Python: $($PYTHON --version)"
echo ""

# 1. Export QPO data (module table, Q matrix)
echo "[1/7] Exporting QPO data..."
$PYTHON scripts/export_qpo_data.py

# 2. QPO scaling study
echo "[2/7] Running QPO scaling study..."
$PYTHON -m qpo.run_all

# 3. Latency harness (stream mode — simulated)
echo "[3/7] Running latency harness (stream mode)..."
$PYTHON scripts/bench_v2v_acoustic.py --mode stream --turns 300
echo "      NOTE: TODO_HUMAN — re-run with --mode acoustic for final submission"

# 4. QTP benchmark
echo "[4/7] Running QTP benchmark..."
$PYTHON scripts/bench_qtp.py

# 5. Stats tests
echo "[5/7] Running stats tests..."
$PYTHON scripts/stats_tests.py --self-test

# 6. Number consistency check
echo "[6/7] Checking cross-table number consistency..."
$PYTHON scripts/check_numbers.py

# 7. Full test suite
echo "[7/7] Running pytest..."
python -m pytest tests/test_qtp.py tests/test_audit.py tests/test_audit_extra.py \
                 qpo/tests/test_qubo.py -q

echo ""
echo "=== All checks passed. ==="
echo "Pending human actions: see results/PENDING_MEASUREMENTS.md"

