"""
Minimap for 3D Mode - Shows top-down view with player, goal, and enemies
"""

import pygame
import math
from utils.colors import COLOR_PLAYER, COLOR_GOAL, COLOR_ENEMY_PATROL


class Minimap3D:
    """
    Minimap overlay for 3D mode showing explored areas
    """

    def __init__(self, width=150, height=100):
        """
        Initialize minimap

        Args:
            width, height: Minimap dimensions in pixels
        """
        self.width = width
        self.height = height
        self.margin = 10

        # Colors
        self.bg_color = (20, 22, 28, 200)
        self.border_color = (60, 65, 75)
        self.wall_color = (100, 100, 110)
        self.explored_color = (40, 45, 55)
        self.unexplored_color = (25, 28, 35)
        self.player_color = COLOR_PLAYER
        self.goal_color = COLOR_GOAL
        self.enemy_color = COLOR_ENEMY_PATROL
        self.fov_color = (70, 140, 255, 80)

        # Create minimap surface
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)

    def render(self, screen, player, level, fog_manager=None, position='top-right'):
        """
        Render minimap on screen

        Args:
            screen: pygame.Surface to render to
            player: Player3D instance
            level: Level instance
            fog_manager: Optional FogManager for visibility
            position: 'top-right', 'top-left', 'bottom-right', 'bottom-left'
        """
        screen_w, screen_h = screen.get_size()

        # Calculate position
        if position == 'top-right':
            x = screen_w - self.width - self.margin
            y = self.margin
        elif position == 'top-left':
            x = self.margin
            y = self.margin
        elif position == 'bottom-right':
            x = screen_w - self.width - self.margin
            y = screen_h - self.height - self.margin
        else:  # bottom-left
            x = self.margin
            y = screen_h - self.height - self.margin

        # Clear minimap surface
        self.surface.fill((0, 0, 0, 0))

        # Draw background
        pygame.draw.rect(self.surface, self.bg_color, (0, 0, self.width, self.height), border_radius=5)

        # Grid asosida scale hisoblash
        # Grid o'lchami: (2*cols+1) x (2*rows+1)
        grid_w = 2 * level.cols + 1
        grid_h = 2 * level.rows + 1
        inner_w = self.width - 10
        inner_h = self.height - 20
        scale_x = inner_w / grid_w
        scale_y = inner_h / grid_h

        # Draw grid (devorlar va bo'shliqlar kvadrat bloklar sifatida)
        self._draw_grid(level, fog_manager, scale_x, scale_y)

        # Draw goal
        self._draw_goal(level, scale_x, scale_y, fog_manager)

        # Draw enemies
        self._draw_enemies(level, scale_x, scale_y, fog_manager)

        # Draw player position and direction
        self._draw_player(player, scale_x, scale_y)

        # Draw border
        pygame.draw.rect(self.surface, self.border_color, (0, 0, self.width, self.height), 2, border_radius=5)

        # Draw label
        font = pygame.font.SysFont("consolas", 10)
        label = font.render("MINIMAP", True, (150, 150, 150))
        self.surface.blit(label, (5, self.height - 15))

        # Blit to screen
        screen.blit(self.surface, (x, y))

    def _draw_grid(self, level, fog_manager, scale_x, scale_y):
        """Grid asosida devorlar va bo'shliqlarni kvadrat bloklar sifatida chizish"""
        offset_x = 5
        offset_y = 5

        grid = level.grid
        grid_h, grid_w = grid.shape
        use_fog = fog_manager and fog_manager.fog and fog_manager.enabled

        for gy in range(grid_h):
            for gx in range(grid_w):
                px = int(gx * scale_x) + offset_x
                py = int(gy * scale_y) + offset_y
                pw = max(1, int((gx + 1) * scale_x) - int(gx * scale_x))
                ph = max(1, int((gy + 1) * scale_y) - int(gy * scale_y))

                # Grid cell ga mos maze cell (fog tekshirish uchun)
                cell_x = max(0, (gx - 1) // 2)
                cell_y = max(0, (gy - 1) // 2)

                if use_fog and not fog_manager.fog.explored[cell_y][cell_x]:
                    pygame.draw.rect(self.surface, self.unexplored_color, (px, py, pw, ph))
                    continue

                if grid[gy, gx] != 0:
                    # Devor — solid blok
                    pygame.draw.rect(self.surface, self.wall_color, (px, py, pw, ph))
                else:
                    # Bo'sh koridor
                    pygame.draw.rect(self.surface, self.explored_color, (px, py, pw, ph))

    def _draw_goal(self, level, scale_x, scale_y, fog_manager):
        """Draw goal position"""
        gx, gy = level.goal_pos
        offset_x = 5
        offset_y = 5

        # Only draw if visible or explored
        if fog_manager and fog_manager.fog and fog_manager.enabled:
            if not fog_manager.fog.explored[gy][gx]:
                return

        # Cell -> grid markazi: 2*cell + 1.5
        px = int((2 * gx + 1.5) * scale_x) + offset_x
        py = int((2 * gy + 1.5) * scale_y) + offset_y

        # Pulsing effect
        pulse = 2 + abs(math.sin(pygame.time.get_ticks() * 0.005)) * 2
        pygame.draw.circle(self.surface, self.goal_color, (px, py), int(pulse))

    def _draw_enemies(self, level, scale_x, scale_y, fog_manager):
        """Draw enemy positions"""
        offset_x = 5
        offset_y = 5

        for enemy in level.enemy_manager.enemies:
            # Only draw if visible
            if fog_manager and fog_manager.enabled:
                if not fog_manager.is_visible(enemy.x, enemy.y):
                    continue

            # Cell -> grid markazi: 2*cell + 1.5
            px = int((2 * enemy.x + 1.5) * scale_x) + offset_x
            py = int((2 * enemy.y + 1.5) * scale_y) + offset_y

            # Get enemy color
            color = enemy.get_color() if hasattr(enemy, 'get_color') else self.enemy_color

            pygame.draw.circle(self.surface, color, (px, py), 2)

    def _draw_player(self, player, scale_x, scale_y):
        """Draw player position and direction indicator"""
        offset_x = 5
        offset_y = 5

        # Player world pozitsiyasi allaqachon grid koordinatalarida
        px = int(player.world_x * scale_x) + offset_x
        py = int(player.world_y * scale_y) + offset_y

        # Draw FOV cone
        fov_length = 15
        fov_angle = math.radians(30)  # Half of FOV

        # Calculate FOV cone points
        angle = player.angle
        left_angle = angle - fov_angle
        right_angle = angle + fov_angle

        left_x = px + int(math.cos(left_angle) * fov_length)
        left_y = py + int(math.sin(left_angle) * fov_length)
        right_x = px + int(math.cos(right_angle) * fov_length)
        right_y = py + int(math.sin(right_angle) * fov_length)

        # Draw FOV as semi-transparent triangle
        fov_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.polygon(fov_surface, self.fov_color,
                            [(px, py), (left_x, left_y), (right_x, right_y)])
        self.surface.blit(fov_surface, (0, 0))

        # Draw direction line
        dir_length = 8
        dir_x = px + int(math.cos(angle) * dir_length)
        dir_y = py + int(math.sin(angle) * dir_length)
        pygame.draw.line(self.surface, (255, 255, 255), (px, py), (dir_x, dir_y), 2)

        # Draw player dot
        pygame.draw.circle(self.surface, self.player_color, (px, py), 3)
        pygame.draw.circle(self.surface, (255, 255, 255), (px, py), 3, 1)

    def set_size(self, width, height):
        """
        Update minimap size

        Args:
            width, height: New dimensions
        """
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
