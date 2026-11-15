"""LEVEL 2 - The Creature Chamber: features, target, classification."""
from __future__ import annotations

import pygame

from ds import dataset as D
from game import assets as A
from game.entities import Bat, Mover, Slime
from game.level import Level
from game.levels.common import *  # noqa
from game.panels import ChoicePanel, FeaturesPanel, RolesPanel
from game.settings import *  # noqa
from game.world import Builder


class Level2(Level):
    ID, NAME, THEME = 2, "The Creature Chamber", "lab"
    CONCEPTS = ["Features", "Target variable", "Classification", "Labelled data"]
    LEARNED = ["FEATURES are the clues a model looks at; the TARGET is what it must predict.",
               "Classification means choosing a category (here: Safe or Dangerous) for each new record.",
               "Not every feature is useful. The useful ones change the outcome a lot between their Yes and No groups."]

    def build(self):
        self.df = D.load_mystic()
        self.train, self.test = D.mystic_split(self.df)
        b = Builder(130)
        b.ground(0, 129, GROUND)
        b.block(0, 0, 1, GROUND)
        self.spawn = (3 * TILE, FLOOR_Y)
        b.platform(9, 11, 3); b.platform(14, 12, 3)
        gem_arc(self, 9, 11, 3); gem_arc(self, 14, 12, 3)
        add_cp(self, 2)
        self.triggers.append((pygame.Rect(5 * TILE, 8 * TILE, 3 * TILE, 6 * TILE), "These tubes hold creatures from the dataset. Each one is a RECORD: a row of clues.", False))
        add_terminal(self, 22, "roles", "DATA CONSOLE")
        door_wall(self, b, 30, color=TEAL)
        # section 2
        add_cp(self, 34)
        b.clear(40, GROUND, 4, 3); b.platform(41, 11, 2)
        b.platform(47, 11, 3); b.platform(52, 9, 3)
        gem_arc(self, 40, 10, 4, 6); gem_arc(self, 47, 11, 3); gem_arc(self, 52, 9, 3)
        self.enemies.append(Slime(48 * TILE, FLOOR_Y, 45 * TILE, 52 * TILE))
        self.enemies.append(Bat(44 * TILE, 8 * TILE, 70, 20))
        add_terminal(self, 58, "features", "FEATURE LAB")
        door_wall(self, b, 64, color=TEAL)
        # section 3: moving platforms
        add_cp(self, 68)
        b.clear(72, GROUND, 10, 3)
        self.movers.append(Mover(72 * TILE, 13 * TILE, 2, dx=3, speed=70, theme="lab"))
        b.platform(78, 12, 2)
        gem_arc(self, 73, 11, 5, 6)
        self.enemies.append(Bat(76 * TILE, 8 * TILE, 90, 20, 1.0))
        b.platform(86, 11, 3); b.platform(91, 9, 3)
        gem_arc(self, 86, 11, 3); gem_arc(self, 91, 9, 3)
        self.enemies.append(Slime(88 * TILE, FLOOR_Y, 84 * TILE, 93 * TILE))
        add_cp(self, 94)
        add_terminal(self, 98, "classify", "CLASSIFIER")
        door_wall(self, b, 106, color=TEAL)
        self.enemies.append(Slime(114 * TILE, FLOOR_Y, 110 * TILE, 120 * TILE))
        self.exit_rect = pygame.Rect(122 * TILE, 11 * TILE, 2 * TILE, 3 * TILE)
        self.grid = b.build()
        self.gate_for = {0: 0, 1: 1, 2: 2}
        self.cages = [(7, "Eagle"), (19, "Wolf"), (36, "Snake"), (55, "Spider"), (70, "Dragon"), (101, "Owl"), (112, "Tiger")]
        self.intro = ["Welcome to the Creature Chamber! This lab stores records of mystic creatures. Some are dangerous, some are harmless.",
                      "Our goal is CLASSIFICATION: look at a creature's clues and decide which category it belongs to.",
                      "Each column in the dataset has a role. Let's inspect the data console ahead."]
        self.hints = {"t0": ["Find the DATA CONSOLE and press E.", "Features are the input clues. The target is the answer we want to predict. A name is only an ID."],
                      "t1": ["Compare the Yes bar with the No bar for each feature.", "A useful feature changes the danger rate a lot. A feature with similar bars tells the model almost nothing."],
                      "t2": ["Use the clues you've learned matter to classify each unseen creature.", "Venomous or aggressive creatures turned out to be dangerous in the data."],
                      "exit": ["The portal is open. Go through!"]}

    def panel_for(self, terminal, game):
        i = self.terminals.index(terminal)
        if i == 0:
            return RolesPanel(game.ctx, self.df, "Creature", D.TARGET)
        if i == 1:
            return FeaturesPanel(game.ctx, self.df, D.MYSTIC_FEATURES, D.TARGET)
        steps = []
        for _, row in self.test.iterrows():
            truth = "Dangerous" if row[D.TARGET] == "Yes" else "Safe"
            def check(ans, truth=truth, name=row["Creature"]):
                return (True, f"Correct: the {name} is {truth.upper()}.") if ans == truth else (False, "Look at the clues again. Which features separated danger from safety?")
            steps.append(dict(prompt=f"Never seen before! Classify the {row['Creature']}.", options=["Safe", "Dangerous"], check=check,
                              card={"name": row["Creature"], "rows": [(f, row[f]) for f in D.MYSTIC_FEATURES], "subtitle": "Unseen record"},
                              note="Use what you learned about which features matter."))
        return ChoicePanel(game.ctx, "CLASSIFIER  -  predict new creatures", steps)

    def on_solved(self, i, instant):
        self.gates[i].set_open(True, instant)
        if not instant:
            self.sfx("door")
            self.say(["Roles confirmed! Features are inputs, the target is what we predict.", "Venom and aggression are the clues that matter. Wings tell us almost nothing!",
                      "You just classified creatures the model never saw. That is what classifiers are for."][i])
        if all(t.solved for t in self.terminals):
            self.exit_open = True

    def draw_back(self, surf, cam):
        for x, name in self.cages:
            r = pygame.Rect(x * TILE - cam[0], GROUND * TILE - 150, 56, 150)
            if r.right < 0 or r.left > WIDTH: continue
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (90, 220, 220, 40), (0, 0, r.w, r.h), border_radius=18)
            pygame.draw.rect(s, (120, 240, 230, 150), (0, 0, r.w, r.h), 2, border_radius=18)
            pygame.draw.ellipse(s, (180, 120, 230, 150), (14, 78, 28, 40))
            pygame.draw.circle(s, (230, 220, 250, 200), (22, 92), 3); pygame.draw.circle(s, (230, 220, 250, 200), (34, 92), 3)
            surf.blit(s, r.topleft)
            t = A.text(name, 12, (140, 230, 220)); surf.blit(t, t.get_rect(midtop=(r.centerx, r.bottom + 2)))
