import random
import pygame
from collections import deque
import heapq

# -----------------------------
# CONFIG
# -----------------------------
CELL_SIZE = 20
COLS = 50
ROWS = 50

WALL_THICK = 3
FPS = 60
PANEL_H = 60

SCREEN_W = COLS * CELL_SIZE
SCREEN_H = ROWS * CELL_SIZE + PANEL_H

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


def can_move(walls, x, y, dx, dy):
    nx, ny = x + dx, y + dy
    if not in_bounds(nx, ny):
        return False
    w = walls[idx(x, y)]
    if dx == 0 and dy == -1:   # up
        return (w & TOP) == 0
    if dx == 1 and dy == 0:    # right
        return (w & RIGHT) == 0
    if dx == 0 and dy == 1:    # down
        return (w & BOTTOM) == 0
    if dx == -1 and dy == 0:   # left
        return (w & LEFT) == 0
    return False


def neighbors_open(walls, x, y):
    res = []
    if can_move(walls, x, y, 0, -1):
        res.append((x, y - 1))
    if can_move(walls, x, y, 1, 0):
        res.append((x + 1, y))
    if can_move(walls, x, y, 0, 1):
        res.append((x, y + 1))
    if can_move(walls, x, y, -1, 0):
        res.append((x - 1, y))
    return res


# -----------------------------
# SOLVERS
# -----------------------------
def bfs_shortest_path(walls, start, goal):
    """BFS shortest path on unweighted graph."""
    if start == goal:
        return [start]

    q = deque([start])
    prev = {start: None}

    while q:
        x, y = q.popleft()
        for n in neighbors_open(walls, x, y):
            if n not in prev:
                prev[n] = (x, y)
                if n == goal:
                    return reconstruct_path(prev, goal)
                q.append(n)

    return []


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_shortest_path(walls, start, goal):
    """
    A* with Manhattan heuristic.
    Returns shortest path in grid graph (same as BFS length, but faster on big grids).
    """
    if start == goal:
        return [start]

    open_heap = []
    heapq.heappush(open_heap, (manhattan(start, goal), 0, start))  # (f, g, node)

    prev = {start: None}
    g_score = {start: 0}
    closed = set()

    while open_heap:
        f, g, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        closed.add(cur)

        if cur == goal:
            return reconstruct_path(prev, goal)

        cx, cy = cur
        for nxt in neighbors_open(walls, cx, cy):
            tentative_g = g + 1
            if nxt in closed:
                continue

            old_g = g_score.get(nxt, 10**9)
            if tentative_g < old_g:
                g_score[nxt] = tentative_g
                prev[nxt] = cur
                new_f = tentative_g + manhattan(nxt, goal)
                heapq.heappush(open_heap, (new_f, tentative_g, nxt))

    return []


def reconstruct_path(prev, goal):
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


# -----------------------------
# RENDER
# -----------------------------
def draw_maze(screen, walls):
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


def draw_cell_fill(screen, x, y, color, pad=6, radius=6):
    rx = x * CELL_SIZE + pad
    ry = y * CELL_SIZE + pad
    rw = CELL_SIZE - pad * 2
    rh = CELL_SIZE - pad * 2
    pygame.draw.rect(screen, color, (rx, ry, rw, rh), border_radius=radius)


def draw_cell_border(screen, x, y, color, thickness=2, pad=4, radius=8):
    rx = x * CELL_SIZE + pad
    ry = y * CELL_SIZE + pad
    rw = CELL_SIZE - pad * 2
    rh = CELL_SIZE - pad * 2
    pygame.draw.rect(screen, color, (rx, ry, rw, rh), thickness, border_radius=radius)


def draw_hint_path(screen, path):
    if not path:
        return

    # subtle fill for cells
    for (x, y) in path:
        draw_cell_fill(screen, x, y, (230, 210, 80), pad=10, radius=6)

    # polyline through centers
    pts = []
    for (x, y) in path:
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2
        pts.append((cx, cy))

    if len(pts) >= 2:
        pygame.draw.lines(screen, (255, 230, 120), False, pts, 4)


# -----------------------------
# ANIMATED GENERATOR (DFS)
# -----------------------------
def animated_dfs_generator(cols, rows, seed=None):
    """
    DFS/backtracking maze generator as a generator (yields step-by-step state).
    Yields dict: walls, visited, current, stack, carved, done
    """
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    stack = [(0, 0)]
    visited[idx(0, 0)] = True

    yield {"walls": walls, "visited": visited, "current": (0, 0), "stack": stack, "carved": None, "done": False}

    while stack:
        cx, cy = stack[-1]
        neighbors = []

        for dx, dy, wall_bit, opp_bit in DIRS:
            nx, ny = cx + dx, cy + dy
            if in_bounds(nx, ny) and not visited[idx(nx, ny)]:
                neighbors.append((nx, ny, wall_bit, opp_bit))

        if neighbors:
            nx, ny, wall_bit, opp_bit = random.choice(neighbors)

            walls[idx(cx, cy)] &= ~wall_bit
            walls[idx(nx, ny)] &= ~opp_bit

            visited[idx(nx, ny)] = True
            stack.append((nx, ny))

            yield {
                "walls": walls,
                "visited": visited,
                "current": (nx, ny),
                "stack": stack,
                "carved": ((cx, cy), (nx, ny)),
                "done": False,
            }
        else:
            stack.pop()
            # backtrack step (also yields)
            yield {"walls": walls, "visited": visited, "current": (cx, cy), "stack": stack, "carved": None, "done": False}

    yield {"walls": walls, "visited": visited, "current": (0, 0), "stack": [], "carved": None, "done": True}


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Maze Game (Animated Generator + Hint BFS/A*)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 28, bold=True)

    # state
    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    player_x, player_y = 0, 0
    goal_x, goal_y = COLS - 1, ROWS - 1
    won = False
    moves = 0

    # hint
    show_hint = False
    use_astar = False  # False=BFS, True=A*
    hint_path = []

    # generation
    generating = True
    gen_paused = False
    gen_speed = 220  # steps per second
    gen_accum = 0.0
    gen = None
    current_cell = (0, 0)
    carved_edge = None

    def compute_path():
        start = (player_x, player_y)
        goal = (goal_x, goal_y)
        if use_astar:
            return astar_shortest_path(walls, start, goal)
        return bfs_shortest_path(walls, start, goal)

    def recalc_hint():
        nonlocal hint_path
        if show_hint and (not generating):
            hint_path = compute_path()
        else:
            hint_path = []

    def start_generation(animated=True):
        nonlocal generating, gen, walls, visited, player_x, player_y, won, moves
        nonlocal current_cell, carved_edge, show_hint, hint_path, gen_paused

        player_x, player_y = 0, 0
        won = False
        moves = 0
        carved_edge = None
        current_cell = (0, 0)

        show_hint = False
        hint_path = []
        gen_paused = False

        if animated:
            generating = True
            gen = animated_dfs_generator(COLS, ROWS)
        else:
            generating = False
            tmp = animated_dfs_generator(COLS, ROWS)
            last = None
            for last in tmp:
                pass
            walls = last["walls"]
            visited = last["visited"]

    def reset_player():
        nonlocal player_x, player_y, won, moves
        player_x, player_y = 0, 0
        won = False
        moves = 0
        recalc_hint()

    def gen_step_once():
        """Run exactly one generator step (used for N in pause mode)."""
        nonlocal generating, carved_edge, current_cell, walls, visited
        try:
            state = next(gen)
            walls = state["walls"]
            visited = state["visited"]
            current_cell = state["current"]
            carved_edge = state["carved"]
            if state["done"]:
                generating = False
                carved_edge = None
                recalc_hint()
        except StopIteration:
            generating = False
            carved_edge = None
            recalc_hint()

    # start
    start_generation(animated=True)

    move_cooldown_ms = 90
    last_move_time = 0

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        now = pygame.time.get_ticks()
        dt = dt_ms / 1000.0

        # ---------------- INPUT ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_g:
                    start_generation(animated=True)

                elif event.key == pygame.K_r:
                    start_generation(animated=False)
                    recalc_hint()

                elif event.key == pygame.K_SPACE and not generating:
                    reset_player()

                elif event.key == pygame.K_h and not generating:
                    show_hint = not show_hint
                    recalc_hint()

                elif event.key == pygame.K_a and not generating:
                    # toggle BFS <-> A*
                    use_astar = not use_astar
                    recalc_hint()

                elif event.key == pygame.K_p and generating:
                    # pause/resume generation
                    gen_paused = not gen_paused

                elif event.key == pygame.K_n and generating and gen_paused:
                    # single step in pause
                    gen_step_once()

                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    gen_speed = min(1200, gen_speed + 60)

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    gen_speed = max(20, gen_speed - 60)

        # ------------- UPDATE (GEN) -------------
        if generating and (not gen_paused):
            gen_accum += dt * gen_speed
            steps = int(gen_accum)
            if steps > 0:
                gen_accum -= steps
                for _ in range(steps):
                    gen_step_once()
                    if not generating:
                        break

        # ------------ UPDATE (PLAYER) -----------
        moved = False
        if (not generating) and (not won) and (now - last_move_time) >= move_cooldown_ms:
            keys = pygame.key.get_pressed()
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
                moved = True

                if (player_x, player_y) == (goal_x, goal_y):
                    won = True

        if moved:
            recalc_hint()

        # ---------------- DRAW -----------------
        screen.fill((20, 22, 28))
        maze_h = ROWS * CELL_SIZE
        pygame.draw.rect(screen, (16, 18, 24), (0, 0, SCREEN_W, maze_h))

        if generating:
            # visited fill
            for y in range(ROWS):
                for x in range(COLS):
                    if visited[idx(x, y)]:
                        draw_cell_fill(screen, x, y, (28, 32, 40), pad=2, radius=4)

            # current highlight
            cx, cy = current_cell
            draw_cell_border(screen, cx, cy, (255, 210, 120), thickness=3, pad=3, radius=6)

            # carved edge highlight
            if carved_edge is not None:
                (ax, ay), (bx, by) = carved_edge
                draw_cell_border(screen, ax, ay, (120, 220, 255), thickness=2, pad=5, radius=6)
                draw_cell_border(screen, bx, by, (120, 220, 255), thickness=2, pad=5, radius=6)

        else:
            # hint path
            if show_hint and hint_path:
                draw_hint_path(screen, hint_path)

            # goal & player
            draw_cell_fill(screen, goal_x, goal_y, (60, 200, 120), pad=6, radius=6)
            draw_cell_fill(screen, player_x, player_y, (70, 140, 255), pad=6, radius=6)

        # walls on top
        draw_maze(screen, walls)

        # panel
        panel_y = maze_h
        pygame.draw.rect(screen, (12, 14, 18), (0, panel_y, SCREEN_W, PANEL_H))

        if generating:
            ptxt = "PAUSED" if gen_paused else "RUN"
            info = f"Generating [{ptxt}] | P: pause | N: step | speed: {gen_speed}/s | G: regen | R: instant | +/-: speed"
        else:
            hint_txt = "ON" if show_hint else "OFF"
            algo = "A*" if use_astar else "BFS"
            info = f"Moves: {moves} | H: hint({hint_txt}) | A: algo({algo}) | Arrows: move | SPACE: restart | G/R: new"

        screen.blit(font.render(info, True, (210, 210, 210)), (12, panel_y + 18))

        if won:
            msg = "YOU WIN! (Press G for new animated maze)"
            text = big_font.render(msg, True, (255, 220, 120))
            screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, panel_y - 44))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
