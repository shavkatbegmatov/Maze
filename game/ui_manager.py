"""
UI Manager - handles all UI rendering (HUD, menus, screens)
"""

import pygame
from utils.colors import (
    COLOR_TEXT, COLOR_TEXT_HIGHLIGHT, COLOR_TEXT_DIM,
    COLOR_HEALTH_BAR_BG, COLOR_HEALTH_BAR_FULL, COLOR_HEALTH_BAR_LOW,
    COLOR_ENERGY_BAR, COLOR_PANEL_BG, COLOR_MENU_SELECTION, COLOR_MENU_BORDER,
    KEY_COLORS
)
from utils.helpers import format_time, format_score
from utils.constants import DIFFICULTY_NAMES


class UIManager:
    """
    Manages all UI rendering
    """
    def __init__(self):
        # Fonts
        self.font_small = None
        self.font_medium = None
        self.font_large = None
        self.font_title = None
        self._init_fonts()

    def _init_fonts(self):
        """Initialize fonts"""
        pygame.font.init()
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.font_medium = pygame.font.SysFont("consolas", 18)
        self.font_large = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 48, bold=True)

    def draw_hud(self, screen, player, level, panel_y, screen_w, panel_h):
        """
        Draw HUD (Heads-Up Display)

        Args:
            screen: Pygame screen
            player: Player object
            level: Current level
            panel_y: Y position of panel
            screen_w: Screen width
            panel_h: Panel height
        """
        # Panel background
        pygame.draw.rect(screen, COLOR_PANEL_BG, (0, panel_y, screen_w, panel_h))

        # Health bar (top left)
        self._draw_health_bar(screen, player, 10, panel_y + 10, 200, 20)

        # Energy bar (below health)
        self._draw_energy_bar(screen, player, 10, panel_y + 35, 200, 15)

        # Timer (top center)
        self._draw_timer(screen, level, screen_w // 2, panel_y + 10)

        # Key inventory (top right)
        self._draw_key_inventory(screen, player, screen_w - 150, panel_y + 10)

        # Active effects (bottom left)
        self._draw_active_effects(screen, player, 10, panel_y + panel_h - 25)

        # Stats (bottom right)
        self._draw_stats(screen, player, level, screen_w - 200, panel_y + 55)

    def _draw_health_bar(self, screen, player, x, y, width, height):
        """Draw health bar"""
        # Background
        pygame.draw.rect(screen, COLOR_HEALTH_BAR_BG, (x, y, width, height), border_radius=4)

        # Health fill
        health_percent = player.get_health_percent()
        fill_width = int(width * health_percent)

        if health_percent > 0.5:
            color = COLOR_HEALTH_BAR_FULL
        elif health_percent > 0.25:
            color = (220, 200, 80)  # Yellow
        else:
            color = COLOR_HEALTH_BAR_LOW

        if fill_width > 0:
            pygame.draw.rect(screen, color, (x, y, fill_width, height), border_radius=4)

        # Border
        pygame.draw.rect(screen, (200, 200, 200), (x, y, width, height), 2, border_radius=4)

        # Text
        text = self.font_small.render(
            f"Health: {int(player.stats['health'])}/{int(player.stats['max_health'])}",
            True, COLOR_TEXT
        )
        screen.blit(text, (x + width + 10, y + 3))

    def _draw_energy_bar(self, screen, player, x, y, width, height):
        """Draw energy bar"""
        # Background
        pygame.draw.rect(screen, COLOR_HEALTH_BAR_BG, (x, y, width, height), border_radius=3)

        # Energy fill
        energy_percent = player.get_energy_percent()
        fill_width = int(width * energy_percent)

        if fill_width > 0:
            pygame.draw.rect(screen, COLOR_ENERGY_BAR, (x, y, fill_width, height), border_radius=3)

        # Border
        pygame.draw.rect(screen, (180, 180, 180), (x, y, width, height), 2, border_radius=3)

        # Text
        text = self.font_small.render(
            f"Energy: {int(player.stats['energy'])}/{int(player.stats['max_energy'])}",
            True, COLOR_TEXT
        )
        screen.blit(text, (x + width + 10, y + 1))

    def _draw_timer(self, screen, level, x, y):
        """Draw timer"""
        time_remaining = level.get_time_remaining()

        if time_remaining is not None:
            time_str = format_time(time_remaining)

            # Color warning if time running out
            if time_remaining < 30:
                color = (255, 100, 100)
            elif time_remaining < 60:
                color = (255, 200, 100)
            else:
                color = COLOR_TEXT

            text = self.font_large.render(time_str, True, color)
            text_rect = text.get_rect(center=(x, y + 15))
            screen.blit(text, text_rect)
        else:
            # No time limit
            text = self.font_medium.render("No Time Limit", True, COLOR_TEXT_DIM)
            text_rect = text.get_rect(center=(x, y + 15))
            screen.blit(text, text_rect)

    def _draw_key_inventory(self, screen, player, x, y):
        """Draw key inventory"""
        label = self.font_small.render("Keys:", True, COLOR_TEXT)
        screen.blit(label, (x, y))

        # Draw keys
        key_x = x + 50
        for i, key_color in enumerate(player.inventory['keys']):
            color_rgb = KEY_COLORS.get(key_color, (255, 255, 255))
            pygame.draw.rect(screen, color_rgb, (key_x + i * 25, y, 20, 20), border_radius=4)
            pygame.draw.rect(screen, (200, 200, 200), (key_x + i * 25, y, 20, 20), 2, border_radius=4)

    def _draw_active_effects(self, screen, player, x, y):
        """Draw active power-up effects"""
        effects = player.get_active_effects()

        if effects:
            text = self.font_small.render(f"Effects: {', '.join(effects)}", True, COLOR_TEXT_HIGHLIGHT)
            screen.blit(text, (x, y))

    def _draw_stats(self, screen, player, level, x, y):
        """Draw player stats"""
        stats = [
            f"Moves: {player.moves}",
            f"Enemies: {len(level.enemy_manager.enemies)}",
        ]

        for i, stat in enumerate(stats):
            text = self.font_small.render(stat, True, COLOR_TEXT)
            screen.blit(text, (x, y + i * 18))

    def draw_menu(self, screen, title, menu_items, selected_index, subtitle=None):
        """
        Draw a menu

        Args:
            screen: Pygame screen
            title: Menu title
            menu_items: List of menu item strings
            selected_index: Currently selected item index
            subtitle: Optional subtitle text
        """
        screen_w, screen_h = screen.get_size()

        # Title
        title_text = self.font_title.render(title, True, COLOR_TEXT_HIGHLIGHT)
        title_rect = title_text.get_rect(center=(screen_w // 2, 80))
        screen.blit(title_text, title_rect)

        # Subtitle
        if subtitle:
            subtitle_text = self.font_medium.render(subtitle, True, COLOR_TEXT)
            subtitle_rect = subtitle_text.get_rect(center=(screen_w // 2, 130))
            screen.blit(subtitle_text, subtitle_rect)

        # Menu items
        start_y = 200
        gap = 40

        for i, item in enumerate(menu_items):
            is_selected = i == selected_index
            color = COLOR_MENU_SELECTION if is_selected else COLOR_TEXT

            text = self.font_large.render(item, True, color)
            text_rect = text.get_rect(center=(screen_w // 2, start_y + i * gap))

            # Selection border
            if is_selected:
                border_rect = text_rect.inflate(40, 20)
                pygame.draw.rect(screen, COLOR_MENU_BORDER, border_rect, 3, border_radius=8)

            screen.blit(text, text_rect)

        # Help text at bottom
        help_texts = [
            "UP/DOWN: Navigate | ENTER: Select | ESC: Back/Quit"
        ]
        help_y = screen_h - 60
        for i, help_text in enumerate(help_texts):
            text = self.font_small.render(help_text, True, COLOR_TEXT_DIM)
            text_rect = text.get_rect(center=(screen_w // 2, help_y + i * 20))
            screen.blit(text, text_rect)

    def draw_difficulty_select(self, screen, selected_difficulty):
        """Draw difficulty selection screen"""
        screen_w, screen_h = screen.get_size()

        # Title
        title = self.font_title.render("SELECT DIFFICULTY", True, COLOR_TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(screen_w // 2, 60))
        screen.blit(title, title_rect)

        # Difficulty options
        start_y = 150
        gap = 70

        for i, name in enumerate(DIFFICULTY_NAMES):
            is_selected = i == selected_difficulty

            # Difficulty name
            color = COLOR_MENU_SELECTION if is_selected else COLOR_TEXT
            text = self.font_large.render(name, True, color)
            text_rect = text.get_rect(center=(screen_w // 2, start_y + i * gap))

            # Selection border
            if is_selected:
                border_rect = text_rect.inflate(50, 25)
                pygame.draw.rect(screen, COLOR_MENU_BORDER, border_rect, 3, border_radius=8)

            screen.blit(text, text_rect)

            # Description (small text below)
            if is_selected:
                desc = self._get_difficulty_description(i)
                desc_text = self.font_small.render(desc, True, COLOR_TEXT_DIM)
                desc_rect = desc_text.get_rect(center=(screen_w // 2, start_y + i * gap + 25))
                screen.blit(desc_text, desc_rect)

    def _get_difficulty_description(self, difficulty):
        """Get brief difficulty description"""
        descriptions = [
            "Perfect for beginners - No enemies, no time limit",
            "Moderate challenge - Basic enemies and obstacles",
            "Significant challenge - Many enemies and traps",
            "Very difficult - Smart enemies, complex maze",
            "Extreme challenge - Boss fight, dynamic maze"
        ]
        return descriptions[difficulty] if difficulty < len(descriptions) else ""

    def draw_level_complete(self, screen, score, time_taken, moves):
        """Draw level complete screen"""
        screen_w, screen_h = screen.get_size()

        # Title
        title = self.font_title.render("LEVEL COMPLETE!", True, (100, 255, 150))
        title_rect = title.get_rect(center=(screen_w // 2, screen_h // 2 - 100))
        screen.blit(title, title_rect)

        # Stats
        stats = [
            f"Score: {format_score(score)}",
            f"Time: {format_time(time_taken)}",
            f"Moves: {moves}"
        ]

        start_y = screen_h // 2
        for i, stat in enumerate(stats):
            text = self.font_large.render(stat, True, COLOR_TEXT)
            text_rect = text.get_rect(center=(screen_w // 2, start_y + i * 40))
            screen.blit(text, text_rect)

        # Continue prompt
        prompt = self.font_medium.render("Press ENTER to continue", True, COLOR_TEXT_HIGHLIGHT)
        prompt_rect = prompt.get_rect(center=(screen_w // 2, screen_h - 80))
        screen.blit(prompt, prompt_rect)

    def draw_game_over(self, screen, reason='died'):
        """Draw game over screen"""
        screen_w, screen_h = screen.get_size()

        # Title
        title_text = "TIME'S UP!" if reason == 'time_up' else "GAME OVER"
        title = self.font_title.render(title_text, True, (255, 100, 100))
        title_rect = title.get_rect(center=(screen_w // 2, screen_h // 2 - 50))
        screen.blit(title, title_rect)

        # Message
        if reason == 'time_up':
            msg = "You ran out of time!"
        else:
            msg = "You died!"

        message = self.font_large.render(msg, True, COLOR_TEXT)
        message_rect = message.get_rect(center=(screen_w // 2, screen_h // 2 + 20))
        screen.blit(message, message_rect)

        # Options
        options = [
            "Press R to retry",
            "Press ESC for menu"
        ]

        start_y = screen_h // 2 + 80
        for i, opt in enumerate(options):
            text = self.font_medium.render(opt, True, COLOR_TEXT_DIM)
            text_rect = text.get_rect(center=(screen_w // 2, start_y + i * 30))
            screen.blit(text, text_rect)

    def draw_paused(self, screen):
        """Draw paused overlay"""
        screen_w, screen_h = screen.get_size()

        # Semi-transparent overlay
        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Title
        title = self.font_title.render("PAUSED", True, COLOR_TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(screen_w // 2, screen_h // 2 - 50))
        screen.blit(title, title_rect)

        # Instructions
        text = self.font_large.render("Press P to resume", True, COLOR_TEXT)
        text_rect = text.get_rect(center=(screen_w // 2, screen_h // 2 + 20))
        screen.blit(text, text_rect)
