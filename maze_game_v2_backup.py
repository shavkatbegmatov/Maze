import random
import pygame
from collections import deque
import heapq

# -----------------------------
# CONFIG
# -----------------------------
CELL_SIZE = 35
COLS = 40
ROWS = 25

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

DIR_TO_BITS = {
    (0, -1): (TOP, BOTTOM),
    (1, 0): (RIGHT, LEFT),
    (0, 1): (BOTTOM, TOP),
    (-1, 0): (LEFT, RIGHT),
}


def neighbor_dirs(x, y):
    res = []
    for dx, dy, wall_bit, opp_bit in DIRS:
        nx, ny = x + dx, y + dy
        if in_bounds(nx, ny):
            res.append((nx, ny, wall_bit, opp_bit))
    return res


def carve_passage(walls, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    bits = DIR_TO_BITS.get((dx, dy))
    if bits is None:
        return
    wall_bit, opp_bit = bits
    walls[idx(ax, ay)] &= ~wall_bit
    walls[idx(bx, by)] &= ~opp_bit


def close_passage(walls, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    bits = DIR_TO_BITS.get((dx, dy))
    if bits is None:
        return
    wall_bit, opp_bit = bits
    walls[idx(ax, ay)] |= wall_bit
    walls[idx(bx, by)] |= opp_bit


def is_open_between(walls, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    bits = DIR_TO_BITS.get((dx, dy))
    if bits is None:
        return False
    wall_bit, _ = bits
    return (walls[idx(ax, ay)] & wall_bit) == 0


ADJ_EDGES = []
for y in range(ROWS):
    for x in range(COLS):
        if x + 1 < COLS:
            ADJ_EDGES.append(((x, y), (x + 1, y)))
        if y + 1 < ROWS:
            ADJ_EDGES.append(((x, y), (x, y + 1)))


def bfs_component_without_edge(walls, start, edge):
    (ax, ay), (bx, by) = edge
    forbidden = {(ax, ay, bx, by), (bx, by, ax, ay)}
    q = deque([start])
    seen = {start}
    while q:
        x, y = q.popleft()
        for nx, ny, _, _ in neighbor_dirs(x, y):
            if (x, y, nx, ny) in forbidden:
                continue
            if is_open_between(walls, x, y, nx, ny) and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def swap_edge_to_break_corridor(walls, edge):
    comp = bfs_component_without_edge(walls, edge[0], edge)
    candidates = []
    for (u, v) in ADJ_EDGES:
        u_in = u in comp
        v_in = v in comp
        if u_in != v_in and not is_open_between(walls, u[0], u[1], v[0], v[1]):
            candidates.append((u, v))
    if not candidates:
        return False
    (ux, uy), (vx, vy) = random.choice(candidates)
    carve_passage(walls, ux, uy, vx, vy)
    (ax, ay), (bx, by) = edge
    close_passage(walls, ax, ay, bx, by)
    return True


def fix_open_borders(walls):
    top = [((x, 0), (x + 1, 0)) for x in range(COLS - 1)]
    bottom = [((x, ROWS - 1), (x + 1, ROWS - 1)) for x in range(COLS - 1)]
    left = [((0, y), (0, y + 1)) for y in range(ROWS - 1)]
    right = [((COLS - 1, y), (COLS - 1, y + 1)) for y in range(ROWS - 1)]

    for edges in (top, right, bottom, left):
        if edges and all(is_open_between(walls, a[0], a[1], b[0], b[1]) for a, b in edges):
            for i, edge in enumerate(edges):
                if i % 2 == 0 and is_open_between(walls, edge[0][0], edge[0][1], edge[1][0], edge[1][1]):
                    swap_edge_to_break_corridor(walls, edge)


def random_cell():
    return random.randrange(COLS), random.randrange(ROWS)


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
def reconstruct_path(prev, goal):
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def bfs_shortest_path(walls, start, goal):
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


# -----------------------------
# BRAID (ADD LOOPS)
# -----------------------------
def exits_count(w):
    # number of open sides
    e = 0
    if (w & TOP) == 0:
        e += 1
    if (w & RIGHT) == 0:
        e += 1
    if (w & BOTTOM) == 0:
        e += 1
    if (w & LEFT) == 0:
        e += 1
    return e


def braid_maze(walls, braid_chance):
    """
    Perfect maze -> braided maze (adds loops by opening extra walls mainly on dead-ends).
    braid_chance: 0.0..0.9 (0%..90%)
    """
    if braid_chance <= 0:
        return

    for y in range(ROWS):
        for x in range(COLS):
            w = walls[idx(x, y)]

            # dead-end = only 1 exit
            if exits_count(w) == 1 and random.random() < braid_chance:
                candidates = []
                for dx, dy, wall_bit, opp_bit in DIRS:
                    nx, ny = x + dx, y + dy
                    if not in_bounds(nx, ny):
                        continue
                    # if wall exists in this direction, we can open it
                    if (w & wall_bit) != 0:
                        candidates.append((nx, ny, wall_bit, opp_bit))

                if candidates:
                    nx, ny, wall_bit, opp_bit = random.choice(candidates)
                    walls[idx(x, y)] &= ~wall_bit
                    walls[idx(nx, ny)] &= ~opp_bit


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

    for (x, y) in path:
        draw_cell_fill(screen, x, y, (230, 210, 80), pad=10, radius=6)

    pts = []
    for (x, y) in path:
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2
        pts.append((cx, cy))

    if len(pts) >= 2:
        pygame.draw.lines(screen, (255, 230, 120), False, pts, 4)


def draw_win_path(screen, path):
    if not path:
        return

    for (x, y) in path:
        draw_cell_fill(screen, x, y, (255, 170, 90), pad=9, radius=6)

    pts = []
    for (x, y) in path:
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2
        pts.append((cx, cy))

    if len(pts) >= 2:
        pygame.draw.lines(screen, (255, 200, 120), False, pts, 4)


def draw_trail(screen, trail):
    if not trail:
        return

    for (x, y) in trail:
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2
        r = max(3, CELL_SIZE // 6)
        glow_r = r + 2
        pygame.draw.circle(screen, (40, 110, 175), (cx, cy), glow_r)
        pygame.draw.circle(screen, (160, 230, 255), (cx, cy), r)


def draw_menu(screen, walls, overlay, menu_items, menu_index, title_font, menu_font, font, best_moves):
    screen.fill((20, 22, 28))
    maze_h = ROWS * CELL_SIZE
    pygame.draw.rect(screen, (16, 18, 24), (0, 0, SCREEN_W, maze_h))
    draw_maze(screen, walls)

    if overlay is not None:
        screen.blit(overlay, (0, 0))

    title = title_font.render("MAZE GAME", True, (255, 220, 120))
    screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 50))

    subtitle = font.render("Select an option", True, (210, 210, 210))
    screen.blit(subtitle, (SCREEN_W // 2 - subtitle.get_width() // 2, 110))

    if best_moves is not None:
        best_txt = font.render(f"Best moves: {best_moves}", True, (170, 230, 190))
        screen.blit(best_txt, (SCREEN_W // 2 - best_txt.get_width() // 2, 135))

    start_y = 190
    gap = 36
    for i, label in enumerate(menu_items):
        is_selected = i == menu_index
        color = (255, 230, 160) if is_selected else (210, 210, 210)
        text = menu_font.render(label, True, color)
        x = SCREEN_W // 2 - text.get_width() // 2
        y = start_y + i * gap

        if is_selected:
            pad_x = 18
            pad_y = 8
            pygame.draw.rect(
                screen,
                (255, 220, 120),
                (x - pad_x, y - pad_y, text.get_width() + pad_x * 2, text.get_height() + pad_y * 2),
                2,
                border_radius=8,
            )
        screen.blit(text, (x, y))

    help_y = SCREEN_H - 120
    help_lines = [
        "Up/Down or W/S: navigate | Enter: select",
        "G: start animated | R: start instant | Esc: quit",
        "M: change generator | A: solver | K/L: loops -/+ (10%)",
    ]
    for i, line in enumerate(help_lines):
        t = font.render(line, True, (190, 190, 190))
        screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, help_y + i * 22))


# -----------------------------
# MAZE GENERATORS
# -----------------------------
def animated_dfs_generator(cols, rows, seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    stack = [(0, 0)]
    visited[idx(0, 0)] = True

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

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

            yield {"walls": walls, "visited": visited, "current": (nx, ny), "carved": ((cx, cy), (nx, ny)), "done": False}
        else:
            stack.pop()
            yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": False}

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


def gen_dfs_backtracker(seed=None):
    return animated_dfs_generator(COLS, ROWS, seed)


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1
        return True


def gen_prim(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    sx, sy = 0, 0
    visited[idx(sx, sy)] = True
    frontier = []
    for nx, ny, _, _ in neighbor_dirs(sx, sy):
        frontier.append(((sx, sy), (nx, ny)))

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": False}

    while frontier:
        i = random.randrange(len(frontier))
        (ax, ay), (bx, by) = frontier.pop(i)
        if visited[idx(bx, by)]:
            continue
        carve_passage(walls, ax, ay, bx, by)
        visited[idx(bx, by)] = True
        yield {"walls": walls, "visited": visited, "current": (bx, by), "carved": ((ax, ay), (bx, by)), "done": False}
        for nx, ny, _, _ in neighbor_dirs(bx, by):
            if not visited[idx(nx, ny)]:
                frontier.append(((bx, by), (nx, ny)))

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": True}


def gen_kruskal(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)
    uf = UnionFind(COLS * ROWS)

    edges = []
    for y in range(ROWS):
        for x in range(COLS):
            if x + 1 < COLS:
                edges.append(((x, y), (x + 1, y)))
            if y + 1 < ROWS:
                edges.append(((x, y), (x, y + 1)))
    random.shuffle(edges)

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    for (ax, ay), (bx, by) in edges:
        if uf.union(idx(ax, ay), idx(bx, by)):
            carve_passage(walls, ax, ay, bx, by)
            visited[idx(ax, ay)] = True
            visited[idx(bx, by)] = True
            yield {"walls": walls, "visited": visited, "current": (bx, by), "carved": ((ax, ay), (bx, by)), "done": False}

    for i in range(len(visited)):
        visited[i] = True
    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


def gen_aldous_broder(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    cx, cy = random_cell()
    visited[idx(cx, cy)] = True
    remaining = COLS * ROWS - 1

    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": False}

    while remaining > 0:
        nx, ny, _, _ = random.choice(neighbor_dirs(cx, cy))
        if not visited[idx(nx, ny)]:
            carve_passage(walls, cx, cy, nx, ny)
            visited[idx(nx, ny)] = True
            remaining -= 1
            yield {"walls": walls, "visited": visited, "current": (nx, ny), "carved": ((cx, cy), (nx, ny)), "done": False}
        cx, cy = nx, ny

    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": True}


def gen_wilson(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    in_maze = [False] * (COLS * ROWS)
    visited = [False] * (COLS * ROWS)

    sx, sy = 0, 0
    in_maze[idx(sx, sy)] = True
    visited[idx(sx, sy)] = True

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": False}

    while not all(in_maze):
        candidates = [(x, y) for y in range(ROWS) for x in range(COLS) if not in_maze[idx(x, y)]]
        wx, wy = random.choice(candidates)
        path = [(wx, wy)]
        path_index = {path[0]: 0}
        cx, cy = wx, wy

        while not in_maze[idx(cx, cy)]:
            nx, ny, _, _ = random.choice(neighbor_dirs(cx, cy))
            nxt = (nx, ny)
            if nxt in path_index:
                loop_i = path_index[nxt]
                for cell in path[loop_i + 1:]:
                    del path_index[cell]
                path = path[:loop_i + 1]
            else:
                path.append(nxt)
                path_index[nxt] = len(path) - 1
            cx, cy = nxt

        for i in range(len(path) - 1):
            ax, ay = path[i]
            bx, by = path[i + 1]
            carve_passage(walls, ax, ay, bx, by)
            in_maze[idx(ax, ay)] = True
            in_maze[idx(bx, by)] = True
            visited[idx(ax, ay)] = True
            visited[idx(bx, by)] = True
            yield {"walls": walls, "visited": visited, "current": (bx, by), "carved": ((ax, ay), (bx, by)), "done": False}

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": True}


def gen_hunt_and_kill(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    cx, cy = random_cell()
    visited[idx(cx, cy)] = True
    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": False}

    while True:
        unvisited_neighbors = [(nx, ny) for nx, ny, _, _ in neighbor_dirs(cx, cy) if not visited[idx(nx, ny)]]
        if unvisited_neighbors:
            nx, ny = random.choice(unvisited_neighbors)
            carve_passage(walls, cx, cy, nx, ny)
            visited[idx(nx, ny)] = True
            yield {"walls": walls, "visited": visited, "current": (nx, ny), "carved": ((cx, cy), (nx, ny)), "done": False}
            cx, cy = nx, ny
            continue

        found = False
        for y in range(ROWS):
            for x in range(COLS):
                if visited[idx(x, y)]:
                    continue
                neighbors = [(nx, ny) for nx, ny, _, _ in neighbor_dirs(x, y) if visited[idx(nx, ny)]]
                if neighbors:
                    nx, ny = random.choice(neighbors)
                    carve_passage(walls, x, y, nx, ny)
                    visited[idx(x, y)] = True
                    yield {"walls": walls, "visited": visited, "current": (x, y), "carved": ((x, y), (nx, ny)), "done": False}
                    cx, cy = x, y
                    found = True
                    break
            if found:
                break

        if not found:
            break

    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": True}


def gen_binary_tree(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    for y in range(ROWS):
        for x in range(COLS):
            # Binary Tree with south/west bias.
            neighbors = []
            if y + 1 < ROWS:
                neighbors.append((x, y + 1))
            if x - 1 >= 0:
                neighbors.append((x - 1, y))
            if neighbors:
                nx, ny = random.choice(neighbors)
                carve_passage(walls, x, y, nx, ny)
                visited[idx(x, y)] = True
                visited[idx(nx, ny)] = True
                yield {"walls": walls, "visited": visited, "current": (x, y), "carved": ((x, y), (nx, ny)), "done": False}

    fix_open_borders(walls)
    for i in range(len(visited)):
        visited[i] = True
    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


def gen_sidewinder(seed=None):
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    for y in range(ROWS):
        run = []
        for x in range(COLS):
            run.append((x, y))
            at_east = x == COLS - 1
            at_north = y == 0
            carve_east = (not at_east) and (at_north or random.choice([True, False]))

            if carve_east:
                carve_passage(walls, x, y, x + 1, y)
                visited[idx(x, y)] = True
                visited[idx(x + 1, y)] = True
                yield {"walls": walls, "visited": visited, "current": (x, y), "carved": ((x, y), (x + 1, y)), "done": False}
            else:
                if not at_north:
                    rx, ry = random.choice(run)
                    carve_passage(walls, rx, ry, rx, ry - 1)
                    visited[idx(rx, ry)] = True
                    visited[idx(rx, ry - 1)] = True
                    yield {"walls": walls, "visited": visited, "current": (rx, ry), "carved": ((rx, ry), (rx, ry - 1)), "done": False}
                run = []

    fix_open_borders(walls)
    for i in range(len(visited)):
        visited[i] = True
    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


GEN_ALGOS = [
    ("DFS Backtracker", gen_dfs_backtracker),
    ("Prim", gen_prim),
    ("Kruskal", gen_kruskal),
    ("Aldous-Broder", gen_aldous_broder),
    ("Wilson", gen_wilson),
    ("Hunt-and-Kill", gen_hunt_and_kill),
    ("Binary Tree", gen_binary_tree),
    ("Sidewinder", gen_sidewinder),
]


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Maze Game (Animated + Hint + A* + Pause/Step + Loop%)")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 28, bold=True)
    title_font = pygame.font.SysFont("consolas", 48, bold=True)
    menu_font = pygame.font.SysFont("consolas", 24)
    menu_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    menu_overlay.fill((10, 12, 16, 200))

    # state
    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(COLS * ROWS)]
    visited = [False] * (COLS * ROWS)

    player_x, player_y = 0, 0
    goal_x, goal_y = COLS - 1, ROWS - 1
    won = False
    moves = 0
    trail = [(0, 0)]

    # hint
    show_hint = False
    use_astar = False
    hint_path = []
    win_path = []
    best_moves = None

    # generation
    generating = True
    gen_paused = False
    gen_speed = 220
    gen_accum = 0.0
    gen = None
    current_cell = (0, 0)
    carved_edge = None

    # loop control (0..90%, step 10%)
    loop_percent = 0  # 0,10,20,...,90
    in_menu = True
    menu_index = 0
    step_mode = False
    gen_algo_index = 0

    MENU_START_ANIM = 0
    MENU_START_INSTANT = 1
    MENU_STEP_MODE = 2
    MENU_GEN_ALGO = 3
    MENU_SOLVER = 4
    MENU_LOOPS = 5
    MENU_QUIT = 6

    def braid_chance():
        return loop_percent / 100.0

    def compute_path():
        start = (player_x, player_y)
        goal = (goal_x, goal_y)
        return astar_shortest_path(walls, start, goal) if use_astar else bfs_shortest_path(walls, start, goal)

    def compute_start_to_goal_path():
        start = (0, 0)
        goal = (goal_x, goal_y)
        return astar_shortest_path(walls, start, goal) if use_astar else bfs_shortest_path(walls, start, goal)

    def recalc_hint():
        nonlocal hint_path
        if show_hint and (not generating):
            hint_path = compute_path()
        else:
            hint_path = []

    def finalize_maze_with_loops():
        nonlocal walls
        # apply braiding after generation completes
        braid_maze(walls, braid_chance())

    def start_generation(animated=True):
        nonlocal generating, gen, walls, visited, player_x, player_y, won, moves, trail
        nonlocal current_cell, carved_edge, show_hint, hint_path, gen_paused, win_path, gen_accum

        player_x, player_y = 0, 0
        won = False
        moves = 0
        trail = [(0, 0)]
        carved_edge = None
        current_cell = (0, 0)
        win_path = []
        gen_accum = 0.0

        show_hint = False
        hint_path = []
        gen_fn = GEN_ALGOS[gen_algo_index][1]
        if animated:
            generating = True
            gen_paused = step_mode
            gen = gen_fn()
        else:
            generating = False
            gen_paused = False
            tmp = gen_fn()
            last = None
            for last in tmp:
                pass
            walls = last["walls"]
            visited = last["visited"]
            finalize_maze_with_loops()
            recalc_hint()

    def reset_player():
        nonlocal player_x, player_y, won, moves, trail, win_path
        player_x, player_y = 0, 0
        won = False
        moves = 0
        trail = [(0, 0)]
        win_path = []
        recalc_hint()

    def gen_step_once():
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
                finalize_maze_with_loops()
                recalc_hint()
        except StopIteration:
            generating = False
            carved_edge = None
            finalize_maze_with_loops()
            recalc_hint()

    # start
    start_generation(animated=False)
    in_menu = True

    def menu_labels():
        algo_txt = "A*" if use_astar else "BFS"
        step_txt = "Step-by-step" if step_mode else "Normal"
        gen_txt = GEN_ALGOS[gen_algo_index][0]
        return [
            "Start (Animated)",
            "Start (Instant)",
            f"Generation: {step_txt}",
            f"Maze Gen: {gen_txt}",
            f"Solver: {algo_txt}",
            f"Loops: {loop_percent}%",
            "Quit",
        ]

    def handle_menu_select():
        nonlocal in_menu, running, use_astar, loop_percent, step_mode, gen_paused, gen_algo_index
        if menu_index == MENU_START_ANIM:
            start_generation(animated=True)
            in_menu = False
        elif menu_index == MENU_START_INSTANT:
            start_generation(animated=False)
            in_menu = False
        elif menu_index == MENU_STEP_MODE:
            step_mode = not step_mode
            if generating:
                gen_paused = step_mode
        elif menu_index == MENU_GEN_ALGO:
            gen_algo_index = (gen_algo_index + 1) % len(GEN_ALGOS)
        elif menu_index == MENU_SOLVER:
            use_astar = not use_astar
        elif menu_index == MENU_LOOPS:
            loop_percent = loop_percent + 10
            if loop_percent > 90:
                loop_percent = 0
        elif menu_index == MENU_QUIT:
            running = False

    move_cooldown_ms = 90
    last_move_time = 0

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        now = pygame.time.get_ticks()
        dt = dt_ms / 1000.0

        # INPUT
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if in_menu:
                    menu_len = len(menu_labels())
                    if event.key in (pygame.K_UP, pygame.K_w):
                        menu_index = (menu_index - 1) % menu_len
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        menu_index = (menu_index + 1) % menu_len
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        handle_menu_select()
                    elif event.key == pygame.K_g:
                        start_generation(animated=True)
                        in_menu = False
                    elif event.key == pygame.K_r:
                        start_generation(animated=False)
                        in_menu = False
                    elif event.key == pygame.K_a:
                        use_astar = not use_astar
                    elif event.key == pygame.K_m:
                        gen_algo_index = (gen_algo_index + 1) % len(GEN_ALGOS)
                    elif event.key == pygame.K_l:
                        loop_percent = min(90, loop_percent + 10)
                    elif event.key == pygame.K_k:
                        loop_percent = max(0, loop_percent - 10)
                    elif event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False
                    continue

                if event.key == pygame.K_g:
                    start_generation(animated=True)
                elif event.key == pygame.K_r:
                    start_generation(animated=False)

                elif event.key == pygame.K_SPACE and not generating:
                    reset_player()

                elif event.key == pygame.K_h and not generating:
                    show_hint = not show_hint
                    recalc_hint()

                elif event.key == pygame.K_a and not generating:
                    use_astar = not use_astar
                    recalc_hint()
                    if won:
                        win_path = compute_start_to_goal_path()

                elif event.key == pygame.K_m and not generating:
                    gen_algo_index = (gen_algo_index + 1) % len(GEN_ALGOS)

                elif event.key == pygame.K_p and generating:
                    gen_paused = not gen_paused

                elif event.key == pygame.K_n and generating:
                    gen_step_once()
                    gen_paused = True

                elif event.key == pygame.K_s:
                    step_mode = not step_mode
                    if generating:
                        gen_paused = step_mode

                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    gen_speed = min(1200, gen_speed + 60)

                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    gen_speed = max(20, gen_speed - 60)

                # loop percent control: K (-10%), L (+10%)
                elif event.key == pygame.K_l:
                    loop_percent = min(90, loop_percent + 10)
                elif event.key == pygame.K_k:
                    loop_percent = max(0, loop_percent - 10)

        if not in_menu:
            # UPDATE (GEN)
            if generating and (not gen_paused) and (not step_mode):
                gen_accum += dt * gen_speed
                steps = int(gen_accum)
                if steps > 0:
                    gen_accum -= steps
                    for _ in range(steps):
                        gen_step_once()
                        if not generating:
                            break

            # UPDATE (PLAYER)
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
                    trail.append((player_x, player_y))
                    last_move_time = now
                    moved = True
                    if (player_x, player_y) == (goal_x, goal_y):
                        won = True
                        win_path = compute_start_to_goal_path()
                        if best_moves is None or moves < best_moves:
                            best_moves = moves

            if moved:
                recalc_hint()

        # DRAW
        if in_menu:
            draw_menu(
                screen,
                walls,
                menu_overlay,
                menu_labels(),
                menu_index,
                title_font,
                menu_font,
                font,
                best_moves,
            )
        else:
            screen.fill((20, 22, 28))
            maze_h = ROWS * CELL_SIZE
            pygame.draw.rect(screen, (16, 18, 24), (0, 0, SCREEN_W, maze_h))

            if generating:
                for y in range(ROWS):
                    for x in range(COLS):
                        if visited[idx(x, y)]:
                            draw_cell_fill(screen, x, y, (28, 32, 40), pad=2, radius=4)

                cx, cy = current_cell
                draw_cell_border(screen, cx, cy, (255, 210, 120), thickness=3, pad=3, radius=6)

                if carved_edge is not None:
                    (ax, ay), (bx, by) = carved_edge
                    draw_cell_border(screen, ax, ay, (120, 220, 255), thickness=2, pad=5, radius=6)
                    draw_cell_border(screen, bx, by, (120, 220, 255), thickness=2, pad=5, radius=6)

            else:
                draw_trail(screen, trail)

                if show_hint and hint_path:
                    draw_hint_path(screen, hint_path)

                if won and win_path:
                    draw_win_path(screen, win_path)

                draw_cell_fill(screen, goal_x, goal_y, (60, 200, 120), pad=6, radius=6)
                draw_cell_fill(screen, player_x, player_y, (70, 140, 255), pad=6, radius=6)

            draw_maze(screen, walls)

            # panel
            panel_y = maze_h
            pygame.draw.rect(screen, (12, 14, 18), (0, panel_y, SCREEN_W, PANEL_H))

            loops_txt = f"{loop_percent}%"
            gen_txt = GEN_ALGOS[gen_algo_index][0]
            if generating:
                step_txt = "ON" if step_mode else "OFF"
                ptxt = "PAUSED" if gen_paused else "RUN"
                info = (
                    f"Generating [{ptxt}] | Gen:{gen_txt} | Step:{step_txt} (S) | P:pause | N:step | Loops:{loops_txt} (K-/L+) "
                    f"| speed:{gen_speed}/s | G:anim | R:instant | +/-:speed"
                )
            else:
                hint_txt = "ON" if show_hint else "OFF"
                algo = "A*" if use_astar else "BFS"
                info = (
                    f"Moves:{moves} | Gen:{gen_txt} (M) | H:hint({hint_txt}) | Solver:{algo} (A) | Loops:{loops_txt} (K-/L+) "
                    f"| Arrows:move | SPACE:restart | G/R:new"
                )

            screen.blit(font.render(info, True, (210, 210, 210)), (12, panel_y + 18))

            if won:
                msg = "YOU WIN! (Press G for new animated maze)"
                text = big_font.render(msg, True, (255, 220, 120))
                screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2, panel_y - 44))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
