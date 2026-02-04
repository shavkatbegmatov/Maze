"""
Maze Game V3 - Nightmare Edition
Full game with all features
"""

import pygame
import sys
import random

from game.level_manager import LevelManager
from game.game_state import GameStateManager, GameState, GameFlow
from game.ui_manager import UIManager
from game.collision import CollisionHandler
from game.fog_of_war import FogManager
from game.save_manager import SaveManager
from entities.particle import ParticleSystem, ParticleEffects
from maze.generator import GEN_ALGOS
from utils.constants import (
    CELL_SIZE, FPS, PANEL_H,
    DIFFICULTY_EASY, DIFFICULTY_NORMAL, DIFFICULTY_HARD,
    DIFFICULTY_EXPERT, DIFFICULTY_NIGHTMARE,
    DIFFICULTY_NAMES, TOP, RIGHT, BOTTOM, LEFT
)
from utils.colors import (
    COLOR_BG, COLOR_MAZE_BG, COLOR_WALL, COLOR_PLAYER, COLOR_GOAL,
    COLOR_VISITED_CELL, COLOR_MENU_OVERLAY
)
from config import GAME_TITLE, GAME_VERSION


class MazeGame:
    """
    Main game class
    """
    def __init__(self):
        pygame.init()

        # Managers
        self.level_manager = LevelManager()
        self.state_manager = GameStateManager()
        self.game_flow = GameFlow(self.level_manager, self.state_manager)
        self.ui_manager = UIManager()
        self.collision_handler = CollisionHandler()

        # Visual effects
        self.fog_manager = FogManager()
        self.particle_system = ParticleSystem()
        self.particle_effects = ParticleEffects(self.particle_system)

        # Save/Load
        self.save_manager = SaveManager()
        self.show_save_message = False
        self.save_message_timer = 0.0
        self.save_message_text = ""

        # Screen (will be resized based on level)
        self.screen = None
        self.screen_w = 800
        self.screen_h = 600
        self._create_screen(self.screen_w, self.screen_h)

        self.clock = pygame.time.Clock()
        self.running = True

        # Menu state
        self.menu_index = 0
        self.menu_items = ["Start Game", "Difficulty", "Generator", "Quit"]

        # Difficulty selection
        self.selected_difficulty = DIFFICULTY_EASY
        self.selected_generator = 0

        # Generation state
        self.generator = None
        self.gen_speed = 220  # Steps per second
        self.gen_accum = 0.0

        # Movement cooldown
        self.move_cooldown_ms = 90
        self.last_move_time = 0

    def _create_screen(self, width, height):
        """Create or resize screen"""
        self.screen_w = width
        self.screen_h = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(f"{GAME_TITLE} v{GAME_VERSION}")

    def _resize_screen_for_level(self, level):
        """Resize screen to fit level"""
        width = level.cols * CELL_SIZE
        height = level.rows * CELL_SIZE + PANEL_H
        self._create_screen(width, height)

    def handle_events(self):
        """Handle input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

    def _handle_keydown(self, key):
        """Handle key press based on current state"""
        state = self.state_manager.current_state

        if state == GameState.MENU:
            self._handle_menu_input(key)

        elif state == GameState.DIFFICULTY_SELECT:
            self._handle_difficulty_select_input(key)

        elif state == GameState.GENERATING:
            # Can skip generation with space
            if key == pygame.K_SPACE:
                self._finish_generation_instantly()

        elif state == GameState.PLAYING:
            self._handle_playing_input(key)

        elif state == GameState.PAUSED:
            if key == pygame.K_p:
                self.game_flow.resume_game()
            elif key == pygame.K_ESCAPE:
                self.game_flow.return_to_menu()

        elif state == GameState.LEVEL_COMPLETE:
            if key == pygame.K_RETURN:
                self.game_flow.return_to_menu()

        elif state == GameState.GAME_OVER:
            if key == pygame.K_r:
                self.game_flow.retry_level()
            elif key == pygame.K_ESCAPE:
                self.game_flow.return_to_menu()

    def _handle_menu_input(self, key):
        """Handle menu input"""
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
        elif key == pygame.K_RETURN:
            self._handle_menu_select()
        elif key == pygame.K_ESCAPE:
            self.running = False

    def _handle_menu_select(self):
        """Handle menu selection"""
        selected = self.menu_items[self.menu_index]

        if selected == "Start Game":
            self._start_new_game()
        elif selected == "Load Game":
            self._quick_load()
        elif "Difficulty:" in selected:
            self.state_manager.transition_to(GameState.DIFFICULTY_SELECT)
        elif "Generator:" in selected:
            self.selected_generator = (self.selected_generator + 1) % len(GEN_ALGOS)
        elif selected == "Quit":
            self.running = False

    def _handle_difficulty_select_input(self, key):
        """Handle difficulty selection input"""
        if key in (pygame.K_UP, pygame.K_w):
            self.selected_difficulty = (self.selected_difficulty - 1) % len(DIFFICULTY_NAMES)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected_difficulty = (self.selected_difficulty + 1) % len(DIFFICULTY_NAMES)
        elif key == pygame.K_RETURN:
            self.state_manager.transition_to(GameState.MENU)
        elif key == pygame.K_ESCAPE:
            self.state_manager.transition_to(GameState.MENU)

    def _handle_playing_input(self, key):
        """Handle playing state input"""
        if key == pygame.K_p:
            self.game_flow.pause_game()
        elif key == pygame.K_ESCAPE:
            self.game_flow.pause_game()
        elif key == pygame.K_r:
            self.game_flow.retry_level()
        elif key == pygame.K_F5:
            # Quick save
            self._quick_save()
        elif key == pygame.K_F9:
            # Quick load
            self._quick_load()

    def _start_new_game(self):
        """Start a new game"""
        level, gen = self.game_flow.start_new_game(
            self.selected_difficulty,
            self.selected_generator,
            animated=True
        )

        self._resize_screen_for_level(level)

        # Create fog of war for level
        self.fog_manager.create_fog(
            level.cols,
            level.rows,
            enabled=level.config.fog_enabled
        )

        # Clear particles
        self.particle_system.clear()

        if gen:
            self.generator = gen
            self.gen_accum = 0.0

    def _finish_generation_instantly(self):
        """Finish generation without animation"""
        if self.generator:
            last_state = None
            for state in self.generator:
                last_state = state

            level = self.level_manager.get_current_level()
            level.finalize_generation(last_state['walls'])
            self.generator = None
            self.game_flow.generation_complete()

    def _quick_save(self):
        """Quick save game"""
        level = self.level_manager.get_current_level()
        if level and level.generation_complete:
            success = self.save_manager.save_game(
                level, level.player, self.state_manager, "quicksave"
            )
            if success:
                self._show_message("Game Saved! (F9 to load)")
            else:
                self._show_message("Save Failed!")

    def _quick_load(self):
        """Quick load game"""
        save_data = self.save_manager.load_game("quicksave")
        if save_data:
            level, success = self.save_manager.restore_game_state(
                save_data, self.level_manager
            )
            if success and level:
                self.level_manager.current_level = level
                self._resize_screen_for_level(level)

                # Recreate fog
                self.fog_manager.create_fog(
                    level.cols,
                    level.rows,
                    enabled=level.config.fog_enabled
                )

                # Clear particles
                self.particle_system.clear()

                # Set state to playing
                self.state_manager.transition_to(GameState.PLAYING)
                self._show_message("Game Loaded!")
            else:
                self._show_message("Load Failed!")
        else:
            self._show_message("No Save Found!")

    def _show_message(self, text, duration=2.0):
        """Show a temporary message"""
        self.show_save_message = True
        self.save_message_timer = duration
        self.save_message_text = text

    def update(self, dt):
        """Update game state"""
        state = self.state_manager.current_state

        # Update save message timer
        if self.show_save_message:
            self.save_message_timer -= dt
            if self.save_message_timer <= 0:
                self.show_save_message = False

        if state == GameState.GENERATING:
            self._update_generation(dt)

        elif state == GameState.PLAYING:
            self._update_playing(dt)

    def _update_generation(self, dt):
        """Update maze generation"""
        if not self.generator:
            return

        self.gen_accum += dt * self.gen_speed
        steps = int(self.gen_accum)

        if steps > 0:
            self.gen_accum -= steps

            for _ in range(steps):
                try:
                    state = next(self.generator)
                    if state['done']:
                        level = self.level_manager.get_current_level()
                        level.finalize_generation(state['walls'])
                        self.generator = None
                        self.game_flow.generation_complete()
                        break
                except StopIteration:
                    self.generator = None
                    self.game_flow.generation_complete()
                    break

    def _update_playing(self, dt):
        """Update playing state"""
        level = self.level_manager.get_current_level()
        if not level:
            return

        # Update level
        result = self.game_flow.update(dt)

        # Update fog of war
        self.fog_manager.update(dt, level.player, level)

        # Update particles
        self.particle_system.update(dt)

        # Ambient sparkles for power-ups
        if random.random() < 0.1:  # 10% chance per frame
            for powerup in level.powerup_manager.get_uncollected_powerups():
                if self.fog_manager.is_visible(powerup.x, powerup.y):
                    self.particle_effects.ambient_sparkle(
                        powerup.x, powerup.y, powerup.get_color()
                    )

        # Handle movement
        self._handle_player_movement()

    def _handle_player_movement(self):
        """Handle player movement input"""
        level = self.level_manager.get_current_level()
        if not level or not level.player:
            return

        now = pygame.time.get_ticks()
        if (now - self.last_move_time) < self.move_cooldown_ms:
            return

        keys = pygame.key.get_pressed()
        dx = dy = 0

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dx, dy = 0, -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx, dy = 1, 0
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dx, dy = 0, 1
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx, dy = -1, 0

        if (dx, dy) != (0, 0):
            # Check if target position has a moving wall
            target_x = level.player.x + dx
            target_y = level.player.y + dy
            if level.moving_wall_manager.is_blocked(target_x, target_y):
                return  # Can't move into a moving wall

            if level.player.move(dx, dy, level.walls, level.cols, level.rows):
                self.last_move_time = now

                # Player trail effect
                if random.random() < 0.3:  # 30% chance
                    self.particle_effects.player_trail(level.player.x, level.player.y)

                # Check collisions
                collision_result = self.collision_handler.check_player_position(
                    level.player,
                    level.enemy_manager,
                    level.powerup_manager,
                    level.trap_manager,
                    level.door_manager,
                    level.walls,
                    level.cols,
                    level.rows
                )

                # Particle effects for collision events
                if collision_result['powerup']:
                    powerup = collision_result['powerup']
                    self.particle_effects.powerup_collection(
                        powerup.x, powerup.y, powerup.type
                    )

                if collision_result['key']:
                    key = collision_result['key']
                    self.particle_effects.key_collection(
                        key.x, key.y, key.get_color_rgb()
                    )

                if collision_result['door']:
                    door = collision_result['door']
                    self.particle_effects.door_unlock(
                        door.x, door.y, door.get_color_rgb()
                    )

                if collision_result['trap']:
                    trap = collision_result['trap']
                    self.particle_effects.trap_trigger(
                        trap.x, trap.y, trap.type
                    )

                if collision_result['enemy']:
                    # Player took damage from enemy
                    self.particle_effects.player_damage(
                        level.player.x, level.player.y
                    )

                if collision_result['player_died']:
                    # Death explosion
                    self.particle_effects.explosion(
                        level.player.x, level.player.y, (255, 50, 50)
                    )
                    self.game_flow.game_over('died')

    def render(self):
        """Render current game state"""
        self.screen.fill(COLOR_BG)

        state = self.state_manager.current_state

        if state == GameState.MENU:
            self._render_menu()

        elif state == GameState.DIFFICULTY_SELECT:
            self._render_difficulty_select()

        elif state == GameState.GENERATING:
            self._render_generating()

        elif state == GameState.PLAYING:
            self._render_playing()

        elif state == GameState.PAUSED:
            self._render_playing()  # Render game underneath
            self.ui_manager.draw_paused(self.screen)

        elif state == GameState.LEVEL_COMPLETE:
            score = self.state_manager.state_data.get('score', 0)
            level = self.level_manager.get_current_level()
            self.ui_manager.draw_level_complete(
                self.screen, score, level.time_elapsed, level.player.moves
            )

        elif state == GameState.GAME_OVER:
            reason = self.state_manager.state_data.get('reason', 'died')
            self.ui_manager.draw_game_over(self.screen, reason)

        pygame.display.flip()

    def _render_menu(self):
        """Render main menu"""
        # Update menu items with current settings
        gen_name = GEN_ALGOS[self.selected_generator][0]
        diff_name = DIFFICULTY_NAMES[self.selected_difficulty]

        self.menu_items = [
            "Start Game",
            "Load Game",
            f"Difficulty: {diff_name}",
            f"Generator: {gen_name}",
            "Quit"
        ]

        self.ui_manager.draw_menu(
            self.screen,
            GAME_TITLE,
            self.menu_items,
            self.menu_index,
            subtitle=f"Version {GAME_VERSION}"
        )

    def _render_difficulty_select(self):
        """Render difficulty selection"""
        self.ui_manager.draw_difficulty_select(self.screen, self.selected_difficulty)

    def _render_generating(self):
        """Render maze generation"""
        level = self.level_manager.get_current_level()
        if not level or not level.walls:
            return

        maze_h = level.rows * CELL_SIZE
        pygame.draw.rect(self.screen, COLOR_MAZE_BG, (0, 0, self.screen_w, maze_h))

        # Draw maze walls
        self._draw_maze(level.walls, level.cols, level.rows)

        # Draw "Generating..." text
        font = pygame.font.SysFont("consolas", 32, bold=True)
        text = font.render("Generating Maze...", True, (255, 220, 120))
        text_rect = text.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
        self.screen.blit(text, text_rect)

        small_font = pygame.font.SysFont("consolas", 18)
        hint = small_font.render("Press SPACE to skip", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(self.screen_w // 2, self.screen_h // 2 + 50))
        self.screen.blit(hint, hint_rect)

    def _render_playing(self):
        """Render playing state"""
        level = self.level_manager.get_current_level()
        if not level:
            return

        maze_h = level.rows * CELL_SIZE
        pygame.draw.rect(self.screen, COLOR_MAZE_BG, (0, 0, self.screen_w, maze_h))

        # Draw entities
        self._draw_goal(level)
        self._draw_keys(level)
        self._draw_doors(level)
        self._draw_powerups(level)
        self._draw_traps(level)
        self._draw_enemies(level)
        self._draw_moving_walls(level)
        self._draw_player(level)

        # Draw maze walls
        self._draw_maze(level.walls, level.cols, level.rows)

        # Draw particles (before fog so fog covers them)
        self.particle_system.render(self.screen)

        # Draw fog of war
        self.fog_manager.render(self.screen, level.player)

        # Draw HUD
        self.ui_manager.draw_hud(
            self.screen, level.player, level,
            maze_h, self.screen_w, PANEL_H
        )

        # Draw save/load message
        if self.show_save_message:
            self._draw_save_message()

    def _draw_maze(self, walls, cols, rows):
        """Draw maze walls"""
        for y in range(rows):
            for x in range(cols):
                idx = y * cols + x
                w = walls[idx]
                x0 = x * CELL_SIZE
                y0 = y * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE

                if w & TOP:
                    pygame.draw.line(self.screen, COLOR_WALL, (x0, y0), (x1, y0), 3)
                if w & RIGHT:
                    pygame.draw.line(self.screen, COLOR_WALL, (x1, y0), (x1, y1), 3)
                if w & BOTTOM:
                    pygame.draw.line(self.screen, COLOR_WALL, (x0, y1), (x1, y1), 3)
                if w & LEFT:
                    pygame.draw.line(self.screen, COLOR_WALL, (x0, y0), (x0, y1), 3)

    def _draw_cell(self, x, y, color, pad=6):
        """Draw filled cell"""
        rx = x * CELL_SIZE + pad
        ry = y * CELL_SIZE + pad
        rw = CELL_SIZE - pad * 2
        rh = CELL_SIZE - pad * 2
        pygame.draw.rect(self.screen, color, (rx, ry, rw, rh), border_radius=6)

    def _draw_goal(self, level):
        if self.fog_manager.is_visible(level.goal_pos[0], level.goal_pos[1]):
            self._draw_cell(level.goal_pos[0], level.goal_pos[1], COLOR_GOAL)

    def _draw_keys(self, level):
        for key in level.door_manager.keys:
            if not key.collected and self.fog_manager.is_visible(key.x, key.y):
                self._draw_cell(key.x, key.y, key.get_color_rgb(), pad=8)

    def _draw_doors(self, level):
        for door in level.door_manager.doors:
            if door.locked and self.fog_manager.is_visible(door.x, door.y):
                self._draw_cell(door.x, door.y, door.get_color_rgb(), pad=4)

    def _draw_powerups(self, level):
        for powerup in level.powerup_manager.get_uncollected_powerups():
            if self.fog_manager.is_visible(powerup.x, powerup.y):
                self._draw_cell(powerup.x, powerup.y, powerup.get_color(), pad=8)

    def _draw_traps(self, level):
        for trap in level.trap_manager.get_visible_traps():
            if self.fog_manager.is_visible(trap.x, trap.y):
                self._draw_cell(trap.x, trap.y, trap.get_color(), pad=10)

    def _draw_enemies(self, level):
        for enemy in level.enemy_manager.enemies:
            if self.fog_manager.is_visible(enemy.x, enemy.y):
                self._draw_cell(enemy.x, enemy.y, enemy.get_color(), pad=7)

    def _draw_player(self, level):
        # Player is always visible
        self._draw_cell(level.player.x, level.player.y, COLOR_PLAYER)

    def _draw_moving_walls(self, level):
        """Draw moving walls"""
        for wall in level.moving_wall_manager.walls:
            if self.fog_manager.is_visible(wall.x, wall.y):
                # Draw with glow effect
                color = wall.get_glow_color()
                self._draw_cell(wall.x, wall.y, color, pad=3)
                # Draw border
                rx = wall.x * CELL_SIZE + 3
                ry = wall.y * CELL_SIZE + 3
                rw = CELL_SIZE - 6
                rh = CELL_SIZE - 6
                pygame.draw.rect(self.screen, (200, 200, 255), (rx, ry, rw, rh), 2, border_radius=4)

    def _draw_save_message(self):
        """Draw save/load message"""
        font = pygame.font.SysFont("consolas", 24, bold=True)
        text = font.render(self.save_message_text, True, (255, 220, 100))
        text_rect = text.get_rect(center=(self.screen_w // 2, 50))

        # Background
        bg_rect = text_rect.inflate(30, 15)
        pygame.draw.rect(self.screen, (30, 30, 40), bg_rect, border_radius=8)
        pygame.draw.rect(self.screen, (255, 220, 100), bg_rect, 2, border_radius=8)

        self.screen.blit(text, text_rect)

    def run(self):
        """Main game loop"""
        while self.running:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0

            self.handle_events()
            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit()


def main():
    """Entry point"""
    game = MazeGame()
    game.run()


if __name__ == "__main__":
    main()
