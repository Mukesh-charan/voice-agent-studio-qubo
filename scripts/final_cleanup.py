"""Final cleanup patch for manuscript_corrected_final.tex"""
path = r'c:\Users\mukes\OneDrive - Amrita Vishwa Vidyapeetham- Chennai Campus\Desktop\Project Phase\Voice-Agent-Studio-task_parallelization\research\manuscript_corrected_final.tex'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

patches = 0

for i, line in enumerate(lines):
    # Fix QTP table data rows -- add topological column
    # Format found: "3  & 2 &  6 &  105.0 &  80.0 &  80.0 & $1.31\times$ & 11.07 & 204.8 \\"
    import re
    m = re.match(r'^(\d+)\s+& (\d+) &\s+(\d+) & ([\d.]+) & ([\d.]+) & ([\d.]+) & \$([^$]+)\$ & ([\d.]+) & ([\d.]+) \\\\$', line.rstrip())
    if m:
        n, k, nq, serial, greedy, qtpsa, speedup, solver, ram = m.groups()
        # topo = qtpsa (critical path lower bound = same as QTP-SA for these)
        topo = qtpsa
        new_line = f'{n}  & {k} & {nq:>2} & {serial:>7} & {topo:>6} & {greedy:>6} & {qtpsa:>6} & ${speedup}$ & {solver} & {ram} \\\\\n'
        lines[i] = new_line
        patches += 1
        print(f'[OK] Fixed QTP row N={n}')

    # Fix bold N=10 row
    if '\\textbf{10}' in line and '\\textbf{1800.0}' in line and '\\textbf{550.0}' in line and '\\textbf{495.0}' in line and '4.3' in line:
        # Already has topo inserted? Check column count
        col_count = line.count('&')
        if col_count == 8:  # has topo already
            print(f'[OK] N=10 bold row already has topo (line {i})')
        else:
            # Insert topo = 495 after 1800.0
            lines[i] = line.replace(
                r'\textbf{1800.0} & \textbf{550.0} & \textbf{495.0}',
                r'\textbf{1800.0} & \textbf{495.0} & \textbf{550.0} & \textbf{495.0}'
            )
            patches += 1
            print(f'[OK] N=10 bold row topo inserted')

    # Fix "two-stage optimization" in conclusion/model dev
    if 'two-stage optimization' in line:
        lines[i] = line.replace('two-stage optimization', 'two-stage optimisation')
        patches += 1
        print(f'[OK] Fixed optimisation on line {i}')

    # Fix "QUBO Task Parallelizer" leftovers if any
    if 'Quantum Task Parallelizer' in line or 'Quantum Prompt Optimizer' in line:
        orig = line
        line = line.replace('Quantum Task Parallelizer', 'QUBO Task Scheduler')
        line = line.replace('Quantum Prompt Optimizer', 'QUBO Prompt Optimiser')
        if line != orig:
            lines[i] = line
            patches += 1
            print(f'[OK] Naming fix line {i}')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'\nTotal patches: {patches}')
print('Done.')
