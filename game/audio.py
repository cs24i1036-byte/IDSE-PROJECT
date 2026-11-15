"""Synthesised sound effects and music (no audio files needed). Fails silently without an audio device."""
from __future__ import annotations

import numpy as np
import pygame

SR = 22050


def _env(n: int, a: float = 0.01, r: float = 0.2) -> np.ndarray:
    t = np.ones(n)
    na, nr = max(1, min(n, int(a * SR))), max(1, min(n, int(r * SR)))
    t[:na] = np.linspace(0, 1, na)
    t[-nr:] *= np.linspace(1, 0, nr)
    return t


def _tone(freq, dur, wave="sine", vol=0.4, a=0.005, r=0.15, sweep=None):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.linspace(freq, sweep, n) if sweep else np.full(n, freq)
    ph = 2 * np.pi * np.cumsum(f) / SR
    if wave == "square":
        s = np.sign(np.sin(ph)) * 0.6
    elif wave == "saw":
        s = 2 * ((ph / (2 * np.pi)) % 1) - 1
    elif wave == "tri":
        s = 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1
    else:
        s = np.sin(ph)
    return s * _env(n, a, r) * vol


def _noise(dur, vol=0.3, r=0.2, lowpass=0.0):
    n = int(dur * SR)
    x = np.random.default_rng(3).uniform(-1, 1, n)
    if lowpass:
        k = int(lowpass)
        x = np.convolve(x, np.ones(k) / k, mode="same")
    return x * _env(n, 0.002, r) * vol


def _seq(parts):
    return np.concatenate(parts)


def _mix(*arrs):
    n = max(len(a) for a in arrs)
    out = np.zeros(n)
    for a in arrs:
        out[: len(a)] += a
    return out


def _arp(notes, step=0.09, wave="tri", vol=0.35, tail=0.25):
    parts = [_tone(f, step + (tail if i == len(notes) - 1 else 0), wave, vol, r=0.1) for i, f in enumerate(notes)]
    return _seq(parts)


def _to_sound(arr: np.ndarray) -> pygame.mixer.Sound:
    pcm = (np.clip(arr, -1, 1) * 32000).astype(np.int16)
    if pygame.mixer.get_init() and pygame.mixer.get_init()[2] == 2:
        pcm = np.column_stack([pcm, pcm])
    return pygame.sndarray.make_sound(np.ascontiguousarray(pcm))


def _build_effects() -> dict[str, np.ndarray]:
    return {
        "jump": _tone(300, 0.16, "square", 0.22, sweep=620, r=0.08),
        "land": _noise(0.09, 0.25, 0.08, lowpass=12),
        "gem": _arp([880, 1320], 0.06, "sine", 0.35, 0.1),
        "hurt": _tone(420, 0.3, "saw", 0.3, sweep=110, r=0.2),
        "checkpoint": _arp([523, 659, 784, 1046], 0.08, "tri", 0.35, 0.3),
        "door": _mix(_noise(0.7, 0.3, 0.4, lowpass=30), _tone(90, 0.7, "saw", 0.2, sweep=60, r=0.4)),
        "correct": _arp([523, 659, 784, 1046, 1318], 0.075, "tri", 0.4, 0.35),
        "wrong": _mix(_tone(160, 0.28, "square", 0.28, r=0.12), _tone(151, 0.28, "square", 0.28, r=0.12)),
        "dash": _noise(0.16, 0.25, 0.14, lowpass=4),
        "attack": _mix(_noise(0.14, 0.22, 0.12, lowpass=3), _tone(500, 0.14, "saw", 0.12, sweep=250, r=0.1)),
        "stomp": _mix(_tone(200, 0.12, "square", 0.3, sweep=90, r=0.08), _noise(0.06, 0.2, 0.05)),
        "click": _tone(900, 0.04, "square", 0.18, r=0.03),
        "hint": _arp([988, 1319], 0.07, "sine", 0.3, 0.15),
        "boss_hit": _mix(_noise(0.35, 0.45, 0.3, lowpass=10), _tone(110, 0.4, "saw", 0.35, sweep=40, r=0.3)),
        "boss_roar": _mix(_tone(70, 0.7, "saw", 0.4, sweep=45, r=0.4), _noise(0.7, 0.2, 0.4, lowpass=25)),
        "shoot": _tone(700, 0.18, "square", 0.18, sweep=260, r=0.1),
        "victory": _seq([_arp([523, 659, 784, 1046], 0.11, "tri", 0.4, 0.05), _arp([659, 784, 988, 1318], 0.11, "tri", 0.4, 0.05),
                         _arp([784, 988, 1175, 1568], 0.16, "tri", 0.45, 0.8)]),
        "unlock": _arp([392, 523, 659, 784], 0.09, "sine", 0.35, 0.3),
    }


def _music(theme: str) -> np.ndarray:
    base = {"dungeon": 110.0, "lab": 123.5, "crystal": 98.0, "tree": 87.3, "arena": 82.4, "menu": 110.0, "victory": 130.8}.get(theme, 110.0)
    minor = [1, 6 / 5, 3 / 2, 2]
    bars = 8
    step = 0.5
    n = int(bars * 4 * step * SR)
    out = np.zeros(n)
    pad = _tone(base, bars * 4 * step, "sine", 0.18, a=1.0, r=1.0) + _tone(base * 1.5, bars * 4 * step, "sine", 0.1, a=1.5, r=1.5)
    out[: len(pad)] += pad[:n]
    pattern = [0, 2, 1, 3, 2, 3, 1, 2]
    for i in range(bars * 4):
        note = base * 2 * minor[pattern[i % len(pattern)]] * (1.0 if (i // 8) % 2 == 0 else 5 / 6)
        tone = _tone(note, step * 1.6, "tri", 0.12, a=0.01, r=0.5)
        s = int(i * step * SR)
        out[s:s + len(tone)] += tone[: max(0, n - s)] if s + len(tone) > n else tone
    return out / max(1.0, np.abs(out).max() * 1.2)


class Audio:
    def __init__(self, volume: float = 0.6, muted: bool = False):
        self.ok = False
        self.volume = volume
        self.muted = muted
        self.sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_cache: dict[str, pygame.mixer.Sound] = {}
        self._channel = None
        self._current = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SR, size=-16, channels=2, buffer=512)
            self.ok = True
            for k, arr in _build_effects().items():
                self.sfx[k] = _to_sound(arr)
            pygame.mixer.set_num_channels(12)
            self._apply_volume()
        except (pygame.error, NotImplementedError, OSError):
            self.ok = False

    def _apply_volume(self) -> None:
        if not self.ok:
            return
        v = 0.0 if self.muted else self.volume
        for s in self.sfx.values():
            s.set_volume(min(1.0, v))
        if self._channel is not None:
            self._channel.set_volume(0.0 if self.muted else self.volume * 0.45)

    def play(self, name: str) -> None:
        if self.ok and not self.muted and name in self.sfx:
            self.sfx[name].play()

    def music(self, theme: str | None) -> None:
        if not self.ok or theme == self._current:
            return
        self._current = theme
        if self._channel is not None:
            self._channel.fadeout(400)
        if theme is None:
            return
        if theme not in self._music_cache:
            self._music_cache[theme] = _to_sound(_music(theme))
        self._channel = self._music_cache[theme].play(loops=-1, fade_ms=600)
        if self._channel is not None:
            self._channel.set_volume(0.0 if self.muted else self.volume * 0.45)

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        self._apply_volume()
        return self.muted

    def set_volume(self, v: float) -> None:
        self.volume = max(0.0, min(1.0, v))
        self._apply_volume()
