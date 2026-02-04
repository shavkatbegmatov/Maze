"""
Enemy AI entities
Different enemy types with varying behaviors
"""

import random
from maze.maze_core import neighbors_open, astar_shortest_path, manhattan
from utils.colors import (
    COLOR_ENEMY_PATROL, COLOR_ENEMY_CHASE, COLOR_ENEMY_TELEPORT, COLOR_ENEMY_SMART
)


class Enemy:
    """
    Base enemy class
    """
    def __init__(self, x, y, enemy_type):
        """
        Args:
            x, y: Grid position
            enemy_type: Type ('patrol', 'chase', 'teleport', 'smart')
        """
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.type = enemy_type

        # AI state
        self.state = 'idle'  # 'idle', 'patrol', 'chase', 'return'
        self.path = []
        self.path_index = 0
        self.target = None

        # Stats
        self.speed = self._get_speed()
        self.vision_range = self._get_vision_range()
        self.damage = self._get_damage()

        # Movement
        self.move_timer = 0.0
        self.move_cooldown = 0.4 / self.speed  # Seconds between moves

        # Patrol-specific
        self.patrol_waypoints = []
        self.current_waypoint = 0

        # Teleport-specific
        self.teleport_cooldown = 0.0
        self.teleport_delay = 5.0  # Seconds between teleports

    def _get_speed(self):
        """Get speed based on enemy type"""
        speeds = {
            'patrol': 0.6,
            'chase': 0.8,
            'teleport': 1.0,
            'smart': 0.9,
        }
        return speeds.get(self.type, 0.5)

    def _get_vision_range(self):
        """Get vision range based on enemy type"""
        ranges = {
            'patrol': 5,
            'chase': 6,
            'teleport': 7,
            'smart': 8,
        }
        return ranges.get(self.type, 5)

    def _get_damage(self):
        """Get damage based on enemy type"""
        damages = {
            'patrol': 15,
            'chase': 20,
            'teleport': 25,
            'smart': 30,
        }
        return damages.get(self.type, 15)

    def get_color(self):
        """Get RGB color for rendering"""
        colors = {
            'patrol': COLOR_ENEMY_PATROL,
            'chase': COLOR_ENEMY_CHASE,
            'teleport': COLOR_ENEMY_TELEPORT,
            'smart': COLOR_ENEMY_SMART,
        }
        return colors.get(self.type, (255, 100, 100))

    def can_see_player(self, player_x, player_y):
        """Check if enemy can see player"""
        dist = abs(self.x - player_x) + abs(self.y - player_y)
        return dist <= self.vision_range

    def attack_player(self, player):
        """Attack player if adjacent"""
        dist = abs(self.x - player.x) + abs(self.y - player.y)
        if dist <= 1:  # Adjacent
            return player.take_damage(self.damage)
        return False

    def update(self, dt, walls, cols, rows, player):
        """
        Update enemy AI

        Args:
            dt: Delta time in seconds
            walls: Maze walls
            cols, rows: Maze dimensions
            player: Player object

        Returns:
            True if enemy attacked player
        """
        # Update move timer
        self.move_timer += dt

        # Check if can move
        if self.move_timer < self.move_cooldown:
            return False

        self.move_timer = 0.0

        # Update based on type
        if self.type == 'patrol':
            return self._update_patrol(walls, cols, rows, player)
        elif self.type == 'chase':
            return self._update_chase(walls, cols, rows, player)
        elif self.type == 'teleport':
            return self._update_teleport(walls, cols, rows, player, dt)
        elif self.type == 'smart':
            return self._update_smart(walls, cols, rows, player)

        return False

    def _update_patrol(self, walls, cols, rows, player):
        """Patrol enemy behavior - follows waypoints"""
        # Check if player is in vision
        if self.can_see_player(player.x, player.y):
            # Alert! But patrol enemies don't chase, just alert
            self.state = 'alert'
            return False

        # Follow patrol path
        if not self.patrol_waypoints:
            # Create patrol path if not exists
            self._create_patrol_path(walls, cols, rows)

        if self.patrol_waypoints:
            target = self.patrol_waypoints[self.current_waypoint]
            if (self.x, self.y) == target:
                # Reached waypoint, go to next
                self.current_waypoint = (self.current_waypoint + 1) % len(self.patrol_waypoints)
                target = self.patrol_waypoints[self.current_waypoint]

            # Move toward target
            self._move_toward(target, walls, cols, rows)

        return self.attack_player(player)

    def _update_chase(self, walls, cols, rows, player):
        """Chase enemy behavior - pursues player when in vision"""
        if self.can_see_player(player.x, player.y):
            # Chase player using A*
            path = astar_shortest_path(walls, cols, rows, (self.x, self.y), (player.x, player.y))
            if path and len(path) > 1:
                next_pos = path[1]  # First step toward player
                self.x, self.y = next_pos
        else:
            # Return to start position
            if (self.x, self.y) != (self.start_x, self.start_y):
                path = astar_shortest_path(walls, cols, rows, (self.x, self.y), (self.start_x, self.start_y))
                if path and len(path) > 1:
                    next_pos = path[1]
                    self.x, self.y = next_pos

        return self.attack_player(player)

    def _update_teleport(self, walls, cols, rows, player, dt):
        """Teleport enemy behavior - randomly teleports near player"""
        self.teleport_cooldown -= dt

        if self.can_see_player(player.x, player.y):
            # Chase like normal chase enemy
            path = astar_shortest_path(walls, cols, rows, (self.x, self.y), (player.x, player.y))
            if path and len(path) > 1:
                next_pos = path[1]
                self.x, self.y = next_pos

            # Teleport if cooldown ready and player is far
            if self.teleport_cooldown <= 0:
                dist = manhattan((self.x, self.y), (player.x, player.y))
                if dist > 8:
                    self._teleport_near_player(player, walls, cols, rows)
                    self.teleport_cooldown = self.teleport_delay
        else:
            # Wander randomly
            neighbors = neighbors_open(walls, cols, rows, self.x, self.y)
            if neighbors:
                self.x, self.y = random.choice(neighbors)

        return self.attack_player(player)

    def _update_smart(self, walls, cols, rows, player):
        """Smart enemy behavior - predicts player movement"""
        if self.can_see_player(player.x, player.y):
            # Predict where player will be
            predicted_pos = self._predict_player_position(player, walls, cols, rows)

            # Try to cut off player
            path = astar_shortest_path(walls, cols, rows, (self.x, self.y), predicted_pos)
            if path and len(path) > 1:
                next_pos = path[1]
                self.x, self.y = next_pos
            else:
                # Fallback to direct chase
                path = astar_shortest_path(walls, cols, rows, (self.x, self.y), (player.x, player.y))
                if path and len(path) > 1:
                    next_pos = path[1]
                    self.x, self.y = next_pos
        else:
            # Return to patrol
            if (self.x, self.y) != (self.start_x, self.start_y):
                path = astar_shortest_path(walls, cols, rows, (self.x, self.y), (self.start_x, self.start_y))
                if path and len(path) > 1:
                    next_pos = path[1]
                    self.x, self.y = next_pos

        return self.attack_player(player)

    def _create_patrol_path(self, walls, cols, rows):
        """Create a patrol path for patrol enemies"""
        # Create a simple back-and-forth or circular path
        path_length = random.randint(4, 8)
        current = (self.x, self.y)
        visited = {current}
        path = [current]

        for _ in range(path_length):
            neighbors = neighbors_open(walls, cols, rows, current[0], current[1])
            unvisited = [n for n in neighbors if n not in visited]

            if unvisited:
                next_pos = random.choice(unvisited)
            elif neighbors:
                next_pos = random.choice(neighbors)
            else:
                break

            path.append(next_pos)
            visited.add(next_pos)
            current = next_pos

        self.patrol_waypoints = path
        if len(path) > 1:
            self.patrol_waypoints.append(path[0])  # Make it loop

    def _move_toward(self, target, walls, cols, rows):
        """Move one step toward target"""
        path = astar_shortest_path(walls, cols, rows, (self.x, self.y), target)
        if path and len(path) > 1:
            self.x, self.y = path[1]

    def _teleport_near_player(self, player, walls, cols, rows):
        """Teleport to a position near player"""
        # Find positions within 3-5 cells of player
        candidates = []
        for y in range(rows):
            for x in range(cols):
                dist = manhattan((x, y), (player.x, player.y))
                if 3 <= dist <= 5:
                    candidates.append((x, y))

        if candidates:
            self.x, self.y = random.choice(candidates)

    def _predict_player_position(self, player, walls, cols, rows):
        """Predict where player will move (simple prediction)"""
        # Look at player's trail to predict direction
        if len(player.trail) >= 2:
            px, py = player.trail[-1]
            ppx, ppy = player.trail[-2]
            dx = px - ppx
            dy = py - ppy

            # Predict 2-3 steps ahead
            prediction_steps = 3
            pred_x = player.x + dx * prediction_steps
            pred_y = player.y + dy * prediction_steps

            # Clamp to bounds
            pred_x = max(0, min(pred_x, cols - 1))
            pred_y = max(0, min(pred_y, rows - 1))

            return (pred_x, pred_y)

        # Fallback to current position
        return (player.x, player.y)

    def reset(self):
        """Reset enemy to starting position"""
        self.x = self.start_x
        self.y = self.start_y
        self.state = 'idle'
        self.path = []
        self.path_index = 0
        self.move_timer = 0.0
        self.current_waypoint = 0
        self.teleport_cooldown = 0.0

    def __repr__(self):
        return f"Enemy(pos=({self.x},{self.y}), type={self.type}, state={self.state})"


class EnemyManager:
    """
    Manages all enemies in the level
    """
    def __init__(self):
        self.enemies = []

    def add_enemy(self, x, y, enemy_type):
        """Add an enemy to the level"""
        enemy = Enemy(x, y, enemy_type)
        self.enemies.append(enemy)
        return enemy

    def update(self, dt, walls, cols, rows, player):
        """
        Update all enemies

        Returns:
            True if any enemy attacked player
        """
        player_attacked = False
        for enemy in self.enemies:
            if enemy.update(dt, walls, cols, rows, player):
                player_attacked = True
        return player_attacked

    def check_collision_with_player(self, player_x, player_y):
        """Check if player position collides with any enemy"""
        for enemy in self.enemies:
            if enemy.x == player_x and enemy.y == player_y:
                return enemy
        return None

    def get_enemies_in_range(self, x, y, range_cells):
        """Get enemies within range of a position"""
        enemies_in_range = []
        for enemy in self.enemies:
            dist = abs(enemy.x - x) + abs(enemy.y - y)
            if dist <= range_cells:
                enemies_in_range.append(enemy)
        return enemies_in_range

    def reset(self):
        """Reset all enemies"""
        for enemy in self.enemies:
            enemy.reset()

    def clear(self):
        """Remove all enemies"""
        self.enemies.clear()

    def __repr__(self):
        return f"EnemyManager(enemies={len(self.enemies)})"
