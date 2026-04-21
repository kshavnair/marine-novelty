import csv
import json
import os
from dataclasses import dataclass
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass
class RunSpec:
    name: str
    path: str
    eval_type: str


ROOT = os.path.dirname(__file__)
OUT_DIR = os.path.join(ROOT, "model_comparison_2026_04_20")
os.makedirs(OUT_DIR, exist_ok=True)

RUNS = [
    RunSpec("Closed-Set Baseline", os.path.join(ROOT, "eval_2026_04_20", "metrics.json"), "closed_set"),
    RunSpec("Hard V1 (Fetch Failure)", os.path.join(ROOT, "eval_2026_04_20_hard", "metrics.json"), "hard"),
    RunSpec("Hard V2 Baseline", os.path.join(ROOT, "eval_2026_04_20_hard_v2", "metrics.json"), "hard"),
    RunSpec("Hard V3 Improved", os.path.join(ROOT, "eval_2026_04_20_hard_v3", "metrics.json"), "hard"),
]


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_results_csv(path: str) -> list[dict]:
    rows = []
    if not os.path.exists(path):
        return rows

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def metric_or_none(value):
    return None if value is None else float(value)


def compute_confidence_rmse(rows: list[dict]) -> float | None:
    scores = []
    for row in rows:
        confidence_raw = row.get("confidence", "")
        if confidence_raw == "":
            continue
        try:
            confidence = float(confidence_raw) / 100.0
        except ValueError:
            continue

        actual = 1.0 if str(row.get("is_match", "")).lower() in {"true", "1", "yes"} else 0.0
        scores.append((confidence - actual) ** 2)

    if not scores:
        return None

    return float((sum(scores) / len(scores)) ** 0.5)


def build_actual_vs_predicted_pairs(rows: list[dict]) -> list[tuple[str, str, float]]:
    pairs = []
    for row in rows:
        actual = row.get("species_tested", "")
        predicted = row.get("predicted_species", "")
        confidence_raw = row.get("confidence", "")
        try:
            confidence = float(confidence_raw) if confidence_raw != "" else 0.0
        except ValueError:
            confidence = 0.0
        pairs.append((actual, predicted, confidence))
    return pairs


def collect_rows() -> list[dict]:
    rows = []
    for run in RUNS:
        if not os.path.exists(run.path):
            continue
        data = load_json(run.path)

        if run.eval_type == "closed_set":
            row = {
                "model": run.name,
                "eval_type": run.eval_type,
                "in_panel_accuracy": metric_or_none(data.get("accuracy")),
                "in_panel_macro_f1": metric_or_none(data.get("macro_f1")),
                "novelty_precision": None,
                "novelty_recall": None,
                "novelty_f1": None,
                "novelty_accuracy": None,
                "tested": None,
                "fetch_errors": None,
                "predict_errors": None,
                "timestamp": data.get("timestamp", ""),
            }
            rows.append(row)
            continue
        novelty = data.get("novelty_detection", {})
        counts = data.get("overall_counts", {})

        row = {
            "model": run.name,
            "eval_type": run.eval_type,
            "in_panel_accuracy": metric_or_none(data.get("in_panel_accuracy")),
            "in_panel_macro_f1": metric_or_none(data.get("in_panel_macro_f1")),
            "novelty_precision": metric_or_none(novelty.get("precision")),
            "novelty_recall": metric_or_none(novelty.get("recall")),
            "novelty_f1": metric_or_none(novelty.get("f1")),
            "novelty_accuracy": metric_or_none(novelty.get("accuracy")),
            "tested": counts.get("tested"),
            "fetch_errors": counts.get("fetch_errors"),
            "predict_errors": counts.get("predict_errors"),
            "timestamp": data.get("timestamp", ""),
        }
        rows.append(row)

    return rows


def build_actual_vs_predicted_summary(results_rows: list[dict]) -> dict:
    pairs = build_actual_vs_predicted_pairs(results_rows)
    if not pairs:
        return {
            "total": 0,
            "exact_match_rate": 0.0,
            "mismatch_rate": 0.0,
            "confidence_rmse": None,
            "actual_counts": {},
            "predicted_counts": {},
        }

    total = len(pairs)
    exact_matches = sum(1 for actual, predicted, _ in pairs if actual == predicted)
    actual_counts = Counter(actual for actual, _, _ in pairs)
    predicted_counts = Counter(predicted for _, predicted, _ in pairs)

    return {
        "total": total,
        "exact_match_rate": exact_matches / total,
        "mismatch_rate": 1.0 - (exact_matches / total),
        "confidence_rmse": compute_confidence_rmse(results_rows),
        "actual_counts": dict(actual_counts),
        "predicted_counts": dict(predicted_counts),
    }


def fmt(v):
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def save_csv(rows: list[dict], path: str) -> None:
    headers = [
        "model",
        "eval_type",
        "in_panel_accuracy",
        "in_panel_macro_f1",
        "novelty_precision",
        "novelty_recall",
        "novelty_f1",
        "novelty_accuracy",
        "tested",
        "fetch_errors",
        "predict_errors",
        "timestamp",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def save_markdown(rows: list[dict], path: str) -> None:
    headers = [
        "Model",
        "Eval Type",
        "In-Panel Acc",
        "In-Panel Macro-F1",
        "Novelty Prec",
        "Novelty Rec",
        "Novelty F1",
        "Novelty Acc",
        "Tested",
        "Fetch Err",
        "Predict Err",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Model Comparison\n\n")
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for r in rows:
            f.write(
                "| "
                + " | ".join(
                    [
                        r["model"],
                        r["eval_type"],
                        fmt(r["in_panel_accuracy"]),
                        fmt(r["in_panel_macro_f1"]),
                        fmt(r["novelty_precision"]),
                        fmt(r["novelty_recall"]),
                        fmt(r["novelty_f1"]),
                        fmt(r["novelty_accuracy"]),
                        fmt(r["tested"]),
                        fmt(r["fetch_errors"]),
                        fmt(r["predict_errors"]),
                    ]
                )
                + " |\n"
            )

        f.write("\n")
        f.write("Notes:\n")
        f.write("- Closed-Set Baseline is not directly comparable on novelty metrics because it used in-panel only testing.\n")
        f.write("- Hard-set runs are directly comparable with each other.\n")


def plot_hard_novelty(rows: list[dict], out_path: str) -> None:
    hard_rows = [r for r in rows if r["eval_type"] == "hard" and r["novelty_f1"] is not None]
    labels = [r["model"] for r in hard_rows]
    prec = [r["novelty_precision"] for r in hard_rows]
    rec = [r["novelty_recall"] for r in hard_rows]
    f1 = [r["novelty_f1"] for r in hard_rows]

    x = list(range(len(labels)))
    w = 0.25
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - w for i in x], prec, width=w, label="Novelty Precision")
    ax.bar(x, rec, width=w, label="Novelty Recall")
    ax.bar([i + w for i in x], f1, width=w, label="Novelty F1")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Hard-Set Novelty Metrics Comparison")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def plot_in_panel(rows: list[dict], out_path: str) -> None:
    labels = [r["model"] for r in rows]
    acc = [r["in_panel_accuracy"] if r["in_panel_accuracy"] is not None else 0.0 for r in rows]
    f1 = [r["in_panel_macro_f1"] if r["in_panel_macro_f1"] is not None else 0.0 for r in rows]

    x = list(range(len(labels)))
    w = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - w / 2 for i in x], acc, width=w, label="In-Panel Accuracy")
    ax.bar([i + w / 2 for i in x], f1, width=w, label="In-Panel Macro F1")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("In-Panel Performance Across Model Versions")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def plot_eval_health(rows: list[dict], out_path: str) -> None:
    hard_rows = [r for r in rows if r["eval_type"] == "hard"]
    labels = [r["model"] for r in hard_rows]
    tested = [r["tested"] or 0 for r in hard_rows]
    fetch_errors = [r["fetch_errors"] or 0 for r in hard_rows]

    x = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x, tested, label="Tested")
    ax.bar(x, fetch_errors, bottom=tested, label="Fetch Errors")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Count")
    ax.set_title("Evaluation Coverage and Fetch Stability")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def plot_actual_vs_predicted(results_rows: list[dict], out_path: str) -> None:
    pairs = build_actual_vs_predicted_pairs(results_rows)
    if not pairs:
        return

    labels = sorted({actual for actual, _, _ in pairs} | {predicted for _, predicted, _ in pairs})
    label_to_index = {label: index for index, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]

    for actual, predicted, _ in pairs:
        matrix[label_to_index[actual]][label_to_index[predicted]] += 1

    fig, ax = plt.subplots(figsize=(12, 10))
    image = ax.imshow(matrix, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted species")
    ax.set_ylabel("Actual species")
    ax.set_title("Actual vs Predicted Species")

    for i, _actual in enumerate(labels):
        for j, _predicted in enumerate(labels):
            value = matrix[i][j]
            if value:
                ax.text(j, i, str(value), ha="center", va="center", color="black", fontsize=10, fontweight="bold")

    fig.colorbar(image, ax=ax, label="Sample count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def main() -> None:
    rows = collect_rows()
    if not rows:
        raise SystemExit("No metrics files found to compare.")

    results_rows = load_results_csv(os.path.join(ROOT, "eval_2026_04_20_hard_v3", "results.csv"))
    actual_vs_predicted_summary = build_actual_vs_predicted_summary(results_rows)

    csv_path = os.path.join(OUT_DIR, "model_comparison_table.csv")
    md_path = os.path.join(OUT_DIR, "model_comparison_table.md")
    novelty_png = os.path.join(OUT_DIR, "hard_novelty_metrics_comparison.png")
    in_panel_png = os.path.join(OUT_DIR, "in_panel_metrics_comparison.png")
    health_png = os.path.join(OUT_DIR, "hard_eval_coverage_comparison.png")
    actual_predicted_png = os.path.join(OUT_DIR, "actual_vs_predicted_species.png")

    save_csv(rows, csv_path)
    save_markdown(rows, md_path)
    plot_hard_novelty(rows, novelty_png)
    plot_in_panel(rows, in_panel_png)
    plot_eval_health(rows, health_png)
    plot_actual_vs_predicted(results_rows, actual_predicted_png)

    if actual_vs_predicted_summary["total"]:
        confidence_rmse = actual_vs_predicted_summary["confidence_rmse"]
        rmse_text = "N/A" if confidence_rmse is None else f"{confidence_rmse:.4f}"
        print(
            f"Actual-vs-predicted summary: match_rate={actual_vs_predicted_summary['exact_match_rate']:.4f}, "
            f"mismatch_rate={actual_vs_predicted_summary['mismatch_rate']:.4f}, confidence_rmse={rmse_text}"
        )

    print("Generated comparison report artifacts:")
    print(csv_path)
    print(md_path)
    print(novelty_png)
    print(in_panel_png)
    print(health_png)
    if os.path.exists(actual_predicted_png):
        print(actual_predicted_png)


if __name__ == "__main__":
    main()
