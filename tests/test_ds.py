"""Unit tests for the Data Science modules (no pygame needed)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import pytest

from ds import dataset as D
from ds import evaluation as EV
from ds import impurity as I
from ds import tree_model as T
from ds import visualise as V


# ------------------------------------------------------------ impurity maths
def test_entropy_known_values():
    assert I.entropy(["a", "b"]) == pytest.approx(1.0)
    assert I.entropy(["a", "a", "a", "b"]) == pytest.approx(-(0.75 * math.log2(0.75) + 0.25 * math.log2(0.25)))
    assert I.entropy(["a", "b", "c", "d"]) == pytest.approx(2.0)


def test_gini_known_values():
    assert I.gini(["a", "b"]) == pytest.approx(0.5)
    assert I.gini(["a", "a", "a", "b"]) == pytest.approx(1 - (0.75 ** 2 + 0.25 ** 2))


def test_pure_and_empty_nodes_are_safe():
    for fn in (I.entropy, I.gini):
        assert fn([]) == 0.0
        assert fn(["x"] * 7) == 0.0
    assert I.weighted_impurity([[], []]) == 0.0
    assert I.weighted_impurity([["a", "a"], []]) == 0.0
    assert I.information_gain([], [[], []]) == 0.0


def test_information_gain_perfect_and_useless_split():
    parent = ["y", "y", "n", "n"]
    assert I.information_gain(parent, [["y", "y"], ["n", "n"]]) == pytest.approx(1.0)
    assert I.information_gain(parent, [["y", "n"], ["y", "n"]]) == pytest.approx(0.0, abs=1e-12)
    assert I.information_gain(parent, [["y", "y"], ["n", "n"]], "gini") == pytest.approx(0.5)


def test_weighted_impurity_matches_hand_calculation():
    kids = [["a", "a", "b"], ["b", "b", "b", "a"]]
    expected = 3 / 7 * I.entropy(kids[0]) + 4 / 7 * I.entropy(kids[1])
    assert I.weighted_impurity(kids) == pytest.approx(expected)


# ------------------------------------------------------------ datasets
def test_mystic_dataset_schema_and_consistency():
    df = D.load_mystic()
    assert list(df.columns) == ["Creature", "Has_wings", "Has_venom", "Aggressive", "Dangerous"]
    assert len(df) >= 24 and df.Creature.is_unique
    assert len(D.find_conflicts(df, D.MYSTIC_FEATURES)) == 0
    # sample records from the brief must be present with their labels
    brief = {"Eagle": "No", "Dragon": "Yes", "Snake": "Yes", "Rabbit": "No", "Scorpion": "Yes", "Wolf": "Yes", "Butterfly": "No", "Spider": "Yes"}
    for name, label in brief.items():
        assert df.set_index("Creature").loc[name, "Dangerous"] == label


def test_validation_catches_bad_data():
    df = D.load_mystic()
    with pytest.raises(D.DatasetError):
        D.validate_dataset(df.iloc[0:0], D.MYSTIC_FEATURES)
    with pytest.raises(D.DatasetError):
        D.validate_dataset(df.drop(columns="Has_venom"), D.MYSTIC_FEATURES)
    bad = df.copy(); bad.loc[0, "Has_wings"] = "Maybe"
    with pytest.raises(D.DatasetError):
        D.validate_dataset(bad, D.MYSTIC_FEATURES, binary=D.MYSTIC_FEATURES)
    conflict = pd.concat([df, df.iloc[[0]].assign(Creature="Twin", Dangerous="Yes")], ignore_index=True)
    with pytest.raises(D.DatasetError):
        D.validate_dataset(conflict, D.MYSTIC_FEATURES, require_consistent=True)


def test_generated_datasets_are_reproducible_and_match_csv_files():
    first, second = D.build_all(), D.build_all()
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])
        on_disk = pd.read_csv(D.DATA_DIR / name)
        pd.testing.assert_frame_equal(first[name].reset_index(drop=True), on_disk, check_dtype=False)


def test_mystic_split_is_deterministic_and_keeps_every_combination_in_training():
    train, test = D.mystic_split()
    train2, test2 = D.mystic_split()
    pd.testing.assert_frame_equal(train, train2); pd.testing.assert_frame_equal(test, test2)
    assert len(test) >= 3 and set(train.Creature).isdisjoint(set(test.Creature))
    combos = lambda d: set(map(tuple, d[D.MYSTIC_FEATURES].to_numpy()))
    assert combos(test) <= combos(train)


# ------------------------------------------------------------ level 3 split logic (derived, not hard-coded)
def test_best_split_is_derived_from_data():
    train, _ = D.mystic_split()
    ranked = I.rank_splits(train, D.MYSTIC_FEATURES, "Dangerous")
    assert ranked[0]["gain"] > ranked[1]["gain"] > ranked[2]["gain"] - 1e-12      # a unique, meaningful winner
    assert ranked[0]["feature"] in ("Aggressive", "Has_venom") and ranked[-1]["feature"] == "Has_wings"
    # flip the data: make wings the perfect predictor and the answer must change with it
    flipped = train.copy(); flipped["Dangerous"] = flipped["Has_wings"]
    assert I.best_splits(flipped, D.MYSTIC_FEATURES, "Dangerous") == ["Has_wings"]


def test_second_round_split_on_impure_child():
    df = D.load_mystic()
    root = I.best_splits(df, D.MYSTIC_FEATURES, "Dangerous")[0]
    sp = I.split_by_feature(df, root, "Dangerous")
    impure = sp["no"] if I.entropy(sp["no_labels"]) > 0 else sp["yes"]
    rest = [f for f in D.MYSTIC_FEATURES if f != root]
    nxt = I.best_splits(impure, rest, "Dangerous")
    assert len(nxt) == 1 and I.rank_splits(impure, rest, "Dangerous")[0]["gain"] > 0.5


def test_entropy_and_gini_agree_on_the_best_feature_for_this_dataset():
    df = D.load_mystic()
    assert I.best_splits(df, D.MYSTIC_FEATURES, "Dangerous", "entropy") == I.best_splits(df, D.MYSTIC_FEATURES, "Dangerous", "gini")


# ------------------------------------------------------------ models
def test_level2_tree_uses_only_the_relevant_features_and_predicts_holdout():
    train, test = D.mystic_split()
    X, y = T.prepare(train, D.MYSTIC_FEATURES)
    m = T.train_tree(X, y)
    assert set(T.used_features(m, D.MYSTIC_FEATURES)) == {"Has_venom", "Aggressive"}
    assert m.score(X, y) == 1.0
    Xt, yt = T.prepare(test, D.MYSTIC_FEATURES)
    assert (m.predict(Xt) == yt).all()


def test_reproducible_split_and_training():
    big = D.load_large()
    a = T.train_test(big, D.LARGE_FEATURES); b = T.train_test(big, D.LARGE_FEATURES)
    for x, z in zip(a, b):
        assert np.array_equal(np.asarray(x), np.asarray(z))
    m1 = T.train_tree(a[0], a[2], max_depth=3); m2 = T.train_tree(b[0], b[2], max_depth=3)
    assert np.array_equal(m1.predict(a[1]), m2.predict(b[1]))


def test_overfitting_experiment_has_real_signal():
    big = D.load_large()
    Xtr, Xte, ytr, yte = T.train_test(big, D.LARGE_FEATURES)
    sweep = T.complexity_sweep(Xtr, ytr, Xte, yte, [1, 2, 3, 4, 6, 8, None])
    deepest = sweep.iloc[-1]
    assert deepest.train_acc == 1.0 and deepest.test_acc < deepest.train_acc - 0.2     # memorises the training set
    best = T.best_depths(sweep)
    assert best == [2] and 1 not in best and None not in best                          # shallowest is NOT automatically best
    assert sweep.leaves.is_monotonic_increasing and sweep.train_acc.is_monotonic_increasing


def test_pruning_beats_the_deep_tree_on_held_out_data():
    big = D.load_large()
    Xtr, Xte, ytr, yte = T.train_test(big, D.LARGE_FEATURES)
    res = T.pruning_experiment(Xtr, ytr, Xte, yte)
    assert res["winner"] == "pruned"
    assert res["pruned"]["test_acc"] > res["deep"]["test_acc"] and res["pruned"]["leaves"] < res["deep"]["leaves"]


def test_level5_model_evaluation():
    train, test = D.load_guardian()
    good = ["Has_venom", "Aggressive", "Size_cm"]
    X, y = T.prepare(train, good); Xt, yt = T.prepare(test, good)
    m = T.train_tree(X, y, max_depth=3)
    ev = EV.evaluate(m, Xt, yt)
    assert ev["accuracy"] >= 0.9 and ev["confusion"].sum() == len(test) == ev["total"]
    assert ev["accuracy"] == pytest.approx(np.trace(ev["confusion"]) / ev["confusion"].sum())
    bad = ["Has_wings", "Glow_level", "Age_years"]
    Xb, _ = T.prepare(train, bad); Xbt, ybt = T.prepare(test, bad)
    assert EV.evaluate(T.train_tree(Xb, y, max_depth=3), Xbt, ybt)["accuracy"] < 0.75
    assert len(train) >= 150 and set(train.Creature).isdisjoint(set(test.Creature))


def test_decision_path_and_prediction_table():
    train, test = D.load_guardian()
    feats = ["Has_venom", "Aggressive", "Size_cm"]
    X, y = T.prepare(train, feats); Xt, _ = T.prepare(test, feats)
    m = T.train_tree(X, y, max_depth=3)
    for i in range(10):
        path = T.decision_path(m, Xt.iloc[i].to_numpy(), feats)
        assert path[-1]["leaf"] and path[-1]["class"] == int(m.predict(Xt.iloc[[i]])[0])
    table = EV.prediction_table(test, m.predict(Xt))
    assert list(table.columns) == ["Creature", "Actual", "Predicted", "Correct"] and len(table) == len(test)


def test_empty_training_data_is_rejected():
    with pytest.raises(ValueError):
        T.train_tree(pd.DataFrame({"a": []}), [])
    with pytest.raises(ValueError):
        EV.accuracy([], [])


# ------------------------------------------------------------ visualisation
def test_figures_render_non_blank_images():
    train, _ = D.load_guardian()
    feats = ["Has_venom", "Aggressive", "Size_cm"]
    X, y = T.prepare(train, feats); m = T.train_tree(X, y, max_depth=3)
    figs = [V.tree_figure(m, feats), V.accuracy_curve_figure([1, 2, None], [.7, .8, 1.0], [.7, .8, .6], mark=2),
            V.confusion_figure(np.array([[5, 1], [2, 7]])), V.impurity_figure(["a", "b"], .9, [.5, .8], [.4, .1], "entropy")]
    for f in figs:
        raw, (w, h) = V.to_rgba(f)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4)
        assert w > 100 and h > 100 and arr[..., :3].std() > 5
