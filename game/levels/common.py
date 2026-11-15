"""Shared level-building helpers."""
from __future__ import annotations

from game.entities import Checkpoint, Gate, Gem, Terminal
from game.settings import TILE

GROUND = 14          # ground surface row (feet at y = 14 * 32)
FLOOR_Y = GROUND * TILE


def door_wall(level, b, x: int, w: int = 2, color=(233, 180, 76), label: str = "") -> Gate:
    """Solid wall from the ceiling down to a 3-tile doorway at ground level, closed by a Gate."""
    b.block(x, 0, w, GROUND - 3)
    g = Gate(x * TILE, (GROUND - 3) * TILE, w * TILE, 3 * TILE, color, label=label)
    level.gates.append(g)
    return g


def add_cp(level, x: int, row: int = GROUND):
    level.checkpoints.append(Checkpoint(x * TILE + 16, row * TILE))


def add_terminal(level, x: int, kind: str, label: str, row: int = GROUND) -> int:
    level.terminals.append(Terminal(x * TILE + 16, row * TILE, kind, label))
    return len(level.terminals) - 1


def gem_arc(level, x0: int, row: int, n: int, rise: int = 0):
    for i in range(n):
        level.gems.append(Gem(x0 * TILE + i * 28 + 16, row * TILE - 22 - (i % 2) * rise))


def gem_line(level, x: int, row: int, n: int):
    for i in range(n):
        level.gems.append(Gem((x + i) * TILE + 16, row * TILE - 20))
