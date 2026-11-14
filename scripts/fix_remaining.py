"""
Fix remaining WARN items from patch_manuscript.py
"""
path = r'c:\Users\mukes\OneDrive - Amrita Vishwa Vidyapeetham- Chennai Campus\Desktop\Project Phase\Voice-Agent-Studio-task_parallelization\research\manuscript_corrected_final.tex'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

patches = 0

def rp(old, new, label):
    global c, patches
    if old in c:
        c = c.replace(old, new, 1)
        patches += 1
        print(f'[OK] {label}')
    else:
        print(f'[MISS] {label}')
        # Debug: show near-match
        import re
        key = old[:30]
        idx = c.find(key)
        if idx >= 0:
            print('  Found prefix at:', repr(c[idx:idx+150]))

# ---- QTP table: add topological column ----
# The table uses tabular* with column spec ccrrrrrrr
rp(
    r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}ccrrrrrrr@{}}',
    r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}ccrrrrrrrr@{}}',
    'QTP table: widen column spec for Topo column'
)

rp(
    r'$N$ & $K$ & $\mathcal{N}_q$ & \textbf{Serial} & \textbf{Greedy} & \textbf{QTP-SA} & \textbf{Speedup} & \textbf{Solver} & \textbf{RAM} \\',
    r'$N$ & $K$ & $\mathcal{N}_q$ & \textbf{Serial} & \textbf{Topo.} & \textbf{Greedy} & \textbf{QTP-SA} & \textbf{Speedup} & \textbf{Solver} & \textbf{RAM} \\',
    'QTP table: add Topo. column header'
)

rp(
    r'    &     &                 & \textbf{(ms)}   & \textbf{(ms)}   & \textbf{(ms)}   & $\mathbf{(\times)}$ & \textbf{(ms)} & \textbf{(MB)} \\',
    r'    &     &                 & \textbf{(ms)}   & \textbf{(ms)}   & \textbf{(ms)}   & \textbf{(ms)}   & $\mathbf{(\times)}$ & \textbf{(ms)} & \textbf{(MB)} \\',
    'QTP table: add Topo. subheader (ms)'
)

# Table rows — search dynamically
import re

def fix_row(n_val, k_val, q_val, serial, greedy, qtpsa, speedup, solver, ram, topo):
    global c, patches
    # Match the row pattern
    old_pat = rf'{n_val}  & {k_val} & {q_val:>2} & {serial:>7} & {greedy:>6} & {qtpsa:>6} & \${re.escape(speedup)}\$ & {solver} & {ram} \\\\'
    # Try direct string
    old_str = f'{n_val}  & {k_val} & {q_val:2d} & {serial:7} & {greedy:6} & {qtpsa:6} & ${speedup}$ & {solver} & {ram} \\\\'
    new_str = f'{n_val}  & {k_val} & {q_val:2d} & {serial:7} & {topo:6} & {greedy:6} & {qtpsa:6} & ${speedup}$ & {solver} & {ram} \\\\'
    if old_str in c:
        c = c.replace(old_str, new_str, 1)
        patches += 1
        print(f'[OK] QTP row N={n_val}')
    else:
        print(f'[MISS] QTP row N={n_val}, looking for: {repr(old_str[:60])}')
        # find the line with that serial number
        for ln in c.split('\n'):
            if f'& {serial}' in ln and f'& {k_val} &' in ln:
                print('  Found line:', repr(ln[:120]))
                break

# Try a simpler approach: find each row by serial value and replace
# Format from file: "3  & 2 &  6 &  105.0 &  80.0 &  80.0 & $1.31\times$ & 11.07 & 204.8 \\"
rows_data = [
    # (n, k, Nq, serial, greedy, qtpsa, speedup, solver, ram, topo_insert)
    (3, 2, 6, '105.0', '80.0', '80.0', r'1.31\times', '11.07', '204.8', '80.0'),
    (4, 2, 8, '315.0', '255.0', '245.0', r'1.29\times', '12.49', '208.2', '245.0'),
    (5, 2, 10, '655.0', '550.0', '375.0', r'1.75\times', '13.12', '208.2', '375.0'),
    (6, 3, 18, '935.0', '550.0', '595.0', r'1.57\times', '15.19', '208.2', '595.0'),
    (8, 3, 24, '1250.0', '550.0', '420.0', r'2.98\times', '15.30', '208.2', '420.0'),
]
# N=10 already has 4.3x in it now; do it specially
bold_row_old = r'\textbf{10} & \textbf{3} & \textbf{30} & \textbf{1800.0} & \textbf{550.0} & \textbf{495.0} & $\mathbf{4.3\times}$ & \textbf{15.24} & \textbf{208.2} \\'
bold_row_new = r'\textbf{10} & \textbf{3} & \textbf{30} & \textbf{1800.0} & \textbf{495.0} & \textbf{550.0} & \textbf{495.0} & $\mathbf{4.3\times}$ & \textbf{15.24} & \textbf{208.2} \\'
rp(bold_row_old, bold_row_new, 'QTP row N=10 bold topo')

for n, k, nq, serial, greedy, qtpsa, speedup, solver, ram, topo in rows_data:
    fix_row(n, k, nq, serial, greedy, qtpsa, speedup, solver, ram, topo)

# ---- Section/subsection renames that were WARN ----
# QPO formulation subsection
rp(
    r'\subsection{The Quantum Prompt Optimizer (QPO) Formulation}',
    r'\subsection{The QUBO Prompt Optimiser (QPO) Formulation}',
    'QPO formulation subsection rename'
)

# Notation table caption
rp(
    r'\caption{Mathematical notation and operational definitions for the Quantum Prompt Optimizer (QPO) and Quantum Task Parallelizer (QTP).}',
    r'\caption{Mathematical notation and operational definitions for the QUBO Prompt Optimiser (QPO) and QUBO Task Scheduler (QTP).}',
    'Notation table caption'
)

# Model development paragraph
rp(
    r'The framework uses two optimization stages: the offline Quantum Prompt Optimizer (QPO) compiles prompt directives, while the runtime Quantum Task Parallelizer (QTP) schedules dependent tool operations.',
    r'The framework uses two optimisation stages: the offline QUBO Prompt Optimiser (QPO) compiles prompt directives, while the runtime QUBO Task Scheduler (QTP) schedules dependent tool operations.',
    'Model development paragraph rename'
)

# QTP results subsection
rp(
    r'\subsection{Quantum Task Parallelizer: Concurrency Speedup, Makespan Reduction, and Resource Profile}',
    r'\subsection{QUBO Task Scheduler (QTP): Wave-Makespan Reduction and Resource Profile}',
    'QTP results subsection rename'
)

# Conclusion first sentence
rp(
    r'This paper presented a two-stage optimization framework for low-latency, privacy-aware enterprise voice agents, combining the Quantum Prompt Optimizer (QPO) and the Quantum Task Parallelizer (QTP).',
    r'This paper presented a two-stage optimisation framework for low-latency, privacy-aware enterprise voice agents, combining the QUBO Prompt Optimiser (QPO) and the QUBO Task Scheduler (QTP).',
    'Conclusion first sentence rename'
)

# ---- Also fix "QUBO Prompt Optimizer" -> "QUBO Prompt Optimiser" (spelling) ----
n = c.count('QUBO Prompt Optimizer')
c = c.replace('QUBO Prompt Optimizer', 'QUBO Prompt Optimiser')
if n > 0:
    print(f'[OK] Fixed QUBO Prompt Optimizer spelling ({n} instances)')

# ---- Fix "optimization" -> "optimisation" in EAAI house style (selective) ----
# Only in prominent places, not in code identifiers
c = c.replace('two-stage optimization framework', 'two-stage optimisation framework')
c = c.replace('offline prompt compilation and runtime task scheduling', 'offline prompt compilation and runtime task optimisation')
print('[OK] optimisation spelling pass')

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print(f'\nPatches applied: {patches}')
print(f'File size: {len(c):,} bytes')
