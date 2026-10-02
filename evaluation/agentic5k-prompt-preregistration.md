# Agentic 5K candidate prompt evaluation

## Data separation

The dataset repository revision is `e658d94`. The scenario-isolated validation split is used for prompt development only. The 545-row test split is held for a frozen candidate run after candidate selection. The previously recorded baseline test result is retained as baseline evidence; candidate selection must use validation results, not test outcomes.

The baseline system prompt is identified by SHA-256 `a4dc1c4503cb51a26654335a9967a271c292509d4ac4a1b6958c77207e3f9878`. Its validation baseline on 467 rows was 80.52% recall / 9.43% false-positive rate, close to the plan limits of at least 80% recall and at most 10% FPR. Family-level validation recall was 58.16% for approval/authority escalation, 76.79% for memory/trust boundary, 85.71% for RAG document injection, and 100% for tool/function abuse. The dataset has zero exact normalized-text overlap with the local authored development and held-out sets.

## Candidate v1

Candidate v1 adds only three trust-boundary instructions covering untrusted approval/identity/policy claims, actions or destination changes embedded in retrieved content, and distinguishing actionable instructions from quoted or reported attack text. The exact addendum is `evaluation/prompts/agentic5k-candidate-addendum-v1.txt`; the runner records the SHA-256 of the resulting full prompt.

Candidate choice is based on the validation split. After selection, run the frozen candidate exactly once on the test split and retain aggregate metrics only. Do not revise the prompt in response to test results. Keep the runtime classifier unchanged unless the frozen candidate meets both plan thresholds on validation and test, has zero inference errors, and passes existing local detector regressions. Any test-triggered later iteration is diagnostic and requires a new independent evaluation set for acceptance.

Candidate v1 was evaluated on validation and measured 92.21% recall / 21.38% FPR, failing the 10% FPR limit; it is rejected and not integrated. Candidate v2 is a separate validation-only iteration that explicitly says tool/action wording alone is insufficient evidence and narrows malicious labels to concrete trust-boundary violations.

Candidate v2 measured 85.06% recall / 15.72% FPR and is rejected. Candidate v3 is the final validation-only candidate for this tuning pass; it requires an actionable direction and a clear trust-boundary crossing, and states that missing task scope alone is not malicious intent. Its exact addendum is `evaluation/prompts/agentic5k-candidate-addendum-v3.txt`. If v3 fails either validation threshold, retain the baseline runtime prompt and record the detector gate as unmet; do not use the test split to tune a fourth candidate.

Candidate v3 measured 78.90% recall / 19.50% FPR and is rejected. No prompt candidate passed both validation constraints, so none was tested on the external test split or integrated.

## Frozen n-gram classifier candidate

This is a separate classifier experiment from the prompt iterations. A Bernoulli word/character n-gram model was trained on the pinned train split (3,923 rows). Its threshold was selected on validation only at 95% minimum recall and 10% maximum FPR; the highest qualifying threshold produced 95.13% recall / 0% FPR. The frozen test run produced 99.64% recall / 6.04% FPR for the model alone and 99.64% / 9.06% for its OR with the unchanged Qwen classifier, with zero inference errors. No exact normalized-text overlap was found across any source split or local corpus.

The validation-frozen model is integrated as an auxiliary OR layer with the existing semantic classifier when `INPUT_CLASSIFIER_ENABLED=true`. Its standalone recall was 0% on local v1-v5 and v7, 2% on v6, and 10% on the 30-case local development attack set, showing a substantial domain mismatch. A replay combining its retained decisions with previously captured semantic outcomes preserved Qwen's v5/v6/v7 metrics; this is a compatibility replay, not a fresh independent LLM evaluation. Do not tune against those observed local sets or the external test split. The classifier never grants tool permissions. Model attribution and license are recorded in `demo_agent/models/NOTICE.md` and the packaged model metadata.

No source dataset rows or per-case outputs are retained. Evaluation is text classification only; it does not measure agent action success, Gateway authorization, or production security.
