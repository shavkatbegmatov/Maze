"""
3D Scene Renderer - Main rendering pipeline for first-person view
Draws ceiling, floor, walls, entities, and HUD
"""

import pygame
import math
from .raycaster import Raycaster
from .textures import TextureManager
from utils.constants import TOP, RIGHT, BOTTOM, LEFT
from utils.colors import (
    COLOR_BG, COLOR_MAZE_BG, COLOR_PLAYER, COLOR_GOAL,
    COLOR_ENEMY_PATROL, COLOR_ENEMY_CHASE, COLOR_ENEMY_TELEPORT, COLOR_ENEMY_SMART,
    COLOR_POWERUP_SPEED, COLOR_POWERUP_VISION, COLOR_POWERUP_INVINCIBLE,
    COLOR_POWERUP_ENERGY, COLOR_TRAP_SPIKE
)


class Renderer3D:
    """
    Main 3D renderer using raycasting
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

        # Rendering height (excluding HUD)
        self.render_height = screen_height

        # Initialize components
        self.raycaster = Raycaster(fov=fov, num_rays=screen_width)
        self.texture_manager = TextureManager(texture_size=64)

        # Pre-load textures
        self.wall_textures = self.texture_manager.get_wall_textures()

        # Ceiling and floor colors
        self.ceiling_color_top = (30, 35, 45)
        self.ceiling_color_bottom = (50, 55, 65)
        self.floor_color_top = (40, 35, 30)
        self.floor_color_bottom = (20, 18, 15)

        # Z-buffer for sprite sorting
        self.z_buffer = [float('inf')] * screen_width

        # Sprite rendering cache
        self._sprite_cache = {}

    def set_render_area(self, width, height):
        """
        Update render area dimensions

        Args:
            width, height: New dimensions
        """
        self.screen_width = width
        self.screen_height = height
        self.render_height = height
        self.raycaster.set_resolution(width)
        self.z_buffer = [float('inf')] * width

    def render(self, screen, player, level, fog_manager=None):
        """
        Render the 3D view

        Args:
            screen: pygame.Surface to render to
            player: Player3D instance
            level: Level instance
            fog_manager: Optional FogManager for visibility
        """
        # Clear z-buffer
        for i in range(len(self.z_buffer)):
            self.z_buffer[i] = float('inf')

        # 1. Draw ceiling
        self._draw_ceiling(screen)

        # 2. Draw floor
        self._draw_floor(screen)

        # 3. Cast rays and draw walls
        self._draw_walls(screen, player, level.walls, level.cols, level.rows)

        # 4. Draw entities (sprites)
        self._draw_entities(screen, player, level, fog_manager)

    def _draw_ceiling(self, screen):
        """Draw gradient ceiling"""
        half_height = self.render_height // 2

        for y in range(half_height):
            # Gradient from top to horizon
            t = y / half_height
            r = int(self.ceiling_color_top[0] + (self.ceiling_color_bottom[0] - self.ceiling_color_top[0]) * t)
            g = int(self.ceiling_color_top[1] + (self.ceiling_color_bottom[1] - self.ceiling_color_top[1]) * t)
            b = int(self.ceiling_color_top[2] + (self.ceiling_color_bottom[2] - self.ceiling_color_top[2]) * t)

            pygame.draw.line(screen, (r, g, b), (0, y), (self.screen_width, y))

    def _draw_floor(self, screen):
        """Draw gradient floor"""
        half_height = self.render_height // 2

        for y in range(half_height, self.render_height):
            # Gradient from horizon to bottom
            t = (y - half_height) / half_height
            r = int(self.floor_color_top[0] + (self.floor_color_bottom[0] - self.floor_color_top[0]) * t)
            g = int(self.floor_color_top[1] + (self.floor_color_bottom[1] - self.floor_color_top[1]) * t)
            b = int(self.floor_color_top[2] + (self.floor_color_bottom[2] - self.floor_color_top[2]) * t)

            pygame.draw.line(screen, (r, g, b), (0, y), (self.screen_width, y))

    def _draw_walls(self, screen, player, walls, cols, rows):
        """
        Draw walls using raycasting

        Args:
            screen: pygame.Surface
            player: Player3D instance
            walls: Maze walls array
            cols, rows: Maze dimensions
        """
        px, py = player.world_x, player.world_y
        angle = player.angle

        # Cast all rays
        ray_results = self.raycaster.cast_all_rays(walls, cols, rows, px, py, angle)

        # Get textures
        tex_ns = self.wall_textures['ns']
        tex_ew = self.wall_textures['ew']
        tex_size = self.texture_manager.texture_size

        # Draw each vertical slice
        for x, (dist, side, hit_x, hit_y, wall_dir, corrected_dist) in enumerate(ray_results):
            if corrected_dist <= 0:
                corrected_dist = 0.01

            # Store in z-buffer
            self.z_buffer[x] = corrected_dist

            # Calculate wall height on screen
            wall_height = int(self.render_height / corrected_dist)

            # Calculate vertical position
            draw_start = max(0, (self.render_height - wall_height) // 2)
            draw_end = min(self.render_height, (self.render_height + wall_height) // 2)

            # Get texture X coordinate
            tex_x = self.raycaster.get_wall_texture_x(hit_x, hit_y, side, wall_dir)
            tex_x_pixel = int(tex_x * tex_size) % tex_size

            # Select texture based on wall direction
            if wall_dir in (TOP, BOTTOM):
                texture = tex_ns
            else:
                texture = tex_ew

            # Apply distance shading
            shade = max(0.3, min(1.0, 1.0 - (corrected_dist / 15.0)))

            # Additional shading for E/W walls (darker)
            if side == 1:
                shade *= 0.8

            # Draw vertical texture slice
            if wall_height > 0:
                self._draw_texture_slice(
                    screen, texture, x,
                    draw_start, draw_end, wall_height,
                    tex_x_pixel, tex_size, shade
                )

    def _draw_texture_slice(self, screen, texture, x, draw_start, draw_end, wall_height, tex_x, tex_size, shade):
        """
        Draw a single vertical texture slice

        Args:
            screen: pygame.Surface
            texture: Texture surface
            x: Screen X position
            draw_start, draw_end: Vertical range to draw
            wall_height: Full wall height on screen
            tex_x: Texture X coordinate (pixel)
            tex_size: Texture dimensions
            shade: Shading factor (0.0 to 1.0)
        """
        if draw_end <= draw_start:
            return

        # Calculate texture step
        tex_step = tex_size / wall_height
        tex_y = (draw_start - (self.render_height - wall_height) / 2) * tex_step

        for y in range(draw_start, draw_end):
            # Get texture Y coordinate
            tex_y_pixel = int(tex_y) % tex_size
            tex_y += tex_step

            # Get color from texture
            color = texture.get_at((tex_x, tex_y_pixel))[:3]

            # Apply shading
            r = int(color[0] * shade)
            g = int(color[1] * shade)
            b = int(color[2] * shade)

            screen.set_at((x, y), (r, g, b))

    def _draw_entities(self, screen, player, level, fog_manager):
        """
        Draw all entities as sprites (billboard style)

        Args:
            screen: pygame.Surface
            player: Player3D instance
            level: Level instance
            fog_manager: Optional FogManager
        """
        sprites = []

        # Collect all visible entities
        px, py = player.world_x, player.world_y
        p_angle = player.angle

        # Goal
        gx, gy = level.goal_pos
        if self._is_visible(gx, gy, fog_manager):
            sprites.append({
                'x': gx + 0.5,
                'y': gy + 0.5,
                'color': COLOR_GOAL,
                'type': 'goal',
                'size': 0.6,
                'pulse': True
            })

        # Enemies
        for enemy in level.enemy_manager.enemies:
            if self._is_visible(enemy.x, enemy.y, fog_manager):
                # Get enemy color based on type
                if hasattr(enemy, 'enemy_type'):
                    if enemy.enemy_type == 'patrol':
                        color = COLOR_ENEMY_PATROL
                    elif enemy.enemy_type == 'chase':
                        color = COLOR_ENEMY_CHASE
                    elif enemy.enemy_type == 'teleport':
                        color = COLOR_ENEMY_TELEPORT
                    elif enemy.enemy_type == 'smart':
                        color = COLOR_ENEMY_SMART
                    else:
                        color = COLOR_ENEMY_PATROL
                else:
                    color = enemy.get_color() if hasattr(enemy, 'get_color') else COLOR_ENEMY_PATROL

                sprites.append({
                    'x': enemy.x + 0.5,
                    'y': enemy.y + 0.5,
                    'color': color,
                    'type': 'enemy',
                    'size': 0.5
                })

        # Power-ups
        for powerup in level.powerup_manager.get_uncollected_powerups():
            if self._is_visible(powerup.x, powerup.y, fog_manager):
                color = powerup.get_color() if hasattr(powerup, 'get_color') else COLOR_POWERUP_ENERGY
                sprites.append({
                    'x': powerup.x + 0.5,
                    'y': powerup.y + 0.5,
                    'color': color,
                    'type': 'powerup',
                    'size': 0.3,
                    'pulse': True
                })

        # Keys
        for key in level.door_manager.keys:
            if not key.collected and self._is_visible(key.x, key.y, fog_manager):
                color = key.get_color_rgb() if hasattr(key, 'get_color_rgb') else (255, 220, 100)
                sprites.append({
                    'x': key.x + 0.5,
                    'y': key.y + 0.5,
                    'color': color,
                    'type': 'key',
                    'size': 0.35
                })

        # Traps (visible ones)
        for trap in level.trap_manager.get_visible_traps():
            if self._is_visible(trap.x, trap.y, fog_manager):
                color = trap.get_color() if hasattr(trap, 'get_color') else COLOR_TRAP_SPIKE
                sprites.append({
                    'x': trap.x + 0.5,
                    'y': trap.y + 0.5,
                    'color': color,
                    'type': 'trap',
                    'size': 0.4
                })

        # Boss
        if level.boss_manager.active:
            boss = level.boss_manager.get_boss()
            if boss and boss.alive and self._is_visible(boss.x, boss.y, fog_manager):
                sprites.append({
                    'x': boss.x + 0.5,
                    'y': boss.y + 0.5,
                    'color': boss.get_color() if hasattr(boss, 'get_color') else (180, 50, 50),
                    'type': 'boss',
                    'size': 1.0
                })

        # Sort sprites by distance (farthest first)
        for sprite in sprites:
            dx = sprite['x'] - px
            dy = sprite['y'] - py
            sprite['dist'] = math.sqrt(dx * dx + dy * dy)
            # Calculate angle to sprite
            sprite['angle'] = math.atan2(dy, dx)

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
        """
        Draw a single sprite

        Args:
            screen: pygame.Surface
            sprite: Sprite data dict
            player: Player3D instance
        """
        px, py = player.world_x, player.world_y
        p_angle = player.angle

        # Calculate relative position
        dx = sprite['x'] - px
        dy = sprite['y'] - py
        dist = sprite['dist']

        if dist < 0.1:
            return  # Too close

        # Check if in front of player
        # Transform to player view space
        inv_det = 1.0 / (math.cos(p_angle + math.pi / 2) * math.sin(p_angle) -
                         math.sin(p_angle + math.pi / 2) * math.cos(p_angle))

        transform_x = inv_det * (math.cos(p_angle + math.pi / 2) * dx - math.cos(p_angle) * dy)
        transform_y = inv_det * (-math.sin(p_angle + math.pi / 2) * dx + math.sin(p_angle) * dy)

        if transform_y <= 0:
            return  # Behind player

        # Calculate screen position
        sprite_screen_x = int((self.screen_width / 2) * (1 + transform_x / transform_y))

        # Calculate size on screen
        base_size = sprite['size']
        sprite_height = int(abs(self.render_height / transform_y) * base_size)
        sprite_width = sprite_height

        # Vertical position
        draw_start_y = max(0, self.render_height // 2 - sprite_height // 2)
        draw_end_y = min(self.render_height, self.render_height // 2 + sprite_height // 2)

        # Horizontal position
        draw_start_x = max(0, sprite_screen_x - sprite_width // 2)
        draw_end_x = min(self.screen_width, sprite_screen_x + sprite_width // 2)

        # Pulsing effect
        pulse_factor = 1.0
        if sprite.get('pulse', False):
            pulse_factor = 0.8 + 0.2 * abs(math.sin(pygame.time.get_ticks() * 0.005))

        # Distance shading
        shade = max(0.3, min(1.0, 1.0 - (dist / 12.0)))

        # Apply pulsing and shading to color
        r = int(min(255, sprite['color'][0] * shade * pulse_factor))
        g = int(min(255, sprite['color'][1] * shade * pulse_factor))
        b = int(min(255, sprite['color'][2] * shade * pulse_factor))
        color = (r, g, b)

        # Draw sprite (only pixels not behind walls)
        for x in range(draw_start_x, draw_end_x):
            if x < 0 or x >= self.screen_width:
                continue
            if transform_y >= self.z_buffer[x]:
                continue  # Behind wall

            # Draw vertical stripe of sprite
            sprite_type = sprite['type']

            for y in range(draw_start_y, draw_end_y):
                # Calculate position within sprite
                rel_x = (x - draw_start_x) / max(1, draw_end_x - draw_start_x)
                rel_y = (y - draw_start_y) / max(1, draw_end_y - draw_start_y)

                # Different shapes based on type
                draw = False

                if sprite_type == 'goal':
                    # Circle
                    cx, cy = 0.5, 0.5
                    dist_to_center = math.sqrt((rel_x - cx) ** 2 + (rel_y - cy) ** 2)
                    draw = dist_to_center < 0.4

                elif sprite_type == 'enemy':
                    # Diamond shape
                    cx, cy = 0.5, 0.5
                    dist_to_center = abs(rel_x - cx) + abs(rel_y - cy)
                    draw = dist_to_center < 0.45

                elif sprite_type == 'boss':
                    # Large hexagon
                    cx, cy = 0.5, 0.5
                    # Approximate hexagon as a large diamond
                    dist_to_center = abs(rel_x - cx) * 0.8 + abs(rel_y - cy)
                    draw = dist_to_center < 0.45

                elif sprite_type == 'powerup':
                    # Small circle
                    cx, cy = 0.5, 0.5
                    dist_to_center = math.sqrt((rel_x - cx) ** 2 + (rel_y - cy) ** 2)
                    draw = dist_to_center < 0.35

                elif sprite_type == 'key':
                    # Key shape (circle on top, rectangle below)
                    if rel_y < 0.5:
                        cx, cy = 0.5, 0.25
                        dist_to_center = math.sqrt((rel_x - cx) ** 2 + (rel_y - cy) ** 2)
                        draw = dist_to_center < 0.2
                    else:
                        draw = 0.4 < rel_x < 0.6

                elif sprite_type == 'trap':
                    # Triangle (pointing up)
                    if rel_y > 0.2:
                        width_at_y = (rel_y - 0.2) * 0.8
                        draw = abs(rel_x - 0.5) < width_at_y

                else:
                    # Default square
                    draw = 0.1 < rel_x < 0.9 and 0.1 < rel_y < 0.9

                if draw:
                    screen.set_at((x, y), color)
