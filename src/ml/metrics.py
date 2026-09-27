"""Classification metrics — implemented directly (no scikit-learn
dependency) so the pipeline's only hard dependencies remain torch,
torchvision, and Pillow, all already used elsewhere in this project.
"""

from __future__ import annotations

from typing import Any


def confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> list[list[int]]:
    index = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    matrix = [[0] * n for _ in range(n)]
    for true_label, pred_label in zip(y_true, y_pred):
        matrix[index[true_label]][index[pred_label]] += 1
    return matrix


def classification_report(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    """Returns overall accuracy, per-class precision/recall/F1/support, the
    confusion matrix, and the total sample count. Returns well-defined
    zeros (not a crash) for a label with zero support, so a class that
    happens to have no test examples in a small pilot is visible in the
    report rather than causing a division-by-zero."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length")

    matrix = confusion_matrix(y_true, y_pred, labels)
    n = len(labels)

    per_class: dict[str, dict[str, float]] = {}
    total_correct = 0
    for i, label in enumerate(labels):
        true_positive = matrix[i][i]
        false_positive = sum(matrix[r][i] for r in range(n)) - true_positive
        false_negative = sum(matrix[i][c] for c in range(n)) - true_positive
        support = sum(matrix[i])

        precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0.0
        recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        total_correct += true_positive

    accuracy = total_correct / len(y_true) if y_true else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "labels": list(labels),
        "n_samples": len(y_true),
    }


def macro_f1(report: dict[str, Any]) -> float:
    """Macro-averaged F1 — used as the model-selection metric during
    training instead of plain accuracy, since accuracy alone can look
    good on an imbalanced dataset (many `normal` images, few
    `mold_like_growth`) while quietly failing the minority classes that
    matter most."""
    f1_values = [cls["f1"] for cls in report["per_class"].values()]
    return round(sum(f1_values) / len(f1_values), 4) if f1_values else 0.0
