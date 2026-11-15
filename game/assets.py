"""Procedural pixel-art assets: every sprite/tile/background is generated in code, so nothing can be missing."""
from __future__ import annotations

import math
import random

import pygame

from game.settings import *  # noqa

_cache: dict = {}


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _px(rows: list[str], pal: dict[str, tuple], scale: int = 2) -> pygame.Surface:
    h, w = len(rows), max(len(r) for r in rows)
    s = _surf(w, h)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in pal:
                s.set_at((x, y), pal[c])
    return pygame.transform.scale(s, (w * scale, h * scale)) if scale != 1 else s


def flip(s: pygame.Surface) -> pygame.Surface:
    return pygame.transform.flip(s, True, False)


# ---------------------------------------------------------------- fonts
def font(size: int, bold: bool = False) -> pygame.font.Font:
    key = ("font", size, bold)
    if key not in _cache:
        for name in ("consolas", "dejavusansmono", "couriernew", "monospace"):
            path = pygame.font.match_font(name, bold=bold)
            if path:
                _cache[key] = pygame.font.Font(path, size)
                break
        else:
            _cache[key] = pygame.font.Font(None, int(size * 1.25))
    return _cache[key]


def text(s: str, size: int = 16, color=CREAM, bold: bool = False, shadow: bool = False) -> pygame.Surface:
    f = font(size, bold)
    img = f.render(s, True, color)
    if shadow:
        sh = f.render(s, True, DARK)
        out = _surf(img.get_width() + 2, img.get_height() + 2)
        out.blit(sh, (2, 2)); out.blit(img, (0, 0))
        return out
    return img


def wrap(s: str, size: int, width: int, bold: bool = False) -> list[str]:
    f = font(size, bold)
    lines = []
    for para in s.split("\n"):
        cur = ""
        for w in para.split(" "):
            t = (cur + " " + w).strip()
            if f.size(t)[0] <= width or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- characters
ALEX = {
    "idle": ["....hhhh....", "...hhhhhh...", "...hsssss...", "...sessse...", "....ssss....", "...cccccc...", "..cccccccc..", "..sccccccs..", "..sccggccs..", "...cccccc...", "...pp..pp...", "...pp..pp...", "..bbb..bbb.."],
}
ALEX_PAL = {"h": (92, 54, 36), "s": (240, 190, 150), "e": (30, 30, 50), "c": (54, 150, 200), "g": GOLD, "p": (60, 70, 120), "b": (80, 50, 40)}


def alex_frames() -> dict:
    if "alex" in _cache:
        return _cache["alex"]
    base = ALEX["idle"]
    idle = _px(base, ALEX_PAL, 3)
    # walk: alternate legs
    w1 = base[:10] + ["...pp..pp...", "..pp....pp..", "..bb....bb.."]
    w2 = base[:10] + ["....pppp....", "....pppp....", "....bbbb...."]
    run = [_px(w1, ALEX_PAL, 3), _px(w2, ALEX_PAL, 3), _px(base, ALEX_PAL, 3), _px(w2, ALEX_PAL, 3)]
    jump = _px(base[:10] + ["..pp....pp..", "..pp....pp..", "..bb....bb.."], ALEX_PAL, 3)
    fall = _px(base[:10] + ["...pp..pp...", "...pp..pp...", "...bb..bb..."], ALEX_PAL, 3)
    d = {"idle": [idle], "run": run, "jump": [jump], "fall": [fall]}
    d["left"] = {k: [flip(f) for f in v] for k, v in d.items()}
    _cache["alex"] = d
    return d


def dat_frames() -> list[pygame.Surface]:
    """DAT the robot (floating, glowing eye)."""
    if "dat" in _cache:
        return _cache["dat"]
    out = []
    for i in range(4):
        s = _surf(40, 40)
        bob = int(2 * math.sin(i * math.pi / 2))
        pygame.draw.circle(s, (80, 220, 255, 60), (20, 20 + bob), 18)
        pygame.draw.rect(s, (180, 190, 210), (8, 10 + bob, 24, 18), border_radius=6)
        pygame.draw.rect(s, (90, 100, 130), (8, 10 + bob, 24, 18), 2, border_radius=6)
        pygame.draw.rect(s, (20, 30, 50), (12, 14 + bob, 16, 9), border_radius=3)
        pygame.draw.circle(s, TEAL, (16 + (i % 2) * 8, 18 + bob), 3)
        pygame.draw.line(s, GOLD, (20, 10 + bob), (20, 4 + bob), 2)
        pygame.draw.circle(s, GOLD if i % 2 else RED, (20, 4 + bob), 2)
        pygame.draw.rect(s, (110, 120, 150), (14, 29 + bob, 12, 4), border_radius=2)
        out.append(s)
    _cache["dat"] = out
    return out


def slime_frames() -> list[pygame.Surface]:
    if "slime" in _cache:
        return _cache["slime"]
    out = []
    for i in range(2):
        s = _surf(30, 22)
        h = 16 + i * 3
        pygame.draw.ellipse(s, (60, 190, 110), (2, 22 - h, 26, h))
        pygame.draw.ellipse(s, (120, 240, 160), (6, 22 - h + 2, 8, 5))
        pygame.draw.circle(s, DARK, (10, 22 - h // 2), 2); pygame.draw.circle(s, DARK, (20, 22 - h // 2), 2)
        out.append(s)
    _cache["slime"] = out
    return out


def bat_frames() -> list[pygame.Surface]:
    if "bat" in _cache:
        return _cache["bat"]
    out = []
    for i in range(2):
        s = _surf(34, 20)
        pygame.draw.ellipse(s, (70, 50, 110), (11, 6, 12, 12))
        up = 2 if i == 0 else 12
        pygame.draw.polygon(s, (100, 70, 150), [(12, 10), (0, up), (4, 14)])
        pygame.draw.polygon(s, (100, 70, 150), [(22, 10), (34, up), (30, 14)])
        pygame.draw.circle(s, RED, (15, 10), 1); pygame.draw.circle(s, RED, (19, 10), 1)
        out.append(s)
    _cache["bat"] = out
    return out


def gem_frame(i: int = 0) -> pygame.Surface:
    key = ("gem", i % 6)
    if key not in _cache:
        s = _surf(20, 20)
        w = 4 + abs(3 - (i % 6)) * 2
        pts = [(10, 1), (10 + w, 9), (10, 19), (10 - w, 9)]
        pygame.draw.polygon(s, TEAL, pts)
        pygame.draw.polygon(s, CREAM, pts, 1)
        pygame.draw.line(s, CREAM, (10, 3), (10, 10), 1)
        _cache[key] = s
    return _cache[key]


def checkpoint_frame(active: bool) -> pygame.Surface:
    key = ("cp", active)
    if key not in _cache:
        s = _surf(32, 64)
        pygame.draw.rect(s, (110, 110, 130), (14, 8, 4, 56))
        pygame.draw.polygon(s, GREEN if active else (130, 90, 90), [(18, 8), (32, 15), (18, 24)])
        pygame.draw.circle(s, GOLD if active else (90, 90, 100), (16, 7), 4)
        _cache[key] = s
    return _cache[key]


def terminal_frame(active: bool, solved: bool, t: float = 0) -> pygame.Surface:
    s = _surf(48, 64)
    pygame.draw.rect(s, (40, 50, 75), (4, 20, 40, 44), border_radius=4)
    pygame.draw.rect(s, (90, 110, 150), (4, 20, 40, 44), 2, border_radius=4)
    col = GREEN if solved else (TEAL if active else (60, 90, 110))
    pygame.draw.rect(s, (10, 20, 30), (9, 26, 30, 20))
    for i in range(3):
        pygame.draw.line(s, col, (12, 30 + i * 5), (12 + 8 + int(14 * abs(math.sin(t * 2 + i))) * (0 if solved else 1) + (14 if solved else 0), 30 + i * 5), 2)
    pygame.draw.rect(s, GOLD, (18, 52, 12, 6), border_radius=2)
    return s


def trophy() -> pygame.Surface:
    s = _surf(40, 48)
    pygame.draw.polygon(s, GOLD, [(8, 6), (32, 6), (28, 26), (12, 26)])
    pygame.draw.rect(s, GOLD, (17, 26, 6, 10)); pygame.draw.rect(s, GOLD, (10, 36, 20, 6), border_radius=2)
    pygame.draw.arc(s, GOLD, (0, 6, 14, 14), 1.57, 4.7, 3); pygame.draw.arc(s, GOLD, (26, 6, 14, 14), -1.57, 1.57, 3)
    return s


def guardian_frame(i: int = 0, hurt: bool = False) -> pygame.Surface:
    """The Guardian: big crystalline tree-golem."""
    s = _surf(128, 144)
    body = (230, 120, 110) if hurt else (84, 66, 140)
    glow = 20 + int(10 * math.sin(i * 0.2))
    pygame.draw.circle(s, (128, 90, 213, 40), (64, 70), 60 + glow // 4)
    pygame.draw.rect(s, (80, 54, 40), (50, 80, 28, 60))                    # trunk legs
    pygame.draw.polygon(s, body, [(64, 6), (110, 60), (96, 100), (32, 100), (18, 60)])
    pygame.draw.polygon(s, (170, 140, 240), [(64, 6), (110, 60), (64, 50)])
    for dx in (-34, 0, 34):                                                   # crown branches
        pygame.draw.line(s, (60, 140, 90), (64 + dx // 2, 52), (64 + dx * 1.4, 18 + abs(dx) // 3), 5)
        pygame.draw.circle(s, GREEN, (int(64 + dx * 1.4), 18 + abs(dx) // 3), 8)
    pygame.draw.circle(s, (20, 10, 30), (46, 66), 9); pygame.draw.circle(s, (20, 10, 30), (82, 66), 9)
    pygame.draw.circle(s, GOLD, (46, 66), 4); pygame.draw.circle(s, GOLD, (82, 66), 4)
    pygame.draw.rect(s, (20, 10, 30), (46, 84, 36, 6), border_radius=3)
    return s


# ---------------------------------------------------------------- tiles
THEMES = {
    "dungeon": {"bg": ((20, 22, 40), (42, 38, 70)), "tile": (74, 78, 110), "top": (110, 120, 170), "acc": GOLD},
    "lab": {"bg": ((12, 30, 40), (24, 64, 74)), "tile": (50, 90, 100), "top": (90, 190, 190), "acc": TEAL},
    "crystal": {"bg": ((26, 16, 50), (60, 34, 100)), "tile": (84, 64, 140), "top": (170, 130, 240), "acc": PURPLE},
    "tree": {"bg": ((10, 30, 24), (30, 70, 44)), "tile": (84, 62, 40), "top": (72, 160, 80), "acc": GREEN},
    "arena": {"bg": ((36, 14, 24), (80, 30, 44)), "tile": (96, 60, 70), "top": (220, 130, 110), "acc": RED},
}


def tile_surface(kind: int, theme: str, variant: int = 0, top: bool = False) -> pygame.Surface:
    key = ("tile", kind, theme, variant, top)
    if key in _cache:
        return _cache[key]
    th = THEMES[theme]
    s = _surf(TILE, TILE)
    rnd = random.Random(variant * 31 + kind)
    if kind == SOLID:
        s.fill(th["tile"])
        for _ in range(10):
            c = tuple(max(0, min(255, v + rnd.randint(-14, 14))) for v in th["tile"])
            pygame.draw.rect(s, c, (rnd.randrange(0, TILE - 4), rnd.randrange(0, TILE - 4), rnd.choice((3, 4, 6)), rnd.choice((2, 3))))
        pygame.draw.rect(s, tuple(max(0, v - 25) for v in th["tile"]), (0, 0, TILE, TILE), 1)
        if top:
            pygame.draw.rect(s, th["top"], (0, 0, TILE, 6))
            pygame.draw.rect(s, tuple(min(255, v + 30) for v in th["top"]), (0, 0, TILE, 2))
    elif kind == ONEWAY:
        pygame.draw.rect(s, th["top"], (0, 0, TILE, 8), border_radius=2)
        pygame.draw.rect(s, th["acc"], (0, 0, TILE, 3))
        for x in range(4, TILE, 8):
            pygame.draw.line(s, tuple(max(0, v - 40) for v in th["top"]), (x, 8), (x, 12), 2)
    elif kind == SPIKE:
        for x in range(0, TILE, 8):
            pygame.draw.polygon(s, (200, 205, 220), [(x, TILE), (x + 4, TILE - 14), (x + 8, TILE)])
            pygame.draw.polygon(s, (130, 135, 160), [(x + 4, TILE - 14), (x + 8, TILE), (x + 4, TILE)])
    _cache[key] = s
    return s


def platform_surface(w: int, theme: str) -> pygame.Surface:
    key = ("plat", w, theme)
    if key not in _cache:
        th = THEMES[theme]
        s = _surf(w, 16)
        pygame.draw.rect(s, th["top"], (0, 0, w, 16), border_radius=4)
        pygame.draw.rect(s, th["acc"], (0, 0, w, 4), border_radius=2)
        pygame.draw.rect(s, tuple(max(0, v - 50) for v in th["top"]), (0, 12, w, 4))
        for x in range(8, w - 4, 16):
            pygame.draw.circle(s, th["acc"], (x, 9), 2)
        _cache[key] = s
    return _cache[key]


# ---------------------------------------------------------------- parallax backgrounds
def background_layers(theme: str, w: int = WIDTH, h: int = HEIGHT) -> list[tuple[pygame.Surface, float]]:
    """Returns [(surface, scroll_factor)] back to front. Surfaces are wider than the screen and wrap horizontally."""
    key = ("bg", theme)
    if key in _cache:
        return _cache[key]
    th = THEMES[theme]
    (top, bot) = th["bg"]
    sky = pygame.Surface((w, h))
    for y in range(h):
        t = y / h
        pygame.draw.line(sky, tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)), (0, y), (w, y))
    rnd = random.Random(hash(theme) & 0xFFFF)
    stars = _surf(w, h)
    for _ in range(60):
        c = rnd.choice((CREAM, th["acc"], (150, 160, 200)))
        pygame.draw.circle(stars, (*c, rnd.randint(70, 180)), (rnd.randrange(w), rnd.randrange(h // 2)), rnd.choice((1, 1, 2)))
    layers = [(sky, 0.0), (stars, 0.02)]
    for depth, (shade, base, var, f) in enumerate(((0.55, 300, 120, 0.12), (0.8, 380, 100, 0.25), (1.1, 450, 70, 0.4))):
        width = w * 2
        s = _surf(width, h)
        col = tuple(int(c * shade * 0.6 + th["tile"][i] * 0.3 * shade) for i, c in enumerate(top))
        col = tuple(max(0, min(255, c + 20 + depth * 12)) for c in col)
        x = 0
        while x < width:
            ww = rnd.randint(70, 150)
            hh = rnd.randint(var // 2, var) + (base - 300) // 2
            if theme == "tree":
                pygame.draw.rect(s, col, (x + ww // 2 - 8, h - hh, 16, hh))
                pygame.draw.circle(s, col, (x + ww // 2, h - hh), ww // 2)
            elif theme in ("crystal", "lab"):
                pygame.draw.polygon(s, col, [(x, h), (x + ww // 2, h - hh), (x + ww, h)])
            elif theme == "arena":
                pygame.draw.rect(s, col, (x, h - hh, ww // 2, hh))
                pygame.draw.rect(s, col, (x + 4, h - hh - 12, ww // 2 - 8, 12))
            else:
                pygame.draw.rect(s, col, (x, h - hh, ww, hh), border_top_left_radius=ww // 2, border_top_right_radius=ww // 2)
            x += ww + rnd.randint(-10, 30)
        layers.append((s, f))
    _cache[key] = layers
    return layers


def glow(radius: int, color) -> pygame.Surface:
    key = ("glow", radius, color)
    if key not in _cache:
        s = _surf(radius * 2, radius * 2)
        for r in range(radius, 0, -3):
            a = int(60 * (1 - r / radius) ** 1.5) + 4
            pygame.draw.circle(s, (*color[:3], a), (radius, radius), r)
        _cache[key] = s
    return _cache[key]


def door_surface(w: int, h: int, color, open_amt: float = 0.0) -> pygame.Surface:
    s = _surf(w, h)
    hh = int(h * (1 - open_amt))
    if hh > 0:
        pygame.draw.rect(s, (46, 52, 80), (0, 0, w, hh))
        pygame.draw.rect(s, color, (0, 0, w, hh), 3)
        for y in range(6, hh, 14):
            pygame.draw.line(s, color, (4, y), (w - 4, y), 1)
        pygame.draw.circle(s, color, (w // 2, hh // 2), 6, 2)
    return s


def vignette(w=WIDTH, h=HEIGHT) -> pygame.Surface:
    key = ("vig",)
    if key not in _cache:
        s = _surf(w, h)
        for i in range(40):
            a = int(120 * (1 - i / 40) ** 2)
            pygame.draw.rect(s, (0, 0, 0, a), (i, i, w - 2 * i, h - 2 * i), 1)
        _cache[key] = s
    return _cache[key]


def holo_panel(w: int, h: int, title: str = "", border=TEAL) -> pygame.Surface:
    s = _surf(w, h)
    pygame.draw.rect(s, (12, 26, 42, 225), (0, 0, w, h), border_radius=10)
    pygame.draw.rect(s, border, (0, 0, w, h), 2, border_radius=10)
    for y in range(6, h, 6):
        pygame.draw.line(s, (*border, 14), (4, y), (w - 4, y))
    if title:
        s.blit(text(title, 16, GOLD, True), (14, 8))
        pygame.draw.line(s, border, (12, 30), (w - 12, 30), 1)
    return s
