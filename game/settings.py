"""Global constants: window, physics, palette and key bindings."""
import pygame

TITLE = "INVISIBLE MAZE"
SUBTITLE = "A Decision Tree Classification Adventure"
WIDTH, HEIGHT = 960, 540
FPS = 60
TILE = 32

# ---- palette (from the brief) ----
NAVY = (16, 24, 39)
PANEL = (27, 41, 59)
GOLD = (233, 180, 76)
TEAL = (54, 198, 176)
PURPLE = (128, 90, 213)
CREAM = (245, 235, 213)
GREEN = (72, 184, 121)
RED = (228, 96, 90)
DARK = (10, 14, 24)

# ---- physics (pixels / second) ----
GRAVITY = 1500.0
MAX_FALL = 900.0
RUN_SPEED = 230.0
GROUND_ACCEL = 2600.0
AIR_ACCEL = 1700.0
FRICTION = 2400.0
JUMP_SPEED = 560.0          # apex ~ 104 px = 3.3 tiles
JUMP_CUT = 0.45             # velocity kept when jump released early
COYOTE = 0.09
JUMP_BUFFER = 0.11
DASH_SPEED = 520.0
DASH_TIME = 0.16
DASH_COOLDOWN = 0.55
ATTACK_TIME = 0.24
INVULN_TIME = 1.2
MAX_HEALTH = 5
START_LIVES = 3

# ---- tile ids ----
EMPTY, SOLID, ONEWAY, SPIKE = 0, 1, 2, 3

# ---- XP / badges ----
LEVELS = [
    {"id": 1, "name": "The First Junction", "xp": 100, "badge": "Path Finder", "theme": "dungeon",
     "topic": "Decision Tree structure"},
    {"id": 2, "name": "The Creature Chamber", "xp": 150, "badge": "Creature Classifier", "theme": "lab",
     "topic": "Features, targets and classification"},
    {"id": 3, "name": "The Split Path", "xp": 200, "badge": "Pattern Seeker", "theme": "crystal",
     "topic": "Entropy, Gini impurity, Information Gain"},
    {"id": 4, "name": "The Overgrown Tree", "xp": 250, "badge": "Tree Guardian", "theme": "tree",
     "topic": "Overfitting, depth and pruning"},
    {"id": 5, "name": "The Guardian's Trial", "xp": 300, "badge": "Master Classifier", "theme": "arena",
     "topic": "Training, testing and evaluation"},
]
TOTAL_XP = sum(l["xp"] for l in LEVELS)

KEYS = {
    "left": (pygame.K_a, pygame.K_LEFT),
    "right": (pygame.K_d, pygame.K_RIGHT),
    "jump": (pygame.K_SPACE, pygame.K_w, pygame.K_UP),
    "dash": (pygame.K_LSHIFT, pygame.K_RSHIFT),
    "interact": (pygame.K_e,),
    "attack": (pygame.K_f, pygame.K_k),
    "hint": (pygame.K_h,),
    "pause": (pygame.K_ESCAPE, pygame.K_p),
}
