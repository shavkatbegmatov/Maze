"""
3D Player - First-person player with smooth movement and collision
"""

import math
from utils.constants import TOP, RIGHT, BOTTOM, LEFT
from .blockmap import WALL_HALF_THICKNESS


class Player3D:
    """
    3D first-person player with smooth movement
    """

    def __init__(self, x, y, angle=0):
        """
        Initialize 3D player

        Args:
            x, y: Starting cell coordinates
            angle: Starting view angle in radians (0 = east, pi/2 = south)
        """
        # Float position (center of cell)
        self.world_x = x + 0.5
        self.world_y = y + 0.5

        # Grid position (for game logic)
        self.grid_x = x
        self.grid_y = y

        # View angle (radians)
        self.angle = angle

        # Movement settings
        self.move_speed = 3.0  # Units per second
        self.strafe_speed = 2.5  # Units per second
        self.turn_speed = 2.5  # Radians per second (for keyboard)
        self.mouse_sensitivity = 0.003  # Radians per pixel

        # Collision settings
        # Keep the camera slightly away from visible wall plane
        self.wall_contact_buffer = 0.02
        self.collision_radius = WALL_HALF_THICKNESS + self.wall_contact_buffer
        self.collision_step = 0.05
        self.collision_epsilon = 1e-3

        # Movement state
        self.velocity_x = 0
        self.velocity_y = 0
        self.friction = 10.0  # Deceleration factor

        # Bobbing effect
        self.bob_timer = 0
        self.bob_amount = 0.03  # Vertical bob amplitude
        self.bob_speed = 8.0  # Bob frequency

        # Head tilt (for strafe effect)
        self.head_tilt = 0
        self.max_tilt = 0.05  # Maximum tilt angle

        # Vertical look (pitch)
        self.pitch = 0.0  # Vertical look offset (-1.0 to 1.0, 0 = horizontal)
        self.max_pitch = 0.8  # Prevent extreme pitch angles that break projection

    @property
    def x(self):
        """Grid X position (for compatibility with 2D player)"""
        return self.grid_x

    @property
    def y(self):
        """Grid Y position (for compatibility with 2D player)"""
        return self.grid_y

    def sync_from_2d_player(self, player_2d):
        """
        Sync position from 2D player

        Args:
            player_2d: The 2D Player instance
        """
        self.grid_x = player_2d.x
        self.grid_y = player_2d.y
        self.world_x = player_2d.x + 0.5
        self.world_y = player_2d.y + 0.5

    def sync_to_2d_player(self, player_2d):
        """
        Sync position back to 2D player

        Args:
            player_2d: The 2D Player instance
        """
        player_2d.x = self.grid_x
        player_2d.y = self.grid_y

    def check_wall_collision(self, walls, cols, rows, new_x, new_y):
        """
        Check if position would collide with walls

        Args:
            walls: Maze walls array
            cols, rows: Maze dimensions
            new_x, new_y: Proposed new position

        Returns:
            (can_move_x, can_move_y) - booleans for each axis
        """
        can_x = not self._would_collide(walls, cols, rows, new_x, self.world_y)
        can_y = not self._would_collide(walls, cols, rows, self.world_x, new_y)
        return can_x, can_y

    @staticmethod
    def _circle_hits_vertical_wall(px, py, radius, wall_x, y0, y1):
        """Circle-vs-vertical-segment intersection test."""
        dx = px - wall_x
        if dx < 0:
            dx = -dx
        if dx > radius:
            return False

        if py < y0:
            closest_y = y0
        elif py > y1:
            closest_y = y1
        else:
            closest_y = py

        dy = py - closest_y
        return (dx * dx + dy * dy) <= (radius * radius)

    @staticmethod
    def _circle_hits_horizontal_wall(px, py, radius, x0, x1, wall_y):
        """Circle-vs-horizontal-segment intersection test."""
        dy = py - wall_y
        if dy < 0:
            dy = -dy
        if dy > radius:
            return False

        if px < x0:
            closest_x = x0
        elif px > x1:
            closest_x = x1
        else:
            closest_x = px

        dx = px - closest_x
        return (dx * dx + dy * dy) <= (radius * radius)

    def _would_collide(self, walls, cols, rows, test_x, test_y):
        """Check if circle player intersects any wall segment or map boundary."""
        r = self.collision_radius
        eps = self.collision_epsilon

        # Map boundary as solid outer walls
        if test_x - r < eps or test_x + r > cols - eps:
            return True
        if test_y - r < eps or test_y + r > rows - eps:
            return True

        min_cell_x = max(0, int(math.floor(test_x - r)) - 1)
        max_cell_x = min(cols - 1, int(math.floor(test_x + r)) + 1)
        min_cell_y = max(0, int(math.floor(test_y - r)) - 1)
        max_cell_y = min(rows - 1, int(math.floor(test_y + r)) + 1)

        for cell_y in range(min_cell_y, max_cell_y + 1):
            for cell_x in range(min_cell_x, max_cell_x + 1):
                idx = cell_y * cols + cell_x
                if idx < 0 or idx >= len(walls):
                    continue
                w = walls[idx]

                # Left wall segment: x = cell_x, y in [cell_y, cell_y + 1]
                if (w & LEFT) != 0:
                    if self._circle_hits_vertical_wall(test_x, test_y, r, cell_x, cell_y, cell_y + 1):
                        return True

                # Right wall segment: x = cell_x + 1, y in [cell_y, cell_y + 1]
                if (w & RIGHT) != 0:
                    if self._circle_hits_vertical_wall(test_x, test_y, r, cell_x + 1, cell_y, cell_y + 1):
                        return True

                # Top wall segment: y = cell_y, x in [cell_x, cell_x + 1]
                if (w & TOP) != 0:
                    if self._circle_hits_horizontal_wall(test_x, test_y, r, cell_x, cell_x + 1, cell_y):
                        return True

                # Bottom wall segment: y = cell_y + 1, x in [cell_x, cell_x + 1]
                if (w & BOTTOM) != 0:
                    if self._circle_hits_horizontal_wall(test_x, test_y, r, cell_x, cell_x + 1, cell_y + 1):
                        return True

        return False

    def move(self, forward, strafe, walls, cols, rows, dt):
        """
        Move player with collision detection

        Args:
            forward: Forward/backward input (-1 to 1)
            strafe: Left/right strafe input (-1 to 1)
            walls: Maze walls array
            cols, rows: Maze dimensions
            dt: Delta time in seconds

        Returns:
            True if player moved
        """
        if forward == 0 and strafe == 0:
            # Apply friction when no input
            self.velocity_x *= max(0, 1 - self.friction * dt)
            self.velocity_y *= max(0, 1 - self.friction * dt)

            # Update head tilt
            self.head_tilt *= max(0, 1 - 10 * dt)
            return False

        # Calculate movement direction
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        # Forward/backward movement
        move_x = cos_a * forward * self.move_speed
        move_y = sin_a * forward * self.move_speed

        # Strafe movement (perpendicular to view)
        move_x += -sin_a * strafe * self.strafe_speed
        move_y += cos_a * strafe * self.strafe_speed

        move_x *= dt
        move_y *= dt

        # Katta dt frame'larda devordan "otib ketmaslik" uchun substep bilan yuritamiz.
        max_delta = max(abs(move_x), abs(move_y))
        steps = max(1, int(math.ceil(max_delta / self.collision_step)))
        step_x = move_x / steps
        step_y = move_y / steps

        moved = False

        for _ in range(steps):
            new_x = self.world_x + step_x
            if not self._would_collide(walls, cols, rows, new_x, self.world_y):
                self.world_x = new_x
                moved = True

            new_y = self.world_y + step_y
            if not self._would_collide(walls, cols, rows, self.world_x, new_y):
                self.world_y = new_y
                moved = True

        # Update grid position
        self.grid_x = int(self.world_x)
        self.grid_y = int(self.world_y)

        # Update bobbing
        if moved:
            self.bob_timer += dt * self.bob_speed
        else:
            self.bob_timer *= 0.9  # Slow down bob when stopped

        # Update head tilt based on strafe
        target_tilt = -strafe * self.max_tilt
        self.head_tilt += (target_tilt - self.head_tilt) * 5 * dt

        return moved

    def rotate(self, delta_angle):
        """
        Rotate player view

        Args:
            delta_angle: Angle change in radians
        """
        self.angle += delta_angle

        # Normalize angle to 0-2pi
        while self.angle < 0:
            self.angle += 2 * math.pi
        while self.angle >= 2 * math.pi:
            self.angle -= 2 * math.pi

    def _clamp_pitch(self):
        """Clamp vertical look to a projection-safe range."""
        if self.pitch > self.max_pitch:
            self.pitch = self.max_pitch
        elif self.pitch < -self.max_pitch:
            self.pitch = -self.max_pitch

    def handle_mouse_look(self, mouse_dx, mouse_dy=0):
        """
        Handle mouse look rotation and pitch

        Args:
            mouse_dx: Mouse X movement in pixels
            mouse_dy: Mouse Y movement in pixels
        """
        self.rotate(mouse_dx * self.mouse_sensitivity)
        self.pitch -= mouse_dy * self.mouse_sensitivity
        self._clamp_pitch()

    def handle_keyboard_turn(self, turn_input, dt):
        """
        Handle keyboard-based turning

        Args:
            turn_input: -1 (left) to 1 (right)
            dt: Delta time
        """
        self.rotate(turn_input * self.turn_speed * dt)

    def get_bob_offset(self):
        """Get current head bob vertical offset"""
        return math.sin(self.bob_timer) * self.bob_amount

    def get_direction_vector(self):
        """Get normalized direction vector"""
        return math.cos(self.angle), math.sin(self.angle)

    def get_position(self):
        """Get current world position"""
        return self.world_x, self.world_y

    def set_position(self, x, y):
        """Set world position"""
        self.world_x = x + 0.5
        self.world_y = y + 0.5
        self.grid_x = x
        self.grid_y = y
        self._clamp_pitch()

    def get_angle_degrees(self):
        """Get view angle in degrees"""
        return math.degrees(self.angle)

    def look_at(self, target_x, target_y):
        """
        Set angle to look at target position

        Args:
            target_x, target_y: Target coordinates
        """
        dx = target_x - self.world_x
        dy = target_y - self.world_y
        self.angle = math.atan2(dy, dx)

    def __repr__(self):
        return f"Player3D(pos=({self.world_x:.2f}, {self.world_y:.2f}), angle={math.degrees(self.angle):.1f}°)"
