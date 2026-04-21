# Model Comparison

| Model | Eval Type | In-Panel Acc | In-Panel Macro-F1 | Novelty Prec | Novelty Rec | Novelty F1 | Novelty Acc | Tested | Fetch Err | Predict Err |
|---|---|---|---|---|---|---|---|---|---|---|
| Closed-Set Baseline | closed_set | 1.0000 | 1.0000 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Hard V1 (Fetch Failure) | hard | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 21 | 0 |
| Hard V2 Baseline | hard | 0.8000 | 0.6667 | 0.6667 | 0.1250 | 0.2105 | 0.2857 | 21 | 0 | 0 |
| Hard V3 Improved | hard | 0.8000 | 0.6667 | 0.9333 | 0.8750 | 0.9032 | 0.8571 | 21 | 0 | 0 |

Notes:
- Closed-Set Baseline is not directly comparable on novelty metrics because it used in-panel only testing.
- Hard-set runs are directly comparable with each other.
