"""
3D Player - First-person player with smooth movement and collision
Grid koordinatalarida ishlaydi (blockmap grid: (2*cols+1) x (2*rows+1))
"""

import math


class Player3D:
    """
    3D first-person player with smooth movement
    Grid koordinatalarida: spawn pozitsiyasi = (2*cell_x + 1.5, 2*cell_y + 1.5)
    """

    def __init__(self, x, y, angle=0):
        """
        Initialize 3D player

        Args:
            x, y: Starting cell coordinates (maze cell)
            angle: Starting view angle in radians (0 = east, pi/2 = south)
        """
        # Grid pozitsiya (koridor markazi)
        self.world_x = 2.0 * x + 1.5
        self.world_y = 2.0 * y + 1.5

        # Maze cell pozitsiya (game logic uchun)
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
        # Grid koridori kengligi = 1.0 unit, radius < 0.5
        self.collision_radius = 0.25
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
        Sync position from 2D player (cell coords -> grid coords)

        Args:
            player_2d: The 2D Player instance
        """
        self.grid_x = player_2d.x
        self.grid_y = player_2d.y
        self.world_x = 2.0 * player_2d.x + 1.5
        self.world_y = 2.0 * player_2d.y + 1.5

    def sync_to_2d_player(self, player_2d):
        """
        Sync position back to 2D player (grid coords -> cell coords)

        Args:
            player_2d: The 2D Player instance
        """
        player_2d.x = max(0, (int(self.world_x) - 1) // 2)
        player_2d.y = max(0, (int(self.world_y) - 1) // 2)

    def _would_collide(self, grid, grid_cols, grid_rows, test_x, test_y):
        """Grid-based collision: 4 burchak tekshirish."""
        r = self.collision_radius
        corners = [
            (test_x - r, test_y - r),
            (test_x + r, test_y - r),
            (test_x - r, test_y + r),
            (test_x + r, test_y + r),
        ]
        for cx, cy in corners:
            gx = int(cx)
            gy = int(cy)
            if gx < 0 or gx >= grid_cols or gy < 0 or gy >= grid_rows:
                return True
            if grid[gy, gx] != 0:
                return True
        return False

    def move(self, forward, strafe, grid, grid_cols, grid_rows, dt):
        """
        Move player with collision detection

        Args:
            forward: Forward/backward input (-1 to 1)
            strafe: Left/right strafe input (-1 to 1)
            grid: 2D int8 massiv (grid_rows, grid_cols), 1=solid, 0=bo'sh
            grid_cols, grid_rows: Grid o'lchamlari
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
            if not self._would_collide(grid, grid_cols, grid_rows, new_x, self.world_y):
                self.world_x = new_x
                moved = True

            new_y = self.world_y + step_y
            if not self._would_collide(grid, grid_cols, grid_rows, self.world_x, new_y):
                self.world_y = new_y
                moved = True

        # Update grid position (cell coords)
        self.grid_x = max(0, (int(self.world_x) - 1) // 2)
        self.grid_y = max(0, (int(self.world_y) - 1) // 2)

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

    def set_position(self, cell_x, cell_y):
        """Set position from maze cell coordinates"""
        self.world_x = 2.0 * cell_x + 1.5
        self.world_y = 2.0 * cell_y + 1.5
        self.grid_x = cell_x
        self.grid_y = cell_y
        self._clamp_pitch()

    def get_angle_degrees(self):
        """Get view angle in degrees"""
        return math.degrees(self.angle)

    def look_at(self, target_x, target_y):
        """
        Set angle to look at target position (cell coordinates)

        Args:
            target_x, target_y: Target cell coordinates
        """
        # Convert target to grid coords
        tx = 2.0 * target_x + 1.5
        ty = 2.0 * target_y + 1.5
        dx = tx - self.world_x
        dy = ty - self.world_y
        self.angle = math.atan2(dy, dx)

    def __repr__(self):
        return f"Player3D(pos=({self.world_x:.2f}, {self.world_y:.2f}), cell=({self.grid_x}, {self.grid_y}), angle={math.degrees(self.angle):.1f})"
