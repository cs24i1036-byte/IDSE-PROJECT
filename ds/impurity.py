"""Entropy, Gini impurity, weighted impurity and Information Gain.

Everything works on plain label sequences (lists, numpy arrays or pandas Series), so the
game can compute the numbers from whatever records are currently in play.

    H(S)    = -sum(p_i * log2(p_i))
    Gini(S) = 1 - sum(p_i ** 2)
    IG      = H(parent) - sum(|child|/|parent| * H(child))
"""
from __future__ import annotations

from collections import Counter
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

TOL = 1e-12


def class_counts(labels: Iterable) -> dict:
    """Counts per class label (insertion-ordered by first appearance)."""
    return dict(Counter(list(labels)))


def _probabilities(labels: Iterable) -> np.ndarray:
    counts = np.array(list(class_counts(labels).values()), dtype=float)
    total = counts.sum()
    if total <= 0:
        return np.array([], dtype=float)
    return counts / total


def entropy(labels: Iterable) -> float:
    """Shannon entropy in bits. Empty and pure nodes have entropy 0."""
    p = _probabilities(labels)
    p = p[p > 0]
    if p.size <= 1:
        return 0.0
    h = float(-(p * np.log2(p)).sum())
    return 0.0 if abs(h) < TOL else h


def gini(labels: Iterable) -> float:
    """Gini impurity. Empty and pure nodes have impurity 0."""
    p = _probabilities(labels)
    if p.size <= 1:
        return 0.0
    g = float(1.0 - (p ** 2).sum())
    return 0.0 if abs(g) < TOL else g


IMPURITY: dict[str, Callable[[Iterable], float]] = {"entropy": entropy, "gini": gini}


def weighted_impurity(children: Sequence[Iterable], criterion: str = "entropy") -> float:
    """Size-weighted impurity of child groups. Empty children are ignored safely."""
    fn = IMPURITY[criterion]
    groups = [list(c) for c in children]
    total = sum(len(g) for g in groups)
    if total == 0:
        return 0.0
    return float(sum(len(g) / total * fn(g) for g in groups if len(g) > 0))


def information_gain(parent: Iterable, children: Sequence[Iterable], criterion: str = "entropy") -> float:
    """Impurity decrease of a split (Information Gain when criterion='entropy')."""
    parent = list(parent)
    gain = IMPURITY[criterion](parent) - weighted_impurity(children, criterion)
    return 0.0 if abs(gain) < TOL else float(gain)


def split_by_feature(df: pd.DataFrame, feature: str, target: str, yes: str = "Yes") -> dict:
    """Split rows on a Yes/No feature. Returns the two child DataFrames and their labels."""
    mask = df[feature] == yes
    left, right = df[mask], df[~mask]
    return {"yes": left, "no": right, "yes_labels": left[target].tolist(), "no_labels": right[target].tolist()}


def evaluate_split(df: pd.DataFrame, feature: str, target: str, criterion: str = "entropy") -> dict:
    """Everything the split panel needs for one candidate question."""
    sp = split_by_feature(df, feature, target)
    parent = df[target].tolist()
    children = [sp["yes_labels"], sp["no_labels"]]
    return {
        "feature": feature,
        "criterion": criterion,
        "parent_counts": class_counts(parent),
        "yes_counts": class_counts(sp["yes_labels"]),
        "no_counts": class_counts(sp["no_labels"]),
        "n_yes": len(sp["yes_labels"]),
        "n_no": len(sp["no_labels"]),
        "parent_impurity": IMPURITY[criterion](parent),
        "yes_impurity": IMPURITY[criterion](sp["yes_labels"]),
        "no_impurity": IMPURITY[criterion](sp["no_labels"]),
        "weighted_impurity": weighted_impurity(children, criterion),
        "gain": information_gain(parent, children, criterion),
    }


def rank_splits(df: pd.DataFrame, features: Sequence[str], target: str, criterion: str = "entropy") -> list[dict]:
    """Candidate splits sorted by gain (best first). Ties keep the feature order."""
    rows = [evaluate_split(df, f, target, criterion) for f in features]
    return sorted(rows, key=lambda r: -r["gain"])


def best_splits(df: pd.DataFrame, features: Sequence[str], target: str, criterion: str = "entropy", tol: float = 1e-9) -> list[str]:
    """All features whose gain equals the maximum (within tolerance). Usually just one."""
    ranked = rank_splits(df, features, target, criterion)
    if not ranked:
        return []
    top = ranked[0]["gain"]
    return [r["feature"] for r in ranked if abs(r["gain"] - top) <= tol]
