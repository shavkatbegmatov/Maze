"""
3D Scene Renderer - Optimized with NumPy frame buffer
High-performance first-person view rendering using surfarray + Numba JIT
"""

import pygame
import pygame.surfarray
import numpy as np
import math
from numba import njit, int32, float64
from .raycaster import Raycaster
from .textures import TextureManager
from utils.constants import TOP, RIGHT, BOTTOM, LEFT
from utils.colors import (
    COLOR_BG, COLOR_MAZE_BG, COLOR_PLAYER, COLOR_GOAL,
    COLOR_ENEMY_PATROL, COLOR_ENEMY_CHASE, COLOR_ENEMY_TELEPORT, COLOR_ENEMY_SMART,
    COLOR_POWERUP_SPEED, COLOR_POWERUP_VISION, COLOR_POWERUP_INVINCIBLE,
    COLOR_POWERUP_ENERGY, COLOR_TRAP_SPIKE
)

# Wall bit constants for Numba
_TOP = int32(TOP)
_BOTTOM = int32(BOTTOM)
_RIGHT = int32(RIGHT)
_LEFT = int32(LEFT)


@njit(cache=True)
def _numba_draw_walls(ray_results, frame_buffer, tex_ns, tex_ew,
                      render_height, tex_size, z_buffer,
                      cos_pitch, sin_pitch):
    """
    Draw wall slices to frame buffer (Numba JIT compiled)
    Uses true 3D perspective projection for pitch.

    Args:
        ray_results: numpy array (num_rays, 6) from cast_all_rays
        frame_buffer: numpy array (width, height, 3) uint8
        tex_ns: numpy array (tex_size, tex_size, 3) uint8 - N/S wall texture
        tex_ew: numpy array (tex_size, tex_size, 3) uint8 - E/W wall texture
        render_height: screen height
        tex_size: texture dimension (e.g. 64)
        z_buffer: numpy array (width,) float32
        cos_pitch: cosine of pitch angle
        sin_pitch: sine of pitch angle
    """
    top = int32(1)
    bottom = int32(4)
    right = int32(2)

    num_rays = ray_results.shape[0]
    half_h = float64(render_height) / 2.0
    f = float64(render_height)  # focal length

    for x in range(num_rays):
        dist = ray_results[x, 0]
        side = int32(ray_results[x, 1])
        hit_x = ray_results[x, 2]
        hit_y = ray_results[x, 3]
        wall_dir = int32(ray_results[x, 4])
        corrected_dist = ray_results[x, 5]

        # Near clipping plane to prevent visual artifacts
        if corrected_dist < 0.1:
            corrected_dist = 0.1

        d = float64(corrected_dist)

        # Store in z-buffer
        z_buffer[x] = corrected_dist

        # True 3D projection: wall top (y_world = +0.5) and bottom (y_world = -0.5)
        # Camera transform: y_cam = y_world * cos_p - d * sin_p
        #                   z_cam = y_world * sin_p + d * cos_p
        # Screen: screen_y = half_h - f * y_cam / z_cam

        # Top edge (y_world = +0.5)
        y_c_top = 0.5 * cos_pitch - d * sin_pitch
        z_c_top = 0.5 * sin_pitch + d * cos_pitch
        if z_c_top > 0.01:
            full_top = int32(half_h - f * y_c_top / z_c_top)
        else:
            full_top = int32(-10000)

        # Bottom edge (y_world = -0.5)
        y_c_bot = -0.5 * cos_pitch - d * sin_pitch
        z_c_bot = -0.5 * sin_pitch + d * cos_pitch
        if z_c_bot > 0.01:
            full_bottom = int32(half_h - f * y_c_bot / z_c_bot)
        else:
            full_bottom = int32(render_height + 10000)

        full_height = full_bottom - full_top
        if full_height <= 0:
            continue

        # Clamp to screen
        draw_start = full_top
        if draw_start < 0:
            draw_start = 0
        draw_end = full_bottom
        if draw_end > render_height:
            draw_end = render_height

        if draw_end <= draw_start:
            continue

        # Texture X coordinate (inline get_wall_texture_x)
        if side == 1:  # E/W wall
            wall_x = hit_y - int(hit_y)
        else:  # N/S wall
            wall_x = hit_x - int(hit_x)

        if wall_dir == right or wall_dir == bottom:
            wall_x = 1.0 - wall_x

        # Ensure wall_x is strictly within [0, 1] to prevent texture bleeding
        if wall_x < 0.0:
            wall_x = 0.0
        elif wall_x >= 1.0:
            wall_x = 0.9999

        tex_x_pixel = int32(wall_x * tex_size)

        # Safety clamp (redundant with the check above but safe for float precision)
        if tex_x_pixel >= tex_size:
            tex_x_pixel = tex_size - 1
        elif tex_x_pixel < 0:
            tex_x_pixel = 0

        # Shading
        shade = 1.0 - (corrected_dist / 15.0)
        if shade < 0.3:
            shade = 0.3
        elif shade > 1.0:
            shade = 1.0
        if side == 1:
            shade *= 0.8

        # Draw each pixel in vertical slice
        for y in range(draw_start, draw_end):
            # Map screen Y to texture Y
            tex_y = int32(((y - full_top) * tex_size) / full_height)
            if tex_y < 0:
                tex_y = 0
            elif tex_y >= tex_size:
                tex_y = tex_size - 1

            # Select texture and sample
            if wall_dir == top or wall_dir == bottom:
                r = tex_ns[tex_x_pixel, tex_y, 0]
                g = tex_ns[tex_x_pixel, tex_y, 1]
                b = tex_ns[tex_x_pixel, tex_y, 2]
            else:
                r = tex_ew[tex_x_pixel, tex_y, 0]
                g = tex_ew[tex_x_pixel, tex_y, 1]
                b = tex_ew[tex_x_pixel, tex_y, 2]

            # Apply shading
            r_shaded = int32(r * shade)
            g_shaded = int32(g * shade)
            b_shaded = int32(b * shade)

            # Clamp
            if r_shaded > 255:
                r_shaded = 255
            if g_shaded > 255:
                g_shaded = 255
            if b_shaded > 255:
                b_shaded = 255

            frame_buffer[x, y, 0] = r_shaded
            frame_buffer[x, y, 1] = g_shaded
            frame_buffer[x, y, 2] = b_shaded


@njit(cache=True)
def _numba_draw_floor_ceiling(frame_buffer, render_height, num_rays,
                               px, py, player_angle, half_fov,
                               cos_pitch, sin_pitch):
    """
    Draw perspective floor and ceiling with checkerboard pattern (Numba JIT)
    Uses true 3D perspective projection for pitch.
    """
    half_h = float64(render_height) / 2.0
    f = float64(render_height)  # focal length (same as walls)

    # Ray direction at left edge and right edge of screen
    angle_left = player_angle - half_fov
    angle_right = player_angle + half_fov

    dir_lx = math.cos(angle_left)
    dir_ly = math.sin(angle_left)
    dir_rx = math.cos(angle_right)
    dir_ry = math.sin(angle_right)

    # Floor colors (checkerboard)
    floor_r1, floor_g1, floor_b1 = 55, 50, 45
    floor_r2, floor_g2, floor_b2 = 35, 32, 28

    # Ceiling colors (checkerboard)
    ceil_r1, ceil_g1, ceil_b1 = 35, 40, 55
    ceil_r2, ceil_g2, ceil_b2 = 25, 30, 42

    for y in range(render_height):
        # True 3D row distance derivation:
        # d = y_w * (f*cos_p - S*sin_p) / (S*cos_p + f*sin_p)
        # where S = half_h - y, y_w = -0.5 (floor) or +0.5 (ceiling)
        # ratio = A/B; ratio > 0 → ceiling, ratio < 0 → floor
        S = half_h - float64(y)
        A = f * cos_pitch - S * sin_pitch
        B = S * cos_pitch + f * sin_pitch

        if abs(B) < 0.001:
            # Horizon line — draw dark
            for x in range(num_rays):
                frame_buffer[x, y, 0] = 20
                frame_buffer[x, y, 1] = 20
                frame_buffer[x, y, 2] = 25
            continue

        row_dist = 0.5 * A / B

        if row_dist > 0.0:
            is_floor = False  # ceiling
        else:
            is_floor = True   # floor
            row_dist = -row_dist

        if row_dist < 0.01:
            for x in range(num_rays):
                frame_buffer[x, y, 0] = 20
                frame_buffer[x, y, 1] = 20
                frame_buffer[x, y, 2] = 25
            continue

        # Floor step — world coordinates at left and right edges for this row
        floor_step_x = row_dist * (dir_rx - dir_lx) / float64(num_rays)
        floor_step_y = row_dist * (dir_ry - dir_ly) / float64(num_rays)

        # Starting world position (left edge of screen)
        floor_x = px + row_dist * dir_lx
        floor_y = py + row_dist * dir_ly

        # Distance shading
        shade = 1.0 - row_dist / 12.0
        if shade < 0.15:
            shade = 0.15
        elif shade > 1.0:
            shade = 1.0

        for x in range(num_rays):
            # Checkerboard pattern
            fx = int(math.floor(floor_x))
            fy = int(math.floor(floor_y))
            checker = (fx + fy) & 1

            if is_floor:
                if checker:
                    r = int(floor_r1 * shade)
                    g = int(floor_g1 * shade)
                    b = int(floor_b1 * shade)
                else:
                    r = int(floor_r2 * shade)
                    g = int(floor_g2 * shade)
                    b = int(floor_b2 * shade)
            else:
                if checker:
                    r = int(ceil_r1 * shade)
                    g = int(ceil_g1 * shade)
                    b = int(ceil_b1 * shade)
                else:
                    r = int(ceil_r2 * shade)
                    g = int(ceil_g2 * shade)
                    b = int(ceil_b2 * shade)

            # Clamp
            if r > 255:
                r = 255
            elif r < 0:
                r = 0
            if g > 255:
                g = 255
            elif g < 0:
                g = 0
            if b > 255:
                b = 255
            elif b < 0:
                b = 0

            frame_buffer[x, y, 0] = r
            frame_buffer[x, y, 1] = g
            frame_buffer[x, y, 2] = b

            floor_x += floor_step_x
            floor_y += floor_step_y


class Renderer3D:
    """
    Optimized 3D renderer using NumPy frame buffer and surfarray
    """

    def __init__(self, screen_width, screen_height, fov=60):
        """
        Initialize 3D renderer

        Args:
            screen_width, screen_height: Screen dimensions
            fov: Field of view in degrees
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.fov = fov
        self.render_height = screen_height

        # Initialize components
        self.raycaster = Raycaster(fov=fov, num_rays=screen_width)
        self.texture_manager = TextureManager(texture_size=64)

        # Pre-load textures as NumPy arrays
        self.wall_textures = self.texture_manager.get_wall_textures()
        self.wall_texture_arrays = self.texture_manager.get_wall_texture_arrays()

        # Pre-convert texture arrays to contiguous uint8 for Numba
        self._tex_ns = np.ascontiguousarray(self.wall_texture_arrays['ns'], dtype=np.uint8)
        self._tex_ew = np.ascontiguousarray(self.wall_texture_arrays['ew'], dtype=np.uint8)

        # Frame buffer - RGB array (width, height, 3)
        self.frame_buffer = np.zeros((screen_width, screen_height, 3), dtype=np.uint8)

        # Z-buffer for sprite sorting
        self.z_buffer = np.full(screen_width, float('inf'), dtype=np.float32)

        # Pre-rendered sprite surfaces
        self._sprite_cache = {}
        self._init_sprite_surfaces()

    def _init_sprite_surfaces(self):
        """Pre-render sprite surfaces for fast blitting"""
        sprite_size = 64

        # Goal - green circle
        self._sprite_cache['goal'] = self._create_circle_surface(sprite_size, COLOR_GOAL)

        # Enemies - diamond shapes
        self._sprite_cache['enemy_patrol'] = self._create_diamond_surface(sprite_size, COLOR_ENEMY_PATROL)
        self._sprite_cache['enemy_chase'] = self._create_diamond_surface(sprite_size, COLOR_ENEMY_CHASE)
        self._sprite_cache['enemy_teleport'] = self._create_diamond_surface(sprite_size, COLOR_ENEMY_TELEPORT)
        self._sprite_cache['enemy_smart'] = self._create_diamond_surface(sprite_size, COLOR_ENEMY_SMART)

        # Power-ups - small circles
        self._sprite_cache['powerup_speed'] = self._create_circle_surface(sprite_size, COLOR_POWERUP_SPEED)
        self._sprite_cache['powerup_vision'] = self._create_circle_surface(sprite_size, COLOR_POWERUP_VISION)
        self._sprite_cache['powerup_invincible'] = self._create_circle_surface(sprite_size, COLOR_POWERUP_INVINCIBLE)
        self._sprite_cache['powerup_energy'] = self._create_circle_surface(sprite_size, COLOR_POWERUP_ENERGY)

        # Trap - triangle
        self._sprite_cache['trap'] = self._create_triangle_surface(sprite_size, COLOR_TRAP_SPIKE)

        # Key - key shape
        self._sprite_cache['key'] = self._create_key_surface(sprite_size, (255, 220, 100))

        # Boss - large hexagon
        self._sprite_cache['boss'] = self._create_hexagon_surface(sprite_size, (180, 50, 50))

    def _create_circle_surface(self, size, color):
        """Create a circle sprite surface with transparency"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, color, (size // 2, size // 2), size // 2 - 2)
        return surface

    def _create_diamond_surface(self, size, color):
        """Create a diamond sprite surface"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        half = size // 2
        points = [(half, 2), (size - 2, half), (half, size - 2), (2, half)]
        pygame.draw.polygon(surface, color, points)
        return surface

    def _create_triangle_surface(self, size, color):
        """Create a triangle sprite surface"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        points = [(size // 2, 2), (size - 2, size - 2), (2, size - 2)]
        pygame.draw.polygon(surface, color, points)
        return surface

    def _create_key_surface(self, size, color):
        """Create a key sprite surface"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        # Key head (circle)
        pygame.draw.circle(surface, color, (size // 2, size // 4), size // 5)
        # Key shaft
        pygame.draw.rect(surface, color, (size // 2 - 3, size // 3, 6, size // 2))
        # Key teeth
        pygame.draw.rect(surface, color, (size // 2, size * 2 // 3, size // 6, 4))
        return surface

    def _create_hexagon_surface(self, size, color):
        """Create a hexagon sprite surface"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        r = size // 2 - 2
        points = []
        for i in range(6):
            angle = math.pi / 6 + i * math.pi / 3
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))
        pygame.draw.polygon(surface, color, points)
        return surface

    def set_render_area(self, width, height):
        """Update render area dimensions"""
        self.screen_width = width
        self.screen_height = height
        self.render_height = height
        self.raycaster.set_resolution(width)

        # Reinitialize frame buffer
        self.frame_buffer = np.zeros((width, height, 3), dtype=np.uint8)
        self.z_buffer = np.full(width, float('inf'), dtype=np.float32)

    def render(self, screen, player, level, fog_manager=None):
        """
        Render the 3D view using NumPy frame buffer

        Args:
            screen: pygame.Surface to render to
            player: Player3D instance
            level: Level instance
            fog_manager: Optional FogManager for visibility
        """
        # Clear z-buffer
        self.z_buffer.fill(float('inf'))

        # 1. Draw ceiling and floor to frame buffer
        self._draw_ceiling_floor(player)

        # 2. Cast rays and draw walls to frame buffer
        self._draw_walls(player, level.walls, level.cols, level.rows)

        # 3. Create render surface and blit frame buffer
        # Use subsurface if screen is larger than render area
        screen_w, screen_h = screen.get_size()
        if screen_w == self.screen_width and screen_h == self.render_height:
            # Same size - blit directly
            pygame.surfarray.blit_array(screen, self.frame_buffer)
            render_surface = screen
        else:
            # Different size - create temp surface
            render_surface = pygame.Surface((self.screen_width, self.render_height))
            pygame.surfarray.blit_array(render_surface, self.frame_buffer)
            screen.blit(render_surface, (0, 0))

        # 4. Draw entities (sprites) directly to screen
        self._draw_entities(screen, player, level, fog_manager)

    def _draw_ceiling_floor(self, player):
        """Draw perspective floor and ceiling with checkerboard pattern"""
        px, py = player.world_x, player.world_y
        angle = player.angle
        half_fov = self.raycaster.half_fov_rad

        # True 3D pitch: tan(θ) = pitch / 2
        p = player.pitch
        hyp = math.sqrt(4.0 + p * p)
        cos_p = 2.0 / hyp
        sin_p = p / hyp

        _numba_draw_floor_ceiling(
            self.frame_buffer, self.render_height, self.screen_width,
            px, py, angle, half_fov, cos_p, sin_p
        )

    def _draw_walls(self, player, walls, cols, rows):
        """Draw walls using raycasting with Numba JIT optimization"""
        px, py = player.world_x, player.world_y
        angle = player.angle

        # Cast all rays (returns numpy array)
        ray_results = self.raycaster.cast_all_rays_blockmap(walls, cols, rows, px, py, angle)

        # True 3D pitch: tan(θ) = pitch / 2
        p = player.pitch
        hyp = math.sqrt(4.0 + p * p)
        cos_p = 2.0 / hyp
        sin_p = p / hyp

        # Call Numba JIT function
        _numba_draw_walls(
            ray_results, self.frame_buffer,
            self._tex_ns, self._tex_ew,
            int32(self.render_height), int32(self.texture_manager.texture_size),
            self.z_buffer, cos_p, sin_p
        )

    def _draw_entities(self, screen, player, level, fog_manager):
        """Draw all entities as sprites using pre-rendered surfaces"""
        sprites = []

        px, py = player.world_x, player.world_y
        p_angle = player.angle

        # Collect all visible entities
        # Goal
        gx, gy = level.goal_pos
        if self._is_visible(gx, gy, fog_manager):
            sprites.append({
                'x': gx + 0.5, 'y': gy + 0.5,
                'surface': self._sprite_cache['goal'],
                'size': 0.6, 'pulse': True
            })

        # Enemies
        for enemy in level.enemy_manager.enemies:
            if self._is_visible(enemy.x, enemy.y, fog_manager):
                enemy_type = getattr(enemy, 'enemy_type', 'patrol')
                cache_key = f'enemy_{enemy_type}'
                surface = self._sprite_cache.get(cache_key, self._sprite_cache['enemy_patrol'])
                sprites.append({
                    'x': enemy.x + 0.5, 'y': enemy.y + 0.5,
                    'surface': surface, 'size': 0.5
                })

        # Power-ups
        for powerup in level.powerup_manager.get_uncollected_powerups():
            if self._is_visible(powerup.x, powerup.y, fog_manager):
                powerup_type = getattr(powerup, 'powerup_type', 'energy')
                cache_key = f'powerup_{powerup_type}'
                surface = self._sprite_cache.get(cache_key, self._sprite_cache['powerup_energy'])
                sprites.append({
                    'x': powerup.x + 0.5, 'y': powerup.y + 0.5,
                    'surface': surface, 'size': 0.3, 'pulse': True
                })

        # Keys
        for key in level.door_manager.keys:
            if not key.collected and self._is_visible(key.x, key.y, fog_manager):
                sprites.append({
                    'x': key.x + 0.5, 'y': key.y + 0.5,
                    'surface': self._sprite_cache['key'],
                    'size': 0.35
                })

        # Traps
        for trap in level.trap_manager.get_visible_traps():
            if self._is_visible(trap.x, trap.y, fog_manager):
                sprites.append({
                    'x': trap.x + 0.5, 'y': trap.y + 0.5,
                    'surface': self._sprite_cache['trap'],
                    'size': 0.4
                })

        # Boss
        if level.boss_manager.active:
            boss = level.boss_manager.get_boss()
            if boss and boss.alive and self._is_visible(boss.x, boss.y, fog_manager):
                sprites.append({
                    'x': boss.x + 0.5, 'y': boss.y + 0.5,
                    'surface': self._sprite_cache['boss'],
                    'size': 1.0
                })

        # Calculate distance and angle for each sprite
        for sprite in sprites:
            dx = sprite['x'] - px
            dy = sprite['y'] - py
            sprite['dist'] = math.sqrt(dx * dx + dy * dy)

        # Sort by distance (farthest first)
        sprites.sort(key=lambda s: s['dist'], reverse=True)

        # Draw sprites
        for sprite in sprites:
            self._draw_sprite(screen, sprite, player)

    def _is_visible(self, x, y, fog_manager):
        """Check if position is visible"""
        if fog_manager is None or not fog_manager.enabled:
            return True
        return fog_manager.is_visible(x, y)

    def _draw_sprite(self, screen, sprite, player):
        """Draw a single sprite using pre-rendered surface with true 3D pitch"""
        px, py = player.world_x, player.world_y
        p_angle = player.angle

        dx = sprite['x'] - px
        dy = sprite['y'] - py
        dist = sprite['dist']

        if dist < 0.1:
            return

        # Transform to player view space
        cos_a = math.cos(p_angle)
        sin_a = math.sin(p_angle)
        cos_a_perp = math.cos(p_angle + math.pi / 2)
        sin_a_perp = math.sin(p_angle + math.pi / 2)

        det = cos_a_perp * sin_a - sin_a_perp * cos_a
        if abs(det) < 0.0001:
            return

        inv_det = 1.0 / det
        transform_x = inv_det * (cos_a_perp * dx - cos_a * dy)
        transform_y = inv_det * (-sin_a_perp * dx + sin_a * dy)

        if transform_y <= 0.1:
            return  # Behind player

        # Calculate screen position (horizontal)
        sprite_screen_x = int((self.screen_width / 2) * (1 + transform_x / transform_y))

        # True 3D pitch projection for sprite
        p = player.pitch
        hyp = math.sqrt(4.0 + p * p)
        cos_p = 2.0 / hyp
        sin_p = p / hyp

        d = transform_y
        base_size = sprite['size']
        half_s = base_size * 0.5
        h = self.render_height
        f = float(h)  # focal length
        half_h = h / 2.0

        # Top of sprite (y_world = +half_s)
        y_c_top = half_s * cos_p - d * sin_p
        z_c_top = half_s * sin_p + d * cos_p
        if z_c_top > 0.01:
            screen_top = half_h - f * y_c_top / z_c_top
        else:
            screen_top = -10000.0

        # Bottom of sprite (y_world = -half_s)
        y_c_bot = -half_s * cos_p - d * sin_p
        z_c_bot = -half_s * sin_p + d * cos_p
        if z_c_bot > 0.01:
            screen_bot = half_h - f * y_c_bot / z_c_bot
        else:
            screen_bot = h + 10000.0

        sprite_height = int(screen_bot - screen_top)
        sprite_width = sprite_height

        if sprite_width <= 0 or sprite_height <= 0:
            return

        # Clamp size
        sprite_width = min(sprite_width, self.screen_width * 2)
        sprite_height = min(sprite_height, self.render_height * 2)

        draw_x = sprite_screen_x - sprite_width // 2
        draw_y = int(screen_top)

        # Check if on screen
        if draw_x + sprite_width < 0 or draw_x >= self.screen_width:
            return
        if draw_y + sprite_height < 0 or draw_y >= self.render_height:
            return

        # Check z-buffer for visibility
        screen_x_start = max(0, draw_x)
        screen_x_end = min(self.screen_width, draw_x + sprite_width)

        visible = False
        for x in range(screen_x_start, screen_x_end):
            if transform_y < self.z_buffer[x]:
                visible = True
                break

        if not visible:
            return

        # Scale sprite surface
        scaled = pygame.transform.scale(sprite['surface'], (sprite_width, sprite_height))

        # Apply distance shading
        shade = max(0.3, min(1.0, 1.0 - (dist / 12.0)))

        # Apply pulsing effect
        if sprite.get('pulse', False):
            pulse = 0.8 + 0.2 * abs(math.sin(pygame.time.get_ticks() * 0.005))
            shade *= pulse

        if shade < 0.99:
            # Create darkened copy
            dark_overlay = pygame.Surface((sprite_width, sprite_height))
            dark_overlay.fill((0, 0, 0))
            dark_overlay.set_alpha(int(255 * (1 - shade)))
            scaled.blit(dark_overlay, (0, 0))

        # Blit to screen
        screen.blit(scaled, (draw_x, draw_y))
