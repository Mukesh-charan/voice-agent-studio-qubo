# Dialogue Turn Detail Retention Annotation Guidelines

## Overview
This document specifies the standard operating procedure for human evaluation of factual detail retention in multi-turn voice-agent conversations (hospitality reservations and clinical appointment scheduling).

## Objective
Evaluate whether the voice agent's synthesized response faithfully retains all necessary domain entities and user-specified constraints without factual hallucination, omission, or distortion.

## Target Domains
1. **Hospitality Concierge**:
   - Dates, check-in/check-out times
   - Room categories and guest headcounts
   - Amenity requests (parking, dietary preferences, late arrival)
   - Reservation ID and pricing quotes

2. **Clinical Scheduling**:
   - Patient name and identification codes
   - Appointment dates and scheduled time slots
   - Department / specialist name
   - Pre-visit instructions (fasting, documentation required)

## Annotation Rubric

### Binary Score: Detail Retention (`detail_retention`)
- **Score 1 (Pass / Retained)**:
  - All critical domain slot values provided in the dialogue context or database query result are accurately reflected in the agent's utterance.
  - Minor stylistic reformulations or conversational paraphrasing are acceptable provided no factual shift occurs.
  - Omission of non-critical filler that does not affect transaction execution is permitted.

- **Score 0 (Fail / Hallucinated or Omitted)**:
  - Any critical slot (e.g., booking date, room type, appointment time, provider name) is incorrect, hallucinated, or missing.
  - The agent asserts confirmed booking without confirming necessary prerequisites.
  - Numeric values (costs, phone numbers, timestamps) differ from retrieved records.

## Inter-Annotator Agreement Protocol
1. Two independent annotators review an identical gold sample of 320 turns.
2. Annotators work independently without cross-communication during labeling.
3. Cohen's Kappa ($\kappa$) is computed via `scripts/cohens_kappa.py`.
4. Any disagreement is documented and reviewed by a third adjudicator.
5. In accordance with the study methodology, automated rule-based scorers serve as the primary reproducible objective metric, complemented by human-evaluated detail retention scores.
