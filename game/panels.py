"""Holographic data-science panels. Each panel is computed from real data; none reveals the answer before an attempt."""
from __future__ import annotations

import pygame

from ds import impurity as I
from ds import tree_model as T
from ds import visualise as V
from ds.evaluation import confusion, evaluate
from game import assets as A
from game import ui
from game.settings import *  # noqa

PW, PH = 840, 470
PX, PY = (WIDTH - PW) // 2, (HEIGHT - PH) // 2 - 6


class Panel:
    title = "HOLOGRAM"
    border = TEAL
    msg_y = None
    task = "Read the panel, click your answer. Wrong answers are fine: you get a hint and try again."

    def __init__(self, ctx, w=PW, h=PH):
        self.ctx = ctx
        self.w, self.h = w, h
        self.rect = pygame.Rect((WIDTH - w) // 2, (HEIGHT - h) // 2 - 6, w, h)
        self.closed = False
        self.result = None
        self.solved = False
        self.msg, self.msg_color, self.msg_t = "", CREAM, 0.0
        self.t = 0.0
        self._bg = A.holo_panel(w, h, self.title, self.border)
        self._close_t = None

    # coordinates local to panel
    def local(self, pos): return (pos[0] - self.rect.x, pos[1] - self.rect.y)

    def say(self, text, color=CREAM, secs=6.0):
        self.msg, self.msg_color, self.msg_t = text, color, secs

    def finish(self, result=True, delay=1.1):
        self.solved, self.result, self._close_t = True, result, delay

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        if self._close_t is not None:
            self._close_t -= dt
            if self._close_t <= 0:
                self.closed = True

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_e) and not self.solved:
            self.closed = True; return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not self.solved:
            self.click(self.local(ev.pos))
        elif ev.type == pygame.KEYDOWN and not self.solved:
            self.key(ev.key)

    def click(self, p): ...
    def key(self, k): ...
    def body(self, s, mouse): ...

    def draw(self, surf):
        surf.blit(self._bg, self.rect.topleft)
        panel = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        mouse = self.local(pygame.mouse.get_pos())
        self.body(panel, mouse)
        if self.msg and self.msg_t > 0:
            ui.draw_text(panel, self.msg, (24, self.msg_y if self.msg_y else self.h - 58), 15, self.msg_color, True, width=self.w - 48)
        t = A.text("E / Esc: close", 12, (130, 145, 170))
        panel.blit(t, (self.w - t.get_width() - 14, 12))
        surf.blit(panel, self.rect.topleft)
        if not self.solved:
            ui.draw_text(surf, "YOUR TASK:  " + self.task_text(), (WIDTH // 2, self.rect.bottom + 14), 15, GOLD, True, align="mid", width=WIDTH - 40)

    def task_text(self): return self.task

    def play(self, name):
        if self.ctx and getattr(self.ctx, "audio", None):
            self.ctx.audio.play(name)


# ---------------------------------------------------------------------------------- generic choice panel
class ChoicePanel(Panel):
    """A sequence of steps. step = dict(prompt, options, check(choice)->(ok,msg), card=None, tree=None, visited=(), current=None, title=None)."""

    def __init__(self, ctx, title, steps):
        self.title = title
        super().__init__(ctx)
        self.steps, self.i = steps, 0
        self.results = []
        self._buttons()

    def _buttons(self):
        st = self.steps[self.i]
        n = len(st["options"])
        bw = min(200, (self.w - 60) // n - 10)
        total = n * bw + (n - 1) * 14
        x0 = (self.w - total) // 2
        cols = st.get("colors") or [GREEN if o in ("Yes", "Safe") else RED if o in ("No", "Dangerous") else TEAL for o in st["options"]]
        self.buttons = [ui.Button((x0 + k * (bw + 14), self.h - 108, bw, 40), o, color=cols[k], size=17) for k, o in enumerate(st["options"])]

    def click(self, p):
        for b in self.buttons:
            if b.hit(p):
                st = self.steps[self.i]
                ok, msg = st["check"](b.label)
                self.say(msg, GREEN if ok else RED)
                self.play("correct" if ok else "wrong")
                if ok:
                    self.results.append(b.label)
                    if self.i + 1 < len(self.steps):
                        self.i += 1; self._buttons()
                    else:
                        self.finish(self.results, 1.4)
                else:
                    self.ctx.mistake() if self.ctx else None
                return

    def key(self, k):
        if pygame.K_1 <= k <= pygame.K_9 and self.buttons:
            idx = k - pygame.K_1
            if idx < len(self.buttons):
                self.click(self.buttons[idx].rect.center)

    def body(self, s, mouse):
        st = self.steps[self.i]
        if len(self.steps) > 1:
            ui.draw_text(s, f"Step {self.i + 1} / {len(self.steps)}", (self.w - 130, 36), 13, TEAL, True)
        card_w = 0
        if st.get("card"):
            c = st["card"]
            card_w = 250
            pygame.draw.rect(s, (22, 38, 58), (24, 50, card_w, 250), border_radius=10)
            pygame.draw.rect(s, GOLD, (24, 50, card_w, 250), 2, border_radius=10)
            ui.draw_text(s, c["name"], (24 + card_w // 2, 60), 24, GOLD, True, align="mid")
            ui.draw_text(s, c.get("subtitle", "Creature record"), (24 + card_w // 2, 92), 12, (150, 165, 190), align="mid")
            for r, (k, v) in enumerate(c["rows"]):
                y = 124 + r * 38
                ui.draw_text(s, k.replace("_", " "), (42, y + 4), 15, CREAM)
                ui.chip(s, pygame.Rect(24 + card_w - 84, y, 62, 28), str(v), v == "Yes", GREEN if v == "Yes" else (120, 130, 155))
        right = 24 + card_w + (16 if card_w else 0)
        ui.draw_text(s, st["prompt"], (right, 52), 19, CREAM, True, width=self.w - right - 24)
        if st.get("tree"):
            ui.draw_tree(s, pygame.Rect(right, 150 if len(st["prompt"]) > 40 else 120, self.w - right - 24, 170), st["tree"], st.get("visited", ()), st.get("current"), self.t)
        elif st.get("note"):
            ui.draw_text(s, st["note"], (right, 130), 15, (170, 185, 210), width=self.w - right - 24)
        for k, b in enumerate(self.buttons):
            b.label = st["options"][k]
            b.draw(s, mouse)
        ui.draw_text(s, "Click an answer (or press 1 / 2)", (self.w // 2, self.h - 64 - 0), 12, (130, 145, 170), align="mid") if not self.msg_t else None


# ---------------------------------------------------------------------------------- Level 2: roles
class RolesPanel(Panel):
    task = "Click each column and label it: ID, Feature (a clue) or Target (the answer we predict)."
    title = "DATASET INSPECTION  -  Mystic Creatures"
    ROLES = ["?", "Feature", "Target", "ID"]

    def __init__(self, ctx, df, name_col, target, rows=8):
        super().__init__(ctx)
        self.df, self.name_col, self.target = df, name_col, target
        self.cols = list(df.columns)
        self.rows = rows
        self.roles = {c: 0 for c in self.cols}
        self.bad: set[str] = set()
        self.cw = (self.w - 48) // len(self.cols)
        self.check_btn = ui.Button((self.w // 2 - 110, self.h - 104, 220, 38), "CHECK ROLES", color=GOLD, size=17)

    def truth(self, c): return "ID" if c == self.name_col else "Target" if c == self.target else "Feature"

    def click(self, p):
        for i, c in enumerate(self.cols):
            r = pygame.Rect(24 + i * self.cw + 4, 62, self.cw - 8, 30)
            if r.collidepoint(p):
                self.roles[c] = (self.roles[c] + 1) % len(self.ROLES); self.bad.discard(c); self.play("click"); return
        if self.check_btn.hit(p):
            self.bad = {c for c in self.cols if self.ROLES[self.roles[c]] != self.truth(c)}
            if self.bad:
                self.play("wrong"); self.ctx.mistake()
                self.say(f"{len(self.bad)} column(s) are labelled wrongly (red). What does the model look at, and what must it predict?", RED)
            else:
                self.play("correct"); self.say("Every column has the right role. Features describe; the target is the answer.", GREEN); self.finish()

    def body(self, s, mouse):
        ui.draw_text(s, "Click a role button to cycle it: Feature = clue, Target = what we predict, ID = a name.", (24, 36), 13, (170, 185, 210), width=self.w - 48)
        for i, c in enumerate(self.cols):
            x = 24 + i * self.cw
            r = pygame.Rect(x + 4, 62, self.cw - 8, 30)
            role = self.ROLES[self.roles[c]]
            col = {"?": (90, 100, 125), "Feature": TEAL, "Target": GOLD, "ID": PURPLE}[role]
            pygame.draw.rect(s, col, r, border_radius=6)
            pygame.draw.rect(s, RED if c in self.bad else CREAM, r, 3 if c in self.bad else 1, border_radius=6)
            t = A.text(role, 14, DARK, True); s.blit(t, t.get_rect(center=r.center))
            h = pygame.Rect(x + 4, 96, self.cw - 8, 28)
            pygame.draw.rect(s, (30, 46, 70), h)
            t = A.text(c.replace("_", " "), 13, GOLD, True); s.blit(t, t.get_rect(center=h.center))
        for j in range(self.rows):
            y = 126 + j * 27
            if j % 2 == 0: pygame.draw.rect(s, (20, 34, 54), (24, y, self.w - 48, 27))
            for i, c in enumerate(self.cols):
                v = str(self.df.iloc[j][c])
                col = GREEN if v == "Yes" else (CREAM if c == self.name_col else (190, 120, 120) if v == "No" else CREAM)
                t = A.text(v, 14, col); s.blit(t, t.get_rect(center=(24 + i * self.cw + self.cw // 2, y + 13)))
        ui.draw_text(s, f"Showing {self.rows} of {len(self.df)} records", (24, 126 + self.rows * 27 + 4), 12, (130, 145, 170))
        self.check_btn.draw(s, mouse)


# ---------------------------------------------------------------------------------- Level 2: which features matter
class FeaturesPanel(Panel):
    task = "Pick the feature that best separates dangerous from safe creatures. Check the danger rates."
    title = "FEATURE ANALYSIS  -  which clues matter?"

    def __init__(self, ctx, df, features, target, spread_min=0.3):
        super().__init__(ctx)
        self.df, self.features, self.target = df, features, target
        self.stats = {}
        for f in features:
            y, n = df[df[f] == "Yes"], df[df[f] == "No"]
            self.stats[f] = {"yes": (y[target] == "Yes").mean() if len(y) else 0.0, "no": (n[target] == "Yes").mean() if len(n) else 0.0, "ny": len(y), "nn": len(n)}
        self.relevant = {f for f in features if abs(self.stats[f]["yes"] - self.stats[f]["no"]) >= spread_min}
        self.chosen: set[str] = set()
        self.btn = ui.Button((self.w // 2 - 120, self.h - 104, 240, 38), "LOCK IN FEATURES", color=GOLD, size=17)

    def click(self, p):
        for i, f in enumerate(self.features):
            if pygame.Rect(24, 96 + i * 82, 200, 46).collidepoint(p):
                self.chosen ^= {f}; self.play("click"); return
        if self.btn.hit(p):
            if not self.chosen:
                self.say("Pick at least one feature first.", RED); return
            if self.chosen == self.relevant:
                self.play("correct"); self.say("These features really separate dangerous from safe creatures.", GREEN); self.finish()
            else:
                self.play("wrong"); self.ctx.mistake()
                self.say("Not quite. A useful feature changes the danger rate a lot between its Yes and No groups. Compare the two bars.", RED)

    def body(self, s, mouse):
        ui.draw_text(s, f"For each feature: how often is a creature {self.target.lower()} when the feature is Yes vs No?  Select the features worth using.", (24, 40), 14, (170, 185, 210), width=self.w - 48)
        for i, f in enumerate(self.features):
            y = 96 + i * 82
            ui.chip(s, pygame.Rect(24, y, 200, 46), f.replace("_", " "), f in self.chosen, TEAL, 16)
            st = self.stats[f]
            for k, (lab, key, n) in enumerate((("when YES", "yes", "ny"), ("when NO", "no", "nn"))):
                yy = y + k * 24 - 2
                ui.draw_text(s, f"{lab}  (n={st[n]})", (250, yy + 2), 13, CREAM)
                ui.bar(s, pygame.Rect(470, yy, 260, 18), st[key], RED if st[key] >= .5 else TEAL)
                ui.draw_text(s, f"{st[key] * 100:.0f}%", (740, yy + 1), 14, GOLD, True)
        self.btn.draw(s, mouse)


# ---------------------------------------------------------------------------------- Level 3: split chooser
class SplitPanel(Panel):
    task = "Click every feature, then build with the one that has the HIGHEST gain."
    title = "SPLIT ANALYSER  -  choose the best question"

    def __init__(self, ctx, df, features, target, on_build, node_name="root", criterion="entropy", lock=False):
        super().__init__(ctx)
        self.df, self.features, self.target, self.on_build = df, features, target, on_build
        self.criterion = criterion
        self.lock = lock
        self.sel = None
        self.inspected: list[str] = []
        self.node_name = node_name
        self.fb = [ui.Button((24, 78 + i * 50, 190, 42), f.replace("_", " "), key=f, color=TEAL, size=16) for i, f in enumerate(features)]
        self.cb = [ui.Button((24 + k * 96, 40, 92, 28), c.title(), key=c, color=PURPLE, size=14, enabled=not lock or c == criterion) for k, c in enumerate(("entropy", "gini"))]
        self.build_btn = ui.Button((24, self.h - 104, 190, 38), "BUILD THE BRIDGE", color=GOLD, size=17, enabled=False)
        self._fig = None
        self._fig_key = None
        self.say("Step 1: click each feature on the left and read its information gain.", CREAM, 9999)

    @property
    def all_seen(self): return len(self.inspected) >= len(self.features)

    def task_text(self):
        n, m = len(self.inspected), len(self.features)
        if not self.all_seen: return f"Step 1 of 3: click every feature on the left ({n} of {m} checked)."
        if self.sel is None: return "Step 2 of 3: find the TALLEST gain bar in the chart, then click that feature."
        return "Step 3 of 3: with the tallest-bar feature selected, press BUILD THE BRIDGE."

    def click(self, p):
        for b in self.cb:
            if b.hit(p) and not self.lock:
                self.criterion = b.key; self.play("click"); return
        for b in self.fb:
            if b.hit(p):
                self.sel = b.key
                if b.key not in self.inspected: self.inspected.append(b.key)
                self.build_btn.enabled = self.all_seen
                self.play("click")
                if self.all_seen: self.say("All checked. The tallest bar in the chart is the best question: select it, then press BUILD THE BRIDGE.", CREAM, 9999)
                return
        if self.build_btn.rect.collidepoint(p):
            if not self.all_seen or self.sel is None:
                self.say(f"Check every feature first ({len(self.inspected)} of {len(self.features)} done), then select the best one and build.", GOLD, 6); self.play("wrong"); return
            ok, msg = self.on_build(self.sel, self.criterion)
            self.say(msg, GREEN if ok else RED, 9)
            self.play("correct" if ok else "wrong")
            if ok: self.finish(self.sel, 1.8)
            else: self.ctx.mistake()

    def _chart(self):
        evs = {f: I.evaluate_split(self.df, f, self.target, self.criterion) for f in self.inspected}
        key = (tuple(self.inspected), self.criterion, self.sel)
        if key != self._fig_key and self.inspected:
            names = list(evs)
            fig = V.impurity_figure(names, evs[names[0]]["parent_impurity"], [evs[n]["weighted_impurity"] for n in names], [evs[n]["gain"] for n in names], self.criterion, highlight=self.sel, size=(500, 200), mode="gain")
            self._fig, self._fig_key = V.to_surface(fig), key
        return evs

    def body(self, s, mouse):
        for b in self.cb: b.draw(s, mouse, selected=b.key == self.criterion)
        ui.draw_text(s, "Measure (fixed here)" if self.lock else "Measure:", (224, 46), 13, (150, 165, 190))
        for b in self.fb:
            b.draw(s, mouse, selected=b.key == self.sel)
            if b.key in self.inspected: pygame.draw.circle(s, GREEN, (b.rect.right - 14, b.rect.centery), 5)
        counts = I.class_counts(self.df[self.target])
        ui.draw_text(s, f"Node '{self.node_name}': {len(self.df)} creatures  ({counts.get('Yes', 0)} dangerous / {counts.get('No', 0)} safe)", (24, 232), 13, GOLD, True, width=200)
        ui.draw_text(s, f"Checked {len(self.inspected)} of {len(self.features)} features", (24, 300), 13, TEAL if self.all_seen else CREAM, True, width=200)
        evs = self._chart()
        x = 236
        if self.sel:
            e = evs[self.sel]
            nm = self.criterion
            rows = [("", "YES group", "NO group")]
            rows.append(("creatures", f"{e['n_yes']}", f"{e['n_no']}"))
            rows.append(("dangerous / safe", f"{e['yes_counts'].get('Yes', 0)} / {e['yes_counts'].get('No', 0)}", f"{e['no_counts'].get('Yes', 0)} / {e['no_counts'].get('No', 0)}"))
            rows.append((nm, f"{e['yes_impurity']:.3f}", f"{e['no_impurity']:.3f}"))
            pygame.draw.rect(s, (20, 36, 56), (x, 78, 330, 112), border_radius=8)
            for r, row in enumerate(rows):
                for c, v in enumerate(row):
                    col = GOLD if r == 0 else CREAM
                    ui.draw_text(s, v, (x + 12 + (0, 138, 238)[c], 84 + r * 26), 14, col, r == 0)
            ui.draw_text(s, f"Parent {nm}: {e['parent_impurity']:.3f}", (x + 350, 84), 14, CREAM)
            ui.draw_text(s, f"Weighted {nm} after the split: {e['weighted_impurity']:.3f}", (x + 350, 110), 14, CREAM, width=230)
            ui.draw_text(s, f"Information gain = {e['gain']:.3f}", (x + 350, 150), 15, TEAL, True, width=260)
            ui.draw_text(s, "(parent - weighted)", (x + 350, 172), 12, (150, 165, 190), width=230)
        else:
            ui.draw_text(s, "Each feature asks a Yes/No question. Click one to see how it splits the creatures into a YES group and a NO group, and how much cleaner (purer) the groups become. That improvement is the information gain.", (x, 84), 15, (170, 185, 210), width=580, line_h=22)
        if self._fig:
            s.blit(self._fig, (236, 198))
            if self.all_seen:
                best = max(evs, key=lambda f: evs[f]["gain"])
                ui.draw_text(s, f"Highest gain: {best.replace('_', ' ')} ({evs[best]['gain']:.3f})", (24, 330), 13, GOLD, True, width=200)
        self.build_btn.draw(s, mouse)


# ---------------------------------------------------------------------------------- Level 4: depth explorer
class DepthPanel(Panel):
    task = "Try each depth. Pick the one where TEST accuracy is highest, not the deepest tree."
    title = "TREE GROWTH LAB  -  how deep should it grow?"

    def __init__(self, ctx, data, names, on_choose, depths=(1, 2, 3, 4, 6, 8, None)):
        super().__init__(ctx)
        self.Xtr, self.Xte, self.ytr, self.yte = data
        self.names, self.on_choose, self.depths = list(names), on_choose, list(depths)
        self.idx = 0
        self.tested: dict = {}
        self.models, self.figs = {}, {}
        self.curve = None
        self.minus = ui.Button((24, 56, 44, 36), "-", color=PURPLE, size=22)
        self.plus = ui.Button((200, 56, 44, 36), "+", color=PURPLE, size=22)
        self.test_btn = ui.Button((24, 160, 220, 38), "TEST ON UNSEEN DATA", color=TEAL, size=14)
        self.prune_btn = ui.Button((24, self.h - 104, 220, 38), "PRUNE TO THIS DEPTH", color=GOLD, size=15)

    @property
    def depth(self): return self.depths[self.idx]

    def model(self):
        d = self.depth
        if d not in self.models: self.models[d] = T.train_tree(self.Xtr, self.ytr, max_depth=d)
        return self.models[d]

    def click(self, p):
        if self.minus.hit(p): self.idx = max(0, self.idx - 1); self.play("click"); return
        if self.plus.hit(p): self.idx = min(len(self.depths) - 1, self.idx + 1); self.play("click"); return
        if self.test_btn.hit(p):
            m = self.model()
            self.tested[self.depth] = (m.score(self.Xtr, self.ytr), m.score(self.Xte, self.yte))
            self.play("hint"); self.curve = None; return
        if self.prune_btn.hit(p):
            ok, msg = self.on_choose(self.depth, dict(self.tested))
            self.say(msg, GREEN if ok else RED, 9)
            self.play("correct" if ok else "wrong")
            if ok: self.finish(self.depth, 2.0)
            else: self.ctx.mistake()

    def body(self, s, mouse):
        m = self.model()
        st = T.tree_stats(m)
        label = "unlimited" if self.depth is None else str(self.depth)
        ui.draw_text(s, "Depth limit", (24, 38), 13, (150, 165, 190))
        self.minus.draw(s, mouse); self.plus.draw(s, mouse)
        t = A.text(label, 22, GOLD, True); s.blit(t, t.get_rect(center=(134, 74)))
        ui.draw_text(s, f"Tree uses {st['leaves']} leaves (depth {st['depth']})", (24, 106), 14, CREAM)
        ui.draw_text(s, "Accuracy on training data", (24, 128), 12, (150, 165, 190))
        tr = m.score(self.Xtr, self.ytr)
        ui.bar(s, pygame.Rect(24, 142, 150, 12), tr, TEAL); ui.draw_text(s, f"{tr * 100:.0f}%", (182, 138), 14, TEAL, True)
        self.test_btn.draw(s, mouse)
        if self.depth in self.tested:
            te = self.tested[self.depth][1]
            ui.draw_text(s, "Accuracy on UNSEEN data", (24, 204), 12, (150, 165, 190))
            ui.bar(s, pygame.Rect(24, 218, 150, 12), te, GOLD); ui.draw_text(s, f"{te * 100:.0f}%", (182, 214), 14, GOLD, True)
        else:
            ui.draw_text(s, "Press TEST to find out how well it generalises.", (24, 204), 12, (150, 165, 190), width=220)
        if self.depth not in self.figs:
            self.figs[self.depth] = V.to_surface(V.tree_figure(m, self.names, size=(540, 215), fontsize=7 if st["leaves"] > 10 else 9))
        s.blit(self.figs[self.depth], (270, 40))
        if self.tested:
            if self.curve is None:
                ds = [d for d in self.depths if d in self.tested]
                self.curve = V.to_surface(V.accuracy_curve_figure(ds, [self.tested[d][0] for d in ds], [self.tested[d][1] for d in ds], size=(330, 138)))
            s.blit(self.curve, (270, 262))
        ui.draw_text(s, "Compare training vs unseen accuracy at several depths, then prune.", (610, 276), 13, (170, 185, 210), width=210)
        self.prune_btn.draw(s, mouse)


# ---------------------------------------------------------------------------------- Level 4: pruning comparison
class PrunePanel(Panel):
    task = "Choose the pruning that keeps unseen-data accuracy high while shrinking the tree."
    title = "PRUNING  -  cutting back the overgrown tree"

    def __init__(self, ctx, data, names, check):
        super().__init__(ctx)
        self.Xtr, self.Xte, self.ytr, self.yte = data
        self.names, self.check = list(names), check
        self.res = None
        self.run_btn = ui.Button((24, 60, 300, 40), "RUN COST-COMPLEXITY PRUNING", color=PURPLE, size=15)
        self.keep = [ui.Button((24, self.h - 104, 260, 38), "KEEP THE DEEP TREE", key="deep", color=RED, size=15, enabled=False),
                     ui.Button((310, self.h - 104, 260, 38), "KEEP THE PRUNED TREE", key="pruned", color=GREEN, size=15, enabled=False)]
        self.figs = {}

    def click(self, p):
        if self.run_btn.hit(p) and not self.res:
            self.res = T.pruning_experiment(self.Xtr, self.ytr, self.Xte, self.yte)
            for k in ("deep", "pruned"):
                self.figs[k] = V.to_surface(V.tree_figure(self.res[k]["model"], self.names, size=(380, 190), fontsize=6 if k == "deep" else 9))
            for b in self.keep: b.enabled = True
            self.play("hint"); return
        for b in self.keep:
            if b.hit(p):
                ok, msg = self.check(b.key, self.res)
                self.say(msg, GREEN if ok else RED, 9); self.play("correct" if ok else "wrong")
                if ok: self.finish(b.key, 2.0)
                else: self.ctx.mistake()

    def body(self, s, mouse):
        ui.draw_text(s, "Pruning removes branches that add complexity but little real predictive value. Which tree would you trust with new creatures?", (350, 66), 14, (170, 185, 210), width=470)
        self.run_btn.draw(s, mouse)
        if self.res:
            for k, x in (("deep", 24), ("pruned", 430)):
                r = self.res[k]
                ui.draw_text(s, "Overgrown tree" if k == "deep" else f"Pruned tree (alpha {self.res['alpha']:.3f})", (x, 114), 15, GOLD, True)
                s.blit(self.figs[k], (x - 4, 134))
                ui.draw_text(s, f"leaves {r['leaves']}   train {r['train_acc'] * 100:.0f}%   unseen {r['test_acc'] * 100:.0f}%", (x, 328), 14, CREAM)
        for b in self.keep: b.draw(s, mouse)


# ---------------------------------------------------------------------------------- Level 5: training console
class TrainPanel(Panel):
    task = "Tick the useful features, train the tree, then confirm if the test accuracy is good enough."
    title = "TRAINING CONSOLE  -  build your classifier"
    msg_y = 424

    def __init__(self, ctx, train_df, test_df, features, target, min_acc, on_confirm):
        super().__init__(ctx)
        self.train_df, self.test_df, self.features, self.target = train_df, test_df, features, target
        self.min_acc, self.on_confirm = min_acc, on_confirm
        self.chosen: list[str] = []
        self.depth = 3
        self.model = None
        self.ev = None
        self.figs = {}
        self.names_used = []
        self.train_btn = ui.Button((24, 298, 212, 34), "1. TRAIN", color=TEAL, size=16, enabled=False)
        self.test_btn = ui.Button((24, 336, 212, 34), "2. TEST (unseen)", color=GOLD, size=16, enabled=False)
        self.ok_btn = ui.Button((24, 374, 212, 34), "3. EQUIP MODEL", color=GREEN, size=16, enabled=False)
        self.dm = ui.Button((170, 262, 30, 28), "-", color=PURPLE, size=18)
        self.dp = ui.Button((206, 262, 30, 28), "+", color=PURPLE, size=18)

    def invalidate(self):
        self.model = self.ev = None; self.figs.clear()
        self.test_btn.enabled = self.ok_btn.enabled = False
        self.train_btn.enabled = bool(self.chosen)

    def click(self, p):
        for i, f in enumerate(self.features):
            if pygame.Rect(24, 48 + i * 30, 212, 26).collidepoint(p):
                if f in self.chosen: self.chosen.remove(f)
                else: self.chosen.append(f)
                self.invalidate(); self.play("click"); return
        if self.dm.hit(p): self.depth = max(1, self.depth - 1); self.invalidate(); return
        if self.dp.hit(p): self.depth = min(8, self.depth + 1); self.invalidate(); return
        if self.train_btn.hit(p):
            X, y = T.prepare(self.train_df, self.chosen)
            self.model = T.train_tree(X, y, max_depth=self.depth)
            self.names_used = list(self.chosen)
            self.figs["tree"] = V.to_surface(V.tree_figure(self.model, self.names_used, size=(560, 215), fontsize=8))
            self.train_acc = float(self.model.score(X, y))
            self.test_btn.enabled = True; self.play("hint"); return
        if self.test_btn.hit(p) and self.model is not None:
            Xt, yt = T.prepare(self.test_df, self.names_used)
            self.ev = evaluate(self.model, Xt, yt)
            self.figs["cm"] = V.to_surface(V.confusion_figure(self.ev["confusion"], size=(210, 150)))
            self.ok_btn.enabled = True; self.play("hint")
            return
        if self.ok_btn.hit(p) and self.ev:
            ok, msg = self.on_confirm(self.model, self.names_used, self.ev, self.depth)
            self.say(msg, GREEN if ok else RED, 9); self.play("correct" if ok else "wrong")
            if ok: self.finish({"features": list(self.names_used), "depth": self.depth}, 1.8)
            else: self.ctx.mistake()

    def body(self, s, mouse):
        ui.draw_text(s, "Choose features", (24, 32), 12, (150, 165, 190))
        for i, f in enumerate(self.features):
            ui.chip(s, pygame.Rect(24, 48 + i * 30, 212, 26), f.replace("_", " "), f in self.chosen, TEAL, 14)
        ui.draw_text(s, f"Max depth: {self.depth}", (24, 266), 15, CREAM, True)
        self.dm.draw(s, mouse); self.dp.draw(s, mouse)
        for b in (self.train_btn, self.test_btn, self.ok_btn): b.draw(s, mouse)
        if self.model is not None:
            s.blit(self.figs["tree"], (262, 36))
            ui.draw_text(s, f"Training accuracy: {self.train_acc * 100:.1f}%   |   leaves: {self.model.get_n_leaves()}", (262, 254), 14, TEAL, True)
        else:
            ui.draw_text(s, "Pick the clues you trust, set how deep the tree may grow, then train it on the training records. Then see how it does on creatures it has never seen.", (262, 60), 15, (170, 185, 210), width=550)
        if self.ev:
            s.blit(self.figs["cm"], (262, 274))
            ui.draw_text(s, "Unseen accuracy", (500, 284), 14, (150, 165, 190))
            ui.draw_text(s, f"{self.ev['accuracy'] * 100:.1f}%", (500, 306), 34, GOLD, True)
            ui.draw_text(s, f"{self.ev['correct']} / {self.ev['total']} correct", (500, 352), 14, CREAM)
            ui.draw_text(s, f"Needed to challenge the Guardian: {self.min_acc * 100:.0f}%", (500, 380), 12, (150, 165, 190))
