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
                      pitch_offset):
    """
    Draw wall slices to frame buffer (Numba JIT compiled)
    Uses Y-shearing for pitch (no keystone distortion).

    Args:
        ray_results: numpy array (num_rays, 6) from cast_all_rays
        frame_buffer: numpy array (width, height, 3) uint8
        tex_ns: numpy array (tex_size, tex_size, 3) uint8 - N/S wall texture
        tex_ew: numpy array (tex_size, tex_size, 3) uint8 - E/W wall texture
        render_height: screen height
        tex_size: texture dimension (e.g. 64)
        z_buffer: numpy array (width,) float32
        pitch_offset: horizon shift in pixels (int32)
    """
    top = int32(1)
    bottom = int32(4)
    right = int32(2)

    num_rays = ray_results.shape[0]
    half_h = float64(render_height) / 2.0
    horizon = half_h + float64(pitch_offset)

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

        # Y-shearing: wall height = render_height / d, centered on horizon
        wall_height = float64(render_height) / d
        full_top = int32(horizon - wall_height * 0.5)
        full_bottom = int32(horizon + wall_height * 0.5)

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

        # Shading (grid masofalar kattaroq — 25.0 bilan normallashtirish)
        shade = 1.0 - (corrected_dist / 25.0)
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
                               pitch_offset):
    """
    Draw perspective floor and ceiling with checkerboard pattern (Numba JIT)
    Uses Y-shearing for pitch.
    """
    half_h = float64(render_height) / 2.0
    horizon = half_h + float64(pitch_offset)

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
        dy = float64(y) - horizon

        if abs(dy) < 0.5:
            # Horizon line — draw dark
            for x in range(num_rays):
                frame_buffer[x, y, 0] = 20
                frame_buffer[x, y, 1] = 20
                frame_buffer[x, y, 2] = 25
            continue

        row_dist = half_h / abs(dy)
        is_floor = (dy > 0.0)

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
        shade = 1.0 - row_dist / 20.0
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
        # Target render area on actual screen (top viewport above HUD)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.render_height = screen_height
        self.fov = fov

        # Internal render resolution scaling for fullscreen performance.
        # The scene is rendered to a smaller buffer and scaled up to target area.
        self._base_render_pixels = 1280 * 720
        self._min_scale = 0.55
        self._max_scale = 1.0
        self._quality_boost = 1.0
        self._quality_hold_frames = 0
        self._ema_frame_ms = 1000.0 / 60.0
        self._quality_warmup_frames = 120
        self._min_internal_width = 480
        self._min_internal_height = 270
        self.internal_width = screen_width
        self.internal_height = screen_height
        self._internal_scale = 1.0

        # Initialize components
        self.raycaster = Raycaster(fov=fov, num_rays=screen_width)
        self.texture_manager = TextureManager(texture_size=64)

        # Pre-load textures as NumPy arrays
        self.wall_textures = self.texture_manager.get_wall_textures()
        self.wall_texture_arrays = self.texture_manager.get_wall_texture_arrays()

        # Pre-convert texture arrays to contiguous uint8 for Numba
        self._tex_ns = np.ascontiguousarray(self.wall_texture_arrays['ns'], dtype=np.uint8)
        self._tex_ew = np.ascontiguousarray(self.wall_texture_arrays['ew'], dtype=np.uint8)

        # Frame buffers and surfaces are (re)allocated in _resize_internal_buffers()
        self.frame_buffer = None
        self.z_buffer = None
        self._render_surface = None
        self._scaled_surface = None
        self._resize_internal_buffers(screen_width, screen_height, reset_quality=True, force=True)

        # Sprite FOV korreksiya koeffitsienti
        self._sprite_fov_factor = 1.0 / math.tan(self.raycaster.half_fov_rad)

        # Pre-rendered sprite surfaces
        self._sprite_cache = {}
        self._init_sprite_surfaces()

    def _compute_base_scale(self, target_w, target_h):
        """Compute baseline internal render scale from target pixel count."""
        pixels = float(target_w * target_h)
        if pixels <= float(self._base_render_pixels):
            return 1.0
        scale = math.sqrt(float(self._base_render_pixels) / pixels)
        return max(self._min_scale, min(self._max_scale, scale))

    def _resize_internal_buffers(self, target_w, target_h, reset_quality=False, force=False):
        """Resize internal render resolution and dependent buffers."""
        self.screen_width = int(max(1, target_w))
        self.screen_height = int(max(1, target_h))
        self.render_height = int(max(1, target_h))

        if reset_quality:
            self._quality_boost = 1.0
            self._quality_hold_frames = 0
            self._quality_warmup_frames = 90

        base_scale = self._compute_base_scale(self.screen_width, self.render_height)
        internal_scale = max(self._min_scale, min(self._max_scale, base_scale * self._quality_boost))
        int_w = int(round(self.screen_width * internal_scale))
        int_h = int(round(self.render_height * internal_scale))
        int_w = min(self.screen_width, max(self._min_internal_width, int_w))
        int_h = min(self.render_height, max(self._min_internal_height, int_h))

        same_internal = (
            self.frame_buffer is not None and
            int_w == self.internal_width and int_h == self.internal_height
        )
        same_scaled_surface = (
            self._scaled_surface is not None and
            self._scaled_surface.get_size() == (self.screen_width, self.render_height)
        )

        if same_internal:
            self._internal_scale = min(
                int_w / float(max(1, self.screen_width)),
                int_h / float(max(1, self.render_height))
            )
            if not same_scaled_surface:
                self._scaled_surface = pygame.Surface((self.screen_width, self.render_height))
            return

        self._internal_scale = min(
            int_w / float(max(1, self.screen_width)),
            int_h / float(max(1, self.render_height))
        )
        self.internal_width = int_w
        self.internal_height = int_h

        self.raycaster.set_resolution(self.internal_width)
        self.frame_buffer = np.zeros((self.internal_width, self.internal_height, 3), dtype=np.uint8)
        self.z_buffer = np.full(self.internal_width, float('inf'), dtype=np.float32)
        self._render_surface = pygame.Surface((self.internal_width, self.internal_height))
        self._scaled_surface = pygame.Surface((self.screen_width, self.render_height))

    def _update_adaptive_quality(self, frame_ms):
        """Dynamically adjust internal render scale to keep FPS stable."""
        if self._quality_warmup_frames > 0:
            self._quality_warmup_frames -= 1
            return

        # Exponential moving average smooths spikes.
        self._ema_frame_ms = self._ema_frame_ms * 0.9 + frame_ms * 0.1

        if self._quality_hold_frames > 0:
            self._quality_hold_frames -= 1
            return

        # If frame time is consistently high, reduce quality quickly.
        if self._ema_frame_ms > 23.0 and self._quality_boost > 0.68:
            self._quality_boost = max(0.65, self._quality_boost - 0.08)
            self._quality_hold_frames = 45
            self._resize_internal_buffers(self.screen_width, self.render_height, reset_quality=False, force=True)
            return

        # If there is headroom, restore quality slowly.
        if self._ema_frame_ms < 14.5 and self._quality_boost < 1.0:
            self._quality_boost = min(1.0, self._quality_boost + 0.04)
            self._quality_hold_frames = 90
            self._resize_internal_buffers(self.screen_width, self.render_height, reset_quality=False, force=True)

    def _init_sprite_surfaces(self):
        """Pre-render sprite surfaces for fast blitting"""
        sprite_size = 64
        enemy_sprite_size = 128

        # Goal - green circle
        self._sprite_cache['goal'] = self._create_circle_surface(sprite_size, COLOR_GOAL)

        # Enemies - humanoid shapes
        self._sprite_cache['enemy_patrol'] = self._create_patrol_sprite(enemy_sprite_size)
        self._sprite_cache['enemy_chase'] = self._create_chase_sprite(enemy_sprite_size)
        self._sprite_cache['enemy_teleport'] = self._create_teleport_sprite(enemy_sprite_size)
        self._sprite_cache['enemy_smart'] = self._create_smart_sprite(enemy_sprite_size)

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

    def _create_humanoid_base(self, size, body_color, head_color, detail_color, eye_color):
        """Asosiy humanoid sprite yaratish"""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        s = size / 128.0  # scale factor

        # === OYOQLAR ===
        leg_w = int(12 * s)
        leg_h = int(30 * s)
        leg_y = int(90 * s)
        # Chap oyoq
        pygame.draw.rect(surface, body_color,
                         (cx - int(16 * s), leg_y, leg_w, leg_h), border_radius=int(3 * s))
        # O'ng oyoq
        pygame.draw.rect(surface, body_color,
                         (cx + int(4 * s), leg_y, leg_w, leg_h), border_radius=int(3 * s))
        # Oyoq tubi (etik)
        boot_color = (max(0, body_color[0] - 30), max(0, body_color[1] - 30), max(0, body_color[2] - 30))
        pygame.draw.rect(surface, boot_color,
                         (cx - int(18 * s), leg_y + leg_h - int(8 * s), int(14 * s), int(8 * s)),
                         border_radius=int(2 * s))
        pygame.draw.rect(surface, boot_color,
                         (cx + int(2 * s), leg_y + leg_h - int(8 * s), int(14 * s), int(8 * s)),
                         border_radius=int(2 * s))

        # === TANA (trapezoid) ===
        body_top_y = int(45 * s)
        body_bot_y = int(92 * s)
        body_points = [
            (cx - int(18 * s), body_top_y),
            (cx + int(18 * s), body_top_y),
            (cx + int(22 * s), body_bot_y),
            (cx - int(22 * s), body_bot_y),
        ]
        pygame.draw.polygon(surface, body_color, body_points)

        # Tana o'rta chizig'i (detail)
        pygame.draw.line(surface, detail_color,
                         (cx, body_top_y + int(5 * s)), (cx, body_bot_y - int(5 * s)), int(2 * s))

        # === QO'LLAR ===
        arm_w = int(10 * s)
        arm_h = int(35 * s)
        arm_y = int(48 * s)
        # Chap qo'l
        pygame.draw.rect(surface, body_color,
                         (cx - int(28 * s), arm_y, arm_w, arm_h), border_radius=int(3 * s))
        # O'ng qo'l
        pygame.draw.rect(surface, body_color,
                         (cx + int(18 * s), arm_y, arm_w, arm_h), border_radius=int(3 * s))

        # === BOSH ===
        head_r = int(16 * s)
        head_cy = int(30 * s)
        pygame.draw.circle(surface, head_color, (cx, head_cy), head_r)

        # === KO'ZLAR (yonuvchi nuqtalar + porlash) ===
        eye_y = head_cy - int(2 * s)
        eye_spacing = int(8 * s)
        eye_r = int(4 * s)
        glow_r = int(6 * s)

        # Porlash (glow)
        glow_color = (eye_color[0], eye_color[1], eye_color[2], 80)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, glow_color, (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (cx - eye_spacing - glow_r, eye_y - glow_r))
        surface.blit(glow_surf, (cx + eye_spacing - glow_r, eye_y - glow_r))

        # Ko'z nuqtalari
        pygame.draw.circle(surface, eye_color, (cx - eye_spacing, eye_y), eye_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx - eye_spacing, eye_y), int(2 * s))
        pygame.draw.circle(surface, eye_color, (cx + eye_spacing, eye_y), eye_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx + eye_spacing, eye_y), int(2 * s))

        return surface

    def _create_patrol_sprite(self, size):
        """Patrol dushman — yashil kiyim, helmet"""
        body_color = (60, 120, 60)
        head_color = (80, 140, 80)
        detail_color = (40, 90, 40)
        eye_color = (200, 255, 200)

        surface = self._create_humanoid_base(size, body_color, head_color, detail_color, eye_color)
        cx = size // 2
        s = size / 128.0

        # Helmet
        helmet_color = (70, 100, 70)
        head_cy = int(30 * s)
        head_r = int(16 * s)
        # Helmet tepa qismi
        pygame.draw.arc(surface, helmet_color,
                        (cx - head_r - int(2 * s), head_cy - head_r - int(4 * s),
                         head_r * 2 + int(4 * s), head_r + int(8 * s)),
                        0, math.pi, int(3 * s))
        # Helmet brim
        pygame.draw.line(surface, helmet_color,
                         (cx - head_r - int(4 * s), head_cy - int(4 * s)),
                         (cx + head_r + int(4 * s), head_cy - int(4 * s)), int(3 * s))

        return surface

    def _create_chase_sprite(self, size):
        """Chase dushman — qizil, shoxlar, sariq ko'zlar"""
        body_color = (160, 50, 50)
        head_color = (140, 40, 40)
        detail_color = (100, 30, 30)
        eye_color = (255, 220, 50)

        surface = self._create_humanoid_base(size, body_color, head_color, detail_color, eye_color)
        cx = size // 2
        s = size / 128.0

        # Shoxlar
        head_cy = int(30 * s)
        head_r = int(16 * s)
        horn_color = (120, 40, 40)
        # Chap shox
        pygame.draw.polygon(surface, horn_color, [
            (cx - int(12 * s), head_cy - head_r + int(4 * s)),
            (cx - int(20 * s), head_cy - head_r - int(14 * s)),
            (cx - int(6 * s), head_cy - head_r + int(2 * s)),
        ])
        # O'ng shox
        pygame.draw.polygon(surface, horn_color, [
            (cx + int(12 * s), head_cy - head_r + int(4 * s)),
            (cx + int(20 * s), head_cy - head_r - int(14 * s)),
            (cx + int(6 * s), head_cy - head_r + int(2 * s)),
        ])

        return surface

    def _create_teleport_sprite(self, size):
        """Teleport dushman — binafsha, nurli aura"""
        body_color = (120, 60, 160)
        head_color = (100, 50, 140)
        detail_color = (80, 40, 120)
        eye_color = (200, 150, 255)

        surface = self._create_humanoid_base(size, body_color, head_color, detail_color, eye_color)
        cx = size // 2
        s = size / 128.0

        # Nurli aura — atrofida yaltiroq chiziqlar
        aura_color = (180, 120, 255, 60)
        aura_r = int(50 * s)
        aura_surf = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, aura_color, (aura_r, aura_r), aura_r)
        # Ichki qism tozalash
        inner_r = int(35 * s)
        pygame.draw.circle(aura_surf, (0, 0, 0, 0), (aura_r, aura_r), inner_r)
        surface.blit(aura_surf, (cx - aura_r, int(55 * s) - aura_r))

        # Yulduz nurlar
        star_color = (200, 160, 255, 120)
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            r1 = int(40 * s)
            r2 = int(48 * s)
            x1 = cx + int(r1 * math.cos(angle))
            y1 = int(55 * s) + int(r1 * math.sin(angle))
            x2 = cx + int(r2 * math.cos(angle))
            y2 = int(55 * s) + int(r2 * math.sin(angle))
            line_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.line(line_surf, star_color, (x1, y1), (x2, y2), int(2 * s))
            surface.blit(line_surf, (0, 0))

        return surface

    def _create_smart_sprite(self, size):
        """Smart dushman — to'q ko'k, medal, epoletlar"""
        body_color = (40, 60, 120)
        head_color = (50, 70, 130)
        detail_color = (30, 45, 90)
        eye_color = (100, 180, 255)

        surface = self._create_humanoid_base(size, body_color, head_color, detail_color, eye_color)
        cx = size // 2
        s = size / 128.0

        # Epoletlar (yelka ustida)
        epaulet_color = (60, 80, 150)
        ep_y = int(44 * s)
        ep_w = int(14 * s)
        ep_h = int(6 * s)
        # Chap yelka
        pygame.draw.rect(surface, epaulet_color,
                         (cx - int(28 * s), ep_y, ep_w, ep_h), border_radius=int(2 * s))
        pygame.draw.rect(surface, (200, 180, 50),
                         (cx - int(28 * s), ep_y, ep_w, int(2 * s)))
        # O'ng yelka
        pygame.draw.rect(surface, epaulet_color,
                         (cx + int(14 * s), ep_y, ep_w, ep_h), border_radius=int(2 * s))
        pygame.draw.rect(surface, (200, 180, 50),
                         (cx + int(14 * s), ep_y, ep_w, int(2 * s)))

        # Medal (ko'krak)
        medal_y = int(60 * s)
        medal_r = int(5 * s)
        pygame.draw.circle(surface, (220, 200, 60), (cx, medal_y), medal_r)
        pygame.draw.circle(surface, (255, 230, 80), (cx, medal_y), int(3 * s))

        return surface

    def set_render_area(self, width, height):
        """Update render area dimensions"""
        self._resize_internal_buffers(width, height, reset_quality=True, force=False)

    def render(self, screen, player, level, fog_manager=None):
        """
        Render the 3D view using NumPy frame buffer

        Args:
            screen: pygame.Surface to render to
            player: Player3D instance
            level: Level instance
            fog_manager: Optional FogManager for visibility
        """
        frame_start = pygame.time.get_ticks()

        # Clear z-buffer
        self.z_buffer.fill(float('inf'))

        # 1. Draw ceiling and floor to frame buffer
        self._draw_ceiling_floor(player)

        # 2. Cast rays and draw walls to frame buffer
        self._draw_walls(player, level.grid, level.grid_cols, level.grid_rows)

        # 3. Blit internal frame buffer to internal render surface
        pygame.surfarray.blit_array(self._render_surface, self.frame_buffer)

        # 4. Draw entities on the same internal surface (shares z-buffer resolution)
        self._draw_entities(self._render_surface, player, level, fog_manager)

        # 5. Present to target render area
        if self.internal_width == self.screen_width and self.internal_height == self.render_height:
            screen.blit(self._render_surface, (0, 0))
        else:
            pygame.transform.scale(
                self._render_surface,
                (self.screen_width, self.render_height),
                self._scaled_surface
            )
            screen.blit(self._scaled_surface, (0, 0))

        # 6. Adaptive quality based on current frame time
        elapsed_ms = float(pygame.time.get_ticks() - frame_start)
        self._update_adaptive_quality(elapsed_ms)

    def _draw_ceiling_floor(self, player):
        """Draw perspective floor and ceiling with checkerboard pattern"""
        px, py = player.world_x, player.world_y
        angle = player.angle
        half_fov = self.raycaster.half_fov_rad

        pitch_offset = int(player.pitch * self.internal_height * 0.5)

        _numba_draw_floor_ceiling(
            self.frame_buffer, self.internal_height, self.internal_width,
            px, py, angle, half_fov, int32(pitch_offset)
        )

    def _draw_walls(self, player, grid, grid_cols, grid_rows):
        """Draw walls using raycasting with Numba JIT optimization"""
        px, py = player.world_x, player.world_y
        angle = player.angle

        # Cast all rays (returns numpy array)
        ray_results = self.raycaster.cast_all_rays_grid(
            grid, grid_rows, grid_cols, px, py, angle)

        pitch_offset = int(player.pitch * self.internal_height * 0.5)

        # Call Numba JIT function
        _numba_draw_walls(
            ray_results, self.frame_buffer,
            self._tex_ns, self._tex_ew,
            int32(self.internal_height), int32(self.texture_manager.texture_size),
            self.z_buffer, int32(pitch_offset)
        )

    def _draw_entities(self, screen, player, level, fog_manager):
        """Draw all entities as sprites using pre-rendered surfaces"""
        sprites = []

        px, py = player.world_x, player.world_y
        p_angle = player.angle

        # Collect all visible entities
        # Entity pozitsiyalari cell koordinatalarida — grid'ga convert qilish:
        # grid_x = 2 * cell_x + 1.5, grid_y = 2 * cell_y + 1.5

        # Goal
        gx, gy = level.goal_pos
        if self._is_visible(gx, gy, fog_manager):
            sprites.append({
                'x': 2 * gx + 1.5, 'y': 2 * gy + 1.5,
                'surface': self._sprite_cache['goal'],
                'size': 0.6, 'pulse': True
            })

        # Enemies
        for enemy in level.enemy_manager.enemies:
            # O'lik va animatsiya tugagan — chizilmaydi
            if not enemy.alive and enemy.death_timer <= 0:
                continue
            if self._is_visible(enemy.x, enemy.y, fog_manager):
                enemy_type = getattr(enemy, 'type', 'patrol')
                cache_key = f'enemy_{enemy_type}'
                surface = self._sprite_cache.get(cache_key, self._sprite_cache['enemy_patrol'])
                sprite_data = {
                    'x': 2 * enemy.x + 1.5, 'y': 2 * enemy.y + 1.5,
                    'surface': surface, 'size': 0.8
                }
                # Death animatsiya — kichrayish va so'lish
                if not enemy.alive and enemy.death_timer > 0:
                    death_progress = enemy.death_timer / 0.5
                    sprite_data['size'] *= death_progress
                    sprite_data['death_alpha'] = int(255 * death_progress)
                # Flash — otib tegildi
                if enemy.flash_timer > 0:
                    sprite_data['flash_alpha'] = int(200 * (enemy.flash_timer / 0.15))
                sprites.append(sprite_data)

        # Power-ups
        for powerup in level.powerup_manager.get_uncollected_powerups():
            if self._is_visible(powerup.x, powerup.y, fog_manager):
                powerup_type = getattr(powerup, 'powerup_type', 'energy')
                cache_key = f'powerup_{powerup_type}'
                surface = self._sprite_cache.get(cache_key, self._sprite_cache['powerup_energy'])
                sprites.append({
                    'x': 2 * powerup.x + 1.5, 'y': 2 * powerup.y + 1.5,
                    'surface': surface, 'size': 0.3, 'pulse': True
                })

        # Keys
        for key in level.door_manager.keys:
            if not key.collected and self._is_visible(key.x, key.y, fog_manager):
                sprites.append({
                    'x': 2 * key.x + 1.5, 'y': 2 * key.y + 1.5,
                    'surface': self._sprite_cache['key'],
                    'size': 0.35
                })

        # Traps
        for trap in level.trap_manager.get_visible_traps():
            if self._is_visible(trap.x, trap.y, fog_manager):
                sprites.append({
                    'x': 2 * trap.x + 1.5, 'y': 2 * trap.y + 1.5,
                    'surface': self._sprite_cache['trap'],
                    'size': 0.4
                })

        # Boss
        if level.boss_manager.active:
            boss = level.boss_manager.get_boss()
            if boss and boss.alive and self._is_visible(boss.x, boss.y, fog_manager):
                sprites.append({
                    'x': 2 * boss.x + 1.5, 'y': 2 * boss.y + 1.5,
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
        """Draw a single sprite using pre-rendered surface with Y-shearing"""
        px, py = player.world_x, player.world_y
        p_angle = player.angle
        view_w = self.internal_width
        view_h = self.internal_height

        dx = sprite['x'] - px
        dy = sprite['y'] - py
        dist = sprite['dist']

        if dist < 0.1:
            return

        # Transform to player view space
        cos_a = math.cos(p_angle)
        sin_a = math.sin(p_angle)

        transform_x = -sin_a * dx + cos_a * dy
        transform_y = cos_a * dx + sin_a * dy

        if transform_y <= 0.1:
            return  # Behind player

        # Calculate screen position (FOV korreksiyali)
        sprite_screen_x = int((view_w / 2) * (1 + transform_x / transform_y * self._sprite_fov_factor))

        # Y-shearing for sprite
        h = view_h
        pitch_offset = int(player.pitch * h * 0.5)
        horizon = h // 2 + pitch_offset
        base_size = sprite['size']

        sprite_height = int(abs(h / transform_y) * base_size)
        sprite_width = sprite_height

        if sprite_width <= 0 or sprite_height <= 0:
            return

        # Minimal sprite size
        sprite_height = max(sprite_height, 8)
        sprite_width = max(sprite_width, 8)

        # Clamp size
        sprite_width = min(sprite_width, view_w * 2)
        sprite_height = min(sprite_height, view_h * 2)

        draw_x = sprite_screen_x - sprite_width // 2
        draw_y = horizon - sprite_height // 2

        # Check if on screen
        if draw_x + sprite_width < 0 or draw_x >= view_w:
            return
        if draw_y + sprite_height < 0 or draw_y >= view_h:
            return

        # Check z-buffer for visibility
        screen_x_start = max(0, draw_x)
        screen_x_end = min(view_w, draw_x + sprite_width)

        visible = False
        for x in range(screen_x_start, screen_x_end):
            if transform_y < self.z_buffer[x]:
                visible = True
                break

        if not visible:
            return

        # Scale sprite surface (favor speed in fullscreen/high-res scenes).
        if self._internal_scale >= 0.95 and sprite_width <= 96 and sprite_height <= 96:
            scaled = pygame.transform.smoothscale(sprite['surface'], (sprite_width, sprite_height))
        else:
            scaled = pygame.transform.scale(sprite['surface'], (sprite_width, sprite_height))

        # Apply distance shading
        shade = max(0.3, min(1.0, 1.0 - (dist / 20.0)))

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

        # Death alpha — so'lib borish
        death_alpha = sprite.get('death_alpha')
        if death_alpha is not None:
            scaled.set_alpha(death_alpha)

        # Flash overlay — otib tegilganda oq miltillash
        flash_alpha = sprite.get('flash_alpha')
        if flash_alpha is not None and flash_alpha > 0:
            flash_overlay = pygame.Surface((sprite_width, sprite_height))
            flash_overlay.fill((255, 255, 255))
            flash_overlay.set_alpha(min(255, flash_alpha))
            scaled.blit(flash_overlay, (0, 0))

        # Blit to screen
        screen.blit(scaled, (draw_x, draw_y))
