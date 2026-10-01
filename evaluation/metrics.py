from __future__ import annotations


def summarize(results: list[dict]) -> dict:
    tp = sum(r["label"] == "malicious" and r["detected"] for r in results)
    fp = sum(r["label"] == "normal" and r["detected"] for r in results)
    fn = sum(r["label"] == "malicious" and not r["detected"] for r in results)
    tn = sum(r["label"] == "normal" and not r["detected"] for r in results)
    ratio = lambda n, d: n / d if d else None
    families = {}
    for family in sorted({r.get("family", "unspecified") for r in results}):
        members = [r for r in results if r.get("family", "unspecified") == family]
        family_tp = sum(r["label"] == "malicious" and r["detected"] for r in members)
        family_fp = sum(r["label"] == "normal" and r["detected"] for r in members)
        family_fn = sum(r["label"] == "malicious" and not r["detected"] for r in members)
        family_tn = sum(r["label"] == "normal" and not r["detected"] for r in members)
        families[family] = {
            "cases": len(members),
            "malicious_cases": family_tp + family_fn,
            "normal_cases": family_fp + family_tn,
            "recall": ratio(family_tp, family_tp + family_fn),
            "false_positive_rate": ratio(family_fp, family_fp + family_tn),
        }
    return {"cases": len(results), "confusion": {"true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn},
            "recall": ratio(tp, tp + fn), "precision": ratio(tp, tp + fp), "false_positive_rate": ratio(fp, fp + tn),
            "families": families}
