"""Tile world, collision queries, level builder DSL and a reachability validator."""
from __future__ import annotations

from collections import deque

import pygame

from game.settings import EMPTY, ONEWAY, SOLID, SPIKE, TILE

ROWS = 17


class Grid:
    def __init__(self, cols: int, rows: int = ROWS):
        self.cols, self.rows = cols, rows
        self.t = [[EMPTY] * cols for _ in range(rows)]

    @property
    def px_w(self): return self.cols * TILE

    @property
    def px_h(self): return self.rows * TILE

    def get(self, tx: int, ty: int) -> int:
        if tx < 0 or tx >= self.cols:
            return SOLID                      # invisible boundary walls
        if ty < 0 or ty >= self.rows:
            return EMPTY
        return self.t[ty][tx]

    def set(self, tx, ty, v):
        if 0 <= tx < self.cols and 0 <= ty < self.rows:
            self.t[ty][tx] = v

    # ------------------------------------------------------------ collision
    def solid_rects(self, rect: pygame.Rect):
        x0, x1 = rect.left // TILE, (rect.right - 1) // TILE
        y0, y1 = rect.top // TILE, (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.get(tx, ty) == SOLID:
                    yield pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)

    def oneway_rects(self, rect: pygame.Rect):
        x0, x1 = rect.left // TILE, (rect.right - 1) // TILE
        y0, y1 = rect.top // TILE, (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.get(tx, ty) == ONEWAY:
                    yield pygame.Rect(tx * TILE, ty * TILE, TILE, 8)

    def touches_spike(self, rect: pygame.Rect) -> bool:
        r = rect.inflate(-6, -4)
        x0, x1 = r.left // TILE, (r.right - 1) // TILE
        y0, y1 = r.top // TILE, (r.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.get(tx, ty) == SPIKE and pygame.Rect(tx * TILE, ty * TILE + 16, TILE, 16).colliderect(r):
                    return True
        return False

    def standable(self, tx, ty) -> bool:
        """Free 2-tile-high cell whose floor is solid/one-way."""
        free = lambda y: self.get(tx, y) in (EMPTY, ONEWAY)
        return free(ty) and free(ty - 1) and self.get(tx, ty + 1) in (SOLID, ONEWAY)


class Builder:
    """Tiny DSL for hand-authoring levels. Rows are counted from the top (row 16 = bottom)."""

    def __init__(self, cols: int, rows: int = ROWS):
        self.g = Grid(cols, rows)

    def ground(self, x0: int, x1: int, row: int):
        for x in range(x0, x1 + 1):
            for y in range(row, self.g.rows):
                self.g.set(x, y, SOLID)
        return self

    def block(self, x: int, y: int, w: int, h: int):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.g.set(xx, yy, SOLID)
        return self

    def platform(self, x: int, y: int, w: int):
        for xx in range(x, x + w):
            self.g.set(xx, y, ONEWAY)
        return self

    def spikes(self, x: int, w: int, row: int):
        for xx in range(x, x + w):
            self.g.set(xx, row, SPIKE)
        return self

    def ceiling(self, x0: int, x1: int, rows: int = 1):
        return self.block(x0, 0, x1 - x0 + 1, rows)

    def clear(self, x: int, y: int, w: int, h: int):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.g.set(xx, yy, EMPTY)
        return self

    def build(self) -> Grid:
        return self.g


# ---------------------------------------------------------------- validation
MAX_UP, MAX_GAP_FLAT = 3, 5      # conservative: jump apex 3.3 tiles, flat air distance ~5.4 tiles


def spots(grid: Grid, extra_floors=()):
    """Every standable cell as (tx, ty) where ty is the row the feet occupy (floor is ty+1)."""
    out = set()
    for ty in range(grid.rows):
        for tx in range(grid.cols):
            if grid.standable(tx, ty):
                out.add((tx, ty))
    out.update(extra_floors)
    return out


def reachable(grid: Grid, start: tuple[int, int], extra_floors=(), allow_drop=True) -> set:
    """BFS over standable cells using conservative jump rules. `extra_floors` = cells made standable by movers/bridges/doors."""
    nodes = spots(grid, extra_floors)
    seen, q = {start}, deque([start])
    while q:
        tx, ty = q.popleft()
        for (nx, ny) in nodes:
            if (nx, ny) in seen:
                continue
            dx, dy = abs(nx - tx), ty - ny           # dy>0 => destination is higher
            ok = False
            if dx <= 1 and dy <= 1 and dy >= -1:
                ok = True
            elif dy >= 0:
                # rising jump: horizontal reach shrinks as height grows
                reach = MAX_GAP_FLAT if dy == 0 else max(1, MAX_GAP_FLAT - dy - 0)
                ok = dy <= MAX_UP and dx <= reach and _clear_line(grid, tx, ty, nx, ny)
            elif allow_drop:
                ok = dx <= MAX_GAP_FLAT + 1 and _clear_line(grid, tx, ty, nx, ny, drop=True)
            if ok:
                seen.add((nx, ny)); q.append((nx, ny))
    return seen


def _clear_line(grid: Grid, x0, y0, x1, y1, drop=False) -> bool:
    """The arc must not be blocked by solid tiles between head height of the two cells."""
    top = min(y0, y1) - 2 if not drop else min(y0, y1) - 1
    a, b = sorted((x0, x1))
    for x in range(a, b + 1):
        for y in range(top, top + 2):
            if y >= 0 and grid.get(x, y) == SOLID and not (x, y) in ((x0, y0), (x1, y1)):
                if x not in (x0, x1) or y < min(y0, y1):
                    return False
    return True


def snap_to_spot(grid: Grid, px: float, py: float):
    tx = int(px // TILE)
    ty = int(py // TILE)
    for dy in range(0, 4):
        if grid.standable(tx, ty - dy):
            return (tx, ty - dy)
        if grid.standable(tx, ty + dy):
            return (tx, ty + dy)
    return None
