# Research Data

## Overview

All turns in this dataset are **synthetic/scripted** for a hospitality booking scenario.
No real patients, customers, or personally identifiable individuals are represented.

> **Ethics statement**: Because all data is synthetic and no real people are involved,
> a formal ethics review is not required for this dataset.
> **TODO_HUMAN**: Verify this assessment with your institution's IRB/ethics office
> before submission, as policies vary by venue and country.

---

## Files

### `dev_turns.jsonl`
JSON Lines file; one booking dialogue turn per line.

Schema:
```json
{
  "turn_id":       "integer — unique turn identifier",
  "utterance":     "string — simulated user speech transcript",
  "response":      "string — agent response text",
  "booking_fields": ["name", "date", "time", "service", "phone"],
  "gold_facts":    ["list of facts agent should retain"],
  "is_adversarial": "boolean",
  "source":        "synthetic"
}
```

### `handtuned_prompt.txt`
Baseline system prompt for the voice booking agent (hand-tuned, not QUBO-optimized).

### `annotation_template.csv`
Template for human annotation of detail-retention quality.
Columns: `turn_id, transcript, response, detail_retention_gold, detail_retention_annotator1, detail_retention_annotator2, notes`

---

## Annotation Guidelines

- **detail_retention_gold**: 0 (poor) / 1 (adequate) / 2 (complete) — set by task author from gold facts.
- **detail_retention_annotator1/2**: Same scale; filled by human annotators.
- Compute Cohen's kappa via `scripts/cohens_kappa.py` once both annotators complete labelling.

---

## TODO_HUMAN
- Recruit second annotator (Phase 4, item 3 in `results/PENDING_MEASUREMENTS.md`).
- Run `scripts/cohens_kappa.py` after annotation is complete.
