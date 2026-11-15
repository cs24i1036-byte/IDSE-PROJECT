"""Reusable UI pieces: buttons, bars, DAT speech, tree diagram, hearts."""
from __future__ import annotations

import math

import pygame

from game import assets as A
from game.settings import *  # noqa


class Button:
    def __init__(self, rect, label, key=None, color=TEAL, size=16, enabled=True, toggle=False):
        self.rect = pygame.Rect(rect)
        self.label, self.key, self.color, self.size = label, key if key is not None else label, color, size
        self.enabled, self.toggle, self.on = enabled, toggle, False

    def hit(self, pos) -> bool:
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surf, mouse=None, selected=False):
        hover = self.enabled and mouse is not None and self.rect.collidepoint(mouse)
        on = selected or self.on
        base = self.color if self.enabled else (70, 78, 95)
        fill = tuple(min(255, int(c * (0.55 if not (hover or on) else 0.9))) for c in base) if self.enabled else (36, 42, 56)
        pygame.draw.rect(surf, fill, self.rect, border_radius=8)
        pygame.draw.rect(surf, CREAM if (hover or on) else base, self.rect, 2, border_radius=8)
        t = A.text(self.label, self.size, DARK if (hover or on) and self.enabled else (CREAM if self.enabled else (120, 128, 145)), True)
        surf.blit(t, t.get_rect(center=self.rect.center))


def draw_text(surf, s, pos, size=16, color=CREAM, bold=False, width=None, line_h=None, align="left"):
    if width is None:
        img = A.text(s, size, color, bold)
        r = img.get_rect(topleft=pos) if align == "left" else img.get_rect(midtop=pos)
        surf.blit(img, r)
        return r.bottom
    y = pos[1]
    lh = line_h or int(size * 1.35)
    for ln in A.wrap(s, size, width, bold):
        img = A.text(ln, size, color, bold)
        surf.blit(img, img.get_rect(topleft=(pos[0], y)) if align == "left" else img.get_rect(midtop=(pos[0], y)))
        y += lh
    return y


def chip(surf, rect, label, on: bool, color=TEAL, size=14):
    pygame.draw.rect(surf, color if on else (40, 52, 72), rect, border_radius=6)
    pygame.draw.rect(surf, CREAM if on else color, rect, 1, border_radius=6)
    t = A.text(label, size, DARK if on else CREAM, True)
    surf.blit(t, t.get_rect(center=rect.center))


def bar(surf, rect, frac, color=GREEN, back=(30, 40, 58), border=CREAM):
    pygame.draw.rect(surf, back, rect, border_radius=5)
    w = int(rect.w * max(0.0, min(1.0, frac)))
    if w > 0:
        pygame.draw.rect(surf, color, (rect.x, rect.y, w, rect.h), border_radius=5)
    pygame.draw.rect(surf, border, rect, 1, border_radius=5)


def hearts(surf, x, y, hp, max_hp=MAX_HEALTH):
    for i in range(max_hp):
        c = RED if i < hp else (60, 40, 50)
        cx = x + i * 26
        pygame.draw.circle(surf, c, (cx + 6, y + 6), 6); pygame.draw.circle(surf, c, (cx + 14, y + 6), 6)
        pygame.draw.polygon(surf, c, [(cx, y + 9), (cx + 20, y + 9), (cx + 10, y + 21)])
        pygame.draw.polygon(surf, CREAM, [(cx, y + 9), (cx + 20, y + 9), (cx + 10, y + 21)], 1) if i < hp else None


def speech(surf, text, anchor, width=300, size=15, accent=TEAL, alpha=235):
    """Speech bubble anchored above `anchor` (screen coords)."""
    lines = A.wrap(text, size, width - 24)
    lh = int(size * 1.35)
    h = len(lines) * lh + 20
    x = max(8, min(WIDTH - width - 8, anchor[0] - width // 2))
    y = max(8, anchor[1] - h - 18)
    bub = pygame.Surface((width, h), pygame.SRCALPHA)
    pygame.draw.rect(bub, (14, 24, 40, alpha), (0, 0, width, h), border_radius=10)
    pygame.draw.rect(bub, accent, (0, 0, width, h), 2, border_radius=10)
    for i, ln in enumerate(lines):
        bub.blit(A.text(ln, size, CREAM), (12, 10 + i * lh))
    surf.blit(bub, (x, y))
    tip = [(anchor[0] - 7, y + h - 1), (anchor[0] + 7, y + h - 1), (anchor[0], y + h + 12)]
    pygame.draw.polygon(surf, (14, 24, 40), tip); pygame.draw.lines(surf, accent, False, tip, 2)


# ------------------------------------------------------------------ tree diagram
def _layout(node, depth=0, x0=0.0, x1=1.0, out=None, parent=None, side=""):
    out = out if out is not None else []
    xm = (x0 + x1) / 2
    idx = len(out)
    out.append({"node": node, "depth": depth, "x": xm, "parent": parent, "side": side})
    if "leaf" not in node:
        _layout(node["yes"], depth + 1, x0, xm, out, idx, "Yes")
        _layout(node["no"], depth + 1, xm, x1, out, idx, "No")
    return out


def tree_depth(node) -> int:
    return 0 if "leaf" in node else 1 + max(tree_depth(node["yes"]), tree_depth(node["no"]))


def draw_tree(surf, rect, tree, visited=(), current=None, pulse=0.0, size=13):
    """Draw a hand-authored tree dict: internal node {'label','yes','no','id'}, leaf {'leaf','id'}.
    visited = set of node ids on the active route; current = id of the node being answered."""
    rect = pygame.Rect(rect)
    nodes = _layout(tree)
    levels = tree_depth(tree) + 1
    gap = rect.h / levels
    pos = []
    for n in nodes:
        pos.append((rect.x + n["x"] * rect.w, rect.y + gap * (n["depth"] + 0.5)))
    for i, n in enumerate(nodes):
        if n["parent"] is not None:
            a, b = pos[n["parent"]], pos[i]
            on = nodes[n["parent"]]["node"].get("id") in visited and n["node"].get("id") in visited
            pygame.draw.line(surf, GOLD if on else (90, 105, 130), a, b, 3 if on else 2)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            t = A.text(n["side"], 12, GOLD if on else (150, 160, 180), True)
            surf.blit(t, t.get_rect(center=(mid[0] + (-14 if n["side"] == "Yes" else 14), mid[1])))
    for i, n in enumerate(nodes):
        node, (x, y) = n["node"], pos[i]
        nid = node.get("id")
        on = nid in visited
        if "leaf" in node:
            col = GREEN if node["leaf"] == "Safe" else RED
            t = A.text(node["leaf"], size, DARK if on else CREAM, True)
            r = pygame.Rect(0, 0, t.get_width() + 14, 24); r.center = (x, y)
            pygame.draw.rect(surf, col if on else (46, 58, 80), r, border_radius=12)
            pygame.draw.rect(surf, CREAM if on else col, r, 2, border_radius=12)
        else:
            w = int(len(node["label"]) * (size * 0.62)) + 16
            r = pygame.Rect(0, 0, w, 26); r.center = (x, y)
            glow = nid == current
            pygame.draw.rect(surf, TEAL if (on or glow) else (46, 58, 80), r, border_radius=8)
            pygame.draw.rect(surf, GOLD if glow and int(pulse * 4) % 2 == 0 else CREAM if on else TEAL, r, 2, border_radius=8)
            t = A.text(node["label"], size, DARK if (on or glow) else CREAM, True)
        surf.blit(t, t.get_rect(center=r.center))
    return pos


def classify_tree(tree, record: dict) -> tuple[str, list]:
    """Walk a hand-authored tree with a creature record. Returns (label, ids visited). Pure data -> no hard-coded routes."""
    node, ids = tree, []
    while "leaf" not in node:
        ids.append(node["id"])
        node = node["yes"] if record[node["feature"]] == "Yes" else node["no"]
    ids.append(node["id"])
    return node["leaf"], ids
