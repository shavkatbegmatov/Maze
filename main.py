"""
Maze Game V3 - Nightmare Edition
Full game with all features
"""

import pygame
import sys
import random
import math

from game.level_manager import LevelManager
from game.game_state import GameStateManager, GameState, GameFlow
from game.ui_manager import UIManager
from game.collision import CollisionHandler
from game.fog_of_war import FogManager
from game.save_manager import SaveManager
from game.camera import CameraManager
from game.display_manager import DisplayManager
from entities.particle import ParticleSystem, ParticleEffects
from maze.generator import GEN_ALGOS
from utils.constants import (
    FPS, PANEL_H,
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

        # Camera system
        self.camera_manager = CameraManager()
        self.cell_size = 35  # Will be updated by camera

        # Display manager
        self.display_manager = DisplayManager()
        self.display_manager.initialize()
        self.display_manager.set_resize_callback(self._on_screen_resize)

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
        """Create or resize screen using DisplayManager"""
        self.screen_w = width
        self.screen_h = height
        self.screen = self.display_manager.create_screen(
            width, height,
            title=f"{GAME_TITLE} v{GAME_VERSION}"
        )
        # Update dimensions from display manager (may differ due to clamping)
        self.screen_w, self.screen_h = self.display_manager.get_size()

    def _resize_screen_for_level(self, level):
        """Resize screen to fit level using camera system"""
        # In fullscreen mode, don't resize window - just recalculate cell size
        if self.display_manager.is_fullscreen():
            screen_w, screen_h = self.display_manager.get_size()
            cell_size, use_camera = self.camera_manager.handle_screen_resize(
                screen_w, screen_h, PANEL_H
            )
            # Update maze info in camera
            self.camera_manager.camera.maze_cols = level.cols
            self.camera_manager.camera.maze_rows = level.rows
            self.cell_size = cell_size
        else:
            # Let camera calculate optimal settings for windowed mode
            screen_w, screen_h, cell_size, use_camera = self.camera_manager.setup_for_level(
                level.cols, level.rows, PANEL_H
            )

            self.cell_size = cell_size
            self._create_screen(screen_w, screen_h)

        # Reset camera position
        self.camera_manager.reset()

        # Log camera mode for debugging
        if use_camera:
            print(f"Camera mode: ON (maze {level.cols}x{level.rows}, cell size {cell_size})")
        else:
            print(f"Camera mode: OFF (maze {level.cols}x{level.rows}, cell size {cell_size})")

    def handle_events(self):
        """Handle input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # Window resize event
            if event.type == pygame.VIDEORESIZE:
                self._handle_window_resize(event.w, event.h)
                continue

            if event.type == pygame.KEYDOWN:
                # Alt+Enter = fullscreen toggle
                if event.key == pygame.K_RETURN:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_ALT:
                        self._toggle_fullscreen()
                        continue
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
        elif key == pygame.K_SPACE:
            # Attack boss if nearby
            self._attack_boss()

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

    def _toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        new_w, new_h = self.display_manager.toggle_fullscreen()
        self.screen = self.display_manager.get_screen()
        self.screen_w = new_w
        self.screen_h = new_h

        # Recalculate cell size and camera for new screen size
        level = self.level_manager.get_current_level()
        if level and level.generation_complete:
            cell_size, use_camera = self.camera_manager.handle_screen_resize(
                new_w, new_h, PANEL_H
            )
            self.cell_size = cell_size

        mode_name = "Fullscreen" if self.display_manager.is_fullscreen() else "Windowed"
        self._show_message(f"{mode_name} Mode", 1.0)

    def _handle_window_resize(self, event_w, event_h):
        """Handle window resize event"""
        new_w, new_h = self.display_manager.handle_resize(event_w, event_h)
        self.screen = self.display_manager.get_screen()
        self.screen_w = new_w
        self.screen_h = new_h

    def _on_screen_resize(self, new_width, new_height):
        """Callback for screen resize - update camera and cell size"""
        level = self.level_manager.get_current_level()
        if level and level.generation_complete:
            cell_size, use_camera = self.camera_manager.handle_screen_resize(
                new_width, new_height, PANEL_H
            )
            self.cell_size = cell_size

            # Recreate fog surface for new size
            self.fog_manager.create_fog(
                level.cols,
                level.rows,
                enabled=level.config.fog_enabled
            )

    def _attack_boss(self):
        """Attack boss if player is adjacent"""
        level = self.level_manager.get_current_level()
        if not level or not level.boss_manager.active:
            return

        boss = level.boss_manager.get_boss()
        if not boss or not boss.alive:
            return

        # Check if player is adjacent to boss
        dist = abs(level.player.x - boss.x) + abs(level.player.y - boss.y)
        if dist <= 1:
            # Attack!
            damage = 15  # Base damage
            if level.boss_manager.damage_boss(damage):
                # Boss defeated!
                self._show_message("BOSS DEFEATED!")
            else:
                # Hit effect
                self.particle_effects.explosion(boss.x, boss.y, (255, 200, 100))
                self._show_message(f"Boss HP: {boss.health}/{boss.max_health}", 0.5)

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

        # Update camera to follow player
        self.camera_manager.update(dt, level.player)

        # Update fog of war
        self.fog_manager.update(dt, level.player, level)

        # Update particles
        self.particle_system.update(dt)

        # Update boss fight
        if level.boss_manager.active:
            boss_events = level.boss_manager.update(
                dt, level.walls, level.cols, level.rows,
                level.player, level.enemy_manager
            )

            # Handle boss events
            if boss_events['fight_started']:
                self._show_message("BOSS FIGHT!")
                # Boss fight particles
                boss = level.boss_manager.get_boss()
                if boss:
                    self.particle_effects.explosion(boss.x, boss.y, (180, 50, 50))

            if boss_events['boss_attacked']:
                self.particle_effects.player_damage(level.player.x, level.player.y)

            if boss_events['boss_charged']:
                boss = level.boss_manager.get_boss()
                if boss:
                    self.particle_effects.explosion(boss.x, boss.y, (255, 100, 50))

            if boss_events['minions_summoned']:
                boss = level.boss_manager.get_boss()
                if boss:
                    self.particle_effects.explosion(boss.x, boss.y, (150, 50, 150))
                    self._show_message("Minions summoned!")

            if boss_events['boss_defeated']:
                boss = level.boss_manager.get_boss()
                if boss:
                    # Epic death explosion
                    for _ in range(5):
                        self.particle_effects.explosion(
                            boss.x + random.randint(-1, 1),
                            boss.y + random.randint(-1, 1),
                            (255, random.randint(50, 150), 50)
                        )
                self._show_message("BOSS DEFEATED!")

            # Check if player died from boss damage
            if not level.player.is_alive():
                self.particle_effects.explosion(level.player.x, level.player.y, (255, 50, 50))
                self.game_flow.game_over('boss')

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

        maze_h = self.camera_manager.get_maze_area_height()
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

        maze_h = self.camera_manager.get_maze_area_height()
        pygame.draw.rect(self.screen, COLOR_MAZE_BG, (0, 0, self.screen_w, maze_h))

        # Draw entities (order matters for layering)
        self._draw_goal(level)
        self._draw_keys(level)
        self._draw_doors(level)
        self._draw_powerups(level)
        self._draw_traps(level)
        self._draw_enemies(level)
        self._draw_moving_walls(level)
        self._draw_boss(level)
        self._draw_player(level)

        # Draw maze walls
        self._draw_maze(level.walls, level.cols, level.rows)

        # Draw particles with camera offset
        self._render_particles()

        # Draw fog of war with camera support
        self._render_fog(level)

        # Draw camera mode indicator
        if self.camera_manager.uses_camera():
            self._draw_minimap(level)

        # Draw HUD
        self.ui_manager.draw_hud(
            self.screen, level.player, level,
            maze_h, self.screen_w, PANEL_H
        )

        # Draw save/load message
        if self.show_save_message:
            self._draw_save_message()

    def _draw_maze(self, walls, cols, rows):
        """Draw maze walls - only visible cells for performance"""
        # Get visible range from camera
        min_x, max_x, min_y, max_y = self.camera_manager.get_visible_range()

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if x < 0 or x >= cols or y < 0 or y >= rows:
                    continue

                idx = y * cols + x
                w = walls[idx]

                # Convert to screen coordinates
                sx, sy = self.camera_manager.world_to_screen(x, y)
                x0, y0 = sx, sy
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size

                if w & TOP:
                    pygame.draw.line(self.screen, COLOR_WALL, (x0, y0), (x1, y0), 3)
                if w & RIGHT:
                    pygame.draw.line(self.screen, COLOR_WALL, (x1, y0), (x1, y1), 3)
                if w & BOTTOM:
                    pygame.draw.line(self.screen, COLOR_WALL, (x0, y1), (x1, y1), 3)
                if w & LEFT:
                    pygame.draw.line(self.screen, COLOR_WALL, (x0, y0), (x0, y1), 3)

    def _draw_cell(self, x, y, color, pad=6):
        """Draw filled cell with camera support"""
        # Skip if not visible
        if not self.camera_manager.is_visible(x, y):
            return

        # Convert to screen coordinates
        sx, sy = self.camera_manager.world_to_screen(x, y)
        rx = sx + pad
        ry = sy + pad
        rw = self.cell_size - pad * 2
        rh = self.cell_size - pad * 2

        # Scale padding for smaller cells
        if self.cell_size < 25:
            pad = max(2, pad - 2)
            rx = sx + pad
            ry = sy + pad
            rw = self.cell_size - pad * 2
            rh = self.cell_size - pad * 2

        pygame.draw.rect(self.screen, color, (rx, ry, rw, rh), border_radius=max(3, 6 * self.cell_size // 35))

    def _draw_goal(self, level):
        gx, gy = level.goal_pos
        if self.camera_manager.is_visible(gx, gy) and self.fog_manager.is_visible(gx, gy):
            self._draw_cell(gx, gy, COLOR_GOAL)

    def _draw_keys(self, level):
        for key in level.door_manager.keys:
            if not key.collected:
                if self.camera_manager.is_visible(key.x, key.y) and self.fog_manager.is_visible(key.x, key.y):
                    self._draw_cell(key.x, key.y, key.get_color_rgb(), pad=8)

    def _draw_doors(self, level):
        for door in level.door_manager.doors:
            if door.locked:
                if self.camera_manager.is_visible(door.x, door.y) and self.fog_manager.is_visible(door.x, door.y):
                    self._draw_cell(door.x, door.y, door.get_color_rgb(), pad=4)

    def _draw_powerups(self, level):
        for powerup in level.powerup_manager.get_uncollected_powerups():
            if self.camera_manager.is_visible(powerup.x, powerup.y) and self.fog_manager.is_visible(powerup.x, powerup.y):
                self._draw_cell(powerup.x, powerup.y, powerup.get_color(), pad=8)

    def _draw_traps(self, level):
        for trap in level.trap_manager.get_visible_traps():
            if self.camera_manager.is_visible(trap.x, trap.y) and self.fog_manager.is_visible(trap.x, trap.y):
                self._draw_cell(trap.x, trap.y, trap.get_color(), pad=10)

    def _draw_enemies(self, level):
        for enemy in level.enemy_manager.enemies:
            if self.camera_manager.is_visible(enemy.x, enemy.y) and self.fog_manager.is_visible(enemy.x, enemy.y):
                self._draw_cell(enemy.x, enemy.y, enemy.get_color(), pad=7)

    def _draw_boss(self, level):
        """Draw boss enemy with camera support"""
        boss = level.boss_manager.get_boss()
        if not boss or not boss.alive:
            return

        if not self.camera_manager.is_visible(boss.x, boss.y):
            return

        if not self.fog_manager.is_visible(boss.x, boss.y):
            return

        # Convert to screen coordinates
        sx, sy = self.camera_manager.world_to_screen(boss.x, boss.y)

        # Draw boss (larger than normal enemies)
        color = boss.get_color()
        pad = int(3 * boss.size_multiplier)

        rx = sx + pad
        ry = sy + pad
        rw = self.cell_size - pad * 2
        rh = self.cell_size - pad * 2

        # Main body
        pygame.draw.rect(self.screen, color, (rx, ry, rw, rh), border_radius=8)

        # Draw telegraphing indicator
        if boss.is_telegraphing():
            # Pulsing warning effect
            pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.01)) * 100)
            warning_color = (255, pulse + 100, 0)
            pygame.draw.rect(self.screen, warning_color, (rx-2, ry-2, rw+4, rh+4), 3, border_radius=10)

        # Phase indicator (scale for cell size)
        horn_scale = self.cell_size / 35
        if boss.phase >= 2 and self.cell_size >= 20:
            # Draw horns for phase 2+
            h_offset = int(5 * horn_scale)
            h_size = int(10 * horn_scale)
            pygame.draw.polygon(self.screen, (100, 50, 50), [
                (rx + h_offset, ry), (rx + h_offset + h_size//2, ry - int(8 * horn_scale)), (rx + h_offset + h_size, ry)
            ])
            pygame.draw.polygon(self.screen, (100, 50, 50), [
                (rx + rw - h_offset - h_size, ry), (rx + rw - h_offset - h_size//2, ry - int(8 * horn_scale)), (rx + rw - h_offset, ry)
            ])

        if boss.phase >= 3 and self.cell_size >= 20:
            # Draw aura for phase 3
            aura_color = (255, 100, 100, 100)
            aura_surf = pygame.Surface((rw + 20, rh + 20), pygame.SRCALPHA)
            pygame.draw.rect(aura_surf, aura_color, (0, 0, rw + 20, rh + 20), border_radius=12)
            self.screen.blit(aura_surf, (rx - 10, ry - 10))

        # Draw boss health bar above boss
        if level.boss_manager.fight_started:
            bar_w = self.cell_size
            bar_h = 6
            bar_x = sx
            bar_y = sy - 10

            # Background
            pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            # Health
            health_w = int(bar_w * boss.get_health_percent())
            health_color = (255, 50, 50) if boss.phase == 3 else (200, 100, 50) if boss.phase == 2 else (150, 50, 50)
            pygame.draw.rect(self.screen, health_color, (bar_x, bar_y, health_w, bar_h))
            # Border
            pygame.draw.rect(self.screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h), 1)

    def _draw_player(self, level):
        """Draw player - always visible"""
        self._draw_cell(level.player.x, level.player.y, COLOR_PLAYER)

    def _draw_moving_walls(self, level):
        """Draw moving walls with camera support"""
        for wall in level.moving_wall_manager.walls:
            if not self.camera_manager.is_visible(wall.x, wall.y):
                continue
            if not self.fog_manager.is_visible(wall.x, wall.y):
                continue

            # Draw with glow effect
            color = wall.get_glow_color()
            self._draw_cell(wall.x, wall.y, color, pad=3)

            # Draw border
            sx, sy = self.camera_manager.world_to_screen(wall.x, wall.y)
            rx = sx + 3
            ry = sy + 3
            rw = self.cell_size - 6
            rh = self.cell_size - 6
            pygame.draw.rect(self.screen, (200, 200, 255), (rx, ry, rw, rh), 2, border_radius=4)

    def _render_particles(self):
        """Render particles with camera offset"""
        base_cell_size = 35  # Original cell size used in particle creation

        for particle in self.particle_system.particles:
            if not particle.alive:
                continue

            # Convert from original pixel coords to cell coords
            cell_x = particle.x / base_cell_size
            cell_y = particle.y / base_cell_size

            if not self.camera_manager.is_visible(cell_x, cell_y):
                continue

            # Convert to screen coordinates
            sx, sy = self.camera_manager.world_to_screen(cell_x, cell_y)

            # Scale particle size based on cell size ratio
            scale = self.cell_size / base_cell_size
            size = max(1, int(particle.size * scale))

            # Calculate alpha based on lifetime (same as particle.render does)
            if particle.fade:
                alpha = int(255 * (particle.lifetime / particle.max_lifetime))
            else:
                alpha = 255

            if size > 0 and alpha > 0:
                color = (*particle.color[:3], alpha)

                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                self.screen.blit(surf, (sx - size, sy - size))

    def _render_fog(self, level):
        """Render fog of war with camera support"""
        if not self.fog_manager.fog or not self.fog_manager.enabled:
            return

        if self.fog_manager.xray_active:
            return

        fog = self.fog_manager.fog
        maze_h = self.camera_manager.get_maze_area_height()

        # Create fog surface for visible area only
        fog_surface = pygame.Surface((self.screen_w, maze_h), pygame.SRCALPHA)

        # Get visible range
        min_x, max_x, min_y, max_y = self.camera_manager.get_visible_range()

        # Get player vision range
        vision_range = level.player.stats['vision_range']

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if x < 0 or x >= level.cols or y < 0 or y >= level.rows:
                    continue

                # Get screen position
                sx, sy = self.camera_manager.world_to_screen(x, y)

                # Get visibility level for this cell (0.0 = invisible, 1.0 = visible)
                visibility = fog.get_cell_visibility(x, y, level.player.x, level.player.y, vision_range)

                if visibility < 1.0:
                    # Calculate fog alpha (0 = visible, 255 = completely dark)
                    alpha = int((1.0 - visibility) * 255)
                    alpha = min(255, max(0, alpha))

                    pygame.draw.rect(
                        fog_surface,
                        (10, 12, 18, alpha),
                        (sx, sy, self.cell_size, self.cell_size)
                    )

        self.screen.blit(fog_surface, (0, 0))

    def _draw_minimap(self, level):
        """Draw minimap when in camera mode"""
        # Minimap dimensions
        map_w = 150
        map_h = 100
        map_x = self.screen_w - map_w - 10
        map_y = 10

        # Background
        pygame.draw.rect(self.screen, (20, 22, 28, 200), (map_x - 2, map_y - 2, map_w + 4, map_h + 4), border_radius=5)
        pygame.draw.rect(self.screen, (40, 45, 55), (map_x, map_y, map_w, map_h), border_radius=3)

        # Scale factors
        scale_x = map_w / level.cols
        scale_y = map_h / level.rows

        # Draw explored areas
        if self.fog_manager.fog and self.fog_manager.enabled:
            for y in range(level.rows):
                for x in range(level.cols):
                    if self.fog_manager.fog.explored[y][x]:
                        px = map_x + int(x * scale_x)
                        py = map_y + int(y * scale_y)
                        pygame.draw.rect(self.screen, (60, 65, 75), (px, py, max(1, int(scale_x)), max(1, int(scale_y))))
        else:
            # No fog - show entire maze
            pygame.draw.rect(self.screen, (50, 55, 65), (map_x, map_y, map_w, map_h))

        # Draw goal
        gx = map_x + int(level.goal_pos[0] * scale_x)
        gy = map_y + int(level.goal_pos[1] * scale_y)
        pygame.draw.rect(self.screen, COLOR_GOAL, (gx, gy, max(3, int(scale_x * 2)), max(3, int(scale_y * 2))))

        # Draw player
        px = map_x + int(level.player.x * scale_x)
        py = map_y + int(level.player.y * scale_y)
        pygame.draw.rect(self.screen, COLOR_PLAYER, (px, py, max(3, int(scale_x * 2)), max(3, int(scale_y * 2))))

        # Draw viewport rectangle
        camera = self.camera_manager.camera
        vx = map_x + int(camera.camera_x * scale_x)
        vy = map_y + int(camera.camera_y * scale_y)
        vw = int(camera.viewport_cols * scale_x)
        vh = int(camera.viewport_rows * scale_y)
        pygame.draw.rect(self.screen, (255, 255, 255), (vx, vy, vw, vh), 1)

        # Label
        font = pygame.font.SysFont("consolas", 10)
        label = font.render("MINIMAP", True, (150, 150, 150))
        self.screen.blit(label, (map_x + 5, map_y + map_h - 15))

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
