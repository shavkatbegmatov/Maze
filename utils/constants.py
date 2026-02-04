"""
Global constants for Maze Game V3
"""

# Screen settings
CELL_SIZE = 35
FPS = 60
WALL_THICK = 3

# HUD panel height (bigger for more info)
PANEL_H = 100

# Wall bit flags (for maze generation)
TOP = 1
RIGHT = 2
BOTTOM = 4
LEFT = 8

# Direction vectors with wall bits
DIRS = [
    (0, -1, TOP, BOTTOM),    # up
    (1, 0, RIGHT, LEFT),     # right
    (0, 1, BOTTOM, TOP),     # down
    (-1, 0, LEFT, RIGHT),    # left
]

# Direction to bit mapping
DIR_TO_BITS = {
    (0, -1): (TOP, BOTTOM),
    (1, 0): (RIGHT, LEFT),
    (0, 1): (BOTTOM, TOP),
    (-1, 0): (LEFT, RIGHT),
}

# Game states
STATE_MENU = 0
STATE_DIFFICULTY_SELECT = 1
STATE_GENERATING = 2
STATE_PLAYING = 3
STATE_PAUSED = 4
STATE_LEVEL_COMPLETE = 5
STATE_GAME_OVER = 6
STATE_WIN = 7

# Player settings
PLAYER_MOVE_COOLDOWN_MS = 90  # Movement delay
PLAYER_BASE_SPEED = 1.0
PLAYER_MAX_HEALTH = 100
PLAYER_MAX_ENERGY = 100
PLAYER_ENERGY_REGEN_RATE = 5.0  # per second
PLAYER_ENERGY_COST_MOVE = 3

# Enemy settings
ENEMY_UPDATE_RATE = 60  # FPS

# Timing
POWERUP_MIN_DURATION = 8.0
POWERUP_MAX_DURATION = 15.0
TRAP_COOLDOWN = 2.0
INVULNERABILITY_DURATION = 1.0

# Vision
DEFAULT_VISION_RANGE = 8

# Difficulty levels (will be detailed in maze/difficulty.py)
DIFFICULTY_EASY = 0
DIFFICULTY_NORMAL = 1
DIFFICULTY_HARD = 2
DIFFICULTY_EXPERT = 3
DIFFICULTY_NIGHTMARE = 4

DIFFICULTY_NAMES = [
    "EASY",
    "NORMAL",
    "HARD",
    "EXPERT",
    "NIGHTMARE"
]

# Score constants
SCORE_BASE_MULTIPLIER = 1000
SCORE_TIME_BONUS = 10
SCORE_HEALTH_BONUS = 5
SCORE_ENEMY_DODGE_BONUS = 50
SCORE_NO_DAMAGE_BONUS = 500
SCORE_HINT_PENALTY = 100
SCORE_DEATH_PENALTY = 200

# Save file
SAVE_FILE = "saves/savegame.json"
