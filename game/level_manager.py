"""
Level Manager - handles maze generation, entity spawning, and level progression
"""

import random
from maze.generator import GEN_ALGOS
from maze.maze_core import braid_maze
from maze.difficulty import (
    get_difficulty_config,
    get_enemy_spawn_positions,
    get_trap_spawn_positions,
    get_powerup_spawn_positions,
    get_key_door_positions
)
from entities.player import Player
from entities.enemy import EnemyManager
from entities.powerup import PowerUpManager
from entities.trap import TrapManager
from entities.door import DoorManager


class Level:
    """
    Represents a single level/maze
    """
    def __init__(self, difficulty_level, generator_index=0):
        """
        Args:
            difficulty_level: Difficulty level (0-4)
            generator_index: Maze generator algorithm index
        """
        self.difficulty_level = difficulty_level
        self.config = get_difficulty_config(difficulty_level)
        self.generator_index = generator_index

        # Maze data
        self.walls = None
        self.cols = self.config.cols
        self.rows = self.config.rows

        # Positions
        self.start_pos = (0, 0)
        self.goal_pos = (self.cols - 1, self.rows - 1)

        # Entities
        self.player = None
        self.enemy_manager = EnemyManager()
        self.powerup_manager = PowerUpManager()
        self.trap_manager = TrapManager()
        self.door_manager = DoorManager()

        # Level state
        self.time_elapsed = 0.0
        self.time_limit = self.config.time_limit
        self.completed = False

        # Generation state
        self.generating = False
        self.generation_complete = False

    def generate_maze(self, animated=False):
        """
        Generate maze using selected algorithm

        Args:
            animated: If True, returns generator for animated generation

        Returns:
            Generator if animated=True, None otherwise
        """
        gen_name, gen_func = GEN_ALGOS[self.generator_index]
        gen = gen_func(self.cols, self.rows)

        if animated:
            self.generating = True
            return gen
        else:
            # Generate instantly
            last_state = None
            for state in gen:
                last_state = state

            self.walls = last_state['walls']
            self._apply_braiding()
            self._spawn_entities()
            self.generation_complete = True
            return None

    def finalize_generation(self, walls):
        """
        Finalize maze after animated generation completes

        Args:
            walls: Generated wall data
        """
        self.walls = walls
        self._apply_braiding()
        self._spawn_entities()
        self.generation_complete = True
        self.generating = False

    def _apply_braiding(self):
        """Apply braiding (add loops) to maze"""
        if self.config.braid_chance > 0:
            braid_maze(self.walls, self.cols, self.rows, self.config.braid_chance)

    def _spawn_entities(self):
        """Spawn all entities in the maze"""
        # Create player
        self.player = Player(self.start_pos[0], self.start_pos[1])

        # Spawn enemies
        enemy_spawns = get_enemy_spawn_positions(
            self.config, self.walls, self.cols, self.rows,
            self.start_pos, self.goal_pos
        )
        for x, y, enemy_type in enemy_spawns:
            self.enemy_manager.add_enemy(x, y, enemy_type)

        # Spawn traps
        trap_spawns = get_trap_spawn_positions(
            self.config, self.walls, self.cols, self.rows,
            self.start_pos, self.goal_pos
        )
        for x, y, trap_type in trap_spawns:
            self.trap_manager.add_trap(x, y, trap_type)

        # Spawn power-ups
        powerup_spawns = get_powerup_spawn_positions(
            self.config, self.walls, self.cols, self.rows,
            self.start_pos, self.goal_pos
        )
        for x, y, powerup_type in powerup_spawns:
            self.powerup_manager.add_powerup(x, y, powerup_type)

        # Spawn keys and doors
        keys, doors = get_key_door_positions(
            self.config, self.walls, self.cols, self.rows,
            self.start_pos, self.goal_pos
        )
        for x, y, color in keys:
            self.door_manager.add_key(x, y, color)
        for x, y, color in doors:
            self.door_manager.add_door(x, y, color)

    def update(self, dt):
        """
        Update level state

        Args:
            dt: Delta time in seconds
        """
        if not self.generation_complete or self.completed:
            return

        # Update time
        self.time_elapsed += dt

        # Check time limit
        if self.time_limit and self.time_elapsed >= self.time_limit:
            # Time's up! Player loses
            return True  # Signal game over

        # Update entities
        self.player.update(dt)
        self.enemy_manager.update(dt, self.walls, self.cols, self.rows, self.player)
        self.powerup_manager.update(dt)
        self.trap_manager.update(dt)
        self.door_manager.update(dt)

        # Check win condition
        if self.player.x == self.goal_pos[0] and self.player.y == self.goal_pos[1]:
            self.completed = True
            return True  # Signal level complete

        return False

    def get_time_remaining(self):
        """Get remaining time in seconds"""
        if self.time_limit is None:
            return None
        remaining = self.time_limit - self.time_elapsed
        return max(0, remaining)

    def reset(self):
        """Reset level to initial state"""
        self.time_elapsed = 0.0
        self.completed = False

        # Reset entities
        if self.player:
            self.player.reset_position(self.start_pos[0], self.start_pos[1])
        self.enemy_manager.reset()
        self.powerup_manager.reset()
        self.trap_manager.reset()
        self.door_manager.reset()

    def __repr__(self):
        return f"Level(difficulty={self.difficulty_level}, size={self.cols}x{self.rows})"


class LevelManager:
    """
    Manages level progression and state
    """
    def __init__(self):
        self.current_level = None
        self.difficulty_level = 0
        self.generator_index = 0
        self.high_scores = {}  # {difficulty_level: score}

    def create_level(self, difficulty_level, generator_index=0, animated=False):
        """
        Create a new level

        Args:
            difficulty_level: Difficulty (0-4)
            generator_index: Maze generator to use
            animated: Whether to use animated generation

        Returns:
            Level object or (Level, generator) if animated
        """
        self.difficulty_level = difficulty_level
        self.generator_index = generator_index

        level = Level(difficulty_level, generator_index)

        if animated:
            gen = level.generate_maze(animated=True)
            self.current_level = level
            return level, gen
        else:
            level.generate_maze(animated=False)
            self.current_level = level
            return level

    def update_current_level(self, dt):
        """
        Update current level

        Returns:
            'continue', 'complete', 'game_over', or 'time_up'
        """
        if not self.current_level:
            return 'continue'

        result = self.current_level.update(dt)

        if result:
            if self.current_level.completed:
                return 'complete'
            elif not self.current_level.player.is_alive():
                return 'game_over'
            elif self.current_level.get_time_remaining() == 0:
                return 'time_up'

        return 'continue'

    def reset_current_level(self):
        """Reset current level"""
        if self.current_level:
            self.current_level.reset()

    def get_current_level(self):
        """Get current level"""
        return self.current_level

    def record_score(self, difficulty_level, score):
        """Record high score for difficulty level"""
        if difficulty_level not in self.high_scores:
            self.high_scores[difficulty_level] = score
        else:
            self.high_scores[difficulty_level] = max(
                self.high_scores[difficulty_level], score
            )

    def get_high_score(self, difficulty_level):
        """Get high score for difficulty level"""
        return self.high_scores.get(difficulty_level, 0)

    def __repr__(self):
        return f"LevelManager(difficulty={self.difficulty_level}, current_level={self.current_level})"
