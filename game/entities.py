"""Player, enemies, collectibles and interactive props."""
from __future__ import annotations

import math

import pygame

from game import assets as A
from game.settings import *  # noqa
from game.settings import SOLID, ONEWAY
from game.world import Grid


# ---------------------------------------------------------------- helpers
def move_axis(rect: pygame.Rect, fx: float, fy: float, dx: float, dy: float, grid: Grid, solids, oneways, vy: float = 0.0):
    """Move a float-positioned AABB, returning (fx, fy, hit_x, hit_y, platform). rect is updated in place.
    `solids` = list of full-solid Rects (doors); `oneways` = list of (rect, owner) movers acting as one-way floors."""
    hit_x = hit_y = False
    plat = None
    fx += dx
    rect.x = round(fx)
    for s in list(grid.solid_rects(rect)) + [r for r in solids if rect.colliderect(r)]:
        if rect.colliderect(s):
            if dx > 0:
                rect.right = s.left
            elif dx < 0:
                rect.left = s.right
            else:
                rect.centerx += 1 if rect.centerx >= s.centerx else -1
            fx = float(rect.x); hit_x = True
    prev_bottom = rect.bottom
    fy += dy
    rect.y = round(fy)
    for s in list(grid.solid_rects(rect)) + [r for r in solids if rect.colliderect(r)]:
        if rect.colliderect(s):
            if dy > 0:
                rect.bottom = s.top; plat = plat
            elif dy < 0:
                rect.top = s.bottom
            fy = float(rect.y); hit_y = True
    if dy >= 0 and not hit_y:
        for s in grid.oneway_rects(rect):
            if rect.colliderect(s) and prev_bottom <= s.top + 2:
                rect.bottom = s.top; fy = float(rect.y); hit_y = True
        for s, owner in oneways:
            if rect.colliderect(s) and prev_bottom <= s.top + 10 and rect.right > s.left + 2 and rect.left < s.right - 2:
                rect.bottom = s.top; fy = float(rect.y); hit_y = True; plat = owner
    if dy >= 0 and not hit_y:
        # sub-pixel gravity can leave the box 1px above the floor: probe one pixel down so "grounded" is stable
        probe = rect.move(0, 1)
        if any(True for _ in grid.solid_rects(probe)) or any(probe.colliderect(r) for r in solids):
            hit_y = True; fy = float(rect.y)
        else:
            for s in grid.oneway_rects(probe):
                if rect.bottom <= s.top + 1 and probe.colliderect(s):
                    hit_y = True; fy = float(rect.y)
            for s, owner in oneways:
                if rect.bottom <= s.top + 1 and probe.colliderect(s) and rect.right > s.left + 2 and rect.left < s.right - 2:
                    hit_y = True; fy = float(rect.y); plat = owner
    return fx, fy, hit_x, hit_y, plat


class Particle:
    def __init__(self, x, y, vx, vy, life, color, size=3, grav=400.0):
        self.x, self.y, self.vx, self.vy, self.life, self.max, self.color, self.size, self.grav = x, y, vx, vy, life, life, color, size, grav

    def update(self, dt):
        self.life -= dt; self.vy += self.grav * dt; self.x += self.vx * dt; self.y += self.vy * dt
        return self.life > 0

    def draw(self, surf, cam):
        a = max(0, min(255, int(255 * self.life / self.max)))
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (self.size, self.size), self.size)
        surf.blit(s, (self.x - cam[0] - self.size, self.y - cam[1] - self.size))


# ---------------------------------------------------------------- moving platform
class Mover:
    def __init__(self, x, y, w_tiles, dx=0, dy=0, speed=60, theme="dungeon"):
        self.w = w_tiles * TILE
        self.rect = pygame.Rect(x, y, self.w, 16)
        self.ax, self.ay = float(x), float(y)
        self.dx, self.dy, self.speed = dx * TILE, dy * TILE, speed
        self.length = max(1.0, math.hypot(self.dx, self.dy))
        self.t = 0.0
        self.delta = (0.0, 0.0)
        self.theme = theme
        self.surf = A.platform_surface(self.w, theme)

    def update(self, dt):
        self.t += dt * self.speed / self.length
        k = 0.5 - 0.5 * math.cos(self.t * math.pi)        # smooth ping-pong 0..1
        nx, ny = self.ax + self.dx * k, self.ay + self.dy * k
        self.delta = (nx - self.rect.x, ny - self.rect.y)
        self.rect.x, self.rect.y = round(nx), round(ny)

    def draw(self, surf, cam):
        surf.blit(self.surf, (self.rect.x - cam[0], self.rect.y - cam[1]))


# ---------------------------------------------------------------- player
class Player:
    W, H = 22, 36

    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, self.W, self.H)
        self.rect.midbottom = (int(x), int(y))
        self.fx, self.fy = float(self.rect.x), float(self.rect.y)
        self.vx = self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.coyote = self.buffer = 0.0
        self.dash_t = self.dash_cd = 0.0
        self.attack_t = 0.0
        self.invuln = 0.0
        self.health = MAX_HEALTH
        self.lives = START_LIVES
        self.anim = 0.0
        self.platform = None
        self.was_ground = False
        self.events: list[str] = []      # consumed by the scene for sfx
        self.jump_held = False
        self.locked = False              # frozen during dialogue / panels
        self.dead = False

    # --- state helpers
    @property
    def attacking(self): return self.attack_t > 0

    def hitbox_attack(self) -> pygame.Rect:
        w = 34
        return pygame.Rect(self.rect.right if self.facing > 0 else self.rect.left - w, self.rect.y - 2, w, self.H + 4)

    def hurt(self, amount=1, knock=(0, 0)) -> bool:
        if self.invuln > 0 or self.dead:
            return False
        self.health -= amount
        self.invuln = INVULN_TIME
        self.vx, self.vy = knock
        self.events.append("hurt")
        if self.health <= 0:
            self.dead = True
        return True

    def respawn(self, pos, full=True):
        self.rect.midbottom = (int(pos[0]), int(pos[1]))
        self.fx, self.fy = float(self.rect.x), float(self.rect.y)
        self.vx = self.vy = 0.0
        self.invuln = 1.5
        self.dash_t = 0
        self.dead = False
        if full:
            self.health = MAX_HEALTH

    # --- update
    def update(self, dt, inp, level):
        grid = level.grid
        self.events.clear()
        left, right = inp["left"], inp["right"]
        if self.locked:
            left = right = False
            inp = {**inp, "jump_pressed": False, "dash_pressed": False, "attack_pressed": False, "jump": False}
        self.invuln = max(0.0, self.invuln - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.attack_t = max(0.0, self.attack_t - dt)

        # carry by moving platform
        if self.platform is not None:
            pdx, pdy = getattr(self.platform, "delta", (0.0, 0.0))
            self.fx, self.fy, *_ = move_axis(self.rect, self.fx, self.fy, pdx, pdy, grid, level.solids(), [])

        axis = (1 if right else 0) - (1 if left else 0)
        if axis:
            self.facing = axis

        if inp.get("dash_pressed") and self.dash_cd <= 0 and self.dash_t <= 0 and not self.locked:
            self.dash_t, self.dash_cd = DASH_TIME, DASH_COOLDOWN
            self.vy = 0
            self.events.append("dash")
        if inp.get("attack_pressed") and self.attack_t <= 0 and not self.locked:
            self.attack_t = ATTACK_TIME
            self.events.append("attack")

        if self.dash_t > 0:
            self.dash_t -= dt
            self.vx = DASH_SPEED * self.facing
            self.vy = 0
        else:
            accel = GROUND_ACCEL if self.on_ground else AIR_ACCEL
            target = axis * RUN_SPEED
            if axis:
                if self.vx < target:
                    self.vx = min(target, self.vx + accel * dt)
                elif self.vx > target:
                    self.vx = max(target, self.vx - accel * dt)
            else:
                f = FRICTION * dt
                self.vx = 0.0 if abs(self.vx) <= f else self.vx - math.copysign(f, self.vx)
            self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)

        # jump (buffer + coyote)
        self.coyote = COYOTE if self.on_ground else max(0.0, self.coyote - dt)
        self.buffer = JUMP_BUFFER if inp.get("jump_pressed") else max(0.0, self.buffer - dt)
        if self.buffer > 0 and self.coyote > 0:
            self.vy = -JUMP_SPEED
            self.buffer = self.coyote = 0.0
            self.on_ground = False
            self.platform = None
            self.events.append("jump")
        if not inp.get("jump") and self.vy < -JUMP_SPEED * JUMP_CUT and self.dash_t <= 0:
            self.vy = -JUMP_SPEED * JUMP_CUT

        solids, oneways = level.solids(), level.oneways()
        self.fx, self.fy, hx, _, _ = move_axis(self.rect, self.fx, self.fy, self.vx * dt, 0, grid, solids, oneways)
        if hx:
            self.vx = 0
        self.fx, self.fy, _, hy, plat = move_axis(self.rect, self.fx, self.fy, 0, self.vy * dt, grid, solids, oneways)
        if hy:
            landed = self.vy > 0
            if landed and not self.was_ground:
                self.events.append("land")
            self.vy = 0 if landed else max(self.vy, 0)
            self.on_ground = landed
        else:
            self.on_ground = False
        self.platform = plat if self.on_ground else None
        self.was_ground = self.on_ground

        # hazards
        if grid.touches_spike(self.rect):
            self.hurt(1, (-self.facing * 120, -380))
        if self.rect.top > grid.px_h + 120:
            self.events.append("fell")

        self.anim += dt * (abs(self.vx) / 40 + 2)

    def frame(self) -> pygame.Surface:
        d = A.alex_frames()
        fr = d["left"] if self.facing < 0 else d
        if not self.on_ground:
            return fr["jump"][0] if self.vy < 0 else fr["fall"][0]
        if abs(self.vx) > 20:
            return fr["run"][int(self.anim * 2) % 4]
        return fr["idle"][0]

    def draw(self, surf, cam):
        if self.invuln > 0 and int(self.invuln * 14) % 2:
            return
        img = self.frame()
        r = img.get_rect(midbottom=(self.rect.centerx - cam[0], self.rect.bottom - cam[1] + 1))
        if self.dash_t > 0:
            for i in range(1, 4):
                g = img.copy(); g.set_alpha(80 - i * 20)
                surf.blit(g, (r.x - self.facing * i * 12, r.y))
        surf.blit(img, r)
        if self.attacking:
            hb = self.hitbox_attack()
            k = 1 - self.attack_t / ATTACK_TIME
            arc = pygame.Surface((hb.w, hb.h), pygame.SRCALPHA)
            pygame.draw.arc(arc, (*CREAM, 220), (0, 0, hb.w * 2 if self.facing > 0 else hb.w * 2, hb.h), 0.4 + k, 2.4 + k, 4) if self.facing > 0 else pygame.draw.arc(arc, (*CREAM, 220), (-hb.w, 0, hb.w * 2, hb.h), 0.8 - k, 2.8 - k, 4)
            surf.blit(arc, (hb.x - cam[0], hb.y - cam[1]))


# ---------------------------------------------------------------- enemies
class Enemy:
    hp = 1
    contact = 1

    def __init__(self):
        self.alive = True
        self.t = 0.0
        self.rect = pygame.Rect(0, 0, 10, 10)

    def kill(self): self.alive = False


class Slime(Enemy):
    def __init__(self, x, y, x_min, x_max):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 28, 18); self.rect.midbottom = (x, y)
        self.x_min, self.x_max, self.dir = x_min, x_max, 1
        self.fx = float(self.rect.x)

    def update(self, dt, level):
        self.t += dt
        self.fx += self.dir * 45 * dt
        self.rect.x = round(self.fx)
        if self.rect.left < self.x_min:
            self.dir = 1
        elif self.rect.right > self.x_max:
            self.dir = -1
        # don't walk off ledges
        ahead = self.rect.right + 2 if self.dir > 0 else self.rect.left - 2
        if level.grid.get(ahead // TILE, self.rect.bottom // TILE) not in (SOLID, ONEWAY):
            self.dir *= -1; self.fx += self.dir * 3

    def draw(self, surf, cam):
        img = A.slime_frames()[int(self.t * 4) % 2]
        surf.blit(img, (self.rect.centerx - 15 - cam[0], self.rect.bottom - 22 - cam[1]))


class Bat(Enemy):
    def __init__(self, x, y, amp_x=80, amp_y=24, speed=1.2):
        super().__init__()
        self.ax, self.ay, self.amp_x, self.amp_y, self.speed = x, y, amp_x, amp_y, speed
        self.rect = pygame.Rect(0, 0, 26, 16); self.rect.center = (x, y)
        self.t = (x % 7) * 0.4

    def update(self, dt, level):
        self.t += dt
        self.rect.center = (self.ax + math.sin(self.t * self.speed) * self.amp_x, self.ay + math.sin(self.t * self.speed * 2) * self.amp_y)

    def draw(self, surf, cam):
        img = A.bat_frames()[int(self.t * 8) % 2]
        surf.blit(img, (self.rect.centerx - 17 - cam[0], self.rect.centery - 10 - cam[1]))


class Projectile:
    def __init__(self, x, y, vx, vy, color=PURPLE, life=4.0):
        self.x, self.y, self.vx, self.vy, self.life, self.color = x, y, vx, vy, life, color
        self.rect = pygame.Rect(0, 0, 14, 14)
        self.alive = True

    def update(self, dt, level):
        self.life -= dt
        self.x += self.vx * dt; self.y += self.vy * dt
        self.rect.center = (self.x, self.y)
        if self.life <= 0 or any(level.grid.solid_rects(self.rect)):
            self.alive = False

    def draw(self, surf, cam):
        surf.blit(A.glow(18, self.color), (self.x - 18 - cam[0], self.y - 18 - cam[1]))
        pygame.draw.circle(surf, CREAM, (int(self.x - cam[0]), int(self.y - cam[1])), 5)
        pygame.draw.circle(surf, self.color, (int(self.x - cam[0]), int(self.y - cam[1])), 7, 2)


# ---------------------------------------------------------------- props
class Gem:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 9, y - 9, 18, 18)
        self.taken = False
        self.t = (x * 0.013) % 6

    def draw(self, surf, cam, time):
        if self.taken:
            return
        bob = math.sin(time * 3 + self.t) * 3
        surf.blit(A.gem_frame(int(time * 8 + self.t)), (self.rect.x - 1 - cam[0], self.rect.y - 1 + bob - cam[1]))


class Checkpoint:
    def __init__(self, x, y_bottom):
        self.rect = pygame.Rect(x - 16, y_bottom - 64, 32, 64)
        self.active = False

    def draw(self, surf, cam):
        surf.blit(A.checkpoint_frame(self.active), (self.rect.x - cam[0], self.rect.y - cam[1]))


class Terminal:
    """A DS console. `kind` selects the holographic panel the level opens on interaction."""

    def __init__(self, x, y_bottom, kind: str, label: str = "TERMINAL"):
        self.rect = pygame.Rect(x - 24, y_bottom - 64, 48, 64)
        self.kind, self.label = kind, label
        self.solved = False

    def near(self, player_rect) -> bool:
        return self.rect.inflate(60, 20).colliderect(player_rect)

    def draw(self, surf, cam, time, active):
        surf.blit(A.terminal_frame(active, self.solved, time), (self.rect.x - cam[0], self.rect.y - cam[1]))
        if not self.solved:
            surf.blit(A.glow(34, TEAL if active else (40, 90, 110)), (self.rect.centerx - 34 - cam[0], self.rect.y + 22 - 34 - cam[1]))


class Gate:
    """A solid barrier that slides open (doors, vine walls, crystal bridges are all Gates)."""

    def __init__(self, x, y, w, h, color=GOLD, key="", label=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.full = self.rect.copy()
        self.color, self.key, self.label = color, key, label
        self.open = False
        self.amt = 0.0

    def set_open(self, v=True, instant=False):
        self.open = v
        if instant:
            self.amt = 1.0 if v else 0.0
            self._sync()

    def _sync(self):
        h = int(self.full.h * (1 - self.amt))
        self.rect = pygame.Rect(self.full.x, self.full.y, self.full.w, h)

    def update(self, dt):
        tgt = 1.0 if self.open else 0.0
        if self.amt != tgt:
            self.amt = min(tgt, self.amt + dt * 1.2) if tgt > self.amt else max(tgt, self.amt - dt * 1.2)
            self._sync()

    def draw(self, surf, cam):
        if self.amt < 1:
            surf.blit(A.door_surface(self.full.w, self.full.h, self.color, self.amt), (self.full.x - cam[0], self.full.y - cam[1]))
        if self.label:
            t = A.text(self.label, 16, self.color, True, True)
            surf.blit(t, (self.full.centerx - t.get_width() // 2 - cam[0], self.full.y - 22 - cam[1]))


class Bridge:
    """Platform tiles that appear when a puzzle is solved (acts as one-way floor segments)."""

    def __init__(self, x, y, w_tiles, color=PURPLE):
        self.rect = pygame.Rect(x, y, w_tiles * TILE, 16)
        self.color, self.built, self.amt = color, False, 0.0
        self.delta = (0.0, 0.0)               # static: lets the player stand on it like any carried platform

    def set_built(self, v=True, instant=False):
        self.built = v
        if instant:
            self.amt = 1.0 if v else 0.0

    def update(self, dt):
        self.amt = min(1.0, self.amt + dt * 1.5) if self.built else max(0.0, self.amt - dt * 1.5)

    def draw(self, surf, cam):
        if self.amt <= 0:
            return
        w = int(self.rect.w * self.amt)
        s = pygame.Surface((max(1, w), 16), pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.color, 200), (0, 0, w, 16), border_radius=4)
        pygame.draw.rect(s, CREAM, (0, 0, w, 16), 2, border_radius=4)
        surf.blit(s, (self.rect.x - cam[0], self.rect.y - cam[1]))
        surf.blit(A.glow(30, self.color), (self.rect.centerx - 30 - cam[0], self.rect.y - 22 - cam[1]))
