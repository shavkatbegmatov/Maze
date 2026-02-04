"""
Fog of War system - limits player vision and creates atmosphere
"""

import pygame
import math
from utils.colors import COLOR_FOG
from utils.constants import CELL_SIZE


class FogOfWar:
    """
    Fog of War system that limits player's vision
    """
    def __init__(self, cols, rows):
        """
        Args:
            cols, rows: Maze dimensions
        """
        self.cols = cols
        self.rows = rows

        # Track explored cells (cells player has seen)
        self.explored = [[False for _ in range(cols)] for _ in range(rows)]

        # Current visible cells (within vision range this frame)
        self.visible = [[False for _ in range(cols)] for _ in range(rows)]

        # Fog surfaces (for optimization)
        self.fog_surface = None
        self.fog_cache_valid = False

    def update(self, player_x, player_y, vision_range):
        """
        Update fog of war based on player position

        Args:
            player_x, player_y: Player position
            vision_range: How far player can see
        """
        # Reset visible cells
        for y in range(self.rows):
            for x in range(self.cols):
                self.visible[y][x] = False

        # Calculate visible cells using radial distance
        for y in range(self.rows):
            for x in range(self.cols):
                # Manhattan distance (faster than Euclidean)
                dist = abs(x - player_x) + abs(y - player_y)

                if dist <= vision_range:
                    self.visible[y][x] = True
                    self.explored[y][x] = True

        self.fog_cache_valid = False

    def is_visible(self, x, y):
        """Check if cell is currently visible"""
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return False
        return self.visible[y][x]

    def is_explored(self, x, y):
        """Check if cell has been explored (seen before)"""
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return False
        return self.explored[y][x]

    def get_cell_visibility(self, x, y, player_x, player_y, vision_range):
        """
        Get visibility level of a cell (0.0 = invisible, 1.0 = fully visible)
        Uses gradient based on distance from player

        Returns:
            float: Visibility level (0.0 to 1.0)
        """
        if not self.is_visible(x, y):
            # If explored but not visible, show dimly
            if self.is_explored(x, y):
                return 0.2
            return 0.0

        # Calculate distance
        dist = math.sqrt((x - player_x)**2 + (y - player_y)**2)

        # Gradient: fully visible up close, fades at edge
        if dist <= vision_range * 0.6:
            return 1.0
        elif dist <= vision_range:
            # Fade from 1.0 to 0.5 at edge
            fade = 1.0 - (dist - vision_range * 0.6) / (vision_range * 0.4)
            return 0.5 + fade * 0.5
        else:
            return 0.2 if self.is_explored(x, y) else 0.0

    def render_fog(self, screen, player_x, player_y, vision_range):
        """
        Render fog of war overlay

        Args:
            screen: Pygame screen
            player_x, player_y: Player position
            vision_range: Vision range
        """
        screen_w, screen_h = screen.get_size()

        # Create fog surface if needed
        if self.fog_surface is None or not self.fog_cache_valid:
            self.fog_surface = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self.fog_surface.fill((0, 0, 0, 0))  # Clear

            # Draw fog over each cell
            for y in range(self.rows):
                for x in range(self.cols):
                    visibility = self.get_cell_visibility(x, y, player_x, player_y, vision_range)

                    if visibility < 1.0:
                        # Calculate fog alpha (0 = visible, 255 = completely dark)
                        alpha = int((1.0 - visibility) * 255)
                        alpha = min(255, max(0, alpha))

                        # Draw fog rectangle
                        fog_color = (*COLOR_FOG[:3], alpha)
                        rect = pygame.Rect(
                            x * CELL_SIZE,
                            y * CELL_SIZE,
                            CELL_SIZE,
                            CELL_SIZE
                        )
                        pygame.draw.rect(self.fog_surface, fog_color, rect)

            self.fog_cache_valid = True

        # Blit fog surface
        screen.blit(self.fog_surface, (0, 0))

    def render_fog_gradient(self, screen, player_x, player_y, vision_range):
        """
        Render fog with smooth radial gradient
        More expensive but prettier

        Args:
            screen: Pygame screen
            player_x, player_y: Player position in grid coordinates
            vision_range: Vision range in grid cells
        """
        screen_w, screen_h = screen.get_size()
        fog_surface = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

        # Player center in pixels
        player_center_x = player_x * CELL_SIZE + CELL_SIZE // 2
        player_center_y = player_y * CELL_SIZE + CELL_SIZE // 2

        # Vision radius in pixels
        vision_radius_px = vision_range * CELL_SIZE

        # Draw gradient circles
        num_circles = 30
        for i in range(num_circles):
            # Radius from edge to beyond vision range
            radius = vision_radius_px + (i / num_circles) * CELL_SIZE * 3

            # Alpha increases as we go outward
            alpha = int((i / num_circles) * 200)

            # Draw circle
            color = (*COLOR_FOG[:3], alpha)
            try:
                pygame.draw.circle(
                    fog_surface,
                    color,
                    (int(player_center_x), int(player_center_y)),
                    int(radius)
                )
            except:
                pass  # Skip if too large

        screen.blit(fog_surface, (0, 0))

    def reset(self):
        """Reset fog of war (clear explored areas)"""
        self.explored = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.visible = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.fog_cache_valid = False

    def reveal_all(self):
        """Reveal entire map (for debugging or X-Ray power-up)"""
        for y in range(self.rows):
            for x in range(self.cols):
                self.visible[y][x] = True
                self.explored[y][x] = True
        self.fog_cache_valid = False


class FogManager:
    """
    Manages fog of war for the game
    """
    def __init__(self):
        self.fog = None
        self.enabled = False
        self.use_gradient = True  # Use prettier gradient rendering
        self.xray_active = False
        self.xray_timer = 0.0

    def create_fog(self, cols, rows, enabled=True):
        """
        Create new fog of war for a level

        Args:
            cols, rows: Maze dimensions
            enabled: Whether fog is enabled for this difficulty
        """
        self.fog = FogOfWar(cols, rows)
        self.enabled = enabled
        self.xray_active = False
        self.xray_timer = 0.0

    def update(self, dt, player, level):
        """
        Update fog of war

        Args:
            dt: Delta time
            player: Player object
            level: Current level
        """
        if not self.fog or not self.enabled:
            return

        # Update X-Ray timer
        if self.xray_timer > 0:
            self.xray_timer -= dt
            if self.xray_timer <= 0:
                self.xray_active = False

        # Check if player has X-Ray power-up
        if player.has_effect('xray'):
            self.xray_active = True

        # Update fog with player position and vision range
        vision_range = player.stats['vision_range']

        # X-Ray gives full vision
        if self.xray_active:
            self.fog.reveal_all()
        else:
            self.fog.update(player.x, player.y, vision_range)

    def render(self, screen, player):
        """
        Render fog of war

        Args:
            screen: Pygame screen
            player: Player object
        """
        if not self.fog or not self.enabled or self.xray_active:
            return

        vision_range = player.stats['vision_range']

        if self.use_gradient:
            self.fog.render_fog_gradient(screen, player.x, player.y, vision_range)
        else:
            self.fog.render_fog(screen, player.x, player.y, vision_range)

    def is_visible(self, x, y):
        """Check if position is visible"""
        if not self.fog or not self.enabled or self.xray_active:
            return True
        return self.fog.is_visible(x, y)

    def is_explored(self, x, y):
        """Check if position has been explored"""
        if not self.fog or not self.enabled:
            return True
        return self.fog.is_explored(x, y)

    def activate_xray(self, duration):
        """Activate X-Ray vision for duration"""
        self.xray_timer = duration
        self.xray_active = True

    def reset(self):
        """Reset fog"""
        if self.fog:
            self.fog.reset()
        self.xray_active = False
        self.xray_timer = 0.0
