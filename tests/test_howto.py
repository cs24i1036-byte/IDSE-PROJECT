import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from game.app import Game
from game.scenes import GameplayScene, HowToScene, MenuScene, StoryScene, CharacterScene


def test_howto_flow_and_objective(tmp_path):
    g = Game(save_path=tmp_path / "s.json"); g.go(MenuScene(g), instant=True)
    g.go(HowToScene(g), instant=True)
    g.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)], .05)
    for _ in range(10): g.step([], .05)
    assert isinstance(g.scene, MenuScene)
    s = StoryScene(g); g.go(s, instant=True)
    g.step([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)], .05)
    for _ in range(10): g.step([], .05)
    assert isinstance(g.scene, HowToScene)
    gs = GameplayScene(g, 1, fresh=True); g.go(gs, instant=True); gs.dialog = []
    for _ in range(3): g.step([], .05)
    assert gs.objective_target() is not None


def test_level3_altar_requires_checking_all_then_accepts_best(tmp_path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_integration import place
    from ds import impurity as I
    g = Game(save_path=tmp_path / "s.json")
    gs = GameplayScene(g, 3, fresh=True); g.go(gs, instant=True); gs.dialog = []
    t = gs.level.terminals[0]; place(gs, t.rect.centerx, t.rect.bottom)
    gs.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)); g.step([], 1 / 60)
    p = gs.panel; c = lambda b: p.click(b.rect.center)
    c(p.fb[0]); c(p.build_btn)
    assert not p.solved and "every feature" in p.msg and "1 of 3" in p.task_text()
    for f in p.fb: c(f)
    best = I.best_splits(p.df, p.features, "Dangerous", p.criterion)[0]
    wrong = next(f for f in p.fb if f.key != best)
    c(wrong); c(p.build_btn); assert not p.solved and "Not the best" in p.msg
    c(next(f for f in p.fb if f.key == best)); c(p.build_btn); assert p.solved


def test_standing_and_walking_on_built_bridge_does_not_crash(tmp_path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_integration import place
    g = Game(save_path=tmp_path / "s.json")
    gs = GameplayScene(g, 3, fresh=True); g.go(gs, instant=True); gs.dialog = []
    gs.level.solve(0, True, True)
    br = gs.level.bridges[0]
    place(gs, br.rect.centerx, br.rect.top - 40)
    for _ in range(120): g.step([], 1 / 60)                      # fall onto the bridge and stand on it
    assert gs.player.platform is br and gs.player.on_ground
    right = {pygame.K_d: True}
    for _ in range(60): g.step([], 1 / 60)
