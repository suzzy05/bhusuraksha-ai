"""Model evaluation helpers: real, calculated metrics only — never fabricated."""
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    labels = list(model.classes_)

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, labels=labels, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_test, y_pred, labels=labels).tolist()

    return {
        "accuracy": round(float(accuracy), 4),
        "labels": labels,
        "classification_report": report,
        "confusion_matrix": matrix,
    }


def print_training_summary(dataset_rows, training_rows, testing_rows, metrics):
    print("=" * 60)
    print("BHUSURAKSHA AI ML TRAINING")
    print("=" * 60)
    print(f"Dataset rows: {dataset_rows}")
    print(f"Training rows: {training_rows}")
    print(f"Testing rows: {testing_rows}")
    print(f"Accuracy: {metrics['accuracy'] * 100:.2f}%")
    print("-" * 60)
    print("Classification report:")
    for label in metrics["labels"]:
        stats = metrics["classification_report"][label]
        print(
            f"  {label:<10} precision={stats['precision']:.2f}  "
            f"recall={stats['recall']:.2f}  f1={stats['f1-score']:.2f}  "
            f"support={int(stats['support'])}"
        )
    print("-" * 60)
    print(f"Confusion matrix (rows=actual, cols=predicted) — labels {metrics['labels']}:")
    for row in metrics["confusion_matrix"]:
        print(f"  {row}")
    print("-" * 60)
    print("Model saved successfully.")
    print("=" * 60)
