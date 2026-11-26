# Evaluation report

## Criterion 1 - Accuracy and completeness of scope, risk and blocker extraction
Gold set: 29 labelled sentences in 2 documents.

| Task | Precision | Recall | F1 |
|---|---|---|---|
| Goal / deliverable extraction | 0.75 | 1.00 | 0.86 |
| Risk detection (new method) | 1.00 | 1.00 | 1.00 |
| Blocker identification | 1.00 | 1.00 | 1.00 |
| Action item identification | 0.60 | 1.00 | 0.75 |
| Risk detection (legacy: no negation filter) | 0.93 | 1.00 | 0.97 |

Risk LEVEL accuracy on gold risks that were detected:

| Method | Detected | Exact match | Within one level |
|---|---|---|---|
| Likelihood x impact (new) | 14/14 | 86% | 100% |
| Keyword base + emphasis (legacy) | 14/14 | 50% | 93% |

Level disagreements (sentence, gold, predicted): "The team is currently over budget on cloud hosting and ..." Medium->High; "Documentation for the API is missing...." Medium->Low

## Criterion 2 - Quality of generated user stories, risk registers and action items

- [PASS] Every user story has an ID, acceptance criteria and a source
- [PASS] User stories exist for extracted goals
- [PASS] Risk register: unique IDs, level, mitigation and source on every row
- [PASS] Risk register sorted by score (highest first)
- [PASS] Every risk explains its rating (Basis)
- [PASS] Action items have owner and priority
- [PASS] Markdown report lists every risk
- [PASS] Word report opens and contains user stories

## Criterion 3 - Relevance and groundedness of assistant responses

- [PASS] Every answer cites only uploaded documents (ok, ok, ok, ok, ok, ok)
- [PASS] Out-of-scope question is declined, not invented

## Criterion 4 - Clarity and usefulness of health scoring

- [PASS] Overall and all three dimensions are within 0-100
- [PASS] Overall equals the documented weights (30/40/30)
- [PASS] Adding meeting notes + overdue tasks lowers the timeline and blocker scores
- [PASS] Label matches thresholds (>=75 on track, >=50 at risk)

## Criterion 5 - Completeness of implementation, testing and documentation

- [PASS] All 8 module files present
- [PASS] Dashboard, API, tests, README and sample documents present
- [PASS] Ingests TXT, MD, CSV, DOCX
- [PASS] Ingests PDF
- [PASS] Incremental upload: adding a document changes agent output

**Checks passed: 19/19**

Caveats: gold labels and rules were written by the same author on a small set (29 sentences), so Criterion 1 figures are optimistic. The dashboard's visual clarity (Criterion 4) and the final demonstration (Criterion 5) cannot be verified by script.
