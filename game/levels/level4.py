"""LEVEL 4 - The Overgrown Tree: overfitting, tree depth, generalisation and pruning."""
from __future__ import annotations

import pygame

from ds import dataset as D
from ds import tree_model as T
from game.entities import Bat, Mover, Slime
from game.level import Level
from game.levels.common import *  # noqa
from game.panels import ChoicePanel, DepthPanel, PrunePanel
from game.settings import *  # noqa
from game.world import Builder

_DATA = {}
DEPTHS = (1, 2, 3, 4, 6, 8, None)


def data():
    if "d" not in _DATA:
        big = D.load_large()
        Xtr, Xte, ytr, yte = T.train_test(big, D.LARGE_FEATURES)
        sweep = T.complexity_sweep(Xtr, ytr, Xte, yte, list(DEPTHS))
        _DATA["d"] = ((Xtr, Xte, ytr, yte), sweep, list(Xtr.columns))
    return _DATA["d"]


class Level4(Level):
    ID, NAME, THEME = 4, "The Overgrown Tree", "tree"
    CONCEPTS = ["Overfitting", "Underfitting", "Tree depth", "Generalisation", "Pruning"]
    LEARNED = ["OVERFITTING: a deep tree memorises its training data (100% train) but fails on unseen data.",
               "A tree that is too shallow UNDERFITS and misses real patterns.",
               "PRUNING or limiting depth trades a little training accuracy for much better GENERALISATION."]

    def build(self):
        (self.split, self.sweep, self.names) = data()
        b = Builder(125)
        b.ground(0, 124, GROUND)
        b.block(0, 0, 1, GROUND)
        self.spawn = (3 * TILE, FLOOR_Y)
        b.platform(9, 11, 3); b.platform(14, 12, 2); b.platform(18, 10, 3)
        gem_arc(self, 9, 11, 3); gem_arc(self, 18, 10, 3)
        add_cp(self, 2)
        self.enemies.append(Slime(13 * TILE, FLOOR_Y, 10 * TILE, 17 * TILE))
        add_terminal(self, 24, "depth", "GROWTH LAB")
        door_wall(self, b, 32, color=GREEN)
        add_cp(self, 36)
        b.clear(41, GROUND, 5, 3)
        self.movers.append(Mover(41 * TILE, 13 * TILE, 2, dx=3, speed=70, theme="tree"))
        gem_arc(self, 42, 11, 4, 6)
        b.platform(48, 11, 3); b.platform(53, 9, 3); b.platform(58, 11, 3)
        gem_arc(self, 48, 11, 3); gem_arc(self, 53, 9, 3); gem_arc(self, 58, 11, 3)
        self.enemies.append(Bat(50 * TILE, 7 * TILE, 90, 20))
        self.enemies.append(Slime(66 * TILE, FLOOR_Y, 62 * TILE, 70 * TILE))
        add_cp(self, 62)
        add_terminal(self, 74, "prune", "PRUNING BENCH")
        door_wall(self, b, 82, color=GREEN)
        add_cp(self, 86)
        b.spikes(91, 4, GROUND - 1); b.platform(92, 11, 2)
        b.platform(98, 11, 3); b.platform(103, 9, 3)
        gem_arc(self, 91, 10, 4, 6); gem_arc(self, 98, 11, 3); gem_arc(self, 103, 9, 3)
        self.enemies.append(Bat(100 * TILE, 7 * TILE, 80, 18))
        add_terminal(self, 108, "concepts", "OBSERVATORY")
        door_wall(self, b, 114, color=GREEN)
        self.exit_rect = pygame.Rect(121 * TILE, 11 * TILE, 2 * TILE, 3 * TILE)
        self.grid = b.build()
        self.intro = ["The Overgrown Tree! This tree grew a branch for every little detail, and now vines block the way.",
                      "A tree that grows too deep can memorise its training data. That is OVERFITTING: perfect on old data, poor on new data.",
                      "Use the growth lab to test different depths on data the tree has never seen, then prune it back."]
        self.hints = {"t0": ["In the growth lab, test several depths and watch both accuracies.", "Training accuracy keeps rising with depth. Look at what happens to the UNSEEN accuracy instead."],
                      "t1": ["Run the pruning, then compare the two trees on unseen data.", "Trust the tree that does better on data it has not seen."],
                      "t2": ["Use the numbers from the earlier labs to name each problem.", "Great on training but weak on unseen = overfitting. Weak on both = underfitting."],
                      "exit": ["The way is clear. Reach the portal!"]}

    # ---------------------------------------------------------------- derived facts
    def best_depths(self): return T.best_depths(self.sweep)

    def row(self, d):
        r = self.sweep[(self.sweep["max_depth"] == d) | (self.sweep["max_depth"].isna() & (d is None))].iloc[0]
        return r

    def panel_for(self, terminal, game):
        i = self.terminals.index(terminal)
        if i == 0:
            def on_choose(d, tested):
                best = self.best_depths()
                r = self.row(d)
                if d in best:
                    return True, f"Depth {d} generalises best: {r.test_acc * 100:.0f}% on unseen data. Deeper trees memorise noise. The vines wither!"
                if d is None or (d or 0) > best[0]:
                    return False, f"Too deep: training {r.train_acc * 100:.0f}% but unseen only {r.test_acc * 100:.0f}%. Try a smaller depth."
                return False, f"Too shallow: unseen accuracy is only {r.test_acc * 100:.0f}%. The tree has not learned enough."
            return DepthPanel(game.ctx, self.split, self.names, on_choose, DEPTHS)
        if i == 1:
            def check(which, res):
                if which == res["winner"]:
                    return True, f"Yes. The pruned tree scores {res['pruned']['test_acc'] * 100:.0f}% on unseen data versus {res['deep']['test_acc'] * 100:.0f}% for the overgrown one, with far fewer leaves."
                return False, "Compare the UNSEEN accuracy of both trees, not the training accuracy."
            return PrunePanel(game.ctx, self.split, self.names, check)
        deep, shallow = self.row(None), self.row(1)
        over = "Overfitting" if deep.train_acc - deep.test_acc > 0.15 else "Underfitting"
        under = "Underfitting" if max(shallow.train_acc, shallow.test_acc) < 0.8 else "Overfitting"
        steps = [dict(prompt=f"The unlimited tree scored {deep.train_acc * 100:.0f}% on training data but {deep.test_acc * 100:.0f}% on unseen data. What is this called?",
                      options=["Overfitting", "Underfitting", "Good fit"], check=lambda a: (a == over, "Correct. It memorised the training set." if a == over else "Big gap between train and unseen accuracy. What does memorising look like?"), colors=[RED, TEAL, GREEN]),
                 dict(prompt=f"A tree limited to depth 1 scored only {shallow.train_acc * 100:.0f}% on training and {shallow.test_acc * 100:.0f}% on unseen data. What is this called?",
                      options=["Overfitting", "Underfitting", "Good fit"], check=lambda a: (a == under, "Correct. It is too simple to capture the pattern." if a == under else "It does badly on BOTH sets. Is that memorising or being too simple?"), colors=[RED, TEAL, GREEN])]
        return ChoicePanel(game.ctx, "OBSERVATORY  -  name the problem", steps)

    def on_solved(self, i, instant):
        self.gates[i].set_open(True, instant)
        if not instant:
            self.sfx("door")
            self.say(["The vines wither! Depth is the dial between too simple and too complex.", "Pruning cut away branches that were only memorising noise.",
                      "Overfitting and underfitting: the two ways a model can go wrong."][i])
        if all(t.solved for t in self.terminals):
            self.exit_open = True
