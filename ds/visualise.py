"""Matplotlib figures rendered off-screen (Agg) so pygame can blit them. Nothing is hand-drawn:
every picture is produced from the real model / numbers passed in."""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sklearn.tree import plot_tree

NAVY, PANEL, GOLD, TEAL, PURPLE, CREAM, GREEN, CORAL = "#101827", "#1B293B", "#E9B44C", "#36C6B0", "#805AD5", "#F5EBD5", "#48B879", "#E4775A"


def _fig(w_px: int, h_px: int, dpi: int = 100) -> Figure:
    fig = Figure(figsize=(w_px / dpi, h_px / dpi), dpi=dpi, facecolor=PANEL)
    FigureCanvasAgg(fig)
    return fig


def _style(ax) -> None:
    ax.set_facecolor("#14202f")
    for s in ax.spines.values():
        s.set_color(GOLD)
    ax.tick_params(colors=CREAM)
    ax.xaxis.label.set_color(CREAM)
    ax.yaxis.label.set_color(CREAM)
    ax.title.set_color(GOLD)
    ax.grid(color="#2a3b52", linewidth=.6)


def to_rgba(fig: Figure) -> tuple[bytes, tuple[int, int]]:
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    return bytes(fig.canvas.buffer_rgba()), (int(w), int(h))


def to_surface(fig: Figure):
    import pygame
    raw, size = to_rgba(fig)
    return pygame.image.frombuffer(raw, size, "RGBA").convert_alpha()


def tree_figure(model, feature_names: Sequence[str], size=(640, 360), fontsize: int = 9,
                class_names=("Safe", "Dangerous")) -> Figure:
    fig = _fig(*size)
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.98])
    ax.set_facecolor(PANEL)
    artists = plot_tree(model, feature_names=list(feature_names), class_names=list(class_names), filled=True, rounded=True,
                        impurity=False, proportion=False, fontsize=fontsize, ax=ax)
    safe, danger = np.array([0x9A, 0xE6, 0xD6]) / 255, np.array([0xF2, 0x9B, 0x86]) / 255
    for i, art in enumerate(artists[: model.tree_.node_count]):
        val = model.tree_.value[i][0]
        frac = float(val[1] / val.sum()) if val.sum() else 0.0
        art.set_color("#101827")
        patch = art.get_bbox_patch()
        if patch is not None:
            patch.set_facecolor(tuple(safe * (1 - frac) + danger * frac))
            patch.set_edgecolor(GOLD)
    return fig


def accuracy_curve_figure(depths: Sequence, train_acc: Sequence[float], test_acc: Sequence[float], mark: int | None = None,
                          size=(520, 300)) -> Figure:
    fig = _fig(*size)
    ax = fig.add_axes([0.13, 0.17, 0.83, 0.68])
    _style(ax)
    xs = [d if d is not None else max([x for x in depths if x is not None] + [0]) + 2 for d in depths]
    ax.plot(xs, train_acc, "-o", color=TEAL, label="Training accuracy", linewidth=2)
    ax.plot(xs, test_acc, "-o", color=GOLD, label="Testing accuracy", linewidth=2)
    if mark is not None and mark in list(depths):
        ax.axvline(xs[list(depths).index(mark)], color=PURPLE, linestyle="--", linewidth=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(["max" if d is None else str(d) for d in depths])
    ax.set_xlabel("Tree depth limit")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0.4, 1.03)
    ax.set_title("Training vs testing accuracy")
    leg = ax.legend(loc="lower left", facecolor="#14202f", edgecolor=GOLD, fontsize=8)
    for t in leg.get_texts():
        t.set_color(CREAM)
    return fig


def confusion_figure(cm: np.ndarray, labels=("Safe", "Dangerous"), size=(300, 260)) -> Figure:
    fig = _fig(*size)
    ax = fig.add_axes([0.2, 0.18, 0.72, 0.64])
    ax.imshow(cm, cmap="viridis")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels, color=CREAM, fontsize=9)
    ax.set_yticklabels(labels, color=CREAM, fontsize=9, rotation=90, va="center")
    ax.set_xlabel("Predicted", color=CREAM)
    ax.set_ylabel("Actual", color=CREAM)
    ax.set_title("Confusion matrix", color=GOLD)
    hi = cm.max() if cm.max() else 1
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(int(cm[i, j])), ha="center", va="center", fontsize=16, fontweight="bold",
                    color="#101827" if cm[i, j] > hi * 0.55 else CREAM)
    for s in ax.spines.values():
        s.set_color(GOLD)
    return fig


def impurity_figure(names: Sequence[str], before: float, after: Sequence[float], gains: Sequence[float], criterion: str,
                    highlight: str | None = None, size=(430, 250), mode: str = "impurity") -> Figure:
    """Impurity before the split (dashed line) vs weighted impurity after splitting on each feature.
    mode="gain" plots the information gain itself (taller bar = better split)."""
    fig = _fig(*size)
    ax = fig.add_axes([0.13, 0.2, 0.84, 0.62])
    _style(ax)
    cols = [GOLD if (highlight is None or n == highlight) else "#6c7a90" for n in names]
    if mode == "gain":
        bars = ax.bar(range(len(names)), gains, color=cols, edgecolor=CREAM)
        for b, g in zip(bars, gains):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"{g:.3f}", ha="center", color=CREAM, fontsize=9)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels([n.replace("_", " ") for n in names], fontsize=8)
        ax.set_ylim(0, max(max(gains, default=0), 0.05) * 1.3)
        ax.set_ylabel("Information gain")
        ax.set_title("Information gain of each feature (taller bar = better)")
        return fig
    bars = ax.bar(range(len(names)), after, color=cols, edgecolor=CREAM)
    ax.axhline(before, color=CORAL, linestyle="--", linewidth=2, label=f"Before split ({before:.3f})")
    for b, g in zip(bars, gains):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"gain {g:.3f}", ha="center", color=CREAM, fontsize=8)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.replace("_", " ") for n in names], fontsize=8)
    ax.set_ylim(0, max(before, max(after, default=0)) * 1.25 + 0.02)
    ax.set_ylabel(f"{criterion.title()} after")
    ax.set_title(f"Weighted {criterion} after each split")
    leg = ax.legend(loc="upper right", facecolor="#14202f", edgecolor=GOLD, fontsize=7)
    for t in leg.get_texts():
        t.set_color(CREAM)
    return fig
