"""Physics, collision and level-geometry tests (headless pygame)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame
import pytest

pygame.init()
pygame.display.set_mode((960, 540))

from game.entities import Gate, Mover, Player
from game.level import Level
from game.levels import make_level
from game.settings import *  # noqa
from game.world import Builder

DT = 1 / 60
NOKEYS = {"left": False, "right": False, "jump": False, "jump_pressed": False, "dash_pressed": False, "attack_pressed": False}


class Flat(Level):
    """A minimal test level: flat ground, optional extras added by the test."""
    def build(self):
        b = Builder(60)
        b.ground(0, 59, 14)
        self.grid = b.build()
        self.spawn = (100, 14 * TILE)

    def panel_for(self, terminal, game): raise NotImplementedError


def settle(p, lv, n=30):
    for _ in range(n):
        p.update(DT, NOKEYS, lv)


def test_player_lands_and_stands_on_ground():
    lv = Flat(); p = Player(100, 100)
    settle(p, lv, 90)
    assert p.on_ground and p.rect.bottom == 14 * TILE and p.vy == 0


def test_jump_apex_height_and_variable_height():
    lv = Flat(); p = Player(100, 14 * TILE); settle(p, lv)
    top = p.rect.bottom
    for i in range(80):
        p.update(DT, {**NOKEYS, "jump": True, "jump_pressed": i == 0}, lv)
        top = min(top, p.rect.bottom)
    full = 14 * TILE - top
    assert 3.0 * TILE <= full <= 3.6 * TILE            # about 3.3 tiles when held
    settle(p, lv, 60)
    top = p.rect.bottom
    for i in range(80):
        p.update(DT, {**NOKEYS, "jump": i < 3, "jump_pressed": i == 0}, lv)
        top = min(top, p.rect.bottom)
    assert 14 * TILE - top < full * 0.6                 # tapping gives a lower hop


def test_coyote_time_and_jump_buffer():
    lv = Flat(); b = Builder(60); b.ground(0, 10, 14); lv.grid = b.build()
    p = Player(10 * TILE - 8, 14 * TILE); settle(p, lv)
    for _ in range(40):                                   # run off the ledge
        p.update(DT, {**NOKEYS, "right": True}, lv)
        if not p.on_ground: break
    p.update(DT, {**NOKEYS, "right": True, "jump_pressed": True, "jump": True}, lv)   # within coyote window
    assert p.vy < 0
    lv2 = Flat(); p2 = Player(300, 0)
    for i in range(120):
        p2.update(DT, {**NOKEYS, "jump_pressed": i == 5, "jump": i < 12}, lv2)
        if p2.on_ground and i > 6: break
    p3 = Player(300, 14 * TILE - 40); jumped = False
    for i in range(60):                                    # press jump slightly before landing: buffered
        p3.update(DT, {**NOKEYS, "jump_pressed": i == 9, "jump": True}, lv2)
        jumped |= "jump" in p3.events
    assert jumped


def test_horizontal_jump_envelope_clears_four_tile_gaps_but_not_seven():
    def attempt(gap, run_up=2):
        lv = Flat(); b = Builder(60); b.ground(0, 19, 14); b.ground(20 + gap, 59, 14); lv.grid = b.build()
        p = Player(10 * TILE, 14 * TILE); settle(p, lv)
        for i in range(400):
            edge = p.rect.right >= 20 * TILE - 4
            p.update(DT, {**NOKEYS, "right": True, "jump": edge or not p.on_ground, "jump_pressed": edge and p.on_ground}, lv)
            if p.rect.top > 14 * TILE + 200: return False
            if p.rect.left > (20 + gap) * TILE and p.on_ground: return True
        return False
    assert attempt(4) and attempt(3) and not attempt(7)


def test_one_way_platform_pass_through_from_below_and_land_on_top():
    lv = Flat(); b = Builder(60); b.ground(0, 59, 14); b.platform(3, 11, 4); lv.grid = b.build()
    p = Player(5 * TILE, 14 * TILE); settle(p, lv)
    for i in range(70):
        p.update(DT, {**NOKEYS, "jump": True, "jump_pressed": i == 0}, lv)
    assert p.on_ground and p.rect.bottom == 11 * TILE


def test_solid_walls_and_gates_block_then_open():
    lv = Flat(); b = Builder(60); b.ground(0, 59, 14); lv.grid = b.build()
    g = Gate(10 * TILE, 11 * TILE, 2 * TILE, 3 * TILE); lv.gates.append(g)
    p = Player(6 * TILE, 14 * TILE); settle(p, lv)
    for _ in range(200): p.update(DT, {**NOKEYS, "right": True}, lv)
    assert p.rect.right <= 10 * TILE
    g.set_open(True)
    for _ in range(100): g.update(DT)
    for _ in range(200): p.update(DT, {**NOKEYS, "right": True}, lv)
    assert p.rect.left > 12 * TILE


def test_moving_platform_carries_player():
    lv = Flat(); m = Mover(8 * TILE, 13 * TILE, 3, dx=4, speed=60); lv.movers.append(m)
    p = Player(9 * TILE, 13 * TILE); p.on_ground = False
    start_x = p.rect.x
    for _ in range(200):
        m.update(DT); p.update(DT, NOKEYS, lv)
    assert p.on_ground and p.platform is m and abs(p.rect.x - start_x) > 10


def test_spikes_hurt_and_invulnerability_prevents_multi_hits():
    lv = Flat(); b = Builder(60); b.ground(0, 59, 14); b.spikes(5, 3, 13); lv.grid = b.build()
    p = Player(6 * TILE, 14 * TILE - 40)
    for _ in range(40): p.update(DT, NOKEYS, lv)
    assert p.health == MAX_HEALTH - 1 and p.invuln > 0


def test_health_loss_to_death_flag():
    p = Player(0, 0)
    for _ in range(MAX_HEALTH):
        p.invuln = 0; p.hurt(1)
    assert p.dead and p.health <= 0
    p.respawn((50, 50)); assert not p.dead and p.health == MAX_HEALTH


def test_dash_moves_faster_than_running():
    lv = Flat(); a = Player(100, 14 * TILE); b = Player(100, 14 * TILE); settle(a, lv); settle(b, lv)
    for i in range(10):
        a.update(DT, {**NOKEYS, "right": True}, lv)
        b.update(DT, {**NOKEYS, "right": True, "dash_pressed": i == 0}, lv)
    assert b.rect.x - 100 > (a.rect.x - 100) * 1.5


# ------------------------------------------------------------------ level geometry
@pytest.mark.parametrize("lid", [1, 2, 3, 4, 5])
def test_levels_build_and_have_required_content(lid):
    lv = make_level(lid)
    assert lv.checkpoints and lv.gems and lv.intro and lv.terminals and lv.hints
    assert lv.grid.cols * TILE >= WIDTH * 2
    sx, sy = lv.spawn
    assert lv.grid.get(sx // TILE, (sy - 1) // TILE) == EMPTY and lv.grid.get(sx // TILE, sy // TILE) == SOLID


@pytest.mark.parametrize("lid", [1, 2, 3, 4, 5])
def test_every_objective_is_reachable_with_conservative_jump_rules(lid):
    lv = make_level(lid)
    reach, start = lv.reach()
    assert start is not None
    near = lambda rect: any(abs(rect.centerx // TILE - x) <= 1 and abs(rect.bottom // TILE - 1 - y) <= 1 for x, y in reach)
    for t in lv.terminals: assert near(t.rect), f"terminal at {t.rect} unreachable"
    for c in lv.checkpoints: assert near(c.rect), f"checkpoint at {c.rect} unreachable"
    if lid != 5: assert near(lv.exit_rect)
    # gems must be reachable too (within 3 tiles of some standable cell)
    for g in lv.gems:
        assert any(abs(g.rect.centerx // TILE - x) <= 2 and 0 <= (y - g.rect.centery // TILE) <= 4 for x, y in reach), f"gem at {g.rect.center} unreachable"


@pytest.mark.parametrize("lid", [1, 2, 3, 4, 5])
def test_no_enemy_or_item_is_embedded_in_solid_tiles(lid):
    lv = make_level(lid)
    for g in lv.gems:
        assert not list(lv.grid.solid_rects(g.rect)), g.rect
    for e in lv.enemies:
        assert not list(lv.grid.solid_rects(e.rect.inflate(-4, -6))), e.rect
    for t in lv.terminals + lv.checkpoints:
        assert not list(lv.grid.solid_rects(t.rect.inflate(-6, -6))), t.rect


def test_levels_have_no_unwinnable_pits_without_pickup_of_mover_or_bridge():
    """Every pit/gap wider than the safe jump must be crossed by a mover or a bridge."""
    for lid in range(1, 6):
        lv = make_level(lid)
        g = lv.grid
        floor = [any(g.get(x, y) in (SOLID, ONEWAY) for y in range(10, g.rows)) for x in range(g.cols)]
        x = 0
        while x < g.cols:
            if not floor[x]:
                x0 = x
                while x < g.cols and not floor[x]: x += 1
                width = x - x0
                if width > 4:
                    covered = any(m.ax // TILE <= x0 + width and (m.ax + m.dx + m.w) // TILE >= x0 for m in lv.movers) or any(b.rect.x // TILE <= x0 + 1 and b.rect.right // TILE >= x - 1 for b in lv.bridges)
                    assert covered, f"level {lid}: {width}-tile pit at {x0} has no mover/bridge"
            x += 1
