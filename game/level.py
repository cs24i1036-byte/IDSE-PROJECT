"""Base class for levels: world objects, update loop, state snapshot for checkpoints."""
from __future__ import annotations

import pygame

from game.entities import Bat, Bridge, Checkpoint, Gate, Gem, Mover, Projectile, Slime, Terminal
from game.settings import *  # noqa
from game.world import Grid, reachable, snap_to_spot


class Level:
    ID = 0
    NAME = ""
    THEME = "dungeon"
    CONCEPTS: list[str] = []
    LEARNED: list[str] = []            # text shown on the completion screen

    def __init__(self, seed: int = 1):
        self.seed = seed
        self.grid: Grid = Grid(10)
        self.spawn = (64, 0)
        self.gems: list[Gem] = []
        self.checkpoints: list[Checkpoint] = []
        self.terminals: list[Terminal] = []
        self.gates: list[Gate] = []
        self.bridges: list[Bridge] = []
        self.movers: list[Mover] = []
        self.enemies = []
        self.projectiles: list[Projectile] = []
        self.triggers: list[tuple[pygame.Rect, str, bool]] = []     # (zone, DAT line, fired)
        self.exit_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_open = False
        self.complete = False
        self.objective = ""
        self.intro: list[str] = []
        self.hints: dict[str, list[str]] = {}
        self.hint_idx: dict[str, int] = {}
        self.cp_index = -1
        self.answers: dict[int, object] = {}
        self.say = lambda *a, **k: None       # replaced by the gameplay scene
        self.sfx = lambda name: None
        self.time = 0.0
        self.mistakes = 0
        self.build()

    # ---------------------------------------------------------------- authoring hooks
    def build(self): raise NotImplementedError

    def checkpoint_pos(self, i: int):
        c = self.checkpoints[i]
        return (c.rect.centerx, c.rect.bottom)

    def panel_for(self, terminal: Terminal, game):            # -> panels.Panel
        raise NotImplementedError

    def on_solved(self, i: int, instant: bool): ...          # world effect of terminal i being solved

    def solve(self, i: int, result=True, instant: bool = False):
        self.terminals[i].solved = True
        self.answers[i] = result
        self.on_solved(i, instant)

    @property
    def stage_key(self) -> str:
        for i, t in enumerate(self.terminals):
            if not t.solved:
                return f"t{i}"
        return "exit"

    def next_terminal(self):
        for t in self.terminals:
            if not t.solved:
                return t
        return None

    def update_extra(self, dt, player, say, audio): ...
    def handle_event(self, ev) -> bool: return False
    def draw_back(self, surf, cam): ...
    def draw_front(self, surf, cam): ...
    def draw_hud(self, surf): ...
    def extra_state(self) -> dict: return {}
    def restore_extra(self, st: dict): ...

    # ---------------------------------------------------------------- collisions for the entity layer
    def solids(self):
        return [g.rect for g in self.gates if g.rect.h > 0]

    def oneways(self):
        return [(m.rect, m) for m in self.movers] + [(b.rect, b) for b in self.bridges if b.amt >= 0.99]

    # ---------------------------------------------------------------- helpers for subclasses
    def add_gems(self, pts):
        for x, y in pts:
            self.gems.append(Gem(x, y))

    def row_y(self, row: int) -> int:
        return row * TILE

    def hint(self) -> str:
        key = self.stage_key
        pool = self.hints.get(key) or self.hints.get("default") or ["Look for a glowing terminal and press E."]
        i = self.hint_idx.get(key, 0)
        self.hint_idx[key] = min(i + 1, len(pool) - 1)
        return pool[min(i, len(pool) - 1)]

    # ---------------------------------------------------------------- per-frame
    def update(self, dt, player, say, audio):
        self.time += dt
        for m in self.movers: m.update(dt)
        for g in self.gates: g.update(dt)
        for b in self.bridges: b.update(dt)
        for e in self.enemies:
            if e.alive: e.update(dt, self)
        for p in self.projectiles: p.update(dt, self)
        self.projectiles = [p for p in self.projectiles if p.alive]
        for i, (zone, line, fired) in enumerate(self.triggers):
            if not fired and zone.colliderect(player.rect):
                self.triggers[i] = (zone, line, True)
                say(line)
        self.update_extra(dt, player, say, audio)

    # ---------------------------------------------------------------- checkpoint snapshot
    def state(self) -> dict:
        return {"gems": [i for i, g in enumerate(self.gems) if g.taken], "answers": {str(i): a for i, a in self.answers.items()},
                "extra": self.extra_state(), "mistakes": self.mistakes}

    def restore(self, st: dict):
        for i in st.get("gems", []):
            if i < len(self.gems): self.gems[i].taken = True
        self.restore_extra(st.get("extra", {}))
        self.mistakes = st.get("mistakes", 0)
        for k, a in sorted(st.get("answers", {}).items(), key=lambda kv: int(kv[0])):
            if int(k) < len(self.terminals):
                self.solve(int(k), a, instant=True)

    # ---------------------------------------------------------------- reachability (used by tests)
    def extra_floors(self):
        """Cells that become standable thanks to bridges / movers (all assumed active for validation)."""
        out = set()
        for b in self.bridges:
            ty = b.rect.y // TILE
            for x in range(b.rect.x // TILE, b.rect.right // TILE):
                out.add((x, ty - 1))
        for m in self.movers:
            x0, y0 = m.ax, m.ay
            for k in (0, 0.5, 1):
                x, y = x0 + m.dx * k, y0 + m.dy * k
                for tx in range(int(x) // TILE, int(x + m.w - 1) // TILE + 1):
                    out.add((tx, int(y) // TILE - 1))
        return out

    def reach(self):
        start = snap_to_spot(self.grid, self.spawn[0], self.spawn[1] - 4)
        return reachable(self.grid, start, self.extra_floors()), start
