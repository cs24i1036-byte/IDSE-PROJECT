import importlib


def make_level(level_id: int, seed: int = 1):
    mod = importlib.import_module(f"game.levels.level{level_id}")
    return getattr(mod, f"Level{level_id}")(seed)
