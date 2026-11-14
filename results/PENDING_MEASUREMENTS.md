# Pending Measurements — TODO_HUMAN Items

This file tracks every measurement or action that cannot be automated and
requires human intervention before final submission.

---

## Open Items

| # | Item | Phase | Status |
|---|------|-------|--------|
| 1 | **Acoustic loopback latency recording** — Run `bench_v2v_acoustic.py --mode acoustic` with a hardware loopback device (VB-Cable / JACK) to replace simulated P50/P90/P99 with real measurements. | Phase 3 | ⏳ TODO |
| 2 | **IBM Quantum hardware run** — Execute the QUBO on real IBM Quantum hardware (not simulator) and record gate fidelity, shot counts, and energy gap. | Phase 2.7 | ⏳ TODO |
| 3 | **Second annotator for detail retention** — Recruit an independent annotator to fill `detail_retention_annotator2` in `research/data/annotation_template.csv`. Compute Cohen's kappa with `scripts/cohens_kappa.py`. | Phase 4 | ⏳ TODO |
| 4 | **Ethics statement verification** — Confirm with your institution's IRB/ethics office that the synthetic-data ethics waiver is acceptable for the target venue. Update `research/submission/ethics_statement.txt`. | Phase 4 | ⏳ TODO |
| 5 | **Zenodo release + DOI** — Archive the final repo snapshot on Zenodo, obtain a DOI, and replace `TODO_HUMAN` placeholders in `CITATION.cff` and `.zenodo.json`. | Phase 6 | ⏳ TODO |
| 6 | **pcap capture for zero-egress claim** — Follow `scripts/capture_egress.md` to verify no external network egress during local inference mode. | Phase 5 | ⏳ TODO |
| 7 | **LLM API key for data-derived QUBO** — Provide an API key for the LLM used to derive QUBO coefficients from real data (not mock). Set in `.env`. | Phase 2.5 | ⏳ TODO |
| 8 | **`journal.tex` location** — The manuscript LaTeX source (`journal.tex`) needs to be located or regenerated from `research/research_paper_ieee.tex`. Verify correct file for submission. | Phase 7 | ⏳ TODO |
| 9 | **BM25 retrieval query set + gold passages** — Provide a held-out query set and gold passage annotations for the BM25 retrieval evaluation in `scripts/bench_retrieval.py`. | Phase 5.3 | ⏳ TODO |

---

## Completed Items

_(None yet — update this section as items are resolved.)_
