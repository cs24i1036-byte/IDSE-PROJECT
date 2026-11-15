"""Persistent game state stored as JSON (atomic write, corruption-safe)."""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from game.settings import LEVELS

SAVE_VERSION = 1


def default_path() -> Path:
    env = os.environ.get("INVISIBLE_MAZE_SAVE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "saves" / "save.json"


@dataclass
class SaveData:
    version: int = SAVE_VERSION
    xp: int = 0
    completed: list = field(default_factory=list)          # level ids
    unlocked: int = 1                                      # highest unlocked level id
    badges: list = field(default_factory=list)
    gems: dict = field(default_factory=dict)               # level id (str) -> best gems collected
    concepts: list = field(default_factory=list)
    progress: dict = field(default_factory=dict)           # level id (str) -> {"checkpoint": i, "state": {...}}
    deaths: int = 0
    intro_seen: bool = False
    volume: float = 0.6
    muted: bool = False

    # ---- derived ----
    @property
    def total_gems(self) -> int:
        return int(sum(self.gems.values()))

    def has_progress(self) -> bool:
        return bool(self.completed or self.progress or self.intro_seen)

    def is_completed(self, level_id: int) -> bool:
        return level_id in self.completed

    def is_unlocked(self, level_id: int) -> bool:
        return level_id <= self.unlocked

    # ---- mutation (rewards are granted once) ----
    def complete_level(self, level_id: int, gems: int, concepts: list[str]) -> bool:
        """Mark a level done. Returns True if rewards were granted now (first completion)."""
        info = next(l for l in LEVELS if l["id"] == level_id)
        key = str(level_id)
        self.gems[key] = max(self.gems.get(key, 0), int(gems))
        self.progress.pop(key, None)
        first = level_id not in self.completed
        if first:
            self.completed.append(level_id)
            self.xp += info["xp"]
            if info["badge"] not in self.badges:
                self.badges.append(info["badge"])
            for c in concepts:
                if c not in self.concepts:
                    self.concepts.append(c)
            self.unlocked = max(self.unlocked, min(level_id + 1, len(LEVELS)))
        self.save()
        return first

    def set_checkpoint(self, level_id: int, index: int, state: dict) -> None:
        self.progress[str(level_id)] = {"checkpoint": int(index), "state": state}
        self.save()

    # ---- persistence ----
    _path: Path = field(default_factory=default_path, repr=False, compare=False)

    def save(self) -> bool:
        data = {k: v for k, v in asdict(self).items() if k != "_path"}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp, self._path)
            return True
        except OSError:
            return False

    @classmethod
    def load(cls, path: Path | None = None) -> "SaveData":
        path = Path(path) if path else default_path()
        sd = cls(_path=path)
        if not path.exists():
            return sd
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for k, v in raw.items():
                if k in sd.__dataclass_fields__ and k != "_path":
                    setattr(sd, k, v)
            sd.unlocked = max(1, min(int(sd.unlocked), len(LEVELS)))
            sd.completed = [int(i) for i in sd.completed if 1 <= int(i) <= len(LEVELS)]
            for i in sd.completed:                       # completed levels always unlock the next one
                sd.unlocked = max(sd.unlocked, min(i + 1, len(LEVELS)))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            try:                                         # keep the broken file for inspection, start fresh
                shutil.copy(path, path.with_suffix(".broken"))
            except OSError:
                pass
            sd = cls(_path=path)
        return sd

    def reset(self) -> None:
        fresh = SaveData(_path=self._path)
        fresh.volume, fresh.muted = self.volume, self.muted
        self.__dict__.update(fresh.__dict__)
        self.save()
