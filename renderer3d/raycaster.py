"""
Raycaster Engine - DDA (Digital Differential Analyzer) algorithm
Wolfenstein3D/Doom style raycasting for maze walls
Optimized with Numba JIT compilation
"""

import math
import numpy as np
from numba import njit, float64, int32
from utils.constants import TOP, RIGHT, BOTTOM, LEFT


@njit(cache=True)
def _numba_cast_all_rays_grid(grid, grid_rows, grid_cols,
                               px, py, ray_angles, fish_eye_table, results):
    """
    Grid ustida oddiy DDA ray casting (lodev.org standarti).

    Args:
        grid: 2D int8 massiv (grid_rows, grid_cols), 1=solid, 0=bo'sh
        grid_rows, grid_cols: grid o'lchamlari
        px, py: o'yinchi pozitsiyasi grid koordinatalarida
        ray_angles: 1D float64 massiv — har bir nurning burchagi
        fish_eye_table: 1D float64 massiv — baliq ko'zi korreksiyasi
        results: (num_rays, 6) float64 massiv — natija yoziladigan joy
    """
    top = int32(1)
    right = int32(2)
    bottom = int32(4)
    left = int32(8)

    for i in range(len(ray_angles)):
        angle = ray_angles[i]
        ray_dir_x = math.cos(angle)
        ray_dir_y = math.sin(angle)

        map_x = int32(px)
        map_y = int32(py)

        # Delta distances
        if abs(ray_dir_x) < 1e-10:
            delta_x = float64(1e10)
        else:
            delta_x = abs(1.0 / ray_dir_x)
        if abs(ray_dir_y) < 1e-10:
            delta_y = float64(1e10)
        else:
            delta_y = abs(1.0 / ray_dir_y)

        # Step va initial side distances
        if ray_dir_x < 0:
            step_x = int32(-1)
            side_dist_x = (px - map_x) * delta_x
        else:
            step_x = int32(1)
            side_dist_x = (map_x + 1.0 - px) * delta_x
        if ray_dir_y < 0:
            step_y = int32(-1)
            side_dist_y = (py - map_y) * delta_y
        else:
            step_y = int32(1)
            side_dist_y = (map_y + 1.0 - py) * delta_y

        # DDA loop
        side = int32(0)
        hit = False
        for _ in range(200):  # max steps
            if side_dist_x < side_dist_y:
                side_dist_x += delta_x
                map_x += step_x
                side = int32(1)  # E/W face
            else:
                side_dist_y += delta_y
                map_y += step_y
                side = int32(0)  # N/S face

            if map_x < 0 or map_x >= grid_cols or map_y < 0 or map_y >= grid_rows:
                break
            if grid[map_y, map_x] != 0:
                hit = True
                break

        # Perpendicular distance (lodev formula)
        if side == 1:
            perp = side_dist_x - delta_x
        else:
            perp = side_dist_y - delta_y
        if perp < 0.01:
            perp = 0.01

        # Hit point (textura uchun)
        if side == 1:
            hit_y_val = py + perp * ray_dir_y
            if step_x > 0:
                hit_x_val = float64(map_x)
            else:
                hit_x_val = float64(map_x + 1)
        else:
            hit_x_val = px + perp * ray_dir_x
            if step_y > 0:
                hit_y_val = float64(map_y)
            else:
                hit_y_val = float64(map_y + 1)

        # Wall direction
        if side == 1:
            if step_x > 0:
                wall_dir = left   # 8 — devorning chap yuzi
            else:
                wall_dir = right  # 2 — devorning o'ng yuzi
        else:
            if step_y > 0:
                wall_dir = top      # 1 — devorning yuqori yuzi
            else:
                wall_dir = bottom   # 4 — devorning pastki yuzi

        corrected = perp * fish_eye_table[i]
        results[i, 0] = perp
        results[i, 1] = float64(side)
        results[i, 2] = hit_x_val
        results[i, 3] = hit_y_val
        results[i, 4] = float64(wall_dir)
        results[i, 5] = corrected


class Raycaster:
    """
    DDA Raycasting engine for 3D maze rendering
    Uses Numba JIT for high-performance ray casting
    """

    def __init__(self, fov=60, num_rays=320):
        self.fov = fov
        self.num_rays = num_rays
        self.half_fov = fov / 2
        self.fov_rad = math.radians(fov)
        self.half_fov_rad = math.radians(fov / 2)

        # Fish-eye correction table as numpy array
        self._fish_eye_table = self._build_fisheye_table(num_rays, fov)

        # Pre-allocated results array
        self._results = np.empty((num_rays, 6), dtype=np.float64)

    @staticmethod
    def _build_fisheye_table(num_rays, fov):
        """Build fish-eye correction table as numpy array"""
        indices = np.arange(num_rays, dtype=np.float64)
        ray_angles = (indices / num_rays - 0.5) * math.radians(fov)
        return np.cos(ray_angles)

    def set_resolution(self, num_rays):
        """Update ray count for different screen widths"""
        if num_rays != self.num_rays:
            self.num_rays = num_rays
            self._fish_eye_table = self._build_fisheye_table(num_rays, self.fov)
            self._results = np.empty((num_rays, 6), dtype=np.float64)

    def cast_all_rays_grid(self, grid, grid_rows, grid_cols, px, py, player_angle):
        """
        Grid ustida DDA bilan nurlarni otish.

        Args:
            grid: 2D int8 massiv — walls_to_blockmap() natijasi
            grid_rows, grid_cols: grid o'lchamlari
            px, py: o'yinchi pozitsiyasi grid koordinatalarida
            player_angle: o'yinchining ko'rish burchagi (radyan)

        Returns:
            numpy array shape (num_rays, 6):
            [dist, side, hit_x, hit_y, wall_dir, corrected_dist]
        """
        # Ray angles massivini hisoblash
        angle_step = self.fov_rad / self.num_rays
        start_angle = player_angle - self.half_fov_rad
        ray_angles = np.empty(self.num_rays, dtype=np.float64)
        for i in range(self.num_rays):
            ray_angles[i] = start_angle + i * angle_step

        _numba_cast_all_rays_grid(
            grid, int32(grid_rows), int32(grid_cols),
            float64(px), float64(py),
            ray_angles, self._fish_eye_table, self._results
        )
        return self._results

    def check_wall(self, walls, cols, rows, cell_x, cell_y, direction):
        """
        Check if there's a wall in the given direction (Python fallback)
        """
        if cell_x < 0 or cell_x >= cols or cell_y < 0 or cell_y >= rows:
            return True

        idx = int(cell_y) * cols + int(cell_x)
        if isinstance(walls, np.ndarray):
            if idx < 0 or idx >= walls.shape[0]:
                return True
            w = walls[idx]
        else:
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

    @staticmethod
    def get_wall_texture_x(hit_x, hit_y, side, wall_dir):
        """
        Calculate texture X coordinate (0.0 to 1.0)
        """
        if side == 1:  # E/W wall
            wall_x = hit_y - int(hit_y)
        else:  # N/S wall
            wall_x = hit_x - int(hit_x)

        # Flip texture based on wall direction
        if wall_dir == RIGHT or wall_dir == BOTTOM:
            wall_x = 1.0 - wall_x

        return wall_x
