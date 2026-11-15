"""LEVEL 3 - The Split Path: entropy, Gini and information gain choose the best split."""
from __future__ import annotations

import pygame

from ds import dataset as D
from ds import impurity as I
from game.entities import Bat, Bridge, Slime
from game.level import Level
from game.levels.common import *  # noqa
from game.panels import SplitPanel
from game.settings import *  # noqa
from game.world import Builder

CHASMS = [(31, 10), (63, 10), (101, 8)]          # (start tile, width)


class Level3(Level):
    ID, NAME, THEME = 3, "The Split Path", "crystal"
    CONCEPTS = ["Entropy", "Gini impurity", "Weighted impurity", "Information gain", "Best split"]
    LEARNED = ["IMPURITY measures how mixed a group is. Entropy and Gini are both 0 for a pure group.",
               "After a split we average the children's impurity, weighted by their sizes.",
               "INFORMATION GAIN = parent impurity - weighted child impurity. The best split has the highest gain."]

    def build(self):
        self.df = D.load_mystic()
        self.train, _ = D.mystic_split(self.df)
        self.large = D.load_large()
        b = Builder(125)
        b.ground(0, 30, GROUND); b.ground(41, 62, GROUND); b.ground(73, 100, GROUND); b.ground(109, 124, GROUND)
        b.block(0, 0, 1, GROUND)
        self.spawn = (3 * TILE, FLOOR_Y)
        gem_arc(self, 8, 11, 3); b.platform(8, 11, 3)
        b.platform(15, 12, 3); b.platform(20, 10, 3); gem_arc(self, 20, 10, 3); gem_arc(self, 15, 12, 3)
        add_cp(self, 2)
        self.enemies.append(Slime(12 * TILE, FLOOR_Y, 9 * TILE, 16 * TILE))
        add_terminal(self, 27, "split", "SPLIT ALTAR")
        for k, (x, w) in enumerate(CHASMS):
            self.bridges.append(Bridge(x * TILE, GROUND * TILE, w, PURPLE))
            self.enemies.append(Bat((x + w // 2) * TILE, 9 * TILE, 110, 22))
            # optional crystal ledge above each chasm
            b.platform(x + 3, 10, 3); gem_arc(self, x + 3, 10, 3)
        add_cp(self, 43)
        b.platform(47, 11, 3); b.platform(52, 12, 2); gem_arc(self, 47, 11, 3)
        self.enemies.append(Slime(50 * TILE, FLOOR_Y, 46 * TILE, 56 * TILE))
        add_terminal(self, 59, "split", "SPLIT ALTAR")
        add_cp(self, 75)
        b.platform(80, 11, 3); b.platform(85, 9, 3); b.platform(90, 11, 3)
        gem_arc(self, 80, 11, 3); gem_arc(self, 85, 9, 3); gem_arc(self, 90, 11, 3)
        self.enemies.append(Slime(84 * TILE, FLOOR_Y, 78 * TILE, 90 * TILE))
        add_terminal(self, 97, "split", "SPLIT ALTAR")
        add_cp(self, 111)
        self.enemies.append(Slime(116 * TILE, FLOOR_Y, 112 * TILE, 121 * TILE))
        self.exit_rect = pygame.Rect(121 * TILE, 11 * TILE, 2 * TILE, 3 * TILE)
        self.grid = b.build()
        self.intro = ["The Split Path! Each chasm needs a bridge, and a bridge only forms when you pick the BEST question to ask about the creatures.",
                      "A question splits creatures into a YES group and a NO group. A good question makes each group PURE: almost all dangerous, or almost all safe.",
                      "INFORMATION GAIN is a score for that: higher means the groups are cleaner. At each altar: 1) click every feature, 2) compare their gains, 3) build with the highest one.",
                      "You will not lose anything for checking all of them. Walk to the glowing altar and press E."]
        self.hints = {"t0": ["At the altar, click ALL the features on the left, one by one. Each shows its information gain.", "Then pick the feature with the biggest information gain (the tallest bar in the chart) and press BUILD THE BRIDGE."],
                      "t1": ["This altar looks at the creatures still mixed after the first split. Click every feature again.", "Same rule: highest information gain wins. Compare the bars."],
                      "t2": ["This altar uses Gini impurity (fixed), but the rule is identical: the highest gain wins.", "Equivalent view: the weighted impurity after the split should be as LOW as possible."],
                      "exit": ["The portal is open. Go through!"]}

    # ---------------------------------------------------------------- data nodes
    def node_for(self, i):
        """(dataframe, features, criterion, lock, name) for altar i. Computed from data, never typed in."""
        feats = D.MYSTIC_FEATURES
        root = I.best_splits(self.train, feats, D.TARGET)[0]
        if i == 0:
            return self.train, feats, "entropy", False, "root"
        if i == 1:
            sp = I.split_by_feature(self.train, root, D.TARGET)
            child = sp["no"] if I.entropy(sp["no_labels"]) >= I.entropy(sp["yes_labels"]) else sp["yes"]
            return child, [f for f in feats if f != root], "entropy", False, f"{root} = " + ("No" if child is sp["no"] else "Yes")
        return self.large, feats, "gini", True, "big dataset"

    def panel_for(self, terminal, game):
        i = self.terminals.index(terminal)
        df, feats, crit, lock, name = self.node_for(i)
        def on_build(feature, criterion):
            best = I.best_splits(df, feats, D.TARGET, criterion)
            e = I.evaluate_split(df, feature, D.TARGET, criterion)
            if feature in best:
                return True, f"Bridge built! Splitting on '{feature}' gives information gain {e['gain']:.3f}, the highest available."
            return False, f"Not the best. '{feature}' has information gain {e['gain']:.3f}. In the chart, another feature has a taller bar. Select that one and build again."
        return SplitPanel(game.ctx, df, feats, D.TARGET, on_build, node_name=name, criterion=crit, lock=lock)

    def on_solved(self, i, instant):
        self.bridges[i].set_built(True, instant)
        if not instant:
            self.sfx("door")
            self.say(["The first bridge forms! The best split gave the largest drop in impurity.", "Second bridge! Each split is chosen greedily, one node at a time.",
                      "Gini agrees: both measures reward pure groups."][i])
        if all(t.solved for t in self.terminals):
            self.exit_open = True
