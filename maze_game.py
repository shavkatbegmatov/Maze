import random
import pygame

# -----------------------------
# CONFIG
# -----------------------------
CELL_SIZE = 28
COLS = 25   # labirint kengligi (kataklar soni)
ROWS = 18   # labirint balandligi (kataklar soni)

WALL_THICK = 3
FPS = 60

SCREEN_W = COLS * CELL_SIZE
SCREEN_H = ROWS * CELL_SIZE + 60  # pastda status panel

# Wall bit flags
TOP, RIGHT, BOTTOM, LEFT = 1, 2, 4, 8

DIRS = [
    (0, -1, TOP, BOTTOM),    # up
    (1, 0, RIGHT, LEFT),     # right
    (0, 1, BOTTOM, TOP),     # down
    (-1, 0, LEFT, RIGHT),    # left
]


def idx(x, y):
    return y * COLS + x


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def generate_maze_dfs(cols, rows, seed=None):
    """Depth-First Search / backtracking maze generator."""
    if seed is not None:
        random.seed(seed)

    # Each cell starts with all walls present
    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    stack = []
    cx, cy = 0, 0
    visited[idx(cx, cy)] = True
    stack.append((cx, cy))

    while stack:
        cx, cy = stack[-1]
        neighbors = []

        # collect unvisited neighbors
        for dx, dy, wall_bit, opp_bit in DIRS:
            nx, ny = cx + dx, cy + dy
            if in_bounds(nx, ny) and not visited[idx(nx, ny)]:
                neighbors.append((nx, ny, wall_bit, opp_bit))

        if neighbors:
            nx, ny, wall_bit, opp_bit = random.choice(neighbors)
            # remove wall between current and next
            walls[idx(cx, cy)] &= ~wall_bit
            walls[idx(nx, ny)] &= ~opp_bit

            visited[idx(nx, ny)] = True
            stack.append((nx, ny))
        else:
            stack.pop()

    return walls


def can_move(walls, x, y, dx, dy):
    """Check if we can move from (x,y) to (x+dx,y+dy) without crossing a wall."""
    nx, ny = x + dx, y + dy
    if not in_bounds(nx, ny):
        return False

    cell_walls = walls[idx(x, y)]
    if dx == 0 and dy == -1:   # up
        return (cell_walls & TOP) == 0
    if dx == 1 and dy == 0:    # right
        return (cell_walls & RIGHT) == 0
    if dx == 0 and dy == 1:    # down
        return (cell_walls & BOTTOM) == 0
    if dx == -1 and dy == 0:   # left
        return (cell_walls & LEFT) == 0
    return False


def draw_maze(screen, walls):
    """Draw maze walls."""
    wall_color = (230, 230, 230)
    for y in range(ROWS):
        for x in range(COLS):
            w = walls[idx(x, y)]
            x0 = x * CELL_SIZE
            y0 = y * CELL_SIZE
            x1 = x0 + CELL_SIZE
            y1 = y0 + CELL_SIZE

            if w & TOP:
                pygame.draw.line(screen, wall_color, (x0, y0), (x1, y0), WALL_THICK)
            if w & RIGHT:
                pygame.draw.line(screen, wall_color, (x1, y0), (x1, y1), WALL_THICK)
            if w & BOTTOM:
                pygame.draw.line(screen, wall_color, (x0, y1), (x1, y1), WALL_THICK)
            if w & LEFT:
                pygame.draw.line(screen, wall_color, (x0, y0), (x0, y1), WALL_THICK)


def draw_cell_overlay(screen, x, y, color, pad=6):
    """Draw a filled rectangle inside the cell."""
    rx = x * CELL_SIZE + pad
    ry = y * CELL_SIZE + pad
    rw = CELL_SIZE - pad * 2
    rh = CELL_SIZE - pad * 2
    pygame.draw.rect(screen, color, (rx, ry, rw, rh), border_radius=6)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Maze Game (Generator + Runner)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 28, bold=True)

    def new_game():
        nonlocal walls, player_x, player_y, goal_x, goal_y, won, moves
        walls = generate_maze_dfs(COLS, ROWS)
        player_x, player_y = 0, 0
        goal_x, goal_y = COLS - 1, ROWS - 1
        won = False
        moves = 0

    def reset_player():
        nonlocal player_x, player_y, won, moves
        player_x, player_y = 0, 0
        won = False
        moves = 0

    walls = []
    player_x = player_y = 0
    goal_x = goal_y = 0
    won = False
    moves = 0

    new_game()

    # simple key repeat control
    move_cooldown_ms = 90
    last_move_time = 0

    running = True
    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    new_game()
                if event.key == pygame.K_SPACE:
                    reset_player()

        keys = pygame.key.get_pressed()
        if not won and (now - last_move_time) >= move_cooldown_ms:
            dx = dy = 0
            if keys[pygame.K_UP]:
                dx, dy = 0, -1
            elif keys[pygame.K_RIGHT]:
                dx, dy = 1, 0
            elif keys[pygame.K_DOWN]:
                dx, dy = 0, 1
            elif keys[pygame.K_LEFT]:
                dx, dy = -1, 0

            if (dx, dy) != (0, 0) and can_move(walls, player_x, player_y, dx, dy):
                player_x += dx
                player_y += dy
                moves += 1
                last_move_time = now

                if (player_x, player_y) == (goal_x, goal_y):
                    won = True

        # -----------------------------
        # DRAW
        # -----------------------------
        screen.fill((20, 22, 28))

        # maze area background
        pygame.draw.rect(screen, (16, 18, 24), (0, 0, SCREEN_W, ROWS * CELL_SIZE))

        # goal + player overlays
        draw_cell_overlay(screen, goal_x, goal_y, (60, 200, 120))    # goal
        draw_cell_overlay(screen, player_x, player_y, (70, 140, 255)) # player

        draw_maze(screen, walls)

        # status panel
        panel_y = ROWS * CELL_SIZE
        pygame.draw.rect(screen, (12, 14, 18), (0, panel_y, SCREEN_W, 60))
        info = f"Moves: {moves} | R: new maze | SPACE: restart | Arrows: move"
        screen.blit(font.render(info, True, (210, 210, 210)), (12, panel_y + 18))

        if won:
            msg = "YOU WIN! (Press R for new maze)"
            text = big_font.render(msg, True, (255, 220, 120))
            screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, panel_y - 44))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
