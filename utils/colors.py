"""
Color palette for Maze Game V3
"""

# Background colors
COLOR_BG = (20, 22, 28)           # Main background
COLOR_MAZE_BG = (16, 18, 24)      # Maze area background
COLOR_PANEL_BG = (12, 14, 18)     # Panel background

# UI colors
COLOR_WALL = (230, 230, 230)      # Maze walls
COLOR_TEXT = (210, 210, 210)      # Normal text
COLOR_TEXT_HIGHLIGHT = (255, 230, 160)  # Highlighted text
COLOR_TEXT_DIM = (150, 150, 150)  # Dimmed text

# Entity colors
COLOR_PLAYER = (70, 140, 255)     # Player
COLOR_PLAYER_TRAIL = (160, 230, 255)  # Player trail
COLOR_GOAL = (60, 200, 120)       # Goal/Exit

# Enemy colors
COLOR_ENEMY_PATROL = (255, 100, 100)    # Patrol enemy
COLOR_ENEMY_CHASE = (255, 50, 50)       # Chase enemy
COLOR_ENEMY_TELEPORT = (200, 50, 200)   # Teleport enemy
COLOR_ENEMY_SMART = (255, 120, 0)       # Smart enemy

# Key colors (6 colors)
COLOR_KEY_RED = (255, 80, 80)
COLOR_KEY_BLUE = (80, 120, 255)
COLOR_KEY_GREEN = (80, 255, 120)
COLOR_KEY_YELLOW = (255, 220, 80)
COLOR_KEY_PURPLE = (200, 80, 255)
COLOR_KEY_CYAN = (80, 220, 255)

# Door colors (matching keys)
COLOR_DOOR_RED = (200, 60, 60)
COLOR_DOOR_BLUE = (60, 100, 200)
COLOR_DOOR_GREEN = (60, 200, 100)
COLOR_DOOR_YELLOW = (200, 180, 60)
COLOR_DOOR_PURPLE = (160, 60, 200)
COLOR_DOOR_CYAN = (60, 180, 200)

# Power-up colors
COLOR_POWERUP_SPEED = (100, 255, 100)       # Speed boost
COLOR_POWERUP_VISION = (100, 200, 255)      # Vision boost
COLOR_POWERUP_INVINCIBLE = (255, 215, 0)    # Invincibility
COLOR_POWERUP_TELEPORT = (255, 100, 255)    # Teleport
COLOR_POWERUP_ENERGY = (100, 255, 200)      # Energy restore
COLOR_POWERUP_XRAY = (200, 200, 255)        # Wall X-ray

# Trap colors
COLOR_TRAP_SPIKE = (180, 50, 50)           # Spike trap
COLOR_TRAP_TELEPORT = (150, 50, 150)       # Teleport trap (invisible when not triggered)
COLOR_TRAP_SLOW = (100, 100, 200)          # Slow trap
COLOR_TRAP_CONFUSION = (200, 150, 50)      # Confusion trap
COLOR_TRAP_POISON = (100, 200, 50)         # Poison trap

# Effect colors
COLOR_HEALTH_BAR_BG = (60, 60, 60)         # Health bar background
COLOR_HEALTH_BAR_FULL = (80, 220, 120)     # Health bar full
COLOR_HEALTH_BAR_LOW = (220, 80, 80)       # Health bar low
COLOR_ENERGY_BAR = (100, 180, 255)         # Energy bar

# Path/hint colors
COLOR_HINT_PATH = (230, 210, 80)           # Hint path
COLOR_WIN_PATH = (255, 170, 90)            # Win path
COLOR_VISITED_CELL = (28, 32, 40)          # Visited during generation

# Fog of war
COLOR_FOG = (10, 12, 16)                   # Fog overlay
COLOR_FOG_GRADIENT_START = (10, 12, 16, 230)  # Fog gradient start
COLOR_FOG_GRADIENT_END = (10, 12, 16, 0)      # Fog gradient end

# Particle effects
COLOR_PARTICLE_PLAYER = (120, 180, 255)
COLOR_PARTICLE_ENEMY = (255, 100, 100)
COLOR_PARTICLE_POWERUP = (255, 220, 100)
COLOR_PARTICLE_EXPLOSION = (255, 150, 50)

# Menu colors
COLOR_MENU_OVERLAY = (10, 12, 16, 200)     # Menu overlay (with alpha)
COLOR_MENU_SELECTION = (255, 220, 120)     # Selected menu item
COLOR_MENU_BORDER = (255, 220, 120)        # Selection border

# Key-color mapping for easy access
KEY_COLORS = {
    'red': COLOR_KEY_RED,
    'blue': COLOR_KEY_BLUE,
    'green': COLOR_KEY_GREEN,
    'yellow': COLOR_KEY_YELLOW,
    'purple': COLOR_KEY_PURPLE,
    'cyan': COLOR_KEY_CYAN,
}

DOOR_COLORS = {
    'red': COLOR_DOOR_RED,
    'blue': COLOR_DOOR_BLUE,
    'green': COLOR_DOOR_GREEN,
    'yellow': COLOR_DOOR_YELLOW,
    'purple': COLOR_DOOR_PURPLE,
    'cyan': COLOR_DOOR_CYAN,
}
