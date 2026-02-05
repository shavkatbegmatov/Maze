"""
Raycaster Engine - DDA (Digital Differential Analyzer) algorithm
Wolfenstein3D/Doom style raycasting for maze walls
"""

import math
from utils.constants import TOP, RIGHT, BOTTOM, LEFT


class Raycaster:
    """
    DDA Raycasting engine for 3D maze rendering
    """

    # Pre-computed tables
    _sin_table = None
    _cos_table = None
    _tan_table = None
    _fish_eye_table = None
    TABLE_SIZE = 3600  # 0.1 degree precision

    def __init__(self, fov=60, num_rays=320):
        """
        Initialize raycaster

        Args:
            fov: Field of view in degrees
            num_rays: Number of rays to cast (screen width)
        """
        self.fov = fov
        self.num_rays = num_rays
        self.half_fov = fov / 2

        # Pre-compute tables if not done
        if Raycaster._sin_table is None:
            self._build_tables()

        # Build fish-eye correction table for current FOV
        self._build_fisheye_table()

    @classmethod
    def _build_tables(cls):
        """Pre-compute trigonometric tables"""
        cls._sin_table = []
        cls._cos_table = []
        cls._tan_table = []

        for i in range(cls.TABLE_SIZE):
            angle = (i / cls.TABLE_SIZE) * 2 * math.pi
            cls._sin_table.append(math.sin(angle))
            cls._cos_table.append(math.cos(angle))
            # Avoid division by zero
            cos_val = math.cos(angle)
            if abs(cos_val) < 0.0001:
                cls._tan_table.append(1e10 if cos_val >= 0 else -1e10)
            else:
                cls._tan_table.append(math.sin(angle) / cos_val)

    def _build_fisheye_table(self):
        """Build fish-eye correction table for current FOV and ray count"""
        self._fish_eye_table = []
        for i in range(self.num_rays):
            # Angle offset from center of view
            ray_angle = (i / self.num_rays - 0.5) * math.radians(self.fov)
            # Fish-eye correction factor
            self._fish_eye_table.append(math.cos(ray_angle))

    def _get_table_index(self, angle_rad):
        """Convert angle to table index"""
        # Normalize to 0-2pi
        while angle_rad < 0:
            angle_rad += 2 * math.pi
        while angle_rad >= 2 * math.pi:
            angle_rad -= 2 * math.pi
        return int((angle_rad / (2 * math.pi)) * self.TABLE_SIZE) % self.TABLE_SIZE

    def fast_sin(self, angle_rad):
        """Fast sine lookup"""
        return self._sin_table[self._get_table_index(angle_rad)]

    def fast_cos(self, angle_rad):
        """Fast cosine lookup"""
        return self._cos_table[self._get_table_index(angle_rad)]

    def set_resolution(self, num_rays):
        """Update ray count for different screen widths"""
        if num_rays != self.num_rays:
            self.num_rays = num_rays
            self._build_fisheye_table()

    def check_wall(self, walls, cols, rows, cell_x, cell_y, direction):
        """
        Check if there's a wall in the given direction

        Args:
            walls: Maze walls array
            cols, rows: Maze dimensions
            cell_x, cell_y: Cell coordinates
            direction: 'top', 'right', 'bottom', 'left' or wall bit constant

        Returns:
            True if wall exists
        """
        if cell_x < 0 or cell_x >= cols or cell_y < 0 or cell_y >= rows:
            return True  # Out of bounds = wall

        idx = int(cell_y) * cols + int(cell_x)
        if idx < 0 or idx >= len(walls):
            return True

        w = walls[idx]

        if isinstance(direction, str):
            if direction == 'top':
                return (w & TOP) != 0
            elif direction == 'right':
                return (w & RIGHT) != 0
            elif direction == 'bottom':
                return (w & BOTTOM) != 0
            elif direction == 'left':
                return (w & LEFT) != 0
        else:
            return (w & direction) != 0

        return False

    def cast_ray(self, walls, cols, rows, px, py, angle):
        """
        Cast a single ray using DDA algorithm

        Args:
            walls: Maze walls array
            cols, rows: Maze dimensions
            px, py: Player position (float, in cell units)
            angle: Ray angle in radians

        Returns:
            (distance, side, hit_x, hit_y, wall_dir)
            - distance: Distance to wall
            - side: 0 for vertical (N/S), 1 for horizontal (E/W)
            - hit_x, hit_y: Exact hit point
            - wall_dir: Wall direction that was hit (TOP, RIGHT, BOTTOM, LEFT)
        """
        # Ray direction
        ray_dir_x = self.fast_cos(angle)
        ray_dir_y = self.fast_sin(angle)

        # Avoid division by zero
        if abs(ray_dir_x) < 1e-10:
            ray_dir_x = 1e-10 if ray_dir_x >= 0 else -1e-10
        if abs(ray_dir_y) < 1e-10:
            ray_dir_y = 1e-10 if ray_dir_y >= 0 else -1e-10

        # Current cell
        map_x = int(px)
        map_y = int(py)

        # Length of ray from one x or y-side to next x or y-side
        delta_dist_x = abs(1 / ray_dir_x)
        delta_dist_y = abs(1 / ray_dir_y)

        # Direction to step in x or y (+1 or -1)
        step_x = 1 if ray_dir_x >= 0 else -1
        step_y = 1 if ray_dir_y >= 0 else -1

        # Calculate distance to first x and y intersection
        if ray_dir_x < 0:
            side_dist_x = (px - map_x) * delta_dist_x
        else:
            side_dist_x = (map_x + 1.0 - px) * delta_dist_x

        if ray_dir_y < 0:
            side_dist_y = (py - map_y) * delta_dist_y
        else:
            side_dist_y = (map_y + 1.0 - py) * delta_dist_y

        # Perform DDA
        hit = False
        side = 0  # 0 = vertical wall (N/S), 1 = horizontal wall (E/W)
        wall_dir = TOP
        max_distance = 100  # Maximum ray distance

        while not hit:
            # Jump to next cell
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 1  # Vertical wall (E/W)
                wall_dir = LEFT if step_x > 0 else RIGHT
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 0  # Horizontal wall (N/S)
                wall_dir = TOP if step_y > 0 else BOTTOM

            # Check if out of bounds
            if map_x < 0 or map_x >= cols or map_y < 0 or map_y >= rows:
                # Hit boundary
                hit = True
                break

            # Check for wall in this cell based on entry direction
            prev_x = map_x - step_x if side == 1 else map_x
            prev_y = map_y - step_y if side == 0 else map_y

            # Check the wall we're crossing
            if side == 1:  # Moving horizontally (crossing vertical wall)
                if step_x > 0:
                    # Moving right, check left wall of new cell
                    if self.check_wall(walls, cols, rows, map_x, map_y, LEFT):
                        hit = True
                        wall_dir = LEFT
                else:
                    # Moving left, check right wall of new cell
                    if self.check_wall(walls, cols, rows, map_x, map_y, RIGHT):
                        hit = True
                        wall_dir = RIGHT
            else:  # Moving vertically (crossing horizontal wall)
                if step_y > 0:
                    # Moving down, check top wall of new cell
                    if self.check_wall(walls, cols, rows, map_x, map_y, TOP):
                        hit = True
                        wall_dir = TOP
                else:
                    # Moving up, check bottom wall of new cell
                    if self.check_wall(walls, cols, rows, map_x, map_y, BOTTOM):
                        hit = True
                        wall_dir = BOTTOM

            # Safety check for max distance
            dist_check = side_dist_x if side == 1 else side_dist_y
            if dist_check > max_distance:
                break

        # Calculate distance
        if side == 1:
            perp_wall_dist = side_dist_x - delta_dist_x
        else:
            perp_wall_dist = side_dist_y - delta_dist_y

        # Calculate exact hit point
        hit_x = px + perp_wall_dist * ray_dir_x
        hit_y = py + perp_wall_dist * ray_dir_y

        return perp_wall_dist, side, hit_x, hit_y, wall_dir

    def cast_all_rays(self, walls, cols, rows, px, py, player_angle):
        """
        Cast all rays for the screen

        Args:
            walls: Maze walls array
            cols, rows: Maze dimensions
            px, py: Player position
            player_angle: Player view angle in radians

        Returns:
            List of (distance, side, hit_x, hit_y, wall_dir, corrected_dist) tuples
        """
        results = []

        # Calculate angle step between rays
        angle_step = math.radians(self.fov) / self.num_rays
        start_angle = player_angle - math.radians(self.half_fov)

        for i in range(self.num_rays):
            ray_angle = start_angle + i * angle_step

            dist, side, hit_x, hit_y, wall_dir = self.cast_ray(
                walls, cols, rows, px, py, ray_angle
            )

            # Apply fish-eye correction
            corrected_dist = dist * self._fish_eye_table[i]

            results.append((dist, side, hit_x, hit_y, wall_dir, corrected_dist))

        return results

    def get_wall_texture_x(self, hit_x, hit_y, side, wall_dir):
        """
        Calculate texture X coordinate (0.0 to 1.0)

        Args:
            hit_x, hit_y: Wall hit point
            side: 0 for N/S wall, 1 for E/W wall
            wall_dir: Direction of wall hit

        Returns:
            Texture X coordinate (0.0 to 1.0)
        """
        if side == 1:  # E/W wall
            wall_x = hit_y - int(hit_y)
        else:  # N/S wall
            wall_x = hit_x - int(hit_x)

        # Flip texture based on wall direction
        if wall_dir == RIGHT or wall_dir == BOTTOM:
            wall_x = 1.0 - wall_x

        return wall_x
