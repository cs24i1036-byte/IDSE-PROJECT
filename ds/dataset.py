"""Dataset loading, validation, deterministic generation and splits."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MYSTIC_FEATURES = ["Has_wings", "Has_venom", "Aggressive"]
TARGET = "Dangerous"
YES, NO = "Yes", "No"
NUMERIC_EXTRA = ["Size_cm", "Speed_kmh", "Glow_level", "Age_years"]
LARGE_FEATURES = MYSTIC_FEATURES + NUMERIC_EXTRA


class DatasetError(ValueError):
    """Raised when a dataset is missing, empty or inconsistent."""


# --------------------------------------------------------------------- loading
def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise DatasetError(f"Dataset file not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        raise DatasetError(f"Dataset is empty: {name}")
    return df


def find_conflicts(df: pd.DataFrame, features: list[str], target: str = TARGET) -> pd.DataFrame:
    """Rows sharing identical feature values but different labels (should be none)."""
    grp = df.groupby(features)[target].nunique()
    bad = grp[grp > 1].index
    if len(bad) == 0:
        return df.iloc[0:0]
    return df.set_index(features).loc[bad].reset_index()


def validate_dataset(df: pd.DataFrame, features: list[str], target: str = TARGET,
                     binary: list[str] | None = None, require_consistent: bool = False) -> None:
    """Raise DatasetError if the dataset cannot be used for classification."""
    if df is None or len(df) == 0:
        raise DatasetError("The dataset is empty.")
    missing = [c for c in features + [target] if c not in df.columns]
    if missing:
        raise DatasetError(f"Missing columns: {missing}")
    if df[features + [target]].isna().any().any():
        raise DatasetError("The dataset contains missing values.")
    for col in (binary or []) + [target]:
        bad = set(df[col].unique()) - {YES, NO}
        if bad:
            raise DatasetError(f"Column {col} must only contain Yes/No (found {sorted(map(str, bad))}).")
    if df[target].nunique() < 2:
        raise DatasetError("The target needs at least two classes.")
    if require_consistent and len(find_conflicts(df, features, target)):
        raise DatasetError("Identical feature combinations have contradictory labels.")


def load_mystic() -> pd.DataFrame:
    """The 24-creature Mystic Creatures Dataset (schema: Creature + 3 features + Dangerous)."""
    df = load_csv("mystic_creatures.csv")
    validate_dataset(df, MYSTIC_FEATURES, TARGET, binary=MYSTIC_FEATURES, require_consistent=True)
    return df


def load_large() -> pd.DataFrame:
    """Noisy, larger version used in Level 4 (overfitting experiment)."""
    df = load_csv("mystic_creatures_large.csv")
    validate_dataset(df, LARGE_FEATURES, TARGET, binary=MYSTIC_FEATURES)
    return df


def load_guardian() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fresh labelled training set and a separate unseen testing set (Level 5)."""
    train, test = load_csv("guardian_training.csv"), load_csv("guardian_testing.csv")
    for d in (train, test):
        validate_dataset(d, LARGE_FEATURES, TARGET, binary=MYSTIC_FEATURES)
    return train, test


# --------------------------------------------------------------------- encoding
def encode(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Numeric feature matrix: Yes/No -> 1/0, numbers unchanged."""
    out = pd.DataFrame(index=df.index)
    for f in features:
        col = df[f]
        out[f] = col.astype(float) if pd.api.types.is_numeric_dtype(col) else col.map({YES: 1.0, NO: 0.0}).astype(float)
    return out


def encode_target(series: pd.Series) -> np.ndarray:
    return (series == YES).astype(int).to_numpy()


# --------------------------------------------------------------------- splits
def mystic_split(df: pd.DataFrame | None = None, n_test: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic hold-out: the LAST record of every feature combination that has >= 3 members.

    Guarantees that every feature combination is still represented in the training records.
    """
    df = load_mystic() if df is None else df
    held: list[int] = []
    for _, grp in df.groupby(MYSTIC_FEATURES, sort=True):
        if len(grp) >= 3:
            held.append(grp.index[-1])
    held = held[:n_test]
    return df.drop(index=held).reset_index(drop=True), df.loc[held].reset_index(drop=True)


# --------------------------------------------------------------------- generation
_ADJ = ["Shadow", "Ember", "Frost", "Moss", "Gloom", "Storm", "Crystal", "Iron", "Silent", "Golden", "Thorn", "Mist"]
_ANI = ["fang", "wing", "claw", "back", "horn", "tail", "eye", "paw", "scale", "mane"]


def _names(rng: np.random.Generator, n: int, prefix: str) -> list[str]:
    return [f"{_ADJ[int(rng.integers(len(_ADJ)))]}{_ANI[int(rng.integers(len(_ANI)))]}-{prefix}{i + 1:03d}" for i in range(n)]


def make_creatures(seed: int, n: int, noise: float, rule: str, prefix: str = "C") -> pd.DataFrame:
    """Deterministic synthetic creatures.

    rule 'venom_or_aggressive': Dangerous = venom OR aggressive
    rule 'venom_or_big_aggressive': Dangerous = venom OR (aggressive AND Size_cm >= 80)
    `noise` flips that fraction of labels (misrecorded old logs), using the same seeded generator.
    """
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({
        "Has_wings": rng.random(n) < 0.45,
        "Has_venom": rng.random(n) < 0.40,
        "Aggressive": rng.random(n) < 0.50,
        "Size_cm": rng.integers(10, 201, n),
        "Speed_kmh": rng.integers(5, 91, n),
        "Glow_level": rng.integers(0, 11, n),
        "Age_years": rng.integers(1, 301, n),
    })
    if rule == "venom_or_aggressive":
        y = (d.Has_venom | d.Aggressive).to_numpy()
    elif rule == "venom_or_big_aggressive":
        y = (d.Has_venom | (d.Aggressive & (d.Size_cm >= 80))).to_numpy()
    else:
        raise ValueError(rule)
    flip = rng.random(n) < noise
    y = np.where(flip, ~y, y)
    for c in MYSTIC_FEATURES:
        d[c] = np.where(d[c], YES, NO)
    d[TARGET] = np.where(y, YES, NO)
    d.insert(0, "Creature", _names(rng, n, prefix))
    return d


def build_all() -> dict[str, pd.DataFrame]:
    """The three generated datasets (used by tools/generate_datasets.py and by the tests)."""
    return {
        "mystic_creatures_large.csv": make_creatures(7, 300, 0.16, "venom_or_aggressive", "L"),
        "guardian_training.csv": make_creatures(2024, 200, 0.05, "venom_or_big_aggressive", "T"),
        "guardian_testing.csv": make_creatures(4048, 60, 0.05, "venom_or_big_aggressive", "U"),
    }
