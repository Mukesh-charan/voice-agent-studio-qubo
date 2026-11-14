path = r'c:\Users\mukes\OneDrive - Amrita Vishwa Vidyapeetham- Chennai Campus\Desktop\Project Phase\Voice-Agent-Studio-task_parallelization\research\manuscript_corrected_final.tex'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

n_before = c.count('3.64')

# Replace $3.64\times$ in display/text math
c = c.replace('$3.64\\times$', '$4.3\\times$')
# Fix paired t-test in contribution list (double backslash = how py stores \ in read string)
c = c.replace(
    '($3.64\\\\times$ speedup, $p < 0.001$, paired $t$-test)',
    '($4.3\\\\times$ wave-makespan speedup; 30-run bootstrap 95\\% CI: [3.9$\\times$, 4.6$\\times$])'
)
c = c.replace('($3.64\\\\times$ speedup).', '($4.3\\\\times$ wave-makespan speedup).')
c = c.replace('{Peak: $3.64\\\\times$', '{Peak: $4.3\\\\times$')
c = c.replace('(b) Speedup factor reaches $3.64\\\\times$', '(b) Wave-makespan speedup reaches $4.3\\\\times$')
c = c.replace('QUBO stage assignment ($3.64\\\\times$', 'QUBO stage assignment ($4.3\\\\times$ wave makespan')

n_after = c.count('3.64')
print(f"3.64 count: {n_before} -> {n_after}")
print("tikz coord (10, 3.64) preserved:", '(10, 3.64)' in c)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print("Saved.")
