"""
3D Player - First-person player with smooth movement and collision
"""

import math
from utils.constants import TOP, RIGHT, BOTTOM, LEFT


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
        self.collision_radius = 0.2  # Radius for wall collision

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
        can_x = True
        can_y = True

        # Current cell
        curr_cell_x = int(self.world_x)
        curr_cell_y = int(self.world_y)

        # Proposed cell
        new_cell_x = int(new_x)
        new_cell_y = int(new_y)

        # Check X movement
        if new_cell_x != curr_cell_x:
            # Crossing cell boundary horizontally
            idx = curr_cell_y * cols + curr_cell_x
            if 0 <= idx < len(walls):
                w = walls[idx]
                if new_cell_x > curr_cell_x:
                    # Moving right
                    if (w & RIGHT) != 0:
                        can_x = False
                else:
                    # Moving left
                    if (w & LEFT) != 0:
                        can_x = False
        else:
            # Within same cell X - check wall proximity
            cell_left = curr_cell_x
            cell_right = curr_cell_x + 1

            idx = curr_cell_y * cols + curr_cell_x
            if 0 <= idx < len(walls):
                w = walls[idx]

                # Too close to left wall?
                if new_x - self.collision_radius < cell_left and (w & LEFT) != 0:
                    can_x = False
                # Too close to right wall?
                if new_x + self.collision_radius > cell_right and (w & RIGHT) != 0:
                    can_x = False

        # Check Y movement
        if new_cell_y != curr_cell_y:
            # Crossing cell boundary vertically
            idx = curr_cell_y * cols + curr_cell_x
            if 0 <= idx < len(walls):
                w = walls[idx]
                if new_cell_y > curr_cell_y:
                    # Moving down
                    if (w & BOTTOM) != 0:
                        can_y = False
                else:
                    # Moving up
                    if (w & TOP) != 0:
                        can_y = False
        else:
            # Within same cell Y - check wall proximity
            cell_top = curr_cell_y
            cell_bottom = curr_cell_y + 1

            idx = curr_cell_y * cols + curr_cell_x
            if 0 <= idx < len(walls):
                w = walls[idx]

                # Too close to top wall?
                if new_y - self.collision_radius < cell_top and (w & TOP) != 0:
                    can_y = False
                # Too close to bottom wall?
                if new_y + self.collision_radius > cell_bottom and (w & BOTTOM) != 0:
                    can_y = False

        # Boundary checks
        if new_x - self.collision_radius < 0 or new_x + self.collision_radius > cols:
            can_x = False
        if new_y - self.collision_radius < 0 or new_y + self.collision_radius > rows:
            can_y = False

        return can_x, can_y

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

        # Calculate new position
        new_x = self.world_x + move_x * dt
        new_y = self.world_y + move_y * dt

        # Check collision
        can_x, can_y = self.check_wall_collision(walls, cols, rows, new_x, new_y)

        moved = False

        # Apply movement with collision response
        if can_x:
            self.world_x = new_x
            moved = True
        else:
            # Slide along wall
            if can_y:
                # Try moving just in Y
                pass

        if can_y:
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

    def handle_mouse_look(self, mouse_dx):
        """
        Handle mouse look rotation

        Args:
            mouse_dx: Mouse X movement in pixels
        """
        self.rotate(mouse_dx * self.mouse_sensitivity)

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
