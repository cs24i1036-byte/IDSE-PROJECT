"""LEVEL 1 - The First Junction: tree structure (root, branch, leaf) as Yes/No doors."""
from __future__ import annotations

import pygame

from ds import dataset as D
from game import ui
from game.entities import Bat, Mover, Slime
from game.level import Level
from game.levels.common import *  # noqa
from game.panels import ChoicePanel
from game.settings import *  # noqa
from game.world import Builder

# The authored example tree (questions are design choices; every route and label is verified against the CSV in tests).
TREE = {"id": "root", "feature": "Has_wings", "label": "Has wings?",
        "yes": {"id": "n_w", "feature": "Aggressive", "label": "Aggressive?", "yes": {"id": "l1", "leaf": "Dangerous"}, "no": {"id": "l2", "leaf": "Safe"}},
        "no": {"id": "n_nw", "feature": "Has_venom", "label": "Has venom?", "yes": {"id": "l3", "leaf": "Dangerous"}, "no": {"id": "l4", "leaf": "Safe"}}}
ROUNDS = ["Dragon", "Snake", "Rabbit"]
BASES = [24, 60, 96]


class Level1(Level):
    ID, NAME, THEME = 1, "The First Junction", "dungeon"
    CONCEPTS = ["Root node", "Branch", "Leaf node", "Decision path"]
    LEARNED = ["A decision tree is a flowchart of Yes/No questions.",
               "The ROOT is the first question; BRANCHES follow each answer; a LEAF gives the final classification.",
               "Every creature follows exactly one path from root to leaf."]

    def build(self):
        self.df = D.load_mystic().set_index("Creature")
        b = Builder(140)
        b.ground(0, 139, GROUND)
        b.block(0, 0, 1, GROUND)                           # left wall
        self.spawn = (3 * TILE, FLOOR_Y)
        self.junction: list[tuple] = []
        # --- intro corridor
        b.platform(10, 11, 3); b.clear(17, GROUND, 3, 3)
        b.platform(16, 12, 2)
        gem_arc(self, 8, 11, 3); gem_arc(self, 16, 12, 3, 4)
        add_cp(self, 2)
        self.triggers.append((pygame.Rect(5 * TILE, 8 * TILE, 3 * TILE, 6 * TILE), "Move with A/D or the arrow keys. SPACE jumps - hold it for a higher jump. SHIFT dashes.", False))
        self.triggers.append((pygame.Rect(21 * TILE, 8 * TILE, 3 * TILE, 6 * TILE), "That glowing console is a terminal. Stand close and press E.", False))
        for r, base in enumerate(BASES):
            ta = add_terminal(self, base + 1, "junction", "ROOT QUESTION")
            wa = base + 10
            self._junction(b, wa, (r * 2) % 2 == 0)
            tb = add_terminal(self, base + 19, "junction", "BRANCH QUESTION")
            wb = base + 30
            self._junction(b, wb, False)
            add_cp(self, base - 3) if r else None
            # obstacle between the two junctions
            if r == 0:
                b.clear(base + 13, GROUND, 4, 3); b.platform(base + 14, 11, 2)
                gem_arc(self, base + 13, 10, 4, 0)
            elif r == 1:
                b.clear(base + 12, GROUND, 6, 3)
                self.movers.append(Mover((base + 12) * TILE, 13 * TILE, 2, dx=3, speed=70, theme="dungeon"))
                gem_arc(self, base + 13, 11, 4, 4)
            else:
                b.spikes(base + 13, 4, GROUND - 1)
                b.platform(base + 14, 11, 2)
                gem_arc(self, base + 13, 10, 4, 0)
            if r == 0:
                self.enemies.append(Slime((base + 38) * TILE, FLOOR_Y, (base + 36) * TILE, (base + 40) * TILE))
            else:
                self.enemies.append(Slime((base + 6) * TILE, FLOOR_Y, (base + 3) * TILE, (base + 9) * TILE)) if False else None
            self.enemies.append(Bat((base + 34) * TILE, 11 * TILE, 60, 14))
            self.enemies.append(Slime((base + 26) * TILE, FLOOR_Y, (base + 24) * TILE, (base + 28) * TILE)) if False else None
        add_cp(self, 62 + 34 + 2) if False else None
        add_cp(self, 100 + 33)
        gem_line(self, 130, GROUND, 3)
        self.exit_rect = pygame.Rect(134 * TILE, 11 * TILE, 2 * TILE, 3 * TILE)
        self.grid = b.build()
        self.intro = ["Alex! Systems online. I'm DAT, your Data Analysis Tutor. Welcome to the Invisible Maze.",
                      "Every door here is guarded by a question. A DECISION TREE is a flowchart of such questions.",
                      "You start at the ROOT, answer a question, follow a BRANCH, and keep going until you reach a LEAF: the final answer.",
                      "Find the glowing terminals and press E. Each shows a creature record. Read it carefully, then choose the right door!"]
        self.hints = {f"t{i}": [] for i in range(6)}
        for i in range(6):
            self.hints[f"t{i}"] = ["Head right and look for the next glowing terminal.", "Press E near the terminal, then read the creature's card before answering."] if i % 2 == 0 else \
                ["Terminal ahead. It asks a second question, then you must classify the creature.", "The leaf is the final label: Safe or Dangerous."]
        self.hints["exit"] = ["The portal at the far right is open. Go through!"]

    # ---------------------------------------------------------------- geometry
    def _junction(self, b, W, _):
        """Wall with a lower YES door and an upper NO door, reached via stepping platforms."""
        b.block(W, 0, 2, 5); b.block(W, 8, 2, 3)
        b.platform(W - 8, 12, 2); b.platform(W - 6, 10, 2)
        b.block(W - 4, 8, 4, 1); b.block(W + 2, 8, 4, 1)
        yes = Gate(W * TILE, 11 * TILE, 2 * TILE, 3 * TILE, GREEN, label="YES")
        no = Gate(W * TILE, 5 * TILE, 2 * TILE, 3 * TILE, RED, label="NO")
        self.gates += [yes, no]
        self.junction.append((yes, no))
        gem_line(self, W - 4, 8, 3)

    # ---------------------------------------------------------------- data-driven logic
    def record(self, r): return self.df.loc[ROUNDS[r]].to_dict() | {"name": ROUNDS[r]}

    def route(self, r):
        return ui.classify_tree(TREE, self.record(r))

    def card(self, r):
        rec = self.record(r)
        return {"name": rec["name"], "rows": [(f, rec[f]) for f in D.MYSTIC_FEATURES], "subtitle": "Creature record"}

    def visited_ids(self, r):
        label, ids = self.route(r)
        n = 0
        if self.terminals[2 * r].solved: n = 2
        if self.terminals[2 * r + 1].solved: n = 3
        return ids[:n]

    def panel_for(self, terminal, game):
        i = self.terminals.index(terminal)
        r, second = divmod(i, 2)
        rec = self.record(r)
        label, ids = self.route(r)
        node = TREE if not second else (TREE["yes"] if rec["Has_wings"] == "Yes" else TREE["no"])
        def ask(n, visited):
            def check(ans):
                truth = "Yes" if rec[n["feature"]] == "Yes" else "No"
                if ans == truth:
                    return True, f"Correct. {n['feature'].replace('_', ' ')} is {truth} for the {rec['name']}, so follow the {truth.upper()} branch."
                return False, f"Not this time. Re-read the card: what does it say for '{n['feature'].replace('_', ' ')}'?"
            return dict(prompt=f"Question at this node: {n['label']}", options=["Yes", "No"], check=check, card=self.card(r), tree=TREE, visited=visited, current=n["id"])
        steps = [ask(node, ids[:i + 1 - 0] if False else (ids[:1] if second == 0 else ids[:2]))]
        if second:
            truth = "Dangerous" if rec["Dangerous"] == "Yes" else "Safe"
            def check_leaf(ans):
                if ans == truth:
                    return True, f"Leaf reached: the {rec['name']} is classified as {truth.upper()}."
                return False, "Follow the path you just walked: which leaf did it end in?"
            steps.append(dict(prompt="You reached a LEAF. What is the final classification?", options=["Safe", "Dangerous"], check=check_leaf, card=self.card(r), tree=TREE, visited=ids, current=ids[-1]))
        return ChoicePanel(game.ctx, "JUNCTION  -  " + ("root question" if not second else "branch question + leaf"), steps)

    def on_solved(self, i, instant):
        ans = self.answers[i]
        first = ans[0] if isinstance(ans, (list, tuple)) else ans
        j = i                                                           # junction index == terminal index
        yes, no = self.junction[j]
        (yes if first == "Yes" else no).set_open(True, instant)
        if not instant:
            self.sfx("door")
            if i % 2 == 1:
                r = i // 2
                self.say(f"The {ROUNDS[r]} is {self.route(r)[0].upper()}. That's one full path from root to leaf!")
            else:
                self.say("The door is open! Take it - " + ("the lower YES door." if first == "Yes" else "the upper NO door, climb the steps."))
        if all(t.solved for t in self.terminals):
            self.exit_open = True

    def draw_hud(self, surf):
        nxt = self.next_terminal()
        r = (self.terminals.index(nxt) // 2) if nxt else len(ROUNDS) - 1
        panel = pygame.Surface((300, 150), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 26, 42, 200), (0, 0, 300, 150), border_radius=8)
        pygame.draw.rect(panel, TEAL, (0, 0, 300, 150), 1, border_radius=8)
        panel.blit(A_text(f"Tracking: {ROUNDS[r]}"), (10, 4))
        ui.draw_tree(panel, pygame.Rect(8, 26, 284, 118), TREE, self.visited_ids(r), None, 0, 11)
        surf.blit(panel, (WIDTH - 310, 8))


def A_text(s):
    from game import assets as A
    return A.text(s, 13, GOLD, True)
