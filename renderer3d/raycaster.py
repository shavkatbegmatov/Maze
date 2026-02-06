"""
Raycaster Engine - DDA (Digital Differential Analyzer) algorithm
Wolfenstein3D/Doom style raycasting for maze walls
Optimized with Numba JIT compilation
"""

import math
import numpy as np
import numba
from numba import njit, float64, int32, int64
from utils.constants import TOP, RIGHT, BOTTOM, LEFT
from .blockmap import walls_to_blockmap, pos_to_blockmap, blockmap_cast_all_rays

# Wall bit constants as module-level for Numba access
_TOP = int32(TOP)
_RIGHT = int32(RIGHT)
_BOTTOM = int32(BOTTOM)
_LEFT = int32(LEFT)


@njit(cache=True)
def _numba_cast_all_rays(walls, cols, rows, px, py, player_angle,
                         fov_rad, half_fov_rad, num_rays, fish_eye_table):
    """
    Cast all rays using DDA algorithm (Numba JIT compiled)

    Args:
        walls: 1D numpy int32 array of wall bitmasks
        cols, rows: Maze dimensions
        px, py: Player position (float)
        player_angle: Player view angle in radians
        fov_rad: Field of view in radians
        half_fov_rad: Half FOV in radians
        num_rays: Number of rays to cast
        fish_eye_table: 1D numpy float64 array of fish-eye correction factors

    Returns:
        results: numpy array shape (num_rays, 6)
                 [dist, side, hit_x, hit_y, wall_dir, corrected_dist]
    """
    results = np.empty((num_rays, 6), dtype=np.float64)

    angle_step = fov_rad / num_rays
    start_angle = player_angle - half_fov_rad

    top = int32(1)
    right = int32(2)
    bottom = int32(4)
    left = int32(8)

    two_pi = 2.0 * math.pi

    for i in range(num_rays):
        ray_angle = start_angle + i * angle_step

        # --- Inline cast_ray DDA ---
        ray_dir_x = math.cos(ray_angle)
        ray_dir_y = math.sin(ray_angle)

        # Avoid division by zero
        if abs(ray_dir_x) < 1e-10:
            if ray_dir_x >= 0:
                ray_dir_x = 1e-10
            else:
                ray_dir_x = -1e-10
        if abs(ray_dir_y) < 1e-10:
            if ray_dir_y >= 0:
                ray_dir_y = 1e-10
            else:
                ray_dir_y = -1e-10

        # Current cell
        map_x = int32(int(px))
        map_y = int32(int(py))

        # Delta distances
        delta_dist_x = abs(1.0 / ray_dir_x)
        delta_dist_y = abs(1.0 / ray_dir_y)

        # Step direction
        if ray_dir_x >= 0:
            step_x = int32(1)
            side_dist_x = (map_x + 1.0 - px) * delta_dist_x
        else:
            step_x = int32(-1)
            side_dist_x = (px - map_x) * delta_dist_x

        if ray_dir_y >= 0:
            step_y = int32(1)
            side_dist_y = (map_y + 1.0 - py) * delta_dist_y
        else:
            step_y = int32(-1)
            side_dist_y = (py - map_y) * delta_dist_y

        # DDA loop
        hit = False
        side = int32(0)
        wall_dir = top
        max_distance = 100.0

        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = int32(1)  # E/W wall
                if step_x > 0:
                    wall_dir = left
                else:
                    wall_dir = right
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = int32(0)  # N/S wall
                if step_y > 0:
                    wall_dir = top
                else:
                    wall_dir = bottom

            # Out of bounds check
            if map_x < 0 or map_x >= cols or map_y < 0 or map_y >= rows:
                hit = True
                break

            # Check wall (inline check_wall)
            idx = map_y * cols + map_x
            if idx < 0 or idx >= walls.shape[0]:
                hit = True
                break

            w = walls[idx]

            if side == 1:  # Horizontal movement
                if step_x > 0:
                    if (w & left) != 0:
                        hit = True
                        wall_dir = left
                else:
                    if (w & right) != 0:
                        hit = True
                        wall_dir = right
            else:  # Vertical movement
                if step_y > 0:
                    if (w & top) != 0:
                        hit = True
                        wall_dir = top
                else:
                    if (w & bottom) != 0:
                        hit = True
                        wall_dir = bottom

            # Max distance safety
            if side == 1:
                dist_check = side_dist_x
            else:
                dist_check = side_dist_y
            if dist_check > max_distance:
                break

        # Calculate perpendicular distance
        if side == 1:
            perp_wall_dist = side_dist_x - delta_dist_x
        else:
            perp_wall_dist = side_dist_y - delta_dist_y

        # Hit point
        hit_x = px + perp_wall_dist * ray_dir_x
        hit_y = py + perp_wall_dist * ray_dir_y

        # Fish-eye correction
        corrected_dist = perp_wall_dist * fish_eye_table[i]

        results[i, 0] = perp_wall_dist
        results[i, 1] = float64(side)
        results[i, 2] = hit_x
        results[i, 3] = hit_y
        results[i, 4] = float64(wall_dir)
        results[i, 5] = corrected_dist

    return results


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

        # Cached walls array
        self._walls_cache = None
        self._walls_id = None

        # Blockmap cache
        self._blockmap_cache = None
        self._blockmap_walls_hash = None

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

    def _get_walls_array(self, walls):
        """Convert walls to numpy int32 array (with caching)"""
        walls_id = id(walls)
        if self._walls_id != walls_id or self._walls_cache is None:
            if isinstance(walls, np.ndarray):
                self._walls_cache = walls.astype(np.int32)
            else:
                self._walls_cache = np.array(walls, dtype=np.int32)
            self._walls_id = walls_id
        return self._walls_cache

    def cast_all_rays(self, walls, cols, rows, px, py, player_angle):
        """
        Cast all rays for the screen using Numba JIT

        Returns:
            numpy array shape (num_rays, 6):
            [dist, side, hit_x, hit_y, wall_dir, corrected_dist]
        """
        walls_arr = self._get_walls_array(walls)
        return _numba_cast_all_rays(
            walls_arr, int32(cols), int32(rows),
            float64(px), float64(py), float64(player_angle),
            float64(self.fov_rad), float64(self.half_fov_rad),
            int32(self.num_rays), self._fish_eye_table
        )

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

    def _get_blockmap(self, walls, cols, rows):
        """Blok xarita yaratish (kesh bilan)"""
        walls_arr = self._get_walls_array(walls)
        walls_hash = hash(walls_arr.data.tobytes())
        if self._blockmap_walls_hash != walls_hash or self._blockmap_cache is None:
            self._blockmap_cache = walls_to_blockmap(walls_arr, int32(cols), int32(rows))
            self._blockmap_walls_hash = walls_hash
        return self._blockmap_cache

    def invalidate_blockmap(self):
        """Blok xarita keshini tozalash"""
        self._blockmap_cache = None
        self._blockmap_walls_hash = None

    def cast_all_rays_blockmap(self, walls, cols, rows, px, py, player_angle):
        """
        Blok xarita orqali nurlarni otish.
        Devorlar qalin ko'rinadi — har bir devor segmenti to'liq katakcha.

        Returns:
            numpy array shape (num_rays, 6):
            [dist, side, hit_x, hit_y, wall_dir, corrected_dist]
        """
        blockmap = self._get_blockmap(walls, cols, rows)
        bm_h, bm_w = blockmap.shape

        # O'yinchi pozitsiyasini blok xarita koordinatalariga o'tkazish
        bpx, bpy = pos_to_blockmap(float64(px), float64(py))

        return blockmap_cast_all_rays(
            blockmap, int32(bm_w), int32(bm_h),
            float64(bpx), float64(bpy), float64(player_angle),
            float64(self.fov_rad), float64(self.half_fov_rad),
            int32(self.num_rays), self._fish_eye_table
        )

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
