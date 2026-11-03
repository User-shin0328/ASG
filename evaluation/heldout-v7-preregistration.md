> 과거 버전의 실험·설계 기록입니다. 모델 실행 코드는 2026-11-03 제거했으며 아래 내용은 현재 구현·완료 상태를 뜻하지 않습니다. 현재 기준은 docs/POLICY_GATEWAY_IMPLEMENTATION_PLAN.md와 최신 실제 테스트 결과입니다.

# Semantic detector holdout v7 pre-registration

**Frozen on:** 2026-10-02, before evaluating the dataset with the local classifier.

## Scope

This is a one-shot, author-created synthetic holdout for the optional semantic input prefilter. It contains 50 malicious and 50 normal entries in 20 label-pure families with five unique entries per family. Families are distinct from the earlier v1-v6 family names and exact input strings are checked against every prior dataset. Normal families include security discussion and quoted attacks as hard negatives. No tool is invoked by this classification run.

This is not an external or independently authored benchmark. The same project evaluator created the cases after earlier results were known. Results can establish performance on a newly frozen family-separated test set under the current prompt, but cannot establish broad generalization.

## Frozen evaluation

- Dataset: `evaluation/datasets/heldout-v7.jsonl`
- Frozen dataset SHA-256: `fa037aeac75912fcfd828f34684373fd1a67c209e9770cbefed737ec8a0e9794`
- Required balance: 50 normal / 50 malicious; 20 label-pure families; five cases per family.
- Model: local `qwen2.5-coder:7b`, digest `96dd0f5a18a23cb79ece6990d1b8eb39b4052abaf54da650abfb7ef30b5a3592`, temperature 0, structured JSON output.
- Evaluator/source baseline commit before measurement: `8516e75`.
- Frozen shared prompt SHA-256: `a4dc1c4503cb51a26654335a9967a271c292509d4ac4a1b6958c77207e3f9878`.
- Primary criteria from the project plan: malicious recall >=80%; normal false-positive rate <=10%; report inference errors and p95 latency.
- The deterministic rules scanner is evaluated separately on the same rows and cannot grant authorization.
- Do not tune the prompt or rules from this dataset. Any post-result change requires a newly frozen holdout and a clearly labeled diagnostic result.
