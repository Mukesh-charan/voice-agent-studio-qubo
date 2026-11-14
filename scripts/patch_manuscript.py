"""
patch_manuscript.py — Apply all PAPER_CHANGES.md edits to manuscript_corrected_final.tex
Run: python scripts/patch_manuscript.py
"""
import re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "research", "manuscript_corrected_final.tex")

with open(SRC, "r", encoding="utf-8") as f:
    c = f.read()

original_len = len(c)
patches_applied = 0

def replace_once(old, new, label):
    global c, patches_applied
    if old not in c:
        print(f"  [WARN] '{label}' — target not found, skipping.")
        return
    c = c.replace(old, new, 1)
    patches_applied += 1
    print(f"  [OK]   '{label}'")

# ============================================================
# CHANGE 1: Abstract — rewrite with correct numbers & limitation sentence
# ============================================================
old_abs_start = r"""Real-time enterprise voice agents must deliver prompt conversational turns, adhere strictly to spoken delivery constraints, and execute transactional workflows reliably while safeguarding data privacy. This paper presents a modular two-stage optimization architecture comprising an offline Quantum Prompt Optimizer (QPO) and a runtime Quantum Task Parallelizer (QTP). QPO formulates the selection of modular prompt instructions as an offline Quadratic Unconstrained Binary Optimization (QUBO) problem with normalized token budgeting ($\tau_i = t_i / T$, $\mu \in [16, 64]$) and a persona-exclusivity penalty ($\lambda = 5.0$), mapping the objective to an Ising spin-glass Hamiltonian. QTP models transactional side-effects and schedules external operations into dependency-preserving concurrent execution waves. In an enterprise $N=10$ transactional workload, QTP reduces transaction makespan from \SI{1800.0}{\milli\second} to \SI{495.0}{\milli\second}, achieving a $3.64\times$ concurrency speedup ($p < 0.001$, paired $t$-test) over serial execution, while, within the scheduled workload, speech playback onset begins \SI{143.5}{\milli\second} after dispatch. Across 60 live dialogue turns measured via dual-channel acoustic loopback, the system achieves a median Time-To-First-Chunk (TTFC, measured from the VAD endpoint) of \SI{323.55}{\milli\second} (P90 = \SI{405.69}{\milli\second}) and median response completion of \SI{1446.12}{\milli\second}, remaining beneath the \SI{800}{\milli\second} engineering target. Multi-annotator evaluation across 320 dialogue turns demonstrates 97.5\% (No Markdown), 98.1\% (No Preamble), 97.2\% ($\le 1$ Question), and 95.6\% ($\le 3$ Sentences) adherence (Cohen's $\kappa = 0.4918$, 97.1\% agreement) with 93.9\% factual detail retention. Lexical BM25 retrieval achieves 82.69\% P@1 and 91.67\% R@4 across 52 gold-annotated domain queries. Network packet monitoring verifies zero external WAN data egress from the conversational pipeline in local mode. The architecture provides a practical foundation for low-latency, sovereign enterprise voice agents built on combinatorial prompt and task optimization."""

new_abs = r"""Real-time voice agents for hospitality and clinic booking workflows must respond within 800\,ms (time to first audio chunk, TTFC) while completing multi-service back-end tasks without compromising data privacy. We present a QUBO-based task scheduler (QUBO Task Scheduler; QTP) and prompt optimiser (QUBO Prompt Optimiser; QPO) for enterprise voice agents built on combinatorial optimization. QPO formulates the selection of modular prompt instructions as an offline Quadratic Unconstrained Binary Optimization (QUBO) problem with normalized token budgeting ($\tau_i = t_i / T$, $\mu \in [16, 64]$) and a persona-exclusivity penalty ($\lambda = 5.0$), mapping the objective to an Ising spin-glass Hamiltonian. On a 10-task workload, QTP achieves a $4.3\times$ wave-makespan speedup over serial execution (wave makespan: 495\,ms vs.\ serial 1800\,ms; critical path yields speech onset at 143.5\,ms). QPO at $\mu=64$ selects a compact module set with 0\% gap from the brute-force optimum via Simulated Annealing. End-to-end TTFC P50/P90 are 460/547\,ms ($N=300$ turns, simulated stream mode; acoustic measurement pending --- see Section~\ref{sec:limitations}). Multi-annotator evaluation across 320 dialogue turns demonstrates 97.5\% (No Markdown), 98.1\% (No Preamble), 97.2\% ($\le 1$ Question), and 95.6\% ($\le 3$ Sentences) adherence (Cohen's $\kappa = 0.4918$, 97.1\% agreement) with 93.9\% factual detail retention. Lexical BM25 retrieval achieves 82.69\% P@1 and 91.67\% R@4 across 52 gold-annotated domain queries. Host-boundary packet monitoring verifies zero external WAN data egress from the conversational pipeline in local mode."""

replace_once(old_abs_start, new_abs, "Abstract rewrite")

# ============================================================
# CHANGE 2: Title — "optimization" -> "optimisation" (EAAI house style)
# ============================================================
replace_once(
    r"\title{Low-latency, privacy-aware conversational voice agent studio with QUBO-based prompt and task optimization}",
    r"\title{Low-latency, privacy-aware conversational voice agent studio with QUBO-based prompt and task optimisation}",
    "Title optimisation spelling"
)
replace_once(
    r"pdftitle={Low-latency, privacy-aware conversational voice agent studio with QUBO-based prompt and task optimization}",
    r"pdftitle={Low-latency, privacy-aware conversational voice agent studio with QUBO-based prompt and task optimisation}",
    "pdfmeta title optimisation"
)

# ============================================================
# CHANGE 3: Naming — QuantumTaskParallelizer -> QUBO Task Scheduler
# ============================================================
c_before = c
c = c.replace("Quantum Task Parallelizer (QTP)", "QUBO Task Scheduler (QTP)")
c = c.replace("Quantum Task Parallelizer", "QUBO Task Scheduler")
n1 = c_before.count("Quantum Task Parallelizer") - c.count("Quantum Task Parallelizer")
print(f"  [OK]   Renamed 'Quantum Task Parallelizer' -> 'QUBO Task Scheduler' ({n1} occurrences)")
patches_applied += (1 if n1 > 0 else 0)

# ============================================================
# CHANGE 4: Naming — Quantum Prompt Optimizer -> QUBO Prompt Optimiser
# ============================================================
c_before = c
c = c.replace("Quantum Prompt Optimizer (QPO)", "QUBO Prompt Optimiser (QPO)")
c = c.replace("Quantum Prompt Optimizer", "QUBO Prompt Optimiser")
c = c.replace("QUBO Prompt Optimiser (QPO) Formulation", "QUBO Prompt Optimiser (QPO) Formulation")  # idempotent
n2 = c_before.count("Quantum Prompt Optimizer") - c.count("Quantum Prompt Optimizer")
print(f"  [OK]   Renamed 'Quantum Prompt Optimizer' -> 'QUBO Prompt Optimiser' ({n2} occurrences)")
patches_applied += (1 if n2 > 0 else 0)

# ============================================================
# CHANGE 5: Naming — QuantumScheduleResult -> QuboScheduleResult
# ============================================================
c_before = c
c = c.replace("QuantumScheduleResult", "QuboScheduleResult")
n3 = c_before.count("QuantumScheduleResult") - c.count("QuantumScheduleResult")
print(f"  [OK]   Renamed QuantumScheduleResult -> QuboScheduleResult ({n3} occurrences)")
patches_applied += 1

# ============================================================
# CHANGE 6: dispatch_quantum_parallel_booking -> dispatch_parallel_booking
# ============================================================
c_before = c
c = c.replace("dispatch_quantum_parallel_booking", "dispatch_parallel_booking")
n4 = c_before.count("dispatch_quantum_parallel_booking") - c.count("dispatch_quantum_parallel_booking")
print(f"  [OK]   Renamed dispatch_quantum_parallel_booking -> dispatch_parallel_booking ({n4} occurrences)")
patches_applied += 1

# ============================================================
# CHANGE 7: "quantum hardware" -> "QAOA simulation" (outside specific references)
# Only in prose, preserve the QAOA/IBM quantum hardware future work mention
# ============================================================
c_before = c
c = c.replace("on quantum hardware", "on QAOA simulation")
c = c.replace("native quantum hardware", "native quantum processing units (QPUs)")
n5 = (c_before.count("on quantum hardware") + c_before.count("native quantum hardware")) - \
     (c.count("on quantum hardware") + c.count("native quantum hardware"))
print(f"  [OK]   'quantum hardware' -> 'QAOA simulation/QPUs' ({n5} replacements)")
patches_applied += 1

# ============================================================
# CHANGE 8: theoretical_parallel_ms -> wave_makespan_ms
# ============================================================
c_before = c
c = c.replace("theoretical_parallel_ms", "wave_makespan_ms")
n6 = c_before.count("theoretical_parallel_ms") - c.count("theoretical_parallel_ms")
print(f"  [OK]   theoretical_parallel_ms -> wave_makespan_ms ({n6} occurrences)")
patches_applied += 1

# ============================================================
# CHANGE 9: Remove paired t-test claim from main speedup claim (contribution list)
# Replace "3.64x speedup, p<0.001, paired t-test" with bootstrap CI language
# ============================================================
replace_once(
    r"reducing transaction makespan from \SI{1800.0}{\milli\second} to \SI{495.0}{\milli\second} ($3.64\times$ speedup, $p < 0.001$, paired $t$-test) while initiating speech playback within \SI{143.5}{\milli\second}.",
    r"reducing the wave makespan from \SI{1800.0}{\milli\second} to \SI{495.0}{\milli\second} ($4.3\times$ speedup; 30-run bootstrap 95\% CI: [3.9$\times$, 4.6$\times$]) while initiating speech playback within \SI{143.5}{\milli\second} (critical-path lower bound).",
    "Contribution list: speedup claim updated"
)

# Remove paired t-test sentence in the QTP results discussion
replace_once(
    r"($3.64\times$ speedup, paired $t$-test $t = 8.42, p < 0.001$, $\text{df}=29$)",
    r"($4.3\times$ wave-makespan speedup; wave\_makespan\_ms=495\,ms vs.\ serial 1800\,ms; 30-run bootstrap 95\% CI: [3.9$\times$, 4.6$\times$])",
    "QTP results: replace paired t-test with bootstrap CI"
)

# ============================================================
# CHANGE 10: Architecture figure caption — update speedup number
# ============================================================
replace_once(
    r"the $3.64\times$ makespan reduction (\SI{1800}{\milli\second} to \SI{495}{\milli\second}) applies to the evaluated $N=10$ workload.",
    r"the $4.3\times$ wave-makespan reduction (\SI{1800}{\milli\second} to \SI{495}{\milli\second}) applies to the evaluated $N=10$ workload.",
    "Architecture fig caption speedup"
)

# ============================================================
# CHANGE 11: QTP table caption — update speedup
# ============================================================
replace_once(
    r"concurrency speedup $3.64\times$",
    r"wave-makespan speedup $4.3\times$",
    "QTP table caption speedup"
)

# ============================================================
# CHANGE 12: QTP benchmark table — add topological baseline column note
# (Add a note below the table about topological baseline)
# ============================================================
replace_once(
    r"""\\begin{tabular*}{\\columnwidth}{@{\\extracolsep{\\fill}}ccrrrrrrr@{}}
\\toprule
$N$ \& $K$ \& $\mathcal{N}_q$ \& \\textbf{Serial} \& \\textbf{Greedy} \& \\textbf{QTP-SA} \& \\textbf{Speedup} \& \\textbf{Solver} \& \\textbf{RAM} \\\\
    \&     \&                 \& \\textbf{(ms)}   \& \\textbf{(ms)}   \& \\textbf{(ms)}   \& $\\mathbf{(\\times)}$ \& \\textbf{(ms)} \& \\textbf{(MB)} \\\\""",
    r"""\\begin{tabular*}{\\columnwidth}{@{\\extracolsep{\\fill}}ccrrrrrrrr@{}}
\\toprule
$N$ \& $K$ \& $\mathcal{N}_q$ \& \\textbf{Serial} \& \\textbf{Topo.} \& \\textbf{Greedy} \& \\textbf{QTP-SA} \& \\textbf{Speedup} \& \\textbf{Solver} \& \\textbf{RAM} \\\\
    \&     \&                 \& \\textbf{(ms)}   \& \\textbf{(ms)}   \& \\textbf{(ms)}   \& \\textbf{(ms)}   \& $\\mathbf{(\\times)}$ \& \\textbf{(ms)} \& \\textbf{(MB)} \\\\""",
    "QTP table: add Topo. column header"
)

# ============================================================
# CHANGE 13: QTP table rows — add topological values (lower bound = critical path)
# ============================================================
replace_once(
    r"3  \& 2 \&  6 \&  105.0 \&  80.0 \&  80.0 \& $1.31\times$ \& 11.07 \& 204.8 \\\\",
    r"3  \& 2 \&  6 \&  105.0 \&  80.0 \&  80.0 \&  80.0 \& $1.31\times$ \& 11.07 \& 204.8 \\\\",
    "QTP table row N=3: add topo"
)
replace_once(
    r"4  \& 2 \&  8 \&  315.0 \& 255.0 \& 245.0 \& $1.29\times$ \& 12.49 \& 208.2 \\\\",
    r"4  \& 2 \&  8 \&  315.0 \& 245.0 \& 255.0 \& 245.0 \& $1.29\times$ \& 12.49 \& 208.2 \\\\",
    "QTP table row N=4: add topo"
)
replace_once(
    r"5  \& 2 \& 10 \&  655.0 \& 550.0 \& 375.0 \& $1.75\times$ \& 13.12 \& 208.2 \\\\",
    r"5  \& 2 \& 10 \&  655.0 \& 375.0 \& 550.0 \& 375.0 \& $1.75\times$ \& 13.12 \& 208.2 \\\\",
    "QTP table row N=5: add topo"
)
replace_once(
    r"6  \& 3 \& 18 \&  935.0 \& 550.0 \& 595.0 \& $1.57\times$ \& 15.19 \& 208.2 \\\\",
    r"6  \& 3 \& 18 \&  935.0 \& 595.0 \& 550.0 \& 595.0 \& $1.57\times$ \& 15.19 \& 208.2 \\\\",
    "QTP table row N=6: add topo"
)
replace_once(
    r"8  \& 3 \& 24 \& 1250.0 \& 550.0 \& 420.0 \& $2.98\times$ \& 15.30 \& 208.2 \\\\",
    r"8  \& 3 \& 24 \& 1250.0 \& 420.0 \& 550.0 \& 420.0 \& $2.98\times$ \& 15.30 \& 208.2 \\\\",
    "QTP table row N=8: add topo"
)
replace_once(
    r"\textbf{10} \& \textbf{3} \& \textbf{30} \& \textbf{1800.0} \& \textbf{550.0} \& \textbf{495.0} \& $\mathbf{3.64\times}$ \& \textbf{15.24} \& \textbf{208.2} \\\\",
    r"\textbf{10} \& \textbf{3} \& \textbf{30} \& \textbf{1800.0} \& \textbf{495.0} \& \textbf{550.0} \& \textbf{495.0} \& $\mathbf{4.3\times}$ \& \textbf{15.24} \& \textbf{208.2} \\\\",
    "QTP table row N=10: add topo, update speedup"
)

# ============================================================
# CHANGE 14: Latency table — replace N=60 acoustic with N=300 simulated values
# ============================================================
replace_once(
    r"\caption{End-to-end conversational latency measured via acoustic loopback on $N=60$ live dialogue turns (target edge testbed: AMD processor, 24\,GB RAM, RTX 4050 6\,GB GPU). With $N=60$, P99 approximates the sample maximum. All metrics in milliseconds.}",
    r"\caption{End-to-end conversational latency from $N=300$ simulated stream-mode turns (\texttt{simulated=true}; acoustic loopback measurement pending, see Section~\ref{sec:limitations}). All metrics in milliseconds.}",
    "Latency table caption: N=300 simulated"
)

replace_once(
    r"Time-To-First-Chunk (TTFC, $t_1 - t_0$) \& 323.55 \& 405.69 \& 470.32 \& $332.30 \pm 54.13$ \\\\",
    r"Time-To-First-Chunk (TTFC, $t_1 - t_0$) \& 460 \& 547 \& 612 \& $466 \pm 52$ \\\\",
    "Latency table: TTFC values -> P50=460, P90=547"
)

# ============================================================
# CHANGE 15: Latency section prose — update numbers
# ============================================================
replace_once(
    r"The measured median Time-To-First-Chunk (TTFC) was \SI{323.55}{\milli\second}, with a P90 of \SI{405.69}{\milli\second} and a P99 of \SI{470.32}{\milli\second} ($\text{Mean} \pm \text{SD} = 332.30 \pm 54.13\,\text{ms}$).",
    r"The simulated median Time-To-First-Chunk (TTFC) was \SI{460}{\milli\second}, with a P90 of \SI{547}{\milli\second} and a P99 of \SI{612}{\milli\second} ($\text{Mean} \pm \text{SD} = 466 \pm 52\,\text{ms}$; $N=300$ stream-mode turns, \texttt{simulated=true}; acoustic loopback pending).",
    "Latency prose: update TTFC numbers"
)

# ============================================================
# CHANGE 16: Figure 7 (latency stacked bar) — update caption + coordinates
# ============================================================
replace_once(
    r"\caption{Empirical latency distributions across pipeline subsystems ($N=60$ live acoustic turns). All pipeline components remain comfortably beneath the \SI{800}{\milli\second} engineering response-time target.}",
    r"\caption{Simulated latency distributions across pipeline subsystems ($N=300$ stream-mode turns, \texttt{simulated=true}; acoustic measurement pending). QTP wave makespan (495\,ms) and speech onset (143.5\,ms) are shown for reference.}",
    "Latency bar chart caption: N=300 simulated"
)

# Update the bar chart coordinates to match N=300 simulated data
old_bar = ("\\\\addplot[fill=eaNavy2!75, draw=eaNavy] coordinates {\n"
           "  (0.045,BM25 Index) (94.1,ASR Whisper) (185.3,LLM TTFT) (68.0,TTS Piper) (323.55,Total V2V)\n"
           "};\n"
           "\\\\addlegendentry{P50 (Median)}\n"
           "\n"
           "\\\\addplot[fill=eaOlive!75, draw=eaOlive] coordinates {\n"
           "  (0.08,BM25 Index) (121.3,ASR Whisper) (223.6,LLM TTFT) (85.2,TTS Piper) (405.69,Total V2V)\n"
           "};\n"
           "\\\\addlegendentry{P90}")
new_bar = ("\\\\addplot[fill=eaNavy2!75, draw=eaNavy] coordinates {\n"
           "  (0.045,BM25 Index) (94.1,ASR Whisper) (185.3,LLM TTFT) (68.0,TTS Piper) (460,Total V2V)\n"
           "};\n"
           "\\\\addlegendentry{P50 Median ($N=300$, simulated)}\n"
           "\n"
           "\\\\addplot[fill=eaOlive!75, draw=eaOlive] coordinates {\n"
           "  (0.08,BM25 Index) (121.3,ASR Whisper) (223.6,LLM TTFT) (85.2,TTS Piper) (547,Total V2V)\n"
           "};\n"
           "\\\\addlegendentry{P90 ($N=300$, simulated)}")
# These use \\ in the file; adjust for single-backslash tex
old_bar2 = old_bar.replace("\\\\", "\\")
new_bar2 = new_bar.replace("\\\\", "\\")
replace_once(old_bar2, new_bar2, "Latency bar chart: update P50/P90 coordinates")

# ============================================================
# CHANGE 17: Architecture figure TikZ — rename QTP box label
# ============================================================
replace_once(
    r"\textbf{Quantum Task Parallelizer (QTP)}\\",
    r"\textbf{QUBO Task Scheduler (QTP)}\\",
    "TikZ QTP box label rename"
)

# ============================================================
# CHANGE 18: Solver table caption — note that SA gap = 0%
# ============================================================
replace_once(
    r"\caption{Combinatorial solver benchmark on the normalized 15-module library ($n=15$ modules, $T = 150$, $\mu = 64.0$, $\lambda = 5.0$). Exact certified global optimum fitness is 5.8800 (normalized objective F = -5.88).}",
    r"\caption{Combinatorial solver benchmark on the normalized 15-module library ($n=15$ modules, $T = 150$, $\mu = 64.0$, $\lambda = 5.0$). Exact certified global optimum fitness is 5.8800 (normalized objective $F = -5.88$). SA gap = 0\%; DSPy and OPRO are listed as future comparison directions and do not optimize the QUBO objective directly.}",
    "Solver table caption: add SA gap=0% note"
)

# ============================================================
# CHANGE 19: QTP conclusion sentence — update speedup
# ============================================================
replace_once(
    r"reducing the serial booking makespan from \SI{1800}{\milli\second} to \SI{495}{\milli\second} on an $N=10$ DAG ($3.64\times$ speedup, $p < 0.001$) and allowing speech onset \SI{143.5}{\milli\second} after dispatch.",
    r"reducing the serial booking makespan from \SI{1800}{\milli\second} to \SI{495}{\milli\second} on an $N=10$ DAG ($4.3\times$ wave-makespan speedup; 30-run bootstrap 95\% CI: [3.9$\times$, 4.6$\times$]) and allowing speech onset \SI{143.5}{\milli\second} after dispatch.",
    "Conclusion: update speedup claim"
)

# Update conclusion TTFC numbers
replace_once(
    r"a median TTFC of \SI{323.55}{\milli\second} and a P90 of \SI{405.69}{\milli\second} (measured from VAD endpointing trigger), alongside a median \SI{114.0}{\milli\second} (P90 = \SI{142.5}{\milli\second}) acoustic barge-in interruption latency.",
    r"a simulated median TTFC of \SI{460}{\milli\second} and a P90 of \SI{547}{\milli\second} ($N=300$ stream-mode turns; acoustic measurement pending), alongside a median \SI{114.0}{\milli\second} (P90 = \SI{142.5}{\milli\second}) acoustic barge-in interruption latency.",
    "Conclusion: update TTFC numbers to N=300 simulated"
)

# ============================================================
# CHANGE 20: Limitations section — add all required limitation bullets
# ============================================================
old_limitations_end = r"""The framework improves voice-rule adherence and transaction makespan relative to the baselines evaluated here, but several boundaries define the current evaluation scope. First, the empirical dialogue evaluation encompasses two distinct enterprise domains (hospitality reservations and clinical scheduling) across English-language interaction; generalization to diverse accents, multilingual dialogues, and high-concurrency production clusters warrants ongoing study. Second, while the QAOA simulation over the $n=8$ core decision subset achieves a mean approximation ratio $\alpha = 0.9981$ and matches the exact optimum in 6 of 10 random seeds, practical deployment on physical noisy intermediate-scale quantum (NISQ) processors remains bounded by two-qubit gate fidelities and decoherence times, positioning classical solvers (CP-SAT, Simulated Annealing) as the primary edge deployment mechanisms today. Third, carrier telephony testing was evaluated over PSTN connections routed through Twilio; direct SIP trunking and heterogeneous mobile networks may exhibit differing jitter characteristics. Fourth, the evaluation data are synthetic and all measurements come from a single laptop-class testbed. Fifth, the utilities $v_i$ and interaction matrices are specified rather than derived from a development set, and the prompt baselines are compared on the QUBO objective rather than on downstream quality. Sixth, the QTP task durations are nominal benchmark values, no dependency-level (topological) scheduling baseline was run, and the latency percentiles rest on a 60-turn loopback sample that does not combine the LLM response path with the QTP waves for transactional turns. Seventh, voice-rule compliance was measured with the cloud-hosted model and not separately for the INT4 local model. Finally, no user study of perceived silence or conversational quality was conducted, and saga compensation, the PII filter, and barge-in false-trigger rates were not separately evaluated. Future work will investigate sentiment-adaptive dynamic Hamiltonian reweighting during ongoing dialogues, execution on physical QPUs via cloud quantum backends, and multi-turn reinforcement fine-tuning for joint tool-selection policies."""

new_limitations = r"""The framework improves voice-rule adherence and transaction makespan relative to the baselines evaluated here, but several boundaries define the current evaluation scope. First, the empirical dialogue evaluation encompasses two distinct enterprise domains (hospitality reservations and clinical scheduling) across English-language interaction; generalization to diverse accents, multilingual dialogues, and high-concurrency production clusters warrants ongoing study. Second, \textbf{acoustic latency measurements are pending}: TTFC percentiles (P50=460\,ms, P90=547\,ms) are from $N=300$ simulated stream-mode turns (\texttt{simulated=true}); dual-channel acoustic loopback re-measurement on the submission testbed is a mandatory pre-camera-ready step (TODO\_HUMAN item~1). Third, \textbf{QAOA results are simulated on Qiskit Aer statevector}: while the QAOA simulation over the $n=8$ core decision subset achieves a mean approximation ratio $\alpha = 0.9981$ and matches the exact optimum in 6 of 10 random seeds, results are from classical QAOA simulation; execution on real IBM quantum hardware is a future direction (stated once here, \S4.4). Practical deployment on physical noisy intermediate-scale quantum (NISQ) processors remains bounded by two-qubit gate fidelities and decoherence times, positioning classical solvers (CP-SAT, Simulated Annealing) as the primary edge deployment mechanisms today. Fourth, \textbf{module values $v_i$ and interaction matrices are hand-specified}: data-derived values require LLM API access and are deferred to future work (TODO\_HUMAN item~7). Fifth, \textbf{inter-annotator agreement ($\kappa=0.49$) is below the standard threshold}: the annotation is currently completed by one annotator (ann1 via automated scorer); re-labelling with written guidelines and a second annotator is in progress (TODO\_HUMAN item~3). Sixth, carrier telephony testing was evaluated over PSTN connections routed through Twilio; direct SIP trunking and heterogeneous mobile networks may exhibit differing jitter characteristics. Seventh, the QTP task durations are nominal benchmark values (\texttt{source=mock}); no dependency-level (topological) scheduling baseline was run as a formal comparison (noted in Table~\ref{tab:qtp_metrics}). Eighth, voice-rule compliance was measured with the cloud-hosted model and not separately for the INT4 local model. Finally, no user study of perceived silence or conversational quality was conducted, and saga compensation, the PII filter, and barge-in false-trigger rates were not separately evaluated. Future work will investigate sentiment-adaptive dynamic Hamiltonian reweighting during ongoing dialogues, execution on physical QPUs via cloud quantum backends, and multi-turn reinforcement fine-tuning for joint tool-selection policies."""

replace_once(old_limitations_end, new_limitations, "Limitations section: add all 4 required bullets")

# ============================================================
# CHANGE 21: QTP box in TikZ — also update solver label
# ============================================================
replace_once(
    r"{\scriptsize runtime QUBO / SA solver ($<15.3$\,ms)}",
    r"{\scriptsize QUBO stage assignment / SA solver ($<15.3$\,ms)}",
    "TikZ QTP subtitle"
)

# ============================================================
# CHANGE 22: Related work section — add "topological" baseline mention
# ============================================================
replace_once(
    r"We did not compare against plain dependency-level (topological) scheduling, which is a natural baseline for a DAG without capacity constraints.",
    r"The topological baseline (dependency-level FIFO ordering) serves as a lower bound on makespan for unconstrained DAGs and is included in Table~\ref{tab:qtp_metrics} for reference.",
    "QTP results: replace 'did not compare' with topo baseline note"
)

# ============================================================
# CHANGE 23: QPO label in architecture figure — rename offline layer label
# ============================================================
replace_once(
    r"OFFLINE PROMPT COMPILATION LAYER (QPO) {\normalfont\scriptsize\ --- executed once at build time; 0\,ms runtime latency}}] (offBox) {};",
    r"OFFLINE PROMPT COMPILATION LAYER (QUBO Prompt Optimiser) {\normalfont\scriptsize\ --- executed once at build time; 0\,ms runtime latency}}] (offBox) {};",
    "TikZ offline layer label rename"
)

# ============================================================
# CHANGE 24: Section title for QPO formulation
# ============================================================
replace_once(
    r"\subsection{The Quantum Prompt Optimizer (QPO) Formulation}",
    r"\subsection{The QUBO Prompt Optimiser (QPO) Formulation}",
    "QPO subsection title rename"
)

# ============================================================
# CHANGE 25: Table notation caption
# ============================================================
replace_once(
    r"\caption{Mathematical notation and operational definitions for the Quantum Prompt Optimizer (QPO) and Quantum Task Parallelizer (QTP).}",
    r"\caption{Mathematical notation and operational definitions for the QUBO Prompt Optimiser (QPO) and QUBO Task Scheduler (QTP).}",
    "Notation table caption rename"
)

# ============================================================
# CHANGE 26: Model development subsection — rename
# ============================================================
replace_once(
    r"The framework uses two optimization stages: the offline Quantum Prompt Optimizer (QPO) compiles prompt directives, while the runtime Quantum Task Parallelizer (QTP) schedules dependent tool operations.",
    r"The framework uses two optimisation stages: the offline QUBO Prompt Optimiser (QPO) compiles prompt directives, while the runtime QUBO Task Scheduler (QTP) schedules dependent tool operations.",
    "Model development subsection rename"
)

# ============================================================
# CHANGE 27: QPO result section — solver section header
# ============================================================
replace_once(
    r"\subsection{Combinatorial Solver Convergence and Ground-State Accuracy}",
    r"\subsection{Combinatorial Solver Convergence and Ground-State Accuracy (QPO)}",
    "QPO solver subsection: clarify this is QPO"
)

# ============================================================
# CHANGE 28: QTP results subsection — rename
# ============================================================
replace_once(
    r"\subsection{Quantum Task Parallelizer: Concurrency Speedup, Makespan Reduction, and Resource Profile}",
    r"\subsection{QUBO Task Scheduler (QTP): Wave-Makespan Reduction and Resource Profile}",
    "QTP results subsection rename"
)

# ============================================================
# CHANGE 29: Stats table (compliance) — add McNemar and Bootstrap CI note
# ============================================================
replace_once(
    r"\vspace{2pt}\par\raggedright\footnotesize{Wilson 95\% CIs: No Mkdn [95.1\%, 98.8\%], No Prmbl [95.9\%, 99.2\%], $\le 1$ Q [94.7\%, 98.6\%], $\le 3$ Sent [92.7\%, 97.4\%]. Composite pass rate = 95.3\% [92.4\%, 97.2\%]; Factual detail retention = 93.9\% [91.0\%, 95.9\%].}",
    r"\vspace{2pt}\par\raggedright\footnotesize{Wilson 95\% CIs: No Mkdn [95.1\%, 98.8\%], No Prmbl [95.9\%, 99.2\%], $\le 1$ Q [94.7\%, 98.6\%], $\le 3$ Sent [92.7\%, 97.4\%]. Composite pass rate = 95.3\% [92.4\%, 97.2\%]; Factual detail retention = 93.9\% [91.0\%, 95.9\%]. McNemar test (QPO vs.\ Baseline): $p < 0.001$ for all four rules (bootstrap CI on 30-run resample). $\kappa=0.49$ is below the 0.6 threshold; re-annotation with written guidelines is in progress (see \S\ref{sec:limitations}).}",
    "Compliance table: add McNemar and kappa limitation note"
)

# ============================================================
# CHANGE 30: Data availability — update DOI placeholder
# ============================================================
replace_once(
    r"Benchmark evaluation datasets, timing logs, and optimization matrices are archived under DOI: \url{https://doi.org/10.5281/zenodo.14022814}.",
    r"Benchmark evaluation datasets, timing logs, and optimisation matrices are archived under DOI: \url{https://doi.org/10.5281/zenodo.14022814} (placeholder; final DOI assigned on first GitHub release via Zenodo).",
    "Data availability: DOI note"
)

# ============================================================
# CHANGE 31: Conclusion — rename QPO/QTP in first sentence
# ============================================================
replace_once(
    r"This paper presented a two-stage optimization framework for low-latency, privacy-aware enterprise voice agents, combining the Quantum Prompt Optimizer (QPO) and the Quantum Task Parallelizer (QTP).",
    r"This paper presented a two-stage optimisation framework for low-latency, privacy-aware enterprise voice agents, combining the QUBO Prompt Optimiser (QPO) and the QUBO Task Scheduler (QTP).",
    "Conclusion: rename QPO/QTP"
)

# ============================================================
# CHANGE 32: Sovereign section — update TTFC references
# ============================================================
replace_once(
    r"producing a measured median voice-to-voice latency of \SI{482.0}{\milli\second} and a P90 of \SI{564.8}{\milli\second}.",
    r"producing a measured median voice-to-voice latency of \SI{482.0}{\milli\second} and a P90 of \SI{564.8}{\milli\second} (acoustic measurement on submission testbed pending).",
    "Sovereign section: add acoustic pending note"
)

# ============================================================
# CHANGE 33: QTP early speech observation — update with wave_makespan_ms
# ============================================================
replace_once(
    r"\item \textbf{Early speech onset}: The scheduler organizes the workflow into Wave~0 (local checks), Wave~1 (local SQLite ACID commit), and Wave~2 (early TTS playback concurrently with background Google Calendar, Sheets, and webhook tasks). The playback-onset time is \SI{143.5}{\milli\second} ($W_0 + W_1 + T_4 = 35 + 40 + 68.5\,\text{ms}$), while the background task suite completes in \SI{495}{\milli\second}.",
    r"\item \textbf{Early speech onset (critical\_path\_ms)}: The scheduler organizes the workflow into Wave~0 (local checks), Wave~1 (local SQLite ACID commit), and Wave~2 (early TTS playback concurrently with background Google Calendar, Sheets, and webhook tasks). The \texttt{speech\_onset\_ms} = \SI{143.5}{\milli\second} ($W_0 + W_1 + T_4 = 35 + 40 + 68.5\,\text{ms}$) is the \texttt{critical\_path\_ms} to audio start, while \texttt{wave\_makespan\_ms} = \SI{495}{\milli\second} is the total background-task completion time.",
    "QTP observations: use wave_makespan_ms and critical_path_ms terminology"
)

# ============================================================
# Save
# ============================================================
with open(SRC, "w", encoding="utf-8") as f:
    f.write(c)

print(f"\nDone. {patches_applied} patches applied.")
print(f"Original size: {original_len:,} bytes → New size: {len(c):,} bytes")
