"""
Maze generation algorithms
Extracted and adapted from maze_game_v2.py
"""

import random
from utils.constants import TOP, RIGHT, BOTTOM, LEFT, DIRS
from maze.maze_core import carve_passage, neighbor_dirs, is_open_between, fix_open_borders


class UnionFind:
    """Union-Find data structure for Kruskal's algorithm"""
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


def idx(cols, x, y):
    """Helper to get 1D index"""
    return y * cols + x


def in_bounds(cols, rows, x, y):
    """Check if coordinates are in bounds"""
    return 0 <= x < cols and 0 <= y < rows


def random_cell(cols, rows):
    """Get random cell"""
    return random.randrange(cols), random.randrange(rows)


# ========== GENERATOR: DFS BACKTRACKER ==========

def gen_dfs_backtracker(cols, rows, seed=None):
    """Depth-First Search with backtracking - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    stack = [(0, 0)]
    visited[idx(cols, 0, 0)] = True

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    while stack:
        cx, cy = stack[-1]
        neighbors = []

        for dx, dy, wall_bit, opp_bit in DIRS:
            nx, ny = cx + dx, cy + dy
            if in_bounds(cols, rows, nx, ny) and not visited[idx(cols, nx, ny)]:
                neighbors.append((nx, ny, wall_bit, opp_bit))

        if neighbors:
            nx, ny, wall_bit, opp_bit = random.choice(neighbors)
            walls[idx(cols, cx, cy)] &= ~wall_bit
            walls[idx(cols, nx, ny)] &= ~opp_bit
            visited[idx(cols, nx, ny)] = True
            stack.append((nx, ny))

            yield {"walls": walls, "visited": visited, "current": (nx, ny), "carved": ((cx, cy), (nx, ny)), "done": False}
        else:
            stack.pop()
            yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": False}

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


# ========== GENERATOR: PRIM ==========

def gen_prim(cols, rows, seed=None):
    """Prim's algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    sx, sy = 0, 0
    visited[idx(cols, sx, sy)] = True
    frontier = []

    # Add neighbors to frontier
    for dx, dy, _, _ in DIRS:
        nx, ny = sx + dx, sy + dy
        if in_bounds(cols, rows, nx, ny):
            frontier.append(((sx, sy), (nx, ny)))

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": False}

    while frontier:
        i = random.randrange(len(frontier))
        (ax, ay), (bx, by) = frontier.pop(i)
        if visited[idx(cols, bx, by)]:
            continue

        carve_passage(walls, cols, ax, ay, bx, by)
        visited[idx(cols, bx, by)] = True
        yield {"walls": walls, "visited": visited, "current": (bx, by), "carved": ((ax, ay), (bx, by)), "done": False}

        for dx, dy, _, _ in DIRS:
            nx, ny = bx + dx, by + dy
            if in_bounds(cols, rows, nx, ny) and not visited[idx(cols, nx, ny)]:
                frontier.append(((bx, by), (nx, ny)))

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": True}


# ========== GENERATOR: KRUSKAL ==========

def gen_kruskal(cols, rows, seed=None):
    """Kruskal's algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)
    uf = UnionFind(cols * rows)

    edges = []
    for y in range(rows):
        for x in range(cols):
            if x + 1 < cols:
                edges.append(((x, y), (x + 1, y)))
            if y + 1 < rows:
                edges.append(((x, y), (x, y + 1)))
    random.shuffle(edges)

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    for (ax, ay), (bx, by) in edges:
        if uf.union(idx(cols, ax, ay), idx(cols, bx, by)):
            carve_passage(walls, cols, ax, ay, bx, by)
            visited[idx(cols, ax, ay)] = True
            visited[idx(cols, bx, by)] = True
            yield {"walls": walls, "visited": visited, "current": (bx, by), "carved": ((ax, ay), (bx, by)), "done": False}

    for i in range(len(visited)):
        visited[i] = True
    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


# ========== GENERATOR: ALDOUS-BRODER ==========

def gen_aldous_broder(cols, rows, seed=None):
    """Aldous-Broder algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    cx, cy = random_cell(cols, rows)
    visited[idx(cols, cx, cy)] = True
    remaining = cols * rows - 1

    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": False}

    while remaining > 0:
        neighbors = []
        for dx, dy, _, _ in DIRS:
            nx, ny = cx + dx, cy + dy
            if in_bounds(cols, rows, nx, ny):
                neighbors.append((nx, ny, dx, dy))

        if not neighbors:
            break

        nx, ny, dx, dy = random.choice(neighbors)

        if not visited[idx(cols, nx, ny)]:
            carve_passage(walls, cols, cx, cy, nx, ny)
            visited[idx(cols, nx, ny)] = True
            remaining -= 1
            yield {"walls": walls, "visited": visited, "current": (nx, ny), "carved": ((cx, cy), (nx, ny)), "done": False}

        cx, cy = nx, ny

    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": True}


# ========== GENERATOR: WILSON ==========

def gen_wilson(cols, rows, seed=None):
    """Wilson's algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    in_maze = [False] * (cols * rows)
    visited = [False] * (cols * rows)

    sx, sy = 0, 0
    in_maze[idx(cols, sx, sy)] = True
    visited[idx(cols, sx, sy)] = True

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": False}

    while not all(in_maze):
        candidates = [(x, y) for y in range(rows) for x in range(cols) if not in_maze[idx(cols, x, y)]]
        if not candidates:
            break

        wx, wy = random.choice(candidates)
        path = [(wx, wy)]
        path_index = {path[0]: 0}
        cx, cy = wx, wy

        while not in_maze[idx(cols, cx, cy)]:
            neighbors = []
            for dx, dy, _, _ in DIRS:
                nx, ny = cx + dx, cy + dy
                if in_bounds(cols, rows, nx, ny):
                    neighbors.append((nx, ny))

            if not neighbors:
                break

            nx, ny = random.choice(neighbors)
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
            carve_passage(walls, cols, ax, ay, bx, by)
            in_maze[idx(cols, ax, ay)] = True
            in_maze[idx(cols, bx, by)] = True
            visited[idx(cols, ax, ay)] = True
            visited[idx(cols, bx, by)] = True
            yield {"walls": walls, "visited": visited, "current": (bx, by), "carved": ((ax, ay), (bx, by)), "done": False}

    yield {"walls": walls, "visited": visited, "current": (sx, sy), "carved": None, "done": True}


# ========== GENERATOR: HUNT AND KILL ==========

def gen_hunt_and_kill(cols, rows, seed=None):
    """Hunt-and-Kill algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    cx, cy = random_cell(cols, rows)
    visited[idx(cols, cx, cy)] = True
    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": False}

    while True:
        unvisited_neighbors = []
        for dx, dy, _, _ in DIRS:
            nx, ny = cx + dx, cy + dy
            if in_bounds(cols, rows, nx, ny) and not visited[idx(cols, nx, ny)]:
                unvisited_neighbors.append((nx, ny))

        if unvisited_neighbors:
            nx, ny = random.choice(unvisited_neighbors)
            carve_passage(walls, cols, cx, cy, nx, ny)
            visited[idx(cols, nx, ny)] = True
            yield {"walls": walls, "visited": visited, "current": (nx, ny), "carved": ((cx, cy), (nx, ny)), "done": False}
            cx, cy = nx, ny
            continue

        found = False
        for y in range(rows):
            for x in range(cols):
                if visited[idx(cols, x, y)]:
                    continue
                neighbors = []
                for dx, dy, _, _ in DIRS:
                    nx, ny = x + dx, y + dy
                    if in_bounds(cols, rows, nx, ny) and visited[idx(cols, nx, ny)]:
                        neighbors.append((nx, ny))

                if neighbors:
                    nx, ny = random.choice(neighbors)
                    carve_passage(walls, cols, x, y, nx, ny)
                    visited[idx(cols, x, y)] = True
                    yield {"walls": walls, "visited": visited, "current": (x, y), "carved": ((x, y), (nx, ny)), "done": False}
                    cx, cy = x, y
                    found = True
                    break
            if found:
                break

        if not found:
            break

    yield {"walls": walls, "visited": visited, "current": (cx, cy), "carved": None, "done": True}


# ========== GENERATOR: BINARY TREE ==========

def gen_binary_tree(cols, rows, seed=None):
    """Binary Tree algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    for y in range(rows):
        for x in range(cols):
            neighbors = []
            if y + 1 < rows:
                neighbors.append((x, y + 1))
            if x - 1 >= 0:
                neighbors.append((x - 1, y))

            if neighbors:
                nx, ny = random.choice(neighbors)
                carve_passage(walls, cols, x, y, nx, ny)
                visited[idx(cols, x, y)] = True
                visited[idx(cols, nx, ny)] = True
                yield {"walls": walls, "visited": visited, "current": (x, y), "carved": ((x, y), (nx, ny)), "done": False}

    fix_open_borders(walls, cols, rows)
    for i in range(len(visited)):
        visited[i] = True
    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


# ========== GENERATOR: SIDEWINDER ==========

def gen_sidewinder(cols, rows, seed=None):
    """Sidewinder algorithm - animated generator"""
    if seed is not None:
        random.seed(seed)

    walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]
    visited = [False] * (cols * rows)

    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": False}

    for y in range(rows):
        run = []
        for x in range(cols):
            run.append((x, y))
            at_east = x == cols - 1
            at_north = y == 0
            carve_east = (not at_east) and (at_north or random.choice([True, False]))

            if carve_east:
                carve_passage(walls, cols, x, y, x + 1, y)
                visited[idx(cols, x, y)] = True
                visited[idx(cols, x + 1, y)] = True
                yield {"walls": walls, "visited": visited, "current": (x, y), "carved": ((x, y), (x + 1, y)), "done": False}
            else:
                if not at_north:
                    rx, ry = random.choice(run)
                    carve_passage(walls, cols, rx, ry, rx, ry - 1)
                    visited[idx(cols, rx, ry)] = True
                    visited[idx(cols, rx, ry - 1)] = True
                    yield {"walls": walls, "visited": visited, "current": (rx, ry), "carved": ((rx, ry), (rx, ry - 1)), "done": False}
                run = []

    fix_open_borders(walls, cols, rows)
    for i in range(len(visited)):
        visited[i] = True
    yield {"walls": walls, "visited": visited, "current": (0, 0), "carved": None, "done": True}


# ========== ALGORITHM LIST ==========

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
