"""
Maze Game V3 - Test Version
Simple test to verify core systems work
"""

import pygame
from game.level_manager import LevelManager
from game.collision import CollisionHandler
from utils.constants import CELL_SIZE, FPS, PANEL_H, DIFFICULTY_EASY
from utils.colors import (
    COLOR_BG, COLOR_MAZE_BG, COLOR_WALL, COLOR_PLAYER, COLOR_GOAL,
    COLOR_TEXT, COLOR_PANEL_BG
)


def draw_maze(screen, walls, cols, rows):
    """Draw maze walls"""
    wall_color = COLOR_WALL
    wall_thick = 3

    for y in range(rows):
        for x in range(cols):
            idx = y * cols + x
            w = walls[idx]
            x0 = x * CELL_SIZE
            y0 = y * CELL_SIZE
            x1 = x0 + CELL_SIZE
            y1 = y0 + CELL_SIZE

            # Draw walls
            if w & 1:  # TOP
                pygame.draw.line(screen, wall_color, (x0, y0), (x1, y0), wall_thick)
            if w & 2:  # RIGHT
                pygame.draw.line(screen, wall_color, (x1, y0), (x1, y1), wall_thick)
            if w & 4:  # BOTTOM
                pygame.draw.line(screen, wall_color, (x0, y1), (x1, y1), wall_thick)
            if w & 8:  # LEFT
                pygame.draw.line(screen, wall_color, (x0, y0), (x0, y1), wall_thick)


def draw_cell(screen, x, y, color, pad=6):
    """Draw filled cell"""
    rx = x * CELL_SIZE + pad
    ry = y * CELL_SIZE + pad
    rw = CELL_SIZE - pad * 2
    rh = CELL_SIZE - pad * 2
    pygame.draw.rect(screen, color, (rx, ry, rw, rh), border_radius=6)


def main():
    pygame.init()

    # Create level
    level_manager = LevelManager()
    level = level_manager.create_level(DIFFICULTY_EASY, generator_index=0, animated=False)

    # Setup screen
    screen_w = level.cols * CELL_SIZE
    screen_h = level.rows * CELL_SIZE + PANEL_H
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("Maze Game V3 - Test Version")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    collision_handler = CollisionHandler()

    # Movement cooldown
    move_cooldown_ms = 90
    last_move_time = 0

    running = True
    won = False

    while running:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 1000.0
        now = pygame.time.get_ticks()

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Reset
                    level.reset()
                    won = False
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # Update
        if not won:
            # Player movement
            if (now - last_move_time) >= move_cooldown_ms:
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
                    if level.player.move(dx, dy, level.walls, level.cols, level.rows):
                        last_move_time = now

                        # Check collisions
                        collision_result = collision_handler.check_player_position(
                            level.player,
                            level.enemy_manager,
                            level.powerup_manager,
                            level.trap_manager,
                            level.door_manager,
                            level.walls,
                            level.cols,
                            level.rows
                        )

                        if collision_result['player_died']:
                            print("Player died!")
                            level.reset()

            # Update level
            level.update(dt)

            # Check win
            if level.player.x == level.goal_pos[0] and level.player.y == level.goal_pos[1]:
                won = True
                print("YOU WIN!")

        # Draw
        screen.fill(COLOR_BG)
        maze_h = level.rows * CELL_SIZE
        pygame.draw.rect(screen, COLOR_MAZE_BG, (0, 0, screen_w, maze_h))

        # Draw entities
        draw_cell(screen, level.goal_pos[0], level.goal_pos[1], COLOR_GOAL)

        # Draw keys
        from utils.colors import KEY_COLORS
        for key in level.door_manager.keys:
            if not key.collected:
                draw_cell(screen, key.x, key.y, key.get_color_rgb(), pad=8)

        # Draw doors
        from utils.colors import DOOR_COLORS
        for door in level.door_manager.doors:
            if door.locked:
                draw_cell(screen, door.x, door.y, door.get_color_rgb(), pad=4)

        # Draw power-ups
        for powerup in level.powerup_manager.get_uncollected_powerups():
            draw_cell(screen, powerup.x, powerup.y, powerup.get_color(), pad=8)

        # Draw traps (only visible ones)
        for trap in level.trap_manager.get_visible_traps():
            draw_cell(screen, trap.x, trap.y, trap.get_color(), pad=10)

        # Draw enemies
        for enemy in level.enemy_manager.enemies:
            draw_cell(screen, enemy.x, enemy.y, enemy.get_color(), pad=7)

        # Draw player
        draw_cell(screen, level.player.x, level.player.y, COLOR_PLAYER)

        # Draw maze walls
        draw_maze(screen, level.walls, level.cols, level.rows)

        # Draw panel
        panel_y = maze_h
        pygame.draw.rect(screen, COLOR_PANEL_BG, (0, panel_y, screen_w, PANEL_H))

        # Info text
        info_lines = [
            f"Health: {level.player.stats['health']:.0f}/{level.player.stats['max_health']}  Energy: {level.player.stats['energy']:.0f}/{level.player.stats['max_energy']}",
            f"Position: ({level.player.x}, {level.player.y})  Moves: {level.player.moves}",
            f"Keys: {len(level.player.inventory['keys'])}  Enemies: {len(level.enemy_manager.enemies)}",
            "R: Reset | ESC: Quit | Arrow keys or WASD: Move"
        ]

        for i, line in enumerate(info_lines):
            text = font.render(line, True, COLOR_TEXT)
            screen.blit(text, (10, panel_y + 10 + i * 20))

        if won:
            big_font = pygame.font.SysFont("consolas", 32, bold=True)
            win_text = big_font.render("YOU WIN!", True, (255, 220, 120))
            screen.blit(win_text, (screen_w // 2 - win_text.get_width() // 2, screen_h // 2))

        pygame.display.flip()

    pygame.quit()
    print("Game closed.")


if __name__ == "__main__":
    main()
