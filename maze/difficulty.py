"""
Difficulty level configurations for Maze Game V3
Defines 5 difficulty levels with increasing challenge
"""

from utils.constants import (
    DIFFICULTY_EASY, DIFFICULTY_NORMAL, DIFFICULTY_HARD,
    DIFFICULTY_EXPERT, DIFFICULTY_NIGHTMARE
)


class DifficultyConfig:
    """Configuration for a single difficulty level"""
    def __init__(self, **kwargs):
        # Maze dimensions
        self.cols = kwargs.get('cols', 20)
        self.rows = kwargs.get('rows', 15)

        # Enemies
        self.enemy_count = kwargs.get('enemy_count', 0)
        self.patrol_enemies = kwargs.get('patrol_enemies', 0)
        self.chase_enemies = kwargs.get('chase_enemies', 0)
        self.teleport_enemies = kwargs.get('teleport_enemies', 0)
        self.smart_enemies = kwargs.get('smart_enemies', 0)

        # Fog of war
        self.fog_enabled = kwargs.get('fog_enabled', False)
        self.fog_radius = kwargs.get('fog_radius', 8)

        # Time limit (seconds, None = unlimited)
        self.time_limit = kwargs.get('time_limit', None)

        # Traps
        self.trap_count = kwargs.get('trap_count', 0)
        self.trap_types = kwargs.get('trap_types', ['spike'])

        # Keys and doors
        self.key_count = kwargs.get('key_count', 0)
        self.key_colors = kwargs.get('key_colors', [])

        # Moving walls
        self.moving_wall_count = kwargs.get('moving_wall_count', 0)

        # Dynamic walls (walls that change over time)
        self.dynamic_walls = kwargs.get('dynamic_walls', False)
        self.wall_change_interval = kwargs.get('wall_change_interval', 30)  # seconds

        # Boss fight
        self.has_boss = kwargs.get('has_boss', False)

        # Maze generation
        self.braid_chance = kwargs.get('braid_chance', 0.0)  # Loop percentage

        # Power-ups
        self.powerup_count = kwargs.get('powerup_count', 0)
        self.powerup_types = kwargs.get('powerup_types', [])

        # Score multiplier
        self.score_multiplier = kwargs.get('score_multiplier', 1.0)

        # Checkpoints
        self.checkpoint_count = kwargs.get('checkpoint_count', 0)


# ========== DIFFICULTY LEVEL DEFINITIONS ==========

LEVEL_EASY = DifficultyConfig(
    cols=20,
    rows=15,
    enemy_count=0,
    patrol_enemies=0,
    chase_enemies=0,
    teleport_enemies=0,
    smart_enemies=0,
    fog_enabled=False,
    fog_radius=0,
    time_limit=None,  # No time limit
    trap_count=0,
    trap_types=[],
    key_count=0,
    key_colors=[],
    moving_wall_count=0,
    dynamic_walls=False,
    has_boss=False,
    braid_chance=0.0,
    powerup_count=3,
    powerup_types=['speed', 'vision', 'energy'],
    score_multiplier=1.0,
    checkpoint_count=0
)

LEVEL_NORMAL = DifficultyConfig(
    cols=30,
    rows=20,
    enemy_count=2,
    patrol_enemies=2,
    chase_enemies=0,
    teleport_enemies=0,
    smart_enemies=0,
    fog_enabled=True,
    fog_radius=8,
    time_limit=300,  # 5 minutes
    trap_count=3,
    trap_types=['spike'],
    key_count=1,
    key_colors=['red'],
    moving_wall_count=0,
    dynamic_walls=False,
    has_boss=False,
    braid_chance=0.1,  # 10% loops
    powerup_count=5,
    powerup_types=['speed', 'vision', 'energy', 'invincible'],
    score_multiplier=1.5,
    checkpoint_count=1
)

LEVEL_HARD = DifficultyConfig(
    cols=45,
    rows=30,
    enemy_count=4,
    patrol_enemies=2,
    chase_enemies=2,
    teleport_enemies=0,
    smart_enemies=0,
    fog_enabled=True,
    fog_radius=5,
    time_limit=240,  # 4 minutes
    trap_count=8,
    trap_types=['spike', 'slow', 'teleport_trap'],
    key_count=2,
    key_colors=['red', 'blue'],
    moving_wall_count=2,
    dynamic_walls=False,
    has_boss=False,
    braid_chance=0.2,  # 20% loops
    powerup_count=7,
    powerup_types=['speed', 'vision', 'energy', 'invincible', 'teleport'],
    score_multiplier=2.0,
    checkpoint_count=2
)

LEVEL_EXPERT = DifficultyConfig(
    cols=60,
    rows=40,
    enemy_count=8,
    patrol_enemies=3,
    chase_enemies=4,
    teleport_enemies=0,
    smart_enemies=1,
    fog_enabled=True,
    fog_radius=4,
    time_limit=180,  # 3 minutes
    trap_count=15,
    trap_types=['spike', 'slow', 'teleport_trap', 'confusion', 'poison'],
    key_count=3,
    key_colors=['red', 'blue', 'green'],
    moving_wall_count=5,
    dynamic_walls=False,
    has_boss=False,
    braid_chance=0.3,  # 30% loops
    powerup_count=10,
    powerup_types=['speed', 'vision', 'energy', 'invincible', 'teleport', 'xray'],
    score_multiplier=3.0,
    checkpoint_count=3
)

LEVEL_NIGHTMARE = DifficultyConfig(
    cols=80,
    rows=50,
    enemy_count=15,
    patrol_enemies=4,
    chase_enemies=6,
    teleport_enemies=3,
    smart_enemies=2,
    fog_enabled=True,
    fog_radius=3,
    time_limit=150,  # 2.5 minutes
    trap_count=25,
    trap_types=['spike', 'slow', 'teleport_trap', 'confusion', 'poison'],
    key_count=5,
    key_colors=['red', 'blue', 'green', 'yellow', 'purple'],
    moving_wall_count=10,
    dynamic_walls=True,
    wall_change_interval=30,  # Walls change every 30 seconds
    has_boss=True,
    braid_chance=0.4,  # 40% loops
    powerup_count=15,
    powerup_types=['speed', 'vision', 'energy', 'invincible', 'teleport', 'xray'],
    score_multiplier=5.0,
    checkpoint_count=5
)

# Difficulty level mapping
DIFFICULTY_CONFIGS = {
    DIFFICULTY_EASY: LEVEL_EASY,
    DIFFICULTY_NORMAL: LEVEL_NORMAL,
    DIFFICULTY_HARD: LEVEL_HARD,
    DIFFICULTY_EXPERT: LEVEL_EXPERT,
    DIFFICULTY_NIGHTMARE: LEVEL_NIGHTMARE,
}


def get_difficulty_config(difficulty_level):
    """
    Get configuration for a difficulty level

    Args:
        difficulty_level: Integer (0-4) or constant from utils.constants

    Returns:
        DifficultyConfig object
    """
    return DIFFICULTY_CONFIGS.get(difficulty_level, LEVEL_EASY)


def get_screen_size(difficulty_level):
    """
    Calculate screen size needed for a difficulty level

    Returns:
        (width, height) tuple in pixels
    """
    from utils.constants import CELL_SIZE, PANEL_H

    config = get_difficulty_config(difficulty_level)
    width = config.cols * CELL_SIZE
    height = config.rows * CELL_SIZE + PANEL_H

    return width, height


def get_difficulty_name(difficulty_level):
    """Get human-readable name for difficulty level"""
    from utils.constants import DIFFICULTY_NAMES

    if 0 <= difficulty_level < len(DIFFICULTY_NAMES):
        return DIFFICULTY_NAMES[difficulty_level]
    return "UNKNOWN"


def get_difficulty_description(difficulty_level):
    """Get detailed description of difficulty level"""
    config = get_difficulty_config(difficulty_level)
    name = get_difficulty_name(difficulty_level)

    desc = f"{name}\n"
    desc += f"Maze: {config.cols}x{config.rows}\n"
    desc += f"Enemies: {config.enemy_count}\n"

    if config.fog_enabled:
        desc += f"Fog of War: {config.fog_radius} cells\n"
    else:
        desc += "Fog of War: Disabled\n"

    if config.time_limit:
        minutes = config.time_limit // 60
        seconds = config.time_limit % 60
        desc += f"Time Limit: {minutes}:{seconds:02d}\n"
    else:
        desc += "Time Limit: None\n"

    desc += f"Traps: {config.trap_count}\n"
    desc += f"Keys: {config.key_count}\n"

    if config.has_boss:
        desc += "Boss Fight: Yes\n"

    return desc


# ========== ENEMY SPAWN HELPERS ==========

def get_enemy_spawn_positions(config, walls, cols, rows, player_pos, goal_pos):
    """
    Generate safe spawn positions for enemies
    Enemies should not spawn too close to player or goal

    Returns:
        List of (x, y, enemy_type) tuples
    """
    import random
    from maze.maze_core import bfs_shortest_path

    spawns = []
    min_distance_from_player = 10
    min_distance_from_goal = 5

    # Calculate path from player to goal
    path = bfs_shortest_path(walls, cols, rows, player_pos, goal_pos)
    path_cells = set(path) if path else set()

    # Generate candidate positions
    candidates = []
    for y in range(rows):
        for x in range(cols):
            # Skip player and goal positions
            if (x, y) == player_pos or (x, y) == goal_pos:
                continue

            # Skip positions on main path
            if (x, y) in path_cells:
                continue

            # Check distance from player
            dist_player = abs(x - player_pos[0]) + abs(y - player_pos[1])
            if dist_player < min_distance_from_player:
                continue

            # Check distance from goal
            dist_goal = abs(x - goal_pos[0]) + abs(y - goal_pos[1])
            if dist_goal < min_distance_from_goal:
                continue

            candidates.append((x, y))

    if not candidates:
        # Fallback: random positions far from player
        candidates = [
            (x, y) for y in range(rows) for x in range(cols)
            if abs(x - player_pos[0]) + abs(y - player_pos[1]) > min_distance_from_player
        ]

    # Shuffle and select positions
    random.shuffle(candidates)

    # Assign enemy types based on config
    enemy_types = []
    enemy_types.extend(['patrol'] * config.patrol_enemies)
    enemy_types.extend(['chase'] * config.chase_enemies)
    enemy_types.extend(['teleport'] * config.teleport_enemies)
    enemy_types.extend(['smart'] * config.smart_enemies)

    # Create spawn list
    for i, enemy_type in enumerate(enemy_types):
        if i < len(candidates):
            spawns.append((candidates[i][0], candidates[i][1], enemy_type))

    return spawns


# ========== TRAP SPAWN HELPERS ==========

def get_trap_spawn_positions(config, walls, cols, rows, player_pos, goal_pos):
    """
    Generate positions for traps

    Returns:
        List of (x, y, trap_type) tuples
    """
    import random
    from maze.maze_core import bfs_shortest_path

    spawns = []
    min_distance_from_start = 5

    # Calculate main path
    path = bfs_shortest_path(walls, cols, rows, player_pos, goal_pos)
    path_cells = set(path) if path else set()

    # 50% of traps on main path, 50% elsewhere
    path_trap_count = config.trap_count // 2
    off_path_trap_count = config.trap_count - path_trap_count

    # Place traps on path
    if path and len(path) > min_distance_from_start:
        path_candidates = list(path[min_distance_from_start:])
        random.shuffle(path_candidates)

        for i in range(min(path_trap_count, len(path_candidates))):
            x, y = path_candidates[i]
            trap_type = random.choice(config.trap_types)
            spawns.append((x, y, trap_type))

    # Place traps off path
    off_path_candidates = [
        (x, y) for y in range(rows) for x in range(cols)
        if (x, y) not in path_cells and (x, y) != player_pos and (x, y) != goal_pos
    ]
    random.shuffle(off_path_candidates)

    for i in range(min(off_path_trap_count, len(off_path_candidates))):
        x, y = off_path_candidates[i]
        trap_type = random.choice(config.trap_types)
        spawns.append((x, y, trap_type))

    return spawns


# ========== POWERUP SPAWN HELPERS ==========

def get_powerup_spawn_positions(config, walls, cols, rows, player_pos, goal_pos):
    """
    Generate positions for power-ups

    Returns:
        List of (x, y, powerup_type) tuples
    """
    import random

    spawns = []
    min_distance_from_start = 3

    # Generate candidate positions
    candidates = [
        (x, y) for y in range(rows) for x in range(cols)
        if (abs(x - player_pos[0]) + abs(y - player_pos[1]) > min_distance_from_start
            and (x, y) != goal_pos)
    ]

    random.shuffle(candidates)

    # Assign power-up types
    for i in range(min(config.powerup_count, len(candidates))):
        x, y = candidates[i]
        powerup_type = random.choice(config.powerup_types)
        spawns.append((x, y, powerup_type))

    return spawns


# ========== KEY/DOOR SPAWN HELPERS ==========

def get_key_door_positions(config, walls, cols, rows, player_pos, goal_pos):
    """
    Generate positions for keys and corresponding doors

    Returns:
        (keys, doors) tuple of lists [(x, y, color), ...]
    """
    import random
    from maze.maze_core import bfs_shortest_path

    keys = []
    doors = []

    if config.key_count == 0:
        return keys, doors

    # Calculate path
    path = bfs_shortest_path(walls, cols, rows, player_pos, goal_pos)
    if not path or len(path) < 10:
        return keys, doors  # Path too short for keys/doors

    # Divide path into segments for each key-door pair
    segment_size = len(path) // (config.key_count + 1)

    for i, color in enumerate(config.key_colors[:config.key_count]):
        # Door position: on path, in segment
        door_segment_start = (i + 1) * segment_size
        door_segment_end = min(door_segment_start + segment_size // 2, len(path) - 1)

        if door_segment_start < len(path):
            door_pos = path[random.randint(door_segment_start, min(door_segment_end, len(path) - 1))]
            doors.append((door_pos[0], door_pos[1], color))

            # Key position: before door, off path
            key_search_end = door_segment_start
            key_candidates = [
                (x, y) for y in range(rows) for x in range(cols)
                if (x, y) not in path[:door_segment_start + 5]  # Not on path near door
                and abs(x - player_pos[0]) + abs(y - player_pos[1]) > 5
            ]

            if key_candidates:
                random.shuffle(key_candidates)
                key_pos = key_candidates[0]
                keys.append((key_pos[0], key_pos[1], color))

    return keys, doors
