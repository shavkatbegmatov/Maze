"""
Moving Walls - Dynamic obstacles that move through the maze
"""

import random
from maze.maze_core import neighbors_open, can_move


class MovingWall:
    """
    A wall segment that moves through the maze
    """
    def __init__(self, x, y, direction='horizontal', speed=0.5):
        """
        Args:
            x, y: Starting grid position
            direction: 'horizontal' or 'vertical'
            speed: Movement speed (cells per second)
        """
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.direction = direction
        self.speed = speed

        # Movement path
        self.path = []
        self.path_index = 0
        self.forward = True  # Movement direction along path

        # Animation
        self.move_timer = 0.0
        self.move_interval = 1.0 / speed  # Time between moves

        # Visual
        self.color = (150, 150, 200)  # Blueish gray
        self.glow_phase = 0.0

    def create_path(self, walls, cols, rows, max_length=5):
        """
        Create a movement path for the wall

        Args:
            walls: Maze walls
            cols, rows: Maze dimensions
            max_length: Maximum path length
        """
        self.path = [(self.x, self.y)]
        current_x, current_y = self.x, self.y

        # Determine primary direction
        if self.direction == 'horizontal':
            primary_dirs = [(1, 0), (-1, 0)]
        else:
            primary_dirs = [(0, 1), (0, -1)]

        # Build path
        for _ in range(max_length):
            moved = False

            # Try primary directions first
            random.shuffle(primary_dirs)
            for dx, dy in primary_dirs:
                if can_move(walls, cols, rows, current_x, current_y, dx, dy):
                    current_x += dx
                    current_y += dy
                    self.path.append((current_x, current_y))
                    moved = True
                    break

            if not moved:
                break

        # If path is too short, just make a back-and-forth
        if len(self.path) < 2:
            self.path = [(self.x, self.y)]
            if self.direction == 'horizontal':
                if self.x + 1 < cols:
                    self.path.append((self.x + 1, self.y))
            else:
                if self.y + 1 < rows:
                    self.path.append((self.x, self.y + 1))

    def update(self, dt):
        """
        Update moving wall position

        Args:
            dt: Delta time in seconds
        """
        if len(self.path) < 2:
            return

        self.move_timer += dt
        self.glow_phase += dt * 2.0

        # Move to next position
        if self.move_timer >= self.move_interval:
            self.move_timer = 0.0

            # Update path index
            if self.forward:
                self.path_index += 1
                if self.path_index >= len(self.path) - 1:
                    self.forward = False
            else:
                self.path_index -= 1
                if self.path_index <= 0:
                    self.forward = True

            # Update position
            self.x, self.y = self.path[self.path_index]

    def is_blocking(self, x, y):
        """Check if wall is blocking a position"""
        return self.x == x and self.y == y

    def get_glow_color(self):
        """Get color with glow effect"""
        import math
        glow = int(abs(math.sin(self.glow_phase)) * 50)
        r = min(255, self.color[0] + glow)
        g = min(255, self.color[1] + glow)
        b = min(255, self.color[2] + glow)
        return (r, g, b)

    def reset(self):
        """Reset to starting position"""
        self.x = self.start_x
        self.y = self.start_y
        self.path_index = 0
        self.forward = True
        self.move_timer = 0.0

    def __repr__(self):
        return f"MovingWall(pos=({self.x},{self.y}), dir={self.direction})"


class MovingWallManager:
    """
    Manages all moving walls in the level
    """
    def __init__(self):
        self.walls = []

    def add_wall(self, x, y, direction='horizontal', speed=0.5):
        """
        Add a moving wall

        Args:
            x, y: Starting position
            direction: 'horizontal' or 'vertical'
            speed: Movement speed

        Returns:
            MovingWall object
        """
        wall = MovingWall(x, y, direction, speed)
        self.walls.append(wall)
        return wall

    def create_paths(self, maze_walls, cols, rows):
        """Create movement paths for all walls"""
        for wall in self.walls:
            wall.create_path(maze_walls, cols, rows)

    def update(self, dt):
        """Update all moving walls"""
        for wall in self.walls:
            wall.update(dt)

    def is_blocked(self, x, y):
        """Check if position is blocked by any moving wall"""
        for wall in self.walls:
            if wall.is_blocking(x, y):
                return True
        return False

    def check_player_collision(self, player):
        """
        Check if player collides with any moving wall

        Args:
            player: Player object

        Returns:
            MovingWall if collision, None otherwise
        """
        for wall in self.walls:
            if wall.is_blocking(player.x, player.y):
                return wall
        return None

    def reset(self):
        """Reset all walls to starting positions"""
        for wall in self.walls:
            wall.reset()

    def clear(self):
        """Remove all walls"""
        self.walls.clear()

    def __repr__(self):
        return f"MovingWallManager(walls={len(self.walls)})"


def spawn_moving_walls(config, walls, cols, rows, player_pos, goal_pos):
    """
    Generate spawn positions for moving walls

    Args:
        config: Difficulty config
        walls: Maze walls
        cols, rows: Maze dimensions
        player_pos: Player starting position
        goal_pos: Goal position

    Returns:
        List of (x, y, direction, speed) tuples
    """
    if config.moving_wall_count == 0:
        return []

    spawns = []
    min_distance_from_start = 8
    min_distance_from_goal = 5

    # Generate candidate positions
    candidates = []
    for y in range(rows):
        for x in range(cols):
            # Check distance from player and goal
            dist_player = abs(x - player_pos[0]) + abs(y - player_pos[1])
            dist_goal = abs(x - goal_pos[0]) + abs(y - goal_pos[1])

            if dist_player < min_distance_from_start or dist_goal < min_distance_from_goal:
                continue

            # Check if position has open paths
            open_neighbors = len(neighbors_open(walls, cols, rows, x, y))
            if open_neighbors >= 2:  # Need at least 2 open neighbors to move
                candidates.append((x, y))

    if not candidates:
        return []

    random.shuffle(candidates)

    # Create spawns
    for i in range(min(config.moving_wall_count, len(candidates))):
        x, y = candidates[i]

        # Determine direction based on available paths
        can_move_h = (can_move(walls, cols, rows, x, y, 1, 0) or
                      can_move(walls, cols, rows, x, y, -1, 0))
        can_move_v = (can_move(walls, cols, rows, x, y, 0, 1) or
                      can_move(walls, cols, rows, x, y, 0, -1))

        if can_move_h and can_move_v:
            direction = random.choice(['horizontal', 'vertical'])
        elif can_move_h:
            direction = 'horizontal'
        elif can_move_v:
            direction = 'vertical'
        else:
            continue

        # Speed varies by difficulty
        speed = random.uniform(0.3, 0.6)

        spawns.append((x, y, direction, speed))

    return spawns
