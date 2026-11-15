"""All game screens: menu, story, characters, level map, gameplay, completion, inventory, victory."""
from __future__ import annotations

import math
import random

import pygame

from game import assets as A
from game import ui
from game.entities import Enemy, Particle, Player
from game.levels import make_level
from game.settings import *  # noqa

BADGE_COLORS = [GOLD, TEAL, PURPLE, GREEN, RED]


class Scene:
    def __init__(self, game):
        self.game = game
        self.t = 0.0

    def enter(self): ...
    def handle(self, ev): ...
    def update(self, dt): self.t += dt
    def draw(self, surf): ...

    @property
    def audio(self): return self.game.audio

    @property
    def save(self): return self.game.save


def backdrop(surf, theme, t, scroll=0.0):
    for layer, f in A.background_layers(theme):
        w = layer.get_width()
        x = -((scroll * f + t * (8 if f > 0.1 else 0) * f) % w)
        surf.blit(layer, (x, 0))
        if x + w < WIDTH:
            surf.blit(layer, (x + w, 0))


def title_text(surf, text, y, size=44, color=GOLD, cx=WIDTH // 2):
    sh = A.text(text, size, (10, 14, 24), True)
    img = A.text(text, size, color, True)
    surf.blit(sh, sh.get_rect(center=(cx + 3, y + 3))); surf.blit(img, img.get_rect(center=(cx, y)))


def badge_icon(surf, center, color, size=34, locked=False, label=""):
    c = (70, 78, 95) if locked else color
    pts = [(center[0] + math.cos(math.radians(a - 90)) * size, center[1] + math.sin(math.radians(a - 90)) * size) for a in range(0, 360, 60)]
    pygame.draw.polygon(surf, (28, 36, 52), pts); pygame.draw.polygon(surf, c, pts, 4)
    pygame.draw.circle(surf, c, center, size // 3)
    if locked:
        t = A.text("?", 22, (110, 118, 135), True); surf.blit(t, t.get_rect(center=center))


# ======================================================================================= MENU
class MenuScene(Scene):
    def enter(self):
        self.audio.music("menu")
        self.rebuild()

    def rebuild(self):
        items = [("NEW GAME", "new"), ("CONTINUE", "continue"), ("LEVEL SELECT", "levels"), ("HOW TO PLAY", "howto"), ("ACHIEVEMENTS", "inv"), ("SOUND: " + ("OFF" if self.audio.muted else "ON"), "mute"), ("QUIT", "quit")]
        self.buttons = []
        for i, (lab, key) in enumerate(items):
            en = not (key in ("continue", "levels", "inv") and not self.save.has_progress())
            self.buttons.append(ui.Button((WIDTH // 2 - 130, 186 + i * 40, 260, 34), lab, key=key, color=GOLD if key == "new" else TEAL, size=17, enabled=en))
        self.sel = 0 if not self.save.has_progress() else 1
        self.confirm = False

    def activate(self, key):
        g = self.game
        self.audio.play("click")
        if key == "new":
            if self.save.has_progress() and not self.confirm:
                self.confirm = True; return
            self.save.reset(); g.go(StoryScene(g))
        elif key == "continue":
            nxt = next((l["id"] for l in LEVELS if not self.save.is_completed(l["id"])), None)
            if nxt is None: g.go(LevelSelectScene(g))
            else: g.go(GameplayScene(g, nxt))
        elif key == "levels": g.go(LevelSelectScene(g))
        elif key == "howto": g.go(HowToScene(g))
        elif key == "inv": g.go(InventoryScene(g, MenuScene(g)))
        elif key == "mute": self.audio.toggle_mute(); self.rebuild()
        elif key == "quit": g.quit()

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b in self.buttons:
                if b.hit(ev.pos): self.activate(b.key); return
        if ev.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.hit(ev.pos): self.sel = i
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.buttons)
                while not self.buttons[self.sel].enabled: self.sel = (self.sel + 1) % len(self.buttons)
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.buttons)
                while not self.buttons[self.sel].enabled: self.sel = (self.sel - 1) % len(self.buttons)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE) and self.buttons[self.sel].enabled: self.activate(self.buttons[self.sel].key)
            elif ev.key == pygame.K_ESCAPE: self.confirm = False

    def draw(self, surf):
        backdrop(surf, "dungeon", self.t, self.t * 20)
        title_text(surf, TITLE, 96, 62)
        title_text(surf, SUBTITLE, 150, 20, CREAM)
        a = A.alex_frames()
        surf.blit(a["run"][int(self.t * 8) % 4], (140, 410 - 39 * 0 - 39)) if False else None
        mouse = pygame.mouse.get_pos()
        for i, b in enumerate(self.buttons): b.draw(surf, mouse, selected=(i == self.sel and b.enabled))
        pygame.draw.rect(surf, (36, 42, 70), (0, 500, WIDTH, 40))
        surf.blit(A.alex_frames()["idle"][0], (150, 462)); surf.blit(A.dat_frames()[int(self.t * 3) % 4], (200, 440 + math.sin(self.t * 3) * 4))
        surf.blit(A.guardian_frame(int(self.t * 10)), (WIDTH - 220, 380))
        ui.draw_text(surf, "Arrows/WASD move   Space jump   Shift dash   E interact   H hint   Esc pause", (WIDTH // 2, 516), 13, (150, 165, 190), align="mid")
        if self.confirm:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 170)); surf.blit(ov, (0, 0))
            ui.draw_text(surf, "Start over? Your saved progress will be erased.", (WIDTH // 2, 230), 20, CREAM, True, align="mid")
            ui.draw_text(surf, "Press the NEW GAME button again to confirm, Esc to cancel.", (WIDTH // 2, 262), 15, GOLD, align="mid")


# ======================================================================================= STORY / CHARACTERS
STORY = ["Long ago, the Great Archive of Mystic Creatures was sealed inside a living puzzle: the INVISIBLE MAZE.",
         "There are no walls to follow. Only questions. Every answer opens a hidden path, and every wrong turn leads nowhere.",
         "Its keeper, the GUARDIAN, yields only to someone who can think like a Decision Tree: ask the right questions, split the world wisely, and classify the unknown.",
         "You are ALEX, a young data explorer. At your side floats DAT, your Data Analysis Tutor. Together you will find the way out."]


class StoryScene(Scene):
    def enter(self):
        self.i, self.chars = 0, 0.0
        self.audio.music("crystal")

    def handle(self, ev):
        adv = ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e))
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.game.go(HowToScene(self.game, lambda: CharacterScene(self.game))); return
        if adv:
            if self.chars < len(STORY[self.i]): self.chars = 1e9
            elif self.i + 1 < len(STORY): self.i += 1; self.chars = 0; self.audio.play("click")
            else: self.game.go(HowToScene(self.game, lambda: CharacterScene(self.game)))

    def update(self, dt):
        super().update(dt); self.chars += dt * 55

    def draw(self, surf):
        backdrop(surf, "crystal", self.t, self.t * 12)
        title_text(surf, "THE LEGEND", 70, 34)
        box = A.holo_panel(760, 220, "", PURPLE); surf.blit(box, (100, 150))
        ui.draw_text(surf, STORY[self.i][: int(self.chars)], (130, 180), 22, CREAM, width=700, line_h=34)
        ui.draw_text(surf, f"{self.i + 1}/{len(STORY)}   Enter / click: continue   Esc: skip", (WIDTH // 2, 400), 14, (150, 165, 190), align="mid")


class CharacterScene(Scene):
    CARDS = [("ALEX", "The Hero", "A curious data explorer: quick on his feet, quicker with a question. Runs, jumps, dashes and strikes.", "alex"),
             ("DAT", "Data Analysis Tutor", "A floating robot companion. Press H any time for a hint, and watch for his tips.", "dat"),
             ("THE GUARDIAN", "Keeper of the Maze", "Waits behind the final door. Respects only an accurate classifier.", "guardian")]

    def enter(self): self.audio.music("menu")

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_ESCAPE)):
            self.save.intro_seen = True; self.save.save()
            self.game.go(GameplayScene(self.game, 1))

    def draw(self, surf):
        backdrop(surf, "lab", self.t, self.t * 10)
        title_text(surf, "MEET THE CAST", 56, 34)
        for i, (name, role, blurb, kind) in enumerate(self.CARDS):
            x = 40 + i * 300
            surf.blit(A.holo_panel(280, 360, "", [GOLD, TEAL, RED][i]), (x, 100))
            if kind == "alex": img = pygame.transform.scale(A.alex_frames()["idle"][0], (72, 78))
            elif kind == "dat": img = pygame.transform.scale(A.dat_frames()[int(self.t * 3) % 4], (96, 96))
            else: img = pygame.transform.smoothscale(A.guardian_frame(int(self.t * 10)), (110, 124))
            surf.blit(img, img.get_rect(center=(x + 140, 190 + math.sin(self.t * 2 + i) * 3)))
            ui.draw_text(surf, name, (x + 140, 270), 22, GOLD, True, align="mid")
            ui.draw_text(surf, role, (x + 140, 300), 14, TEAL, align="mid")
            ui.draw_text(surf, blurb, (x + 18, 336), 15, CREAM, width=250)
        ui.draw_text(surf, "Press Enter to begin your adventure", (WIDTH // 2, 490), 18, GOLD, True, align="mid")



# ======================================================================================= HOW TO PLAY
HOWTO_STEPS = [("1", "WALK TO THE GLOWING TERMINAL", "Follow the big arrow on screen. Run with A / D, jump with Space. Jump on enemies to beat them."),
               ("2", "PRESS  E  AND ANSWER", "A puzzle window opens. Read it, click your answer. A wrong answer is fine: it just tells you why and you try again."),
               ("3", "THE PATH OPENS, KEEP GOING", "A right answer opens the door or bridge. Solve every terminal, then enter the golden portal to finish the level.")]


class HowToScene(Scene):
    def __init__(self, game, nxt=None):
        super().__init__(game); self.nxt = nxt

    def enter(self): self.audio.music("menu")

    def leave(self):
        self.audio.play("click")
        self.game.go(self.nxt() if self.nxt else MenuScene(self.game))

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_ESCAPE)):
            self.leave()

    def draw(self, surf):
        backdrop(surf, "lab", self.t, self.t * 10)
        title_text(surf, "HOW TO PLAY", 48, 36)
        ui.draw_text(surf, "Every level is the same simple loop:", (WIDTH // 2, 86), 17, CREAM, align="mid")
        for i, (n, head, body) in enumerate(HOWTO_STEPS):
            x = 36 + i * 306
            surf.blit(A.holo_panel(290, 230, "", [GOLD, TEAL, GREEN][i]), (x, 112))
            pygame.draw.circle(surf, [GOLD, TEAL, GREEN][i], (x + 40, 158), 24); ui.draw_text(surf, n, (x + 40, 143), 28, (10, 16, 28), True, align="mid")
            ui.draw_text(surf, head, (x + 76, 142), 15, GOLD, True, width=200, line_h=19)
            ui.draw_text(surf, body, (x + 18, 196), 15, CREAM, width=258, line_h=21)
        keys = [("A / D", "move"), ("Space", "jump"), ("Shift", "dash"), ("F", "attack"), ("E", "use terminal"), ("H", "hint from DAT")]
        for i, (k, d) in enumerate(keys):
            x = 40 + i * 148
            pygame.draw.rect(surf, (20, 30, 50), (x, 372, 138, 62), border_radius=10); pygame.draw.rect(surf, TEAL, (x, 372, 138, 62), 2, border_radius=10)
            ui.draw_text(surf, k, (x + 69, 390), 18, GOLD, True, align="mid"); ui.draw_text(surf, d, (x + 69, 414), 13, CREAM, align="mid")
        ui.draw_text(surf, "Stuck? Press H. DAT gives a hint for exactly where you are.", (WIDTH // 2, 456), 16, TEAL, True, align="mid")
        ui.draw_text(surf, "Press Enter to continue", (WIDTH // 2, 500), 18, GOLD, True, align="mid")

# ======================================================================================= LEVEL SELECT
class LevelSelectScene(Scene):
    POS = [(130, 360), (300, 250), (490, 340), (680, 230), (840, 330)]

    def enter(self):
        self.audio.music("menu")
        done = [l["id"] for l in LEVELS if self.save.is_completed(l["id"])]
        self.sel = min(len(LEVELS), (max(done) + 1) if done else 1) if len(done) < len(LEVELS) else 1

    def start(self, lid):
        if not self.save.is_unlocked(lid):
            self.audio.play("wrong"); return
        self.audio.play("click"); self.game.go(GameplayScene(self.game, lid))

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RIGHT, pygame.K_d): self.sel = min(len(LEVELS), self.sel + 1)
            elif ev.key in (pygame.K_LEFT, pygame.K_a): self.sel = max(1, self.sel - 1)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE): self.start(self.sel)
            elif ev.key == pygame.K_ESCAPE: self.game.go(MenuScene(self.game))
            elif ev.key == pygame.K_i: self.game.go(InventoryScene(self.game, LevelSelectScene(self.game)))
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, p in enumerate(self.POS):
                if math.hypot(ev.pos[0] - p[0], ev.pos[1] - p[1]) < 38:
                    self.sel = i + 1; self.start(i + 1)

    def draw(self, surf):
        backdrop(surf, LEVELS[self.sel - 1]["theme"], self.t, self.t * 10)
        title_text(surf, "THE MAZE MAP", 50, 34)
        for a, b in zip(self.POS, self.POS[1:]):
            pygame.draw.line(surf, (90, 105, 135), a, b, 5)
        for i, p in enumerate(self.POS):
            lv = LEVELS[i]; lid = lv["id"]
            done, unlocked = self.save.is_completed(lid), self.save.is_unlocked(lid)
            col = GREEN if done else (BADGE_COLORS[i] if unlocked else (70, 78, 95))
            pygame.draw.circle(surf, (20, 28, 44), p, 34); pygame.draw.circle(surf, col, p, 34, 4)
            if lid == self.sel: pygame.draw.circle(surf, CREAM, p, 40, 2 + int(math.sin(self.t * 6) > 0))
            t = A.text(str(lid) if unlocked else "X", 26, col, True); surf.blit(t, t.get_rect(center=p))
            if done: pygame.draw.circle(surf, GREEN, (p[0] + 26, p[1] - 26), 10); ui.draw_text(surf, "OK", (p[0] + 26, p[1] - 33), 11, DARK, True, align="mid")
        lv = LEVELS[self.sel - 1]
        box = A.holo_panel(520, 120, "", BADGE_COLORS[self.sel - 1]); surf.blit(box, ((WIDTH - 520) // 2, 396))
        ui.draw_text(surf, f"Level {lv['id']}: {lv['name']}", (WIDTH // 2, 408), 22, GOLD, True, align="mid")
        ui.draw_text(surf, lv["topic"], (WIDTH // 2, 438), 15, CREAM, align="mid")
        state = "COMPLETED" if self.save.is_completed(lv["id"]) else ("Locked: finish the previous level" if not self.save.is_unlocked(lv["id"]) else "Enter: play")
        ui.draw_text(surf, f"{state}    Reward: {lv['xp']} XP + '{lv['badge']}' badge", (WIDTH // 2, 468), 14, TEAL, align="mid")
        ui.draw_text(surf, f"XP {self.save.xp}/{TOTAL_XP}    Left/Right: choose    I: achievements    Esc: menu", (WIDTH // 2, 520), 13, (150, 165, 190), align="mid")


# ======================================================================================= GAMEPLAY
class GameplayScene(Scene):
    def __init__(self, game, level_id: int, fresh: bool = False):
        super().__init__(game)
        self.level_id = level_id
        self.info = LEVELS[level_id - 1]
        self.level = make_level(level_id)
        self.level.say, self.level.sfx = self.say, self.audio.play
        self.player = Player(*self.level.spawn)
        self.level.player = self.player
        self.ctx = game.ctx
        self.ctx.level = self.level
        self.ctx.on_mistake = self.on_mistake
        self.cam = [0.0, 0.0]
        self.particles: list[Particle] = []
        self.panel = None
        self.panel_terminal = None
        self.dialog: list[str] = []
        self.dchars = 0.0
        self.bark = ("", 0.0)
        self.paused = False
        self.pause_sel = 0
        self.over = None                       # 'gameover'
        self.flags = {k: False for k in ("jump", "dash", "attack", "interact")}
        self.safe = (self.level.spawn[0], self.level.spawn[1])
        self.safe_t = 0.0
        self.dat_pos = [self.player.rect.centerx, self.player.rect.top - 40]
        self.consec_mistakes = 0
        self.shake = 0.0
        self.gems_collected = 0
        self.tile_layer = None
        self.cp_index = -1
        self._resume(fresh)
        self._render_tiles()

    # ---------------------------------------------------------------- setup
    def _resume(self, fresh):
        prog = self.save.progress.get(str(self.level_id))
        if prog and not fresh and not self.save.is_completed(self.level_id):
            idx = prog.get("checkpoint", -1)
            self.level.restore(prog.get("state", {}))
            self._activate_cps(idx)
            if 0 <= idx < len(self.level.checkpoints):
                self.player.respawn(self.level.checkpoint_pos(idx))
                self.safe = self.level.checkpoint_pos(idx)
            self.gems_collected = sum(g.taken for g in self.level.gems)
            self.dialog = []
        else:
            self.dialog = list(self.level.intro)
        if not self.dialog:
            self.say("Welcome back, Alex. Press H if you need a hint.")

    def _activate_cps(self, idx):
        self.cp_index = idx
        for i, c in enumerate(self.level.checkpoints): c.active = i <= idx

    def _render_tiles(self):
        g = self.level.grid
        layer = pygame.Surface((g.px_w, g.px_h), pygame.SRCALPHA)
        for ty in range(g.rows):
            for tx in range(g.cols):
                k = g.t[ty][tx]
                if not k: continue
                top = ty == 0 or g.t[ty - 1][tx] != SOLID
                layer.blit(A.tile_surface(k, self.info["theme"], (tx * 7 + ty * 13) % 4, top and k == SOLID), (tx * TILE, ty * TILE))
        self.tile_layer = layer

    def enter(self):
        self.audio.music(self.info["theme"])

    # ---------------------------------------------------------------- helpers
    def say(self, text, secs=5.5):
        self.bark = (text, secs)

    def on_mistake(self):
        self.consec_mistakes += 1
        if self.consec_mistakes >= 2:
            self.say("Hmm. Press H for a hint, or Esc to leave the panel and think.", 6)

    def burst(self, x, y, color, n=10, speed=160):
        for _ in range(n):
            a = random.random() * 6.28
            self.particles.append(Particle(x, y, math.cos(a) * speed * random.random(), math.sin(a) * speed * random.random() - 60, 0.6 + random.random() * 0.4, color, 3))

    def objective(self):
        lv = self.level
        if lv.exit_open: return "Reach the glowing portal"
        t = lv.next_terminal()
        if self.level_id == 5 and lv.model is not None: return "Defeat the Guardian!"
        return f"Use the {t.label.title()}" if t else "Explore"

    def cam_bounds(self):
        if hasattr(self.level, "camera_bounds"):
            return self.level.camera_bounds(self.player)
        return 0, self.level.grid.px_w - WIDTH

    # ---------------------------------------------------------------- input
    def handle(self, ev):
        if self.panel:
            self.panel.handle(ev); return
        if self.over:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE): self.retry()
            elif ev.type == pygame.MOUSEBUTTONDOWN: self.retry()
            return
        if self.dialog:
            if ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e)):
                if self.dchars < len(self.dialog[0]): self.dchars = 1e9
                else: self.dialog.pop(0); self.dchars = 0; self.audio.play("click")
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: self.dialog = []
            return
        if self.paused:
            self.handle_pause(ev); return
        if hasattr(self.level, "handle_event") and self.level.handle_event(ev): return
        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if k in KEYS["pause"]: self.paused, self.pause_sel = True, 0
            elif k in KEYS["jump"]: self.flags["jump"] = True
            elif k in KEYS["dash"]: self.flags["dash"] = True
            elif k in KEYS["attack"]: self.flags["attack"] = True
            elif k in KEYS["interact"]: self.flags["interact"] = True
            elif k in KEYS["hint"]: self.say(self.level.hint(), 8); self.audio.play("hint")
            elif k == pygame.K_m: self.audio.toggle_mute()

    PAUSE_ITEMS = ["Resume", "Restart from checkpoint", "Achievements", "Sound on/off", "Leave to map"]

    def handle_pause(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in KEYS["pause"]: self.paused = False
            elif ev.key in (pygame.K_DOWN, pygame.K_s): self.pause_sel = (self.pause_sel + 1) % 5
            elif ev.key in (pygame.K_UP, pygame.K_w): self.pause_sel = (self.pause_sel - 1) % 5
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE): self.pause_do(self.pause_sel)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i in range(5):
                if pygame.Rect(WIDTH // 2 - 160, 190 + i * 48, 320, 40).collidepoint(ev.pos): self.pause_do(i)

    def pause_do(self, i):
        self.audio.play("click")
        if i == 0: self.paused = False
        elif i == 1: self.paused = False; self.respawn(lose_life=False)
        elif i == 2: self.game.go(InventoryScene(self.game, self))
        elif i == 3: self.audio.toggle_mute()
        elif i == 4: self.save.save(); self.game.go(LevelSelectScene(self.game))

    # ---------------------------------------------------------------- rules
    def respawn(self, lose_life=True, pos=None):
        p = self.player
        full = pos is None                      # falling into a pit keeps the damage; dying/restarting refills health
        if pos is None:
            pos = self.level.checkpoint_pos(self.cp_index) if self.cp_index >= 0 else self.level.spawn
        p.respawn(pos, full=full)
        self.level.projectiles.clear()

    def retry(self):
        self.over = None
        self.player.lives = START_LIVES
        self.respawn()

    def die(self):
        p = self.player
        p.lives -= 1; self.save.deaths += 1
        self.audio.play("hurt")
        self.burst(p.rect.centerx, p.rect.centery, RED, 20, 220)
        if p.lives <= 0: self.over = "gameover"; p.locked = True
        else:
            self.respawn()
            self.say(f"Ouch! Back to the checkpoint. {p.lives} lives left.")

    def update(self, dt):
        super().update(dt)
        p, lv = self.player, self.level
        if self.dialog:
            self.dchars += dt * 60
        self.bark = (self.bark[0], max(0.0, self.bark[1] - dt))
        if self.over:
            return
        if self.panel:
            self.panel.update(dt)
            if self.panel.closed:
                t, panel = self.panel_terminal, self.panel
                self.panel, self.panel_terminal = None, None
                if panel.solved and t is not None and not t.solved:
                    self.consec_mistakes = 0
                    lv.solve(lv.terminals.index(t), panel.result)
                    self.gems_collected += 0
                    self.burst(t.rect.centerx, t.rect.centery, TEAL, 24, 220)
                    self.save.set_checkpoint(self.level_id, max(self.cp_index, -1), lv.state()) if self.cp_index >= 0 else None
            return
        if self.paused:
            return
        locked = bool(self.dialog)
        p.locked = locked
        keys = pygame.key.get_pressed()
        held = lambda name: any(keys[k] for k in KEYS[name])
        inp = {"left": held("left"), "right": held("right"), "jump": held("jump"),
               "jump_pressed": self.flags["jump"], "dash_pressed": self.flags["dash"], "attack_pressed": self.flags["attack"]}
        interact = self.flags["interact"]
        self.flags = {k: False for k in self.flags}
        p.update(dt, inp, lv)
        for ev in p.events:
            self.audio.play({"jump": "jump", "land": "land", "hurt": "hurt", "dash": "dash", "attack": "attack"}.get(ev, "click")) if ev != "fell" else None
        if "land" in p.events: self.burst(p.rect.centerx, p.rect.bottom, (180, 180, 200), 4, 70)
        if "fell" in p.events:
            self.audio.play("hurt")
            p.hurt(1) if p.invuln <= 0 else None
            if p.health > 0: self.respawn(pos=self.safe)
        lv.update(dt, p, self.say, self.audio)
        # safe position tracking
        self.safe_t -= dt
        if p.on_ground and p.platform is None and self.safe_t <= 0 and not lv.grid.touches_spike(p.rect):
            ahead = lambda dx: lv.grid.get((p.rect.centerx + dx) // TILE, p.rect.bottom // TILE)
            if ahead(-26) == SOLID and ahead(26) == SOLID:
                self.safe, self.safe_t = (p.rect.centerx, p.rect.bottom), 0.4
        self._collisions(p, lv, interact)
        if p.dead: self.die()
        # camera + dat
        lo, hi = self.cam_bounds()
        tx = p.rect.centerx - WIDTH * 0.42 + p.facing * 40
        self.cam[0] += (max(lo, min(hi, tx)) - self.cam[0]) * min(1.0, dt * 6)
        self.cam[0] = max(lo, min(hi, self.cam[0]))
        self.cam[1] = max(0, min(lv.grid.px_h - HEIGHT, 0))
        tgt = (p.rect.centerx - p.facing * 46, p.rect.top - 30 + math.sin(self.t * 3) * 5)
        self.dat_pos[0] += (tgt[0] - self.dat_pos[0]) * min(1.0, dt * 4); self.dat_pos[1] += (tgt[1] - self.dat_pos[1]) * min(1.0, dt * 4)
        self.particles = [q for q in self.particles if q.update(dt)]
        self.shake = lv.shake if hasattr(lv, "shake") else 0.0
        if lv.exit_open and lv.exit_rect.w and lv.exit_rect.colliderect(p.rect):
            self.finish_level()

    def _collisions(self, p, lv, interact):
        for g in lv.gems:
            if not g.taken and g.rect.colliderect(p.rect):
                g.taken = True; self.gems_collected += 1; self.audio.play("gem"); self.burst(g.rect.centerx, g.rect.centery, TEAL, 8, 120)
        for i, c in enumerate(lv.checkpoints):
            if not c.active and c.rect.colliderect(p.rect):
                self._activate_cps(i)
                self.save.set_checkpoint(self.level_id, i, lv.state())
                self.audio.play("checkpoint"); self.say("Checkpoint saved!", 2.5); self.burst(c.rect.centerx, c.rect.y, GREEN, 14, 160)
                self.safe = lv.checkpoint_pos(i)
        for e in lv.enemies:
            if not e.alive: continue
            hit = e.rect.colliderect(p.rect)
            if p.attacking and p.hitbox_attack().colliderect(e.rect):
                e.kill(); self.audio.play("stomp"); self.burst(e.rect.centerx, e.rect.centery, GREEN, 12, 180)
            elif hit:
                if p.vy > 120 and p.rect.bottom - e.rect.top < 20:
                    e.kill(); p.vy = -380; self.audio.play("stomp"); self.burst(e.rect.centerx, e.rect.centery, GREEN, 12, 180)
                else:
                    p.hurt(1, (-260 if p.rect.centerx < e.rect.centerx else 260, -300))
        near = next((t for t in lv.terminals if t.near(p.rect)), None)
        self.near_terminal = near
        if near and interact:
            if near.solved: self.say("This terminal is already solved.", 2.5)
            elif lv.terminals.index(near) != next(i for i, t in enumerate(lv.terminals) if not t.solved):
                self.say("Another terminal needs to be solved first.", 3)
            else:
                self.panel, self.panel_terminal = lv.panel_for(near, self.game), near
                self.panel.msg_t = 0
                self.audio.play("click")

    def finish_level(self):
        lv = self.level
        first = self.save.complete_level(self.level_id, self.gems_collected, lv.CONCEPTS)
        self.audio.play("victory")
        self.game.go(LevelCompleteScene(self.game, self.level_id, first, self.gems_collected, len(lv.gems), lv))

    # ---------------------------------------------------------------- drawing
    def draw(self, surf):
        lv, p = self.level, self.player
        cam = [int(self.cam[0]), int(self.cam[1])]
        if self.shake > 0:
            cam[0] += random.randint(-4, 4); cam[1] += random.randint(-3, 3)
        backdrop(surf, self.info["theme"], 0, cam[0])
        lv.draw_back(surf, cam)
        surf.blit(self.tile_layer, (-cam[0], -cam[1]))
        for b in lv.bridges: b.draw(surf, cam)
        for m in lv.movers: m.draw(surf, cam)
        for g in lv.gates: g.draw(surf, cam)
        for c in lv.checkpoints: c.draw(surf, cam)
        for t in lv.terminals: t.draw(surf, cam, self.t, t is getattr(self, "near_terminal", None))
        for g in lv.gems: g.draw(surf, cam, self.t)
        # exit portal
        if lv.exit_rect.w:
            r = lv.exit_rect.move(-cam[0], -cam[1])
            if lv.exit_open:
                surf.blit(A.glow(70, GOLD), (r.centerx - 70, r.centery - 70))
                for k in range(3):
                    pygame.draw.ellipse(surf, (255, 230, 150), r.inflate(-k * 10 + math.sin(self.t * 4 + k) * 4, -k * 8), 2)
            else:
                pygame.draw.ellipse(surf, (70, 78, 100), r, 3)
        for e in lv.enemies:
            if e.alive: e.draw(surf, cam)
        p.draw(surf, cam)
        surf.blit(A.dat_frames()[int(self.t * 6) % 4], (self.dat_pos[0] - 20 - cam[0], self.dat_pos[1] - 20 - cam[1]))
        for q in self.particles: q.draw(surf, cam)
        lv.draw_front(surf, cam)
        surf.blit(A.vignette(), (0, 0))
        self.draw_hud(surf, cam)
        if self.panel:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 120)); surf.blit(ov, (0, 0))
            self.panel.draw(surf)
        if self.dialog: self.draw_dialog(surf)
        if self.paused: self.draw_pause(surf)
        if self.over: self.draw_over(surf)

    def draw_hud(self, surf, cam):
        p, lv = self.player, self.level
        pygame.draw.rect(surf, (10, 16, 28, 200), (0, 0, WIDTH, 0))
        ui.hearts(surf, 14, 12, p.health)
        ui.draw_text(surf, f"Lives x{p.lives}", (14, 40), 14, CREAM, True)
        ui.draw_text(surf, f"Gems {self.gems_collected}/{len(lv.gems)}   XP {self.save.xp}", (14, 60), 14, TEAL, True)
        ui.draw_text(surf, f"L{self.level_id}: {self.info['name']}", (14, 82), 13, GOLD, True)
        ui.draw_text(surf, "H: hint", (14, 100), 12, (130, 145, 170))
        lv.draw_hud(surf)
        self.draw_objective(surf, cam)
        # terminal prompt
        nt = getattr(self, "near_terminal", None)
        if nt and not nt.solved and not self.panel:
            nxt = lv.next_terminal()
            txt = "Press E" if nt is nxt else "Locked: solve the previous one first"
            ui.speech(surf, txt, (nt.rect.centerx - cam[0], nt.rect.y - 8), 150 if nt is nxt else 260, 14, GOLD)
        if self.bark[1] > 0 and self.bark[0] and not self.dialog:
            ui.speech(surf, self.bark[0], (int(self.dat_pos[0] - cam[0]), int(self.dat_pos[1] - 26 - cam[1])), 330, 15, TEAL)

    def objective_target(self):
        lv = self.level
        if lv.exit_open and lv.exit_rect.w: return lv.exit_rect.center
        if self.level_id == 5 and lv.model is not None: return None
        t = lv.next_terminal()
        return t.rect.center if t else None

    def draw_objective(self, surf, cam):
        lv, p = self.level, self.player
        if self.panel or self.dialog or self.over or self.paused: return
        n, done = len(lv.terminals), sum(t.solved for t in lv.terminals)
        text = self.objective()
        if lv.exit_open: head = "FINAL STEP"
        elif self.level_id == 5 and lv.model is not None: head = "BOSS FIGHT"
        else: head = f"TERMINAL {min(done + 1, n)} OF {n}"
        tgt = self.objective_target()
        if tgt is not None:
            near = self.near_terminal if getattr(self, "near_terminal", None) and not lv.exit_open else None
            if near is not None and near is lv.next_terminal(): text = "Press  E  to open the terminal"
            elif lv.exit_open: text = "Walk into the golden portal"
            else: text = "Walk to the glowing terminal"
        w = 420; bx = 168
        box = pygame.Surface((w, 52), pygame.SRCALPHA)
        pygame.draw.rect(box, (10, 18, 32, 220), (0, 0, w, 52), border_radius=12); pygame.draw.rect(box, GOLD, (0, 0, w, 52), 2, border_radius=12)
        surf.blit(box, (bx, 8))
        ui.draw_text(surf, head, (bx + w // 2, 14), 12, TEAL, True, align="mid")
        ui.draw_text(surf, text, (bx + w // 2, 30), 18, CREAM, True, align="mid")
        if tgt is None: return
        sx, sy = tgt[0] - cam[0], tgt[1] - cam[1]
        bob = math.sin(self.t * 5) * 5
        if 30 < sx < WIDTH - 30 and 70 < sy < HEIGHT - 20:                    # on screen: bouncing marker above it
            if getattr(self, "near_terminal", None) is None or lv.exit_open:
                pygame.draw.polygon(surf, GOLD, [(sx - 12, sy - 56 + bob), (sx + 12, sy - 56 + bob), (sx, sy - 38 + bob)])
        else:                                                                  # off screen: arrow on the edge
            ax = min(max(sx, 36), WIDTH - 36); ay = min(max(sy, 96), HEIGHT - 36)
            dx, dy = sx - p.rect.centerx + cam[0], sy - p.rect.centery + cam[1]
            ang = math.atan2(sy - HEIGHT / 2, sx - WIDTH / 2)
            pts = [(ax + math.cos(ang) * 22, ay + math.sin(ang) * 22), (ax + math.cos(ang + 2.5) * 18, ay + math.sin(ang + 2.5) * 18), (ax + math.cos(ang - 2.5) * 18, ay + math.sin(ang - 2.5) * 18)]
            pygame.draw.polygon(surf, GOLD, pts); pygame.draw.polygon(surf, (10, 16, 28), pts, 2)
            dist = int(math.hypot(dx, dy) / 48)
            ui.draw_text(surf, f"{dist} m", (ax, ay + (22 if ay < HEIGHT / 2 else -30)), 12, GOLD, True, align="mid")
        if self.t < 14 and self.level_id == 1:                                   # controls strip for the first seconds
            ui.draw_text(surf, "A/D move   Space jump   E use terminal   H hint", (WIDTH // 2, HEIGHT - 22), 15, CREAM, True, align="mid")

    def draw_dialog(self, surf):
        txt = self.dialog[0]
        box = pygame.Surface((WIDTH - 120, 150), pygame.SRCALPHA)
        pygame.draw.rect(box, (12, 24, 40, 238), (0, 0, WIDTH - 120, 150), border_radius=12)
        pygame.draw.rect(box, TEAL, (0, 0, WIDTH - 120, 150), 2, border_radius=12)
        surf.blit(box, (60, HEIGHT - 170))
        surf.blit(pygame.transform.scale(A.dat_frames()[int(self.t * 3) % 4], (80, 80)), (78, HEIGHT - 150))
        ui.draw_text(surf, "DAT", (84, HEIGHT - 66), 15, GOLD, True)
        ui.draw_text(surf, txt[: int(self.dchars)], (180, HEIGHT - 152), 19, CREAM, width=WIDTH - 280, line_h=28)
        ui.draw_text(surf, "Enter / click: next    Esc: skip", (WIDTH - 80, HEIGHT - 40), 12, (130, 145, 170), align="left") if False else ui.draw_text(surf, "Enter / click: next   Esc: skip", (WIDTH - 340, HEIGHT - 44), 12, (130, 145, 170))

    def draw_pause(self, surf):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 170)); surf.blit(ov, (0, 0))
        title_text(surf, "PAUSED", 130, 40)
        mouse = pygame.mouse.get_pos()
        for i, lab in enumerate(self.PAUSE_ITEMS):
            ui.Button((WIDTH // 2 - 160, 190 + i * 48, 320, 40), lab, color=GOLD if i == self.pause_sel else TEAL, size=17).draw(surf, mouse, selected=i == self.pause_sel)

    def draw_over(self, surf):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((40, 0, 0, 190)); surf.blit(ov, (0, 0))
        title_text(surf, "OUT OF LIVES", 200, 46, RED)
        ui.draw_text(surf, "Don't worry: every mistake is training data.", (WIDTH // 2, 262), 20, CREAM, align="mid")
        ui.draw_text(surf, "Press Enter to retry from your last checkpoint", (WIDTH // 2, 310), 18, GOLD, True, align="mid")


# ======================================================================================= LEVEL COMPLETE
class LevelCompleteScene(Scene):
    def __init__(self, game, level_id, first, gems, total_gems, level):
        super().__init__(game)
        self.lid, self.first, self.gems, self.total = level_id, first, gems, total_gems
        self.info = LEVELS[level_id - 1]
        self.level = level

    def enter(self): self.audio.music(None)

    def handle(self, ev):
        if self.t > 0.8 and (ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e))):
            self.audio.play("click")
            if self.lid == len(LEVELS): self.game.go(VictoryScene(self.game))
            else: self.game.go(LevelSelectScene(self.game))

    def draw(self, surf):
        backdrop(surf, self.info["theme"], self.t, self.t * 15)
        title_text(surf, "LEVEL COMPLETE", 44, 40, GOLD)
        ui.draw_text(surf, f"Level {self.lid}: {self.info['name']}", (WIDTH // 2, 80), 20, CREAM, align="mid")
        surf.blit(A.holo_panel(880, 380, "", TEAL), (40, 112))
        xp = int(self.info["xp"] * min(1.0, self.t / 1.2)) if self.first else 0
        ui.draw_text(surf, f"+{xp} XP" if self.first else "Already completed: no new XP", (80, 130), 28, GOLD, True)
        ui.draw_text(surf, f"Gems {self.gems}/{self.total}   Mistakes {self.level.mistakes}", (80, 168), 16, TEAL, True)
        badge_icon(surf, (800, 200), BADGE_COLORS[self.lid - 1], 44)
        ui.draw_text(surf, f"Badge: {self.info['badge']}", (790, 258), 15, BADGE_COLORS[self.lid - 1], True, align="mid")
        ui.draw_text(surf, "Concepts mastered:  " + ", ".join(self.level.CONCEPTS), (80, 206), 15, CREAM, width=560)
        y = 262
        ui.draw_text(surf, "What you learned", (80, y - 24), 15, GOLD, True)
        for line in self.level.LEARNED:
            y = ui.draw_text(surf, "- " + line, (80, y), 15, CREAM, width=700) + 4
        for line in (self.level.summary() if hasattr(self.level, "summary") else []):
            y = ui.draw_text(surf, line, (80, y + 6), 15, TEAL, True, width=700) + 4
        if self.t > 0.8:
            ui.draw_text(surf, "Press Enter to continue", (WIDTH // 2, 508), 18, GOLD, True, align="mid")


# ======================================================================================= INVENTORY
class InventoryScene(Scene):
    def __init__(self, game, back):
        super().__init__(game)
        self.back = back

    def enter(self): ...

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_i, pygame.K_SPACE)):
            if isinstance(self.back, GameplayScene): self.game.scene = self.back   # return to the paused game without rebuilding
            else: self.game.go(self.back)

    def draw(self, surf):
        backdrop(surf, "crystal", self.t, self.t * 10)
        title_text(surf, "ACHIEVEMENTS", 44, 36)
        for i, lv in enumerate(LEVELS):
            x = 90 + i * 170
            earned = lv["badge"] in self.save.badges
            surf.blit(A.holo_panel(150, 180, "", BADGE_COLORS[i] if earned else (70, 78, 95)), (x - 55, 90))
            badge_icon(surf, (x + 20, 150), BADGE_COLORS[i], 36, locked=not earned)
            ui.draw_text(surf, lv["badge"] if earned else "Locked", (x + 20, 200), 14, CREAM if earned else (110, 118, 135), True, align="mid")
            ui.draw_text(surf, f"Level {lv['id']}", (x + 20, 224), 12, (150, 165, 190), align="mid")
        surf.blit(A.holo_panel(880, 190, "Concepts learned", TEAL), (40, 290))
        ui.draw_text(surf, ", ".join(self.save.concepts) if self.save.concepts else "Complete levels to learn data science concepts.", (60, 326), 16, CREAM, width=840)
        ui.draw_text(surf, f"Total XP {self.save.xp}/{TOTAL_XP}    Gems {self.save.total_gems}    Falls and defeats {self.save.deaths}", (WIDTH // 2, 490), 17, GOLD, True, align="mid")
        ui.draw_text(surf, "Esc / Enter: back", (WIDTH // 2, 518), 13, (150, 165, 190), align="mid")


# ======================================================================================= VICTORY
class VictoryScene(Scene):
    def enter(self):
        self.audio.music("victory")
        self.confetti = [Particle(random.randint(0, WIDTH), random.randint(-HEIGHT, 0), random.uniform(-20, 20), random.uniform(60, 160), 99, random.choice((GOLD, TEAL, PURPLE, GREEN, RED, CREAM)), 3, 0) for _ in range(120)]

    def handle(self, ev):
        if self.t > 1.5 and (ev.type == pygame.MOUSEBUTTONDOWN or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE))):
            self.game.go(MenuScene(self.game))

    def update(self, dt):
        super().update(dt)
        for c in self.confetti:
            c.update(dt)
            if c.y > HEIGHT: c.y, c.x = -10, random.randint(0, WIDTH)

    def draw(self, surf):
        backdrop(surf, "arena", self.t, self.t * 12)
        for c in self.confetti: c.draw(surf, (0, 0))
        title_text(surf, "VICTORY!", 52, 52, GOLD)
        title_text(surf, "MASTER CLASSIFIER", 108, 34, TEAL)
        surf.blit(A.holo_panel(860, 150, "", TEAL), (50, 140))
        surf.blit(pygame.transform.scale(A.dat_frames()[int(self.t * 3) % 4], (80, 80)), (66, 160))
        msg = ("You did it, Alex! You learned to ask good questions, to measure how pure a split is, to avoid overfitting, and to test a model on data it has never seen. "
               "You are no longer just exploring the maze. You can classify the unknown. I am proud to be your DAT!")
        ui.draw_text(surf, msg, (166, 152), 17, CREAM, width=720, line_h=25)
        ui.draw_text(surf, f"Total XP  {self.save.xp} / {TOTAL_XP}", (WIDTH // 2, 308), 26, GOLD, True, align="mid")
        for i, lv in enumerate(LEVELS):
            x = 130 + i * 175
            badge_icon(surf, (x, 372), BADGE_COLORS[i], 30, locked=lv["badge"] not in self.save.badges)
            ui.draw_text(surf, lv["badge"], (x, 410), 13, CREAM, True, align="mid")
        ui.draw_text(surf, "Concepts: " + ", ".join(self.save.concepts), (60, 440), 13, (170, 185, 210), width=840)
        if self.t > 1.5: ui.draw_text(surf, "Press Enter to return to the menu", (WIDTH // 2, 512), 16, GOLD, True, align="mid")
