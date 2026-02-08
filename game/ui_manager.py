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
        self._crosshair_color = (200, 200, 200)
        self._init_fonts()

    def _init_fonts(self):
        """Initialize fonts"""
        pygame.font.init()
        self.font_small = pygame.font.SysFont("consolas", 15)
        self.font_medium = pygame.font.SysFont("consolas", 20)
        self.font_large = pygame.font.SysFont("consolas", 30, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 50, bold=True)

    @staticmethod
    def _draw_panel_block(screen, rect, fill_rgb, border_rgb, radius=12, alpha=230, border_width=1):
        """Draw rounded translucent panel block."""
        x, y, w, h = rect
        if w <= 0 or h <= 0:
            return
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*fill_rgb, alpha), (0, 0, w, h), border_radius=radius)
        if border_width > 0:
            pygame.draw.rect(surf, (*border_rgb, min(255, alpha + 20)), (0, 0, w, h), border_width, border_radius=radius)
        screen.blit(surf, (x, y))

    @staticmethod
    def _clamp(value, low, high):
        """Clamp integer value to range."""
        return max(low, min(high, value))

    def _draw_stat_bar_block(self, screen, label, current, maximum, x, y, width, height, fill_color):
        """Draw modern HUD stat bar with label and numeric values."""
        # Label row
        label_text = self.font_small.render(label, True, (210, 215, 225))
        value_text = self.font_small.render(f"{int(current)}/{int(maximum)}", True, (210, 215, 225))
        screen.blit(label_text, (x, y))
        value_rect = value_text.get_rect(right=x + width, top=y)
        screen.blit(value_text, value_rect)

        bar_y = y + 18
        bar_bg = (46, 52, 64)
        pygame.draw.rect(screen, bar_bg, (x, bar_y, width, height), border_radius=8)

        pct = 0.0
        if maximum > 0:
            pct = max(0.0, min(1.0, float(current) / float(maximum)))
        fill_w = int(width * pct)
        if fill_w > 0:
            pygame.draw.rect(screen, fill_color, (x, bar_y, fill_w, height), border_radius=8)

        pygame.draw.rect(screen, (112, 120, 140), (x, bar_y, width, height), 1, border_radius=8)

    def _fit_text(self, text, max_width):
        """Trim text with ellipsis to fit the given pixel width."""
        if max_width <= 0:
            return ""
        if self.font_small.size(text)[0] <= max_width:
            return text
        ell = "..."
        low, high = 0, len(text)
        while low < high:
            mid = (low + high) // 2
            candidate = text[:mid].rstrip() + ell
            if self.font_small.size(candidate)[0] <= max_width:
                low = mid + 1
            else:
                high = mid
        cut = max(0, low - 1)
        return text[:cut].rstrip() + ell

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
        # Base panel
        pygame.draw.rect(screen, COLOR_PANEL_BG, (0, panel_y, screen_w, panel_h))
        pygame.draw.line(screen, (80, 88, 106), (0, panel_y), (screen_w, panel_y), 1)

        margin = self._clamp(panel_h // 10, 8, 18)
        gap = self._clamp(panel_h // 12, 8, 14)
        inner_y = panel_y + margin
        inner_h = max(56, panel_h - margin * 2)
        avail_w = max(220, screen_w - margin * 2)

        # Responsive 3-column split.
        left_w = self._clamp(int(avail_w * 0.33), 220, 420)
        right_w = self._clamp(int(avail_w * 0.27), 190, 340)
        center_w = avail_w - left_w - right_w - gap * 2

        min_center_w = 180
        if center_w < min_center_w:
            need = min_center_w - center_w
            shrink_left = min(need, max(0, left_w - 205))
            left_w -= shrink_left
            need -= shrink_left
            shrink_right = min(need, max(0, right_w - 180))
            right_w -= shrink_right
            center_w = avail_w - left_w - right_w - gap * 2

        max_center_w = 520
        if center_w > max_center_w:
            extra = center_w - max_center_w
            grow_right = min(extra, 340 - right_w)
            right_w += grow_right
            extra -= grow_right
            grow_left = min(extra, 420 - left_w)
            left_w += grow_left
            center_w = avail_w - left_w - right_w - gap * 2

        left_rect = (margin, inner_y, left_w, inner_h)
        center_rect = (left_rect[0] + left_w + gap, inner_y, center_w, inner_h)
        right_rect = (center_rect[0] + center_w + gap, inner_y, right_w, inner_h)

        radius = self._clamp(inner_h // 6, 8, 14)
        self._draw_panel_block(screen, left_rect, (24, 28, 36), (72, 80, 96), radius=radius, alpha=235)
        self._draw_panel_block(screen, center_rect, (24, 28, 36), (72, 80, 96), radius=radius, alpha=235)
        self._draw_panel_block(screen, right_rect, (24, 28, 36), (72, 80, 96), radius=radius, alpha=235)

        # Left: vitals
        block_pad_x = self._clamp(inner_h // 8, 10, 16)
        block_pad_y = self._clamp(inner_h // 12, 6, 12)
        lx = left_rect[0] + block_pad_x
        ly = left_rect[1] + block_pad_y
        lw = max(90, left_rect[2] - block_pad_x * 2)
        hp_h = self._clamp(inner_h // 7, 10, 16)
        en_h = self._clamp(inner_h // 8, 9, 14)
        row_gap = self._clamp(inner_h // 10, 8, 14)
        energy_y = ly + 18 + hp_h + row_gap
        self._draw_stat_bar_block(
            screen,
            "HEALTH",
            player.stats['health'],
            player.stats['max_health'],
            lx, ly, lw, hp_h,
            COLOR_HEALTH_BAR_FULL if player.get_health_percent() > 0.35 else COLOR_HEALTH_BAR_LOW
        )
        self._draw_stat_bar_block(
            screen,
            "ENERGY",
            player.stats['energy'],
            player.stats['max_energy'],
            lx, energy_y, lw, en_h, COLOR_ENERGY_BAR
        )

        effects = player.get_active_effects()
        effects_text = "Effects: " + (", ".join(effects) if effects else "None")
        effects_text = self._fit_text(effects_text, lw)
        effects_y = left_rect[1] + inner_h - self.font_small.get_height() - 6
        min_effects_y = energy_y + 18 + en_h + 4
        if effects_y >= min_effects_y:
            effects_render = self.font_small.render(
                effects_text, True, COLOR_TEXT_DIM if not effects else COLOR_TEXT_HIGHLIGHT
            )
            screen.blit(effects_render, (lx, effects_y))

        # Center: timer + run state
        cx = center_rect[0] + center_rect[2] // 2
        self._draw_timer(screen, level, cx, center_rect[1] + max(4, inner_h // 14))
        run_info_text = f"Maze: {level.cols}x{level.rows}   Difficulty: {DIFFICULTY_NAMES[level.difficulty_level]}"
        run_info_text = self._fit_text(run_info_text, center_rect[2] - 20)
        run_info = self.font_small.render(run_info_text, True, COLOR_TEXT_DIM)
        run_info_rect = run_info.get_rect(center=(cx, center_rect[1] + inner_h - self.font_small.get_height()))
        screen.blit(run_info, run_info_rect)

        # Right: keys + stats
        rx = right_rect[0] + 10
        ry = right_rect[1] + block_pad_y
        right_w_inner = right_rect[2] - 20
        compact_mode = (inner_h < 95) or (right_w_inner < 255)
        self._draw_key_inventory(screen, player, rx, ry, max_width=right_w_inner, compact=compact_mode)
        if right_w_inner >= 260:
            compact_stats = f"Moves: {player.moves}   Enemies: {len(level.enemy_manager.enemies)}   Traps: {len(level.trap_manager.traps)}"
        else:
            compact_stats = f"M:{player.moves}  E:{len(level.enemy_manager.enemies)}  T:{len(level.trap_manager.traps)}"
        compact_stats = self._fit_text(compact_stats, right_w_inner)
        stats_render = self.font_small.render(compact_stats, True, COLOR_TEXT)
        screen.blit(stats_render, (rx, right_rect[1] + inner_h - self.font_small.get_height() - 6))

        # Boss health bar (top, above maze)
        if level.boss_manager.active and level.boss_manager.fight_started:
            self._draw_boss_health_bar(screen, level.boss_manager, screen_w)

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

    def _draw_key_inventory(self, screen, player, x, y, max_width=None, compact=False):
        """Draw key inventory"""
        label = self.font_small.render("Keys:", True, COLOR_TEXT)
        screen.blit(label, (x, y))

        if compact:
            slot_size = 14
            slot_step = 17
            label_gap = label.get_width() + 8
        else:
            slot_size = 18
            slot_step = 23
            label_gap = label.get_width() + 10

        # Draw keys
        key_x = x + label_gap
        keys = player.inventory['keys']
        max_slots = len(keys)
        if max_width is not None:
            available = max_width - label_gap
            max_slots = max(0, available // slot_step)

        draw_count = min(len(keys), max_slots)
        for i in range(draw_count):
            key_color = keys[i]
            color_rgb = KEY_COLORS.get(key_color, (255, 255, 255))
            slot_x = key_x + i * slot_step
            pygame.draw.rect(screen, (45, 50, 60), (slot_x, y, slot_size, slot_size), border_radius=4)
            inset = 2 if slot_size >= 16 else 1
            pygame.draw.rect(
                screen, color_rgb,
                (slot_x + inset, y + inset, slot_size - inset * 2, slot_size - inset * 2),
                border_radius=3
            )
            pygame.draw.rect(screen, (180, 188, 206), (slot_x, y, slot_size, slot_size), 1, border_radius=4)

        if len(keys) > draw_count:
            more = self.font_small.render(f"+{len(keys) - draw_count}", True, COLOR_TEXT_DIM)
            screen.blit(more, (key_x + draw_count * slot_step, y))

        if not keys:
            empty = self.font_small.render("none", True, COLOR_TEXT_DIM)
            screen.blit(empty, (key_x, y))

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
            f"Traps: {len(level.trap_manager.traps)}",
        ]

        for i, stat in enumerate(stats):
            text = self.font_small.render(stat, True, COLOR_TEXT)
            screen.blit(text, (x, y + i * 17))

    def _draw_boss_health_bar(self, screen, boss_manager, screen_w):
        """Draw boss health bar at top of screen"""
        boss = boss_manager.get_boss()
        if not boss or not boss.alive:
            return

        # Boss health bar dimensions
        bar_w = screen_w - 100
        bar_h = 25
        bar_x = 50
        bar_y = 10

        # Background
        pygame.draw.rect(screen, (40, 20, 20), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=6)
        pygame.draw.rect(screen, COLOR_HEALTH_BAR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # Health fill with phase colors
        health_percent = boss.get_health_percent()
        fill_w = int(bar_w * health_percent)

        if boss.phase == 3:
            health_color = (255, 50, 50)  # Bright red
        elif boss.phase == 2:
            health_color = (220, 100, 50)  # Orange
        else:
            health_color = (180, 50, 50)  # Dark red

        if fill_w > 0:
            pygame.draw.rect(screen, health_color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        # Border
        pygame.draw.rect(screen, (200, 100, 100), (bar_x, bar_y, bar_w, bar_h), 3, border_radius=4)

        # Boss name and phase
        phase_text = f"BOSS - Phase {boss.phase}"
        name_render = self.font_medium.render(phase_text, True, (255, 200, 200))
        name_rect = name_render.get_rect(center=(screen_w // 2, bar_y + bar_h // 2))
        screen.blit(name_render, name_rect)

        # Health numbers
        hp_text = f"{int(boss.health)}/{int(boss.max_health)}"
        hp_render = self.font_small.render(hp_text, True, COLOR_TEXT)
        hp_rect = hp_render.get_rect(right=bar_x + bar_w - 10, centery=bar_y + bar_h // 2)
        screen.blit(hp_render, hp_rect)

        # Attack hint
        hint_text = "[SPACE] to attack when near boss"
        hint_render = self.font_small.render(hint_text, True, (150, 150, 150))
        hint_rect = hint_render.get_rect(center=(screen_w // 2, bar_y + bar_h + 15))
        screen.blit(hint_render, hint_rect)

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

        # Scale factors for different screen sizes
        scale = min(screen_w / 800, screen_h / 600)
        scale = max(0.6, min(1.5, scale))  # Clamp between 0.6 and 1.5

        # Dynamic positioning
        title_y = int(60 * scale)
        subtitle_y = int(100 * scale)
        start_y = int(150 * scale) if subtitle else int(120 * scale)
        gap = int(45 * scale)
        help_y = screen_h - int(40 * scale)

        # Title
        title_text = self.font_title.render(title, True, COLOR_TEXT_HIGHLIGHT)
        title_rect = title_text.get_rect(center=(screen_w // 2, title_y))
        screen.blit(title_text, title_rect)

        # Subtitle
        if subtitle:
            subtitle_text = self.font_medium.render(subtitle, True, COLOR_TEXT)
            subtitle_rect = subtitle_text.get_rect(center=(screen_w // 2, subtitle_y))
            screen.blit(subtitle_text, subtitle_rect)

        # Menu items
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
            "UP/DOWN: Navigate | ENTER: Select | ESC: Back/Quit",
            "Alt+Enter: Fullscreen"
        ]
        for i, help_text in enumerate(help_texts):
            text = self.font_small.render(help_text, True, COLOR_TEXT_DIM)
            text_rect = text.get_rect(center=(screen_w // 2, help_y + i * 18))
            screen.blit(text, text_rect)

    def draw_difficulty_select(self, screen, selected_difficulty):
        """Draw difficulty selection screen"""
        screen_w, screen_h = screen.get_size()

        # Scale factors for different screen sizes
        scale = min(screen_w / 800, screen_h / 600)
        scale = max(0.6, min(1.5, scale))

        # Dynamic positioning
        title_y = int(50 * scale)
        start_y = int(110 * scale)
        gap = int(55 * scale)

        # Title
        title = self.font_title.render("SELECT DIFFICULTY", True, COLOR_TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(screen_w // 2, title_y))
        screen.blit(title, title_rect)

        # Difficulty options
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
                desc_rect = desc_text.get_rect(center=(screen_w // 2, start_y + i * gap + 22))
                screen.blit(desc_text, desc_rect)

    def _get_difficulty_description(self, difficulty):
        """Get brief difficulty description"""
        descriptions = [
            "Easy mode - 2 patrol enemies, no time limit",
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
        if reason == 'time_up':
            title_text = "TIME'S UP!"
        elif reason == 'boss':
            title_text = "BOSS DEFEATED YOU!"
        else:
            title_text = "GAME OVER"

        title = self.font_title.render(title_text, True, (255, 100, 100))
        title_rect = title.get_rect(center=(screen_w // 2, screen_h // 2 - 50))
        screen.blit(title, title_rect)

        # Message
        if reason == 'time_up':
            msg = "You ran out of time!"
        elif reason == 'boss':
            msg = "The boss was too powerful!"
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

    def draw_mode_select(self, screen, selected_mode):
        """
        Draw game mode selection screen (2D / 3D)

        Args:
            screen: pygame.Surface
            selected_mode: 0 = 2D, 1 = 3D
        """
        screen_w, screen_h = screen.get_size()

        # Scale factors
        scale = min(screen_w / 800, screen_h / 600)
        scale = max(0.6, min(1.5, scale))

        # Dynamic positioning
        title_y = int(60 * scale)
        start_y = int(150 * scale)
        gap = int(80 * scale)

        # Title
        title = self.font_title.render("SELECT GAME MODE", True, COLOR_TEXT_HIGHLIGHT)
        title_rect = title.get_rect(center=(screen_w // 2, title_y))
        screen.blit(title, title_rect)

        # Mode options
        modes = [
            ("2D Mode", "Classic top-down view"),
            ("3D Mode", "First-person (Wolfenstein style)")
        ]

        for i, (name, desc) in enumerate(modes):
            is_selected = i == selected_mode
            color = COLOR_MENU_SELECTION if is_selected else COLOR_TEXT

            # Mode name
            text = self.font_large.render(name, True, color)
            text_rect = text.get_rect(center=(screen_w // 2, start_y + i * gap))

            # Selection border
            if is_selected:
                border_rect = text_rect.inflate(60, 30)
                pygame.draw.rect(screen, COLOR_MENU_BORDER, border_rect, 3, border_radius=10)

            screen.blit(text, text_rect)

            # Description
            desc_text = self.font_small.render(desc, True, COLOR_TEXT_DIM)
            desc_rect = desc_text.get_rect(center=(screen_w // 2, start_y + i * gap + 28))
            screen.blit(desc_text, desc_rect)

        # Help text
        help_y = screen_h - int(60 * scale)
        help_texts = [
            "UP/DOWN: Select | ENTER: Confirm | ESC: Back"
        ]
        for i, help_text in enumerate(help_texts):
            text = self.font_small.render(help_text, True, COLOR_TEXT_DIM)
            text_rect = text.get_rect(center=(screen_w // 2, help_y + i * 18))
            screen.blit(text, text_rect)

    def draw_hud_3d(self, screen, player, level, screen_h, weapon=None):
        """
        Draw minimal HUD for 3D mode (overlay style)

        Args:
            screen: pygame.Surface
            player: Player instance (2D player for stats)
            level: Level instance
            screen_h: Screen height
            weapon: Weapon instance (ammo ko'rsatish uchun)
        """
        screen_w = screen.get_width()

        # Semi-transparent bottom bar
        bar_h = 60
        bar_surface = pygame.Surface((screen_w, bar_h), pygame.SRCALPHA)
        bar_surface.fill((0, 0, 0, 150))
        screen.blit(bar_surface, (0, screen_h - bar_h))

        # Health bar (left side)
        self._draw_health_bar(screen, player, 10, screen_h - bar_h + 10, 180, 18)

        # Energy bar (below health)
        self._draw_energy_bar(screen, player, 10, screen_h - bar_h + 35, 180, 14)

        # Timer (center)
        self._draw_timer(screen, level, screen_w // 2, screen_h - bar_h + 5)

        # Key inventory (right side, yuqorida)
        self._draw_key_inventory(screen, player, screen_w - 130, screen_h - bar_h + 10)

        # Ammo display (o'ng pastda)
        if weapon is not None:
            ammo_x = screen_w - 160
            ammo_y = screen_h - bar_h + 12

            # Ammo raqamlari
            ammo_text = f"{weapon.magazine_ammo} / {weapon.reserve_ammo}"
            ammo_render = self.font_large.render(ammo_text, True, (255, 255, 255))
            ammo_rect = ammo_render.get_rect(right=screen_w - 15, centery=ammo_y + 10)
            screen.blit(ammo_render, ammo_rect)

            # Reload indikator
            if weapon.is_reloading:
                reload_text = "RELOADING..."
                reload_render = self.font_small.render(reload_text, True, (255, 220, 80))
                reload_rect = reload_render.get_rect(right=screen_w - 15, centery=ammo_y + 32)
                screen.blit(reload_render, reload_rect)

        # Crosshair (4 chiziqli, markazda gap bilan)
        cx, cy = screen_w // 2, (screen_h - bar_h) // 2
        crosshair_size = 10
        gap = 4
        crosshair_color = self._crosshair_color if hasattr(self, '_crosshair_color') else (200, 200, 200)

        # 4 ta chiziq (markazda bo'sh joy)
        pygame.draw.line(screen, crosshair_color, (cx - crosshair_size, cy), (cx - gap, cy), 2)
        pygame.draw.line(screen, crosshair_color, (cx + gap, cy), (cx + crosshair_size, cy), 2)
        pygame.draw.line(screen, crosshair_color, (cx, cy - crosshair_size), (cx, cy - gap), 2)
        pygame.draw.line(screen, crosshair_color, (cx, cy + gap), (cx, cy + crosshair_size), 2)

        # Boss health bar (top, if active)
        if level.boss_manager.active and level.boss_manager.fight_started:
            self._draw_boss_health_bar(screen, level.boss_manager, screen_w)
