"""Decision Tree training, depth/leaf analysis, pruning experiments and predictions."""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.tree import DecisionTreeClassifier

from ds.dataset import TARGET, encode, encode_target

RANDOM_STATE = 42
CLASS_NAMES = ("Safe", "Dangerous")   # class 0 = Dangerous 'No', class 1 = Dangerous 'Yes'


def prepare(df: pd.DataFrame, features: Sequence[str], target: str = TARGET) -> tuple[pd.DataFrame, np.ndarray]:
    return encode(df, list(features)), encode_target(df[target])


def train_test(df: pd.DataFrame, features: Sequence[str], test_size: float = 0.3, seed: int = RANDOM_STATE):
    """Controlled, stratified, reproducible split. Returns Xtr, Xte, ytr, yte."""
    X, y = prepare(df, features)
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)


def train_tree(X, y, max_depth: int | None = None, ccp_alpha: float = 0.0, criterion: str = "gini",
               random_state: int = RANDOM_STATE) -> DecisionTreeClassifier:
    if len(X) == 0:
        raise ValueError("Cannot train on an empty dataset.")
    model = DecisionTreeClassifier(max_depth=max_depth, ccp_alpha=ccp_alpha, criterion=criterion, random_state=random_state)
    return model.fit(X, y)


def tree_stats(model: DecisionTreeClassifier) -> dict:
    return {"depth": int(model.get_depth()), "leaves": int(model.get_n_leaves()), "nodes": int(model.tree_.node_count)}


def complexity_sweep(Xtr, ytr, Xte, yte, depths: Sequence[int | None]) -> pd.DataFrame:
    """Train one tree per max_depth and record accuracy on both sets (the Level 4 experiment)."""
    rows = []
    for d in depths:
        m = train_tree(Xtr, ytr, max_depth=d)
        st = tree_stats(m)
        rows.append({"max_depth": d, "depth": st["depth"], "leaves": st["leaves"],
                     "train_acc": float(m.score(Xtr, ytr)), "test_acc": float(m.score(Xte, yte))})
    return pd.DataFrame(rows)


def best_depths(sweep: pd.DataFrame, tol: float = 1e-12) -> list:
    """All max_depth values that achieve the highest test accuracy."""
    top = sweep["test_acc"].max()
    vals = sweep.loc[(sweep["test_acc"] - top).abs() <= tol, "max_depth"].tolist()
    return [None if (v is None or v != v) else int(v) for v in vals]


def pruned_model(Xtr, ytr, cv_seed: int = RANDOM_STATE, folds: int = 5) -> tuple[DecisionTreeClassifier, float]:
    """Cost-complexity pruning. alpha is chosen by cross-validation on TRAINING data only."""
    full = train_tree(Xtr, ytr)
    alphas = sorted(set(float(a) for a in full.cost_complexity_pruning_path(Xtr, ytr).ccp_alphas))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=cv_seed)
    best_alpha, best_score = 0.0, -1.0
    for a in alphas:
        score = float(np.mean(cross_val_score(DecisionTreeClassifier(ccp_alpha=a, random_state=RANDOM_STATE), Xtr, ytr, cv=cv)))
        if score > best_score + 1e-12:          # prefer the smaller alpha on ties => keep more of the tree
            best_alpha, best_score = a, score
    # among equally good alphas prefer the simplest tree: scan again from the large end
    for a in reversed(alphas):
        score = float(np.mean(cross_val_score(DecisionTreeClassifier(ccp_alpha=a, random_state=RANDOM_STATE), Xtr, ytr, cv=cv)))
        if abs(score - best_score) <= 1e-12:
            best_alpha = a
            break
    return train_tree(Xtr, ytr, ccp_alpha=best_alpha), best_alpha


def pruning_experiment(Xtr, ytr, Xte, yte) -> dict:
    """Compare an unpruned tree with a cross-validated pruned tree on held-out data."""
    deep = train_tree(Xtr, ytr)
    pruned, alpha = pruned_model(Xtr, ytr)
    out = {"alpha": alpha}
    for key, m in (("deep", deep), ("pruned", pruned)):
        out[key] = {**tree_stats(m), "train_acc": float(m.score(Xtr, ytr)), "test_acc": float(m.score(Xte, yte)), "model": m}
    out["winner"] = "pruned" if out["pruned"]["test_acc"] > out["deep"]["test_acc"] else (
        "deep" if out["deep"]["test_acc"] > out["pruned"]["test_acc"] else "tie")
    return out


def predict_records(model: DecisionTreeClassifier, df: pd.DataFrame, features: Sequence[str]) -> np.ndarray:
    return model.predict(encode(df, list(features)))


def used_features(model: DecisionTreeClassifier, names: Sequence[str]) -> list[str]:
    """Features the fitted tree actually splits on."""
    idx = {int(i) for i in model.tree_.feature if i >= 0}
    return [names[i] for i in sorted(idx)]


def root_feature(model: DecisionTreeClassifier, names: Sequence[str]) -> str | None:
    f = int(model.tree_.feature[0])
    return names[f] if f >= 0 else None


def decision_path(model: DecisionTreeClassifier, x_row: np.ndarray, names: Sequence[str]) -> list[dict]:
    """The nodes one record visits: [{'feature','threshold','value','go'}...] plus the final class."""
    t = model.tree_
    node, steps = 0, []
    x = np.asarray(x_row, dtype=float)
    while t.children_left[node] != -1:
        f, thr = int(t.feature[node]), float(t.threshold[node])
        go_left = x[f] <= thr
        steps.append({"node": node, "feature": names[f], "threshold": thr, "value": float(x[f]), "go": "left" if go_left else "right"})
        node = int(t.children_left[node] if go_left else t.children_right[node])
    cls = int(np.argmax(t.value[node][0]))
    steps.append({"node": node, "leaf": True, "class": cls})
    return steps
