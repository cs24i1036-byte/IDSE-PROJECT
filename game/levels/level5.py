"""LEVEL 5 - The Guardian's Trial: build, train and evaluate a classifier, then use it against the Guardian."""
from __future__ import annotations

import math
import random

import pygame

from ds import dataset as D
from ds import tree_model as T
from game import assets as A
from game import ui
from game.entities import Bat, Mover, Projectile, Slime
from game.level import Level
from game.levels.common import *  # noqa
from game.panels import TrainPanel
from game.settings import *  # noqa
from game.world import Builder

MIN_ACC = 0.80
ARENA_X0, ARENA_X1 = 52, 84
BOSS_HP = 9
WINDOW_TIME = 16.0
PX, PY = 330, 52                      # compact classification window (top centre: the Guardian and the action stay visible)


class Level5(Level):
    ID, NAME, THEME = 5, "The Guardian's Trial", "arena"
    CONCEPTS = ["Feature selection", "Training data", "Testing data", "Accuracy", "Confusion matrix"]
    LEARNED = ["Choose features that carry real signal; irrelevant clues add noise, not accuracy.",
               "TRAIN on one set of records, TEST on records the model has never seen.",
               "ACCURACY = correct predictions / all predictions. The CONFUSION MATRIX shows which mistakes were made."]

    def build(self):
        self.train, self.test = D.load_guardian()
        self.features = D.LARGE_FEATURES
        self.rng = random.Random(self.seed * 7919 + 5)
        order = list(range(len(self.test))); self.rng.shuffle(order)
        self.queue = order
        b = Builder(90)
        b.ground(0, 13, GROUND); b.ground(18, 27, GROUND); b.ground(34, 89, GROUND)
        b.block(0, 0, 1, GROUND)
        b.block(ARENA_X1, 0, 6, GROUND)
        self.spawn = (3 * TILE, FLOOR_Y)
        b.platform(7, 11, 3); gem_arc(self, 7, 11, 3)
        b.platform(15, 11, 2); gem_arc(self, 14, 10, 4, 6)
        add_cp(self, 2)
        self.movers.append(Mover(28 * TILE, 13 * TILE, 2, dx=3, speed=70, theme="arena"))
        gem_arc(self, 29, 11, 4, 6)
        self.enemies.append(Slime(22 * TILE, FLOOR_Y, 19 * TILE, 26 * TILE))
        self.enemies.append(Bat(30 * TILE, 8 * TILE, 70, 20))
        add_cp(self, 36)
        b.spikes(40, 3, GROUND - 1); b.platform(40, 11, 3)
        gem_arc(self, 39, 10, 4, 6)
        self.enemies.append(Slime(45 * TILE, FLOOR_Y, 43 * TILE, 48 * TILE))
        add_terminal(self, 47, "train", "TRAINING CONSOLE")
        self.gate = door_wall(self, b, 50, color=RED)
        add_cp(self, 55)
        # arena furniture
        b.platform(56, 11, 4); b.platform(61, 9, 4); b.platform(66, 11, 4); b.platform(71, 9, 4); b.platform(76, 11, 3)
        gem_arc(self, 57, 11, 3); gem_arc(self, 62, 9, 3); gem_arc(self, 67, 11, 3); gem_arc(self, 72, 9, 3)
        self.grid = b.build()
        self.exit_rect = pygame.Rect(0, 0, 0, 0)
        self.boss_rect = pygame.Rect(0, 0, 112, 140); self.boss_rect.midbottom = ((ARENA_X1 - 4) * TILE, GROUND * TILE)
        self.model = None; self.model_features: list[str] = []; self.depth = 3; self.model_eval = None
        self.arena_active = False
        self.boss_hp = BOSS_HP
        self.qi = 0; self.asked = 0; self.right = 0
        self.q = None; self.q_timer = 0.0; self.q_wait = 5.0; self.feedback = ""; self.fb_t = 0.0; self.fb_color = CREAM
        self.atk_t = 3.0; self.hit_flash = 0.0; self.defeated = False; self.shake = 0.0
        self.btns = [ui.Button((PX + 10, PY + 184, 134, 30), "1  SAFE", color=GREEN, size=14), ui.Button((PX + 156, PY + 184, 134, 30), "2  DANGEROUS", color=RED, size=13)]
        self.intro = ["The Guardian's Trial. Beyond that door waits the Guardian, keeper of the Invisible Maze.",
                      "Everything you learned comes together. Choose good FEATURES, TRAIN a tree on the training records, then TEST it on records it has never seen.",
                      "The Guardian only takes damage when a creature is classified correctly. Your tree will advise you, but it's only as good as its accuracy."]
        self.hints = {"t0": ["Use the training console. Pick features, train, then test on unseen data.", "Features that carry real signal beat piles of noisy ones. Check the unseen accuracy, not just training.",
                             "Aim for at least 80% accuracy on the unseen test set before equipping the model."],
                      "exit": ["Face the Guardian. Classify each creature in the window: press 1 for Safe, 2 for Dangerous. Dodge the orbs!", "Strike orbs with F to destroy them."],
                      "default": ["Face the Guardian. Classify each creature in the window: press 1 for Safe, 2 for Dangerous. Dodge the orbs!"]}

    # ---------------------------------------------------------------- panel / model
    def panel_for(self, terminal, game):
        def on_confirm(model, feats, ev, depth):
            if ev["accuracy"] >= MIN_ACC:
                return True, f"Model equipped: {ev['accuracy'] * 100:.1f}% accurate on unseen creatures. The door unlocks!"
            return False, f"Only {ev['accuracy'] * 100:.1f}% on unseen data. The Guardian would crush this. Choose better features or adjust the depth."
        return TrainPanel(game.ctx, self.train, self.test, self.features, D.TARGET, MIN_ACC, on_confirm)

    def on_solved(self, i, instant):
        res = self.answers[i]
        feats = res["features"] if isinstance(res, dict) else list(self.features)
        self.depth = res["depth"] if isinstance(res, dict) else 3
        X, y = T.prepare(self.train, feats)
        self.model = T.train_tree(X, y, max_depth=self.depth)
        self.model_features = list(feats)
        Xt, yt = T.prepare(self.test, feats)
        from ds.evaluation import evaluate
        self.model_eval = evaluate(self.model, Xt, yt)
        self.gate.set_open(True, instant)
        if not instant:
            self.sfx("door")
            self.say("The door grinds open. Remember: the Guardian only flinches when a classification is right!")

    def predict(self, row) -> str:
        x = T.prepare(row.to_frame().T.reset_index(drop=True), self.model_features)[0] if False else None
        import pandas as pd
        frame = pd.DataFrame([row])
        pred = self.model.predict(T.prepare(frame, self.model_features)[0])[0]
        return "Dangerous" if pred == 1 else "Safe"

    # ---------------------------------------------------------------- camera
    def camera_bounds(self, player):
        if self.arena_active:
            return ARENA_X0 * TILE, ARENA_X1 * TILE - WIDTH
        return 0, (ARENA_X0 + 2) * TILE - WIDTH if player.rect.centerx < (ARENA_X0 + 1) * TILE else 0

    # ---------------------------------------------------------------- boss logic
    @property
    def stage(self): return min(3, 1 + (BOSS_HP - self.boss_hp) // 3)

    def open_window(self):
        idx = self.queue[self.qi % len(self.queue)]
        self.qi += 1
        row = self.test.iloc[idx]
        self.q = {"row": row, "pred": self.predict(row) if self.model is not None else "?"}
        self.q_timer = WINDOW_TIME
        self.sfx("hint")

    def answer(self, label: str, player):
        row = self.q["row"]
        truth = "Dangerous" if row[D.TARGET] == "Yes" else "Safe"
        self.asked += 1
        self.q = None
        self.q_wait = 3.0
        if label == truth:
            self.right += 1
            self.boss_hp -= 1; self.hit_flash = 0.5; self.shake = 0.35
            self.feedback, self.fb_color, self.fb_t = f"CORRECT! The {row['Creature']} is {truth}. The Guardian staggers!", GREEN, 3.0
            self.sfx("boss_hit")
            self.projectiles.clear()
            if self.boss_hp <= 0:
                self.defeated = True
                self.exit_open = True
                self.exit_rect = pygame.Rect((ARENA_X1 - 7) * TILE, 11 * TILE, 2 * TILE, 3 * TILE)
                self.say("The Guardian crumbles! You classified your way through the maze. Step into the portal!")
        else:
            self.feedback, self.fb_color, self.fb_t = f"WRONG. The {row['Creature']} is actually {truth}.", RED, 3.5
            self.sfx("wrong")
            player.hurt(1, (-player.facing * 160, -300))
            self.mistakes += 1

    def update_extra(self, dt, player, say, audio):
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.shake = max(0.0, self.shake - dt)
        self.fb_t = max(0.0, self.fb_t - dt)
        if self.model is None or self.defeated:
            self.arena_active = self.arena_active and not self.defeated
            self._smash_projectiles(player)
            return
        if not self.arena_active and player.rect.centerx > (ARENA_X0 + 3) * TILE and self.gate.open:
            self.arena_active = True
            self.sfx("boss_roar")
            say("The Guardian awakens! Classify each creature in the window: 1 = Safe, 2 = Dangerous. Dodge the orbs!")
        if not self.arena_active:
            return
        if self.q is None:
            self.q_wait -= dt
            if self.q_wait <= 0 and not player.locked:
                self.open_window()
        else:
            self.q_timer -= dt
            if self.q_timer <= 0:
                self.q = None; self.q_wait = 3.0; self.asked += 1; self.mistakes += 1
                self.feedback, self.fb_color, self.fb_t = "Too slow! The Guardian strikes back.", RED, 3.0
                player.hurt(1, (-player.facing * 160, -300)); self.sfx("wrong")
        # attacks
        self.atk_t -= dt
        if self.atk_t <= 0:
            self.atk_t = (2.6, 2.0, 1.5)[self.stage - 1]
            cx, cy = self.boss_rect.centerx, self.boss_rect.y + 50
            dx, dy = player.rect.centerx - cx, player.rect.centery - cy
            n = math.hypot(dx, dy) or 1
            self.projectiles.append(Projectile(cx - 30, cy, dx / n * 250, dy / n * 250))
            self.sfx("shoot")
            kind = self.rng.random()
            if self.stage >= 2 and kind < 0.5:
                self.projectiles.append(Projectile(cx - 40, GROUND * TILE - 14, -210, 0, RED, 6))
            if self.stage >= 3:
                for _ in range(2):
                    self.projectiles.append(Projectile(self.rng.randint(ARENA_X0 + 2, ARENA_X1 - 10) * TILE, 10, 0, 230, TEAL, 5))
        for p in self.projectiles:
            if p.rect.colliderect(player.rect) and p.alive:
                p.alive = False
                player.hurt(1, ((1 if p.vx < 0 else -1) * 150, -280))
        self._smash_projectiles(player)
        if self.boss_rect.inflate(-34, -20).colliderect(player.rect):
            player.hurt(1, (-260, -300))

    def _smash_projectiles(self, player):
        if player.attacking:
            hb = player.hitbox_attack()
            for p in self.projectiles:
                if hb.colliderect(p.rect):
                    p.alive = False; self.sfx("stomp")

    def handle_event(self, ev) -> bool:
        if self.q is None:
            return False
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_1, pygame.K_KP1):
            self.answer("Safe", self.player); return True
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_2, pygame.K_KP2):
            self.answer("Dangerous", self.player); return True
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b, lab in zip(self.btns, ("Safe", "Dangerous")):
                if b.rect.collidepoint(ev.pos):
                    self.answer(lab, self.player); return True
        return False

    # ---------------------------------------------------------------- state
    def extra_state(self):
        return {"hp": self.boss_hp, "qi": self.qi, "asked": self.asked, "right": self.right}

    def restore_extra(self, st):
        self.boss_hp = st.get("hp", BOSS_HP); self.qi = st.get("qi", 0); self.asked = st.get("asked", 0); self.right = st.get("right", 0)
        if self.boss_hp <= 0:
            self.defeated = True

    def summary(self) -> list[str]:
        out = []
        if self.model_eval:
            out.append(f"Your model: {self.model_eval['accuracy'] * 100:.1f}% accurate on {self.model_eval['total']} unseen creatures (features: {', '.join(f.replace('_', ' ') for f in self.model_features)}).")
        if self.asked:
            out.append(f"Against the Guardian you classified {self.right} of {self.asked} creatures correctly.")
        return out

    # ---------------------------------------------------------------- drawing
    def draw_front(self, surf, cam):
        if self.model is None and not self.arena_active:
            pass
        r = self.boss_rect
        if self.defeated:
            return
        img = A.guardian_frame(int(self.time * 10), self.hit_flash > 0)
        bob = int(math.sin(self.time * 2) * 4)
        surf.blit(img, (r.centerx - 64 - cam[0], r.bottom - 144 - cam[1] + bob))
        for p in self.projectiles:
            p.draw(surf, cam)

    def draw_hud(self, surf):
        if self.arena_active and not self.defeated:
            w = 360
            x = (WIDTH - w) // 2
            ui.draw_text(surf, "THE GUARDIAN", (WIDTH // 2, 8), 15, GOLD, True, align="mid")
            for i in range(BOSS_HP):
                col = PURPLE if i < self.boss_hp else (50, 40, 70)
                pygame.draw.rect(surf, col, (x + i * (w // BOSS_HP), 30, w // BOSS_HP - 4, 12), border_radius=3)
                pygame.draw.rect(surf, CREAM, (x + i * (w // BOSS_HP), 30, w // BOSS_HP - 4, 12), 1, border_radius=3)
        if self.fb_t > 0 and self.feedback:
            ui.draw_text(surf, self.feedback, (WIDTH // 2, 54), 18, self.fb_color, True, align="mid")
        if self.q is not None:
            row = self.q["row"]
            panel = A.holo_panel(300, 224, "", GOLD)
            surf.blit(panel, (PX, PY))
            ox, oy = PX, PY
            ui.draw_text(surf, "CLASSIFY: " + str(row["Creature"]), (ox + 150, oy + 8), 15, GOLD, True, align="mid")
            for k, f in enumerate(self.features):
                col, rowi = divmod(k, 4)
                x, y = ox + 12 + col * 146, oy + 36 + rowi * 25
                ui.draw_text(surf, f.replace("_", " ").replace("Has ", ""), (x, y + 2), 12, (180, 190, 210))
                v = row[f]
                if f in D.MYSTIC_FEATURES:
                    ui.chip(surf, pygame.Rect(x + 84, y, 44, 19), v, v == "Yes", GREEN if v == "Yes" else (120, 130, 155), 12)
                else:
                    ui.draw_text(surf, f"{v}", (x + 84, y + 1), 14, GOLD, True)
            ui.draw_text(surf, f"Your tree predicts: {self.q['pred']}", (ox + 12, oy + 142), 14, TEAL, True)
            ui.bar(surf, pygame.Rect(ox + 12, oy + 166, 276, 7), self.q_timer / WINDOW_TIME, GOLD)
            mouse = pygame.mouse.get_pos()
            for b in self.btns: b.draw(surf, mouse)
        if self.hit_flash > 0:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); fl.fill((255, 255, 255, int(120 * self.hit_flash)))
            surf.blit(fl, (0, 0))
