"""Model evaluation: accuracy, confusion matrix and prediction tables."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix

LABELS = ("Safe", "Dangerous")


def accuracy(y_true, y_pred) -> float:
    if len(y_true) == 0:
        raise ValueError("Cannot evaluate on an empty set.")
    return float(accuracy_score(y_true, y_pred))


def confusion(y_true, y_pred) -> np.ndarray:
    """2x2 matrix, rows = actual (Safe, Dangerous), columns = predicted (Safe, Dangerous)."""
    return confusion_matrix(y_true, y_pred, labels=[0, 1])


def evaluate(model, X, y) -> dict:
    pred = model.predict(X)
    cm = confusion(y, pred)
    return {"accuracy": accuracy(y, pred), "confusion": cm, "predicted": pred, "actual": np.asarray(y),
            "correct": int((pred == np.asarray(y)).sum()), "total": int(len(y))}


def prediction_table(df: pd.DataFrame, pred, name_col: str = "Creature", target: str = "Dangerous") -> pd.DataFrame:
    """Names + actual label + predicted label + correctness, ready for display."""
    actual = df[target].to_numpy()
    predicted = np.where(np.asarray(pred) == 1, "Yes", "No")
    out = pd.DataFrame({name_col: df[name_col].to_numpy(), "Actual": actual, "Predicted": predicted})
    out["Correct"] = out["Actual"] == out["Predicted"]
    return out
