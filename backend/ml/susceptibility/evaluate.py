"""Binary-classification evaluation for the susceptibility model — real,
calculated metrics only. Extends the retired demo model's `ml/evaluate.py`
pattern with precision/recall/F1/PR-AUC, which `docs/ML_LIMITATIONS.md`
explicitly flags as never having been computed for real data."""
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)


def evaluate_binary_model(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, list(model.classes_).index(1)] if 1 in model.classes_ else None

    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, y_pred, labels=[0, 1], zero_division=0
    )
    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()

    metrics = {
        "precision": {"negative": round(float(precision[0]), 4), "positive": round(float(precision[1]), 4)},
        "recall": {"negative": round(float(recall[0]), 4), "positive": round(float(recall[1]), 4)},
        "f1": {"negative": round(float(f1[0]), 4), "positive": round(float(f1[1]), 4)},
        "support": {"negative": int(support[0]), "positive": int(support[1])},
        "confusion_matrix": matrix,
    }

    if y_proba is not None and len(set(y_test)) > 1:
        metrics["pr_auc"] = round(float(average_precision_score(y_test, y_proba)), 4)
        metrics["roc_auc"] = round(float(roc_auc_score(y_test, y_proba)), 4)
    else:
        metrics["pr_auc"] = None
        metrics["roc_auc"] = None

    return metrics


def print_training_summary(dataset_rows, training_rows, testing_rows, split_date, metrics):
    print("=" * 60)
    print("BHUSURAKSHA AI SUSCEPTIBILITY MODEL TRAINING (Phase 20)")
    print("=" * 60)
    print(f"Dataset rows: {dataset_rows}")
    print(f"Training rows: {training_rows} (earliest, time-based split)")
    print(f"Testing rows: {testing_rows} (most recent, split at {split_date})")
    print("-" * 60)
    print(f"PR-AUC:  {metrics['pr_auc']}")
    print(f"ROC-AUC: {metrics['roc_auc']}")
    for cls in ("negative", "positive"):
        print(
            f"  {cls:<9} precision={metrics['precision'][cls]:.2f}  "
            f"recall={metrics['recall'][cls]:.2f}  f1={metrics['f1'][cls]:.2f}  "
            f"support={metrics['support'][cls]}"
        )
    print("-" * 60)
    print(f"Confusion matrix (rows=actual, cols=predicted) — labels [0, 1]:")
    for row in metrics["confusion_matrix"]:
        print(f"  {row}")
    print("=" * 60)
