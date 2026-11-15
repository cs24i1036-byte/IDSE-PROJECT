"""Application shell: window, main loop, scene switching with fades."""
from __future__ import annotations

import os

import pygame

from game.audio import Audio
from game.save import SaveData
from game.settings import *  # noqa


class Ctx:
    """Services shared by scenes and panels."""

    def __init__(self, audio, save):
        self.audio, self.save = audio, save
        self.level = None
        self.on_mistake = None

    def mistake(self):
        if self.level is not None:
            self.level.mistakes += 1
        if self.on_mistake:
            self.on_mistake()


class Game:
    def __init__(self, headless: bool = False, save_path=None, fullscreen: bool = False):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption(TITLE)
        dummy = os.environ.get("SDL_VIDEODRIVER") == "dummy"          # headless tests: plain software surface
        flags = 0 if dummy else pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if fullscreen else 0)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        self.clock = pygame.time.Clock()
        self.save = SaveData.load(save_path)
        self.audio = Audio(self.save.volume, self.save.muted)
        self.ctx = Ctx(self.audio, self.save)
        self.scene = None
        self._next = None
        self.fade = 0.0
        self.fade_dir = 0
        self.running = True
        self.time = 0.0

    # ---------------------------------------------------------------- scenes
    def go(self, scene, instant: bool = False):
        if instant or self.scene is None:
            self._set(scene)
        else:
            self._next, self.fade_dir = scene, 1

    def _set(self, scene):
        self.scene = scene
        scene.enter()

    def quit(self):
        self.running = False

    # ---------------------------------------------------------------- loop
    def step(self, events, dt: float):
        """One frame: used by run() and by headless tests."""
        self.time += dt
        for ev in events:
            if ev.type == pygame.QUIT:
                self.running = False
            elif self.fade_dir == 0:
                self.scene.handle(ev)
        self.scene.update(dt)
        if self.fade_dir:
            self.fade += dt * 4.0 * self.fade_dir
            if self.fade_dir > 0 and self.fade >= 1:
                self.fade, self.fade_dir = 1.0, -1
                self._set(self._next); self._next = None
            elif self.fade_dir < 0 and self.fade <= 0:
                self.fade, self.fade_dir = 0.0, 0
        self.scene.draw(self.screen)
        if self.fade > 0:
            f = pygame.Surface((WIDTH, HEIGHT)); f.fill((0, 0, 0)); f.set_alpha(int(255 * min(1.0, self.fade)))
            self.screen.blit(f, (0, 0))

    def run(self, first_scene):
        self.go(first_scene, instant=True)
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 30)
            self.step(pygame.event.get(), dt)
            pygame.display.flip()
        self.save.volume, self.save.muted = self.audio.volume, self.audio.muted
        self.save.save()
        pygame.quit()
