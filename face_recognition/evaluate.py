"""Evaluate a consented, held-out set of labeled image pairs. Never claim accuracy from self-matches."""

import argparse
import csv
import json
from pathlib import Path

from app.engine import MODEL_VERSION, best_similarity, get_engine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pairs",
        type=Path,
        help="CSV: first,second,same (1/0). Each photo must contain one clear face.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = get_engine()
    scores = []
    root = args.pairs.resolve().parent
    for row in csv.DictReader(args.pairs.open(encoding="utf-8")):
        first, second = ((root / row[key]).resolve() for key in ("first", "second"))
        if first == second:
            raise ValueError("Use distinct photos, not self-matches, for evaluation.")
        query = engine.extract(first.read_bytes(), query=True)[0]["vector"]
        faces = engine.extract(second.read_bytes(), query=True)
        if row["same"] not in {"0", "1"}:
            raise ValueError("same must be 0 or 1.")
        scores.append((best_similarity(query, faces), row["same"] == "1"))
    if not any(same for _, same in scores) or not any(not same for _, same in scores):
        raise ValueError("Include both same-person and different-person pairs.")
    report = {"model_version": MODEL_VERSION, "pairs": len(scores), "thresholds": []}
    for threshold in (0.363, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65):
        tp = sum(score >= threshold and same for score, same in scores)
        fp = sum(score >= threshold and not same for score, same in scores)
        fn = sum(score < threshold and same for score, same in scores)
        tn = sum(score < threshold and not same for score, same in scores)
        report["thresholds"].append(
            {
                "threshold": threshold,
                "true_matches": tp,
                "false_matches": fp,
                "missed_matches": fn,
                "true_rejections": tn,
                "precision": tp / (tp + fp) if tp + fp else None,
                "recall": tp / (tp + fn),
                "false_accept_rate": fp / (fp + tn),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Evaluated {len(scores)} pairs. Report saved locally; no images or vectors exported.")


if __name__ == "__main__":
    main()
