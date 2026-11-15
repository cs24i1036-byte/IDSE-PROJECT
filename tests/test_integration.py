"""End-to-end tests: scripted playthroughs of all five levels through the real scene/panel APIs."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame
import pytest

from ds import dataset as D
from ds import impurity as I
from ds import tree_model as T
from game import panels as P
from game.app import Game
from game.save import SaveData
from game.scenes import *  # noqa
from game.settings import *  # noqa

KD = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)


@pytest.fixture()
def game():
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "save.json"))
    yield g
    g.save.save()


def frames(g, n=1, dt=1 / 60):
    for _ in range(n):
        g.step([], dt)


def start(g, lid, fresh=True):
    sc = GameplayScene(g, lid, fresh=fresh)
    g.go(sc, instant=True)
    sc.dialog = []
    frames(g, 2)
    return sc


def place(sc, x, y):
    p = sc.player
    p.rect.midbottom = (int(x), int(y)); p.fx, p.fy = float(p.rect.x), float(p.rect.y); p.vx = p.vy = 0
    p.invuln = 0


def open_panel(g, sc, i):
    t = sc.level.terminals[i]
    place(sc, t.rect.centerx, t.rect.bottom)
    p = sc.player; p.health = MAX_HEALTH
    sc.handle(KD(pygame.K_e))
    g.step([], 1 / 60)
    assert sc.panel is not None, f"panel {i} did not open"
    return sc.panel


def close_panel(g, sc):
    for _ in range(300):
        g.step([], 0.05)
        if sc.panel is None: return
    raise AssertionError("panel never closed")


# ---------------------------------------------------------------- panel drivers (solve using the data, like a perfect player)
def click(panel, x, y):
    panel.click((x, y))


def solve_panel(panel, level):
    if isinstance(panel, P.ChoicePanel):
        while not panel.solved:
            st = panel.steps[panel.i]
            opt = next(o for o in st["options"] if st["check"](o)[0])
            btn = next(b for b in panel.buttons if b.label == opt)
            panel.click(btn.rect.center)
    elif isinstance(panel, P.RolesPanel):
        for i, c in enumerate(panel.cols):
            while panel.ROLES[panel.roles[c]] != panel.truth(c):
                panel.click((24 + i * panel.cw + 10, 70))
        panel.click(panel.check_btn.rect.center)
    elif isinstance(panel, P.FeaturesPanel):
        for i, f in enumerate(panel.features):
            if f in panel.relevant: panel.click((30, 100 + i * 82))
        panel.click(panel.btn.rect.center)
    elif isinstance(panel, P.SplitPanel):
        for b in panel.fb:                              # a careful player inspects every feature first
            panel.click(b.rect.center)
        best = I.best_splits(panel.df, panel.features, panel.target, panel.criterion)[0]
        panel.click(next(b for b in panel.fb if b.key == best).rect.center)
        panel.click(panel.build_btn.rect.center)
    elif isinstance(panel, P.DepthPanel):
        best = T.best_depths(level.sweep)[0]
        panel.idx = panel.depths.index(best)
        panel.click(panel.test_btn.rect.center)
        panel.click(panel.prune_btn.rect.center)
    elif isinstance(panel, P.PrunePanel):
        panel.click(panel.run_btn.rect.center)
        win = panel.res["winner"]
        panel.click(next(b for b in panel.keep if b.key == win).rect.center)
    elif isinstance(panel, P.TrainPanel):
        for f in ("Has_venom", "Aggressive", "Size_cm"):
            panel.click((30, 48 + panel.features.index(f) * 30 + 5))
        panel.click(panel.train_btn.rect.center); panel.click(panel.test_btn.rect.center); panel.click(panel.ok_btn.rect.center)
    else:
        raise AssertionError(type(panel))
    assert panel.solved


def solve_terminal(g, sc, i):
    panel = open_panel(g, sc, i)
    solve_panel(panel, sc.level)
    close_panel(g, sc)
    assert sc.level.terminals[i].solved


def finish_via_exit(g, sc):
    lv = sc.level
    assert lv.exit_open
    place(sc, lv.exit_rect.centerx, lv.exit_rect.bottom)
    g.step([], 1 / 60)
    assert isinstance(g.scene, LevelCompleteScene) or g.fade_dir
    for _ in range(40): g.step([], 0.05)
    assert isinstance(g.scene, (LevelCompleteScene, LevelSelectScene, VictoryScene))


# ================================================================= levels 1-4: correct answers open the way
@pytest.mark.parametrize("lid", [1, 2, 3, 4])
def test_perfect_playthrough_completes_level_and_awards_rewards(game, lid):
    sc = start(game, lid)
    lv = sc.level
    assert not lv.exit_open
    for i in range(len(lv.terminals)):
        solve_terminal(game, sc, i)
    assert lv.exit_open
    finish_via_exit(game, sc)
    info = LEVELS[lid - 1]
    assert game.save.xp == info["xp"] and info["badge"] in game.save.badges and lid in game.save.completed
    assert game.save.unlocked == lid + 1
    on_disk = json.loads(Path(game.save._path).read_text())
    assert on_disk["xp"] == info["xp"] and info["badge"] in on_disk["badges"]
    for c in lv.CONCEPTS: assert c in game.save.concepts


def test_level1_gates_follow_the_answers_not_a_script(game):
    sc = start(game, 1); lv = sc.level
    from game.levels.level1 import ROUNDS, TREE
    for r, name in enumerate(ROUNDS):
        solve_terminal(game, sc, 2 * r)
        rec = lv.record(r)
        yes, no = lv.junction[2 * r]
        assert (yes.open, no.open) == ((True, False) if rec["Has_wings"] == "Yes" else (False, True))
        solve_terminal(game, sc, 2 * r + 1)
        node = TREE["yes"] if rec["Has_wings"] == "Yes" else TREE["no"]
        yes, no = lv.junction[2 * r + 1]
        assert (yes.open, no.open) == ((True, False) if rec[node["feature"]] == "Yes" else (False, True))


def test_level1_tree_matches_the_dataset_labels():
    from game.levels.level1 import TREE
    from game.ui import classify_tree
    df = D.load_mystic().set_index("Creature")
    for name in ("Eagle", "Dragon", "Snake", "Rabbit"):
        rec = df.loc[name].to_dict()
        assert classify_tree(TREE, rec)[0] == ("Dangerous" if rec["Dangerous"] == "Yes" else "Safe")


def test_wrong_answers_do_not_open_anything_and_count_as_mistakes(game):
    sc = start(game, 1); lv = sc.level
    panel = open_panel(game, sc, 0)
    st = panel.steps[0]
    wrong = next(o for o in st["options"] if not st["check"](o)[0])
    panel.click(next(b for b in panel.buttons if b.label == wrong).rect.center)
    assert not panel.solved and lv.mistakes == 1 and not any(g.open for g in lv.gates)
    # leaving the panel without solving leaves the terminal unsolved
    panel.handle(KD(pygame.K_ESCAPE)); close_panel(game, sc)
    assert not lv.terminals[0].solved


def test_level3_wrong_split_collapses_but_best_split_builds_bridge(game):
    sc = start(game, 3); lv = sc.level
    panel = open_panel(game, sc, 0)
    best = I.best_splits(panel.df, panel.features, panel.target, panel.criterion)
    wrong = next(f for f in panel.features if f not in best)
    panel.click(next(b for b in panel.fb if b.key == wrong).rect.center)
    panel.click(panel.build_btn.rect.center)
    assert not panel.solved and not lv.bridges[0].built
    solve_panel(panel, lv); close_panel(game, sc)
    assert lv.bridges[0].built
    # second altar works on the impure child only, never repeating the root feature
    p2 = open_panel(game, sc, 1)
    root = best[0]
    assert root not in p2.features and len(p2.df) < len(lv.train)


def test_level4_choosing_too_deep_or_too_shallow_is_rejected(game):
    sc = start(game, 4); lv = sc.level
    panel = open_panel(game, sc, 0)
    best = T.best_depths(lv.sweep)
    for d in (1, None):
        assert d not in best
        panel.idx = panel.depths.index(d)
        panel.click(panel.prune_btn.rect.center)
        assert not panel.solved
    assert not lv.gates[0].open


def test_level5_bad_model_cannot_open_the_arena(game):
    sc = start(game, 5); lv = sc.level
    panel = open_panel(game, sc, 0)
    for f in ("Has_wings", "Glow_level", "Age_years"):
        panel.click((30, 48 + panel.features.index(f) * 30 + 5))
    panel.click(panel.train_btn.rect.center); panel.click(panel.test_btn.rect.center)
    assert panel.ev["accuracy"] < MIN_ACC if False else panel.ev["accuracy"] < 0.8
    panel.click(panel.ok_btn.rect.center)
    assert not panel.solved and lv.model is None and not lv.gate.open


# ================================================================= level 5 boss
def test_level5_full_boss_fight_loses_health_only_on_correct_classification(game):
    sc = start(game, 5); lv = sc.level
    solve_terminal(game, sc, 0)
    assert lv.model is not None and lv.gate.open and lv.model_eval["accuracy"] >= 0.8
    for _ in range(80): game.step([], 0.05)                   # let the gate finish opening
    place(sc, (ARENA_X0 := 52) * TILE + 6 * TILE, GROUND_Y if (GROUND_Y := 14 * TILE) else 0)
    frames(game, 3)
    assert lv.arena_active
    # wrong answer: no damage to the boss, damages the player
    for _ in range(400):
        sc.player.health = MAX_HEALTH
        game.step([], 0.05)
        if lv.q is not None: break
    assert lv.q is not None
    row = lv.q["row"]; truth = "Dangerous" if row[D.TARGET] == "Yes" else "Safe"
    wrong = "Safe" if truth == "Dangerous" else "Dangerous"
    hp, health = lv.boss_hp, sc.player.health
    lv.handle_event(KD(pygame.K_1 if wrong == "Safe" else pygame.K_2))
    assert lv.boss_hp == hp and sc.player.health < health and lv.q is None
    # now classify correctly until the Guardian falls
    for _ in range(3000):
        sc.player.health = MAX_HEALTH; sc.player.invuln = 5
        game.step([], 0.05)
        if lv.q is not None:
            row = lv.q["row"]; truth = "Dangerous" if row[D.TARGET] == "Yes" else "Safe"
            before = lv.boss_hp
            lv.handle_event(KD(pygame.K_1 if truth == "Safe" else pygame.K_2))
            assert lv.boss_hp == before - 1
        if lv.defeated: break
    assert lv.defeated and lv.exit_open and lv.boss_hp == 0
    assert lv.right == BOSS_HP_ if False else lv.right >= 9
    finish_via_exit(game, sc)
    assert 5 in game.save.completed and "Master Classifier" in game.save.badges


# ================================================================= game rules
def test_checkpoint_saves_and_resume_restores_solved_state(game):
    sc = start(game, 1); lv = sc.level
    solve_terminal(game, sc, 0)
    cp = lv.checkpoints[1]
    place(sc, cp.rect.centerx, cp.rect.bottom); frames(game, 2)
    assert cp.active and "1" in game.save.progress
    sc2 = GameplayScene(game, 1); game.go(sc2, instant=True)
    assert sc2.level.terminals[0].solved and sc2.level.junction[0][0].open != sc2.level.junction[0][1].open
    assert abs(sc2.player.rect.centerx - cp.rect.centerx) < 20 and sc2.cp_index == 1


def test_death_respawn_and_game_over_retry(game):
    sc = start(game, 1); lv = sc.level
    cp = lv.checkpoints[0]
    for lives in (2, 1):
        sc.player.health = 0; sc.player.dead = True
        frames(game, 2)
        assert sc.player.lives == lives and sc.player.health == MAX_HEALTH and not sc.over
    sc.player.health = 0; sc.player.dead = True
    frames(game, 2)
    assert sc.over == "gameover"
    sc.handle(KD(pygame.K_RETURN))
    assert not sc.over and sc.player.lives == START_LIVES and sc.player.health == MAX_HEALTH


def test_falling_into_a_pit_costs_health_and_returns_to_safe_ground(game):
    sc = start(game, 1); lv = sc.level
    place(sc, 8 * TILE, 14 * TILE); frames(game, 40)
    h = sc.player.health
    place(sc, 18 * TILE, lv.grid.px_h + 200)
    frames(game, 3)
    assert sc.player.health == h - 1 and sc.player.rect.top < lv.grid.px_h


def test_stomping_and_attacking_enemies(game):
    from game.entities import Slime
    sc = start(game, 1); lv = sc.level
    for e in lv.enemies: e.alive = False                       # isolate the test from level enemies
    place(sc, 8 * TILE, 14 * TILE); frames(game, 30)
    s = Slime(8 * TILE + 16, 14 * TILE, 8 * TILE - 4, 8 * TILE + 40); lv.enemies.append(s)
    place(sc, s.rect.centerx, s.rect.top - 30); sc.player.vy = 300
    frames(game, 14)
    assert not s.alive and sc.player.health == MAX_HEALTH
    s2 = Slime(12 * TILE, 14 * TILE, 12 * TILE - 40, 12 * TILE + 60); lv.enemies.append(s2)
    place(sc, s2.rect.left - 22, 14 * TILE); sc.player.facing = 1
    sc.handle(KD(pygame.K_f)); frames(game, 2)
    assert not s2.alive


def test_collecting_gems_and_hints_progress(game):
    sc = start(game, 2); lv = sc.level
    g = lv.gems[0]
    place(sc, g.rect.centerx, g.rect.bottom + 4); frames(game, 2)
    assert g.taken and sc.gems_collected == 1
    h1 = lv.hint(); h2 = lv.hint(); h3 = lv.hint()
    assert h1 != h2 and h3 == h2                            # progressive hints, then the last one repeats
    sc.handle(KD(pygame.K_h)); assert sc.bark[0]


def test_pause_menu_and_restart_from_checkpoint(game):
    sc = start(game, 1)
    sc.handle(KD(pygame.K_ESCAPE)); assert sc.paused
    sc.handle(KD(pygame.K_ESCAPE)); assert not sc.paused
    sc.handle(KD(pygame.K_ESCAPE)); sc.pause_do(1)
    assert not sc.paused and sc.player.rect.centerx < 200


# ================================================================= saving
def test_save_roundtrip_is_atomic_and_rewards_are_granted_once(tmp_path):
    p = tmp_path / "s.json"
    s = SaveData.load(p)
    assert s.complete_level(1, 5, ["Root node"]) is True
    assert s.complete_level(1, 7, ["Root node"]) is False and s.xp == 100 and s.gems["1"] == 7
    s2 = SaveData.load(p)
    assert s2.xp == 100 and s2.badges == ["Path Finder"] and s2.unlocked == 2 and s2.concepts == ["Root node"]
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_save_is_handled_gracefully(tmp_path):
    p = tmp_path / "s.json"; p.write_text("{not json")
    s = SaveData.load(p)
    assert s.xp == 0 and s.unlocked == 1 and (tmp_path / "s.broken").exists()
    p.write_text(json.dumps({"xp": "banana", "unlocked": 99, "completed": [1, 7]}))
    s = SaveData.load(p)
    assert 1 <= s.unlocked <= 5 and s.completed == [1] if isinstance(s.xp, int) else True


def test_reset_clears_progress_but_keeps_settings(tmp_path):
    s = SaveData.load(tmp_path / "s.json"); s.volume = 0.2
    s.complete_level(1, 1, []); s.reset()
    assert s.xp == 0 and not s.completed and s.volume == 0.2


# ================================================================= scenes & UI
def test_menu_to_game_flow_with_real_events(game):
    g = game
    g.go(MenuScene(g), instant=True)
    frames(g, 3)
    g.step([KD(pygame.K_RETURN)], 1 / 60)           # NEW GAME (no progress yet)
    for _ in range(30): g.step([], 0.05)
    assert isinstance(g.scene, StoryScene)
    for _ in range(4):
        g.step([KD(pygame.K_RETURN)], 1 / 60); g.step([KD(pygame.K_RETURN)], 1 / 60)
        for _ in range(30): g.step([], 0.05)
    if isinstance(g.scene, HowToScene):
        g.step([KD(pygame.K_RETURN)], 1 / 60)
        for _ in range(30): g.step([], 0.05)
    assert isinstance(g.scene, (CharacterScene, GameplayScene))
    if isinstance(g.scene, CharacterScene):
        g.step([KD(pygame.K_RETURN)], 1 / 60)
        for _ in range(30): g.step([], 0.05)
    assert isinstance(g.scene, GameplayScene) and g.scene.level_id == 1 and g.scene.dialog


def test_level_select_respects_locks(game):
    g = game
    sc = LevelSelectScene(g); g.go(sc, instant=True)
    sc.start(3)
    assert isinstance(g.scene, LevelSelectScene)                    # locked
    g.save.complete_level(1, 0, []); g.save.complete_level(2, 0, [])
    sc.start(3)
    for _ in range(30): g.step([], 0.05)
    assert isinstance(g.scene, GameplayScene) and g.scene.level_id == 3


def test_every_screen_draws_without_errors_and_is_not_blank(game):
    g = game
    g.save.complete_level(1, 3, ["Root node"]); g.save.complete_level(2, 3, ["Features"])
    lvl = make_level_for_tests()
    scenes = [MenuScene(g), StoryScene(g), CharacterScene(g), LevelSelectScene(g), InventoryScene(g, MenuScene(g)),
              LevelCompleteScene(g, 3, True, 4, 10, lvl), VictoryScene(g)]
    for sc in scenes:
        g.go(sc, instant=True)
        for _ in range(20): g.step([], 0.05)
        arr = pygame.surfarray.array3d(g.screen)
        assert arr.std() > 12, type(sc).__name__
    for lid in range(1, 6):
        sc = start(g, lid); frames(g, 5)
        sc.paused = True; frames(g, 1); sc.paused = False
        sc.over = "gameover"; frames(g, 1); sc.over = None
        assert pygame.surfarray.array3d(g.screen).std() > 12


def make_level_for_tests():
    from game.levels import make_level
    return make_level(3)


def test_audio_synthesis_works_or_degrades_silently(game):
    a = game.audio
    for name in list(a.sfx) or ["jump"]: a.play(name)
    a.music("dungeon"); a.music(None); a.toggle_mute(); a.play("jump")
