"""
Core maze functions - generation, pathfinding, and manipulation
Extracted from maze_game_v2.py
"""

import random
from collections import deque
import heapq
from utils.constants import TOP, RIGHT, BOTTOM, LEFT, DIRS, DIR_TO_BITS


class MazeGrid:
    """
    Maze grid with wall-based representation
    Each cell has 4 possible walls: TOP, RIGHT, BOTTOM, LEFT
    """
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        # Initialize all walls closed
        self.walls = [TOP | RIGHT | BOTTOM | LEFT for _ in range(cols * rows)]

    def idx(self, x, y):
        """Convert 2D coordinates to 1D index"""
        return y * self.cols + x

    def in_bounds(self, x, y):
        """Check if coordinates are within grid bounds"""
        return 0 <= x < self.cols and 0 <= y < self.rows

    def random_cell(self):
        """Get random cell coordinates"""
        return random.randrange(self.cols), random.randrange(self.rows)


def neighbor_dirs(grid, x, y):
    """Get valid neighbor directions from a cell"""
    res = []
    for dx, dy, wall_bit, opp_bit in DIRS:
        nx, ny = x + dx, y + dy
        if grid.in_bounds(nx, ny):
            res.append((nx, ny, wall_bit, opp_bit))
    return res


def carve_passage(walls, cols, ax, ay, bx, by):
    """Carve a passage between two adjacent cells"""
    dx = bx - ax
    dy = by - ay
    bits = DIR_TO_BITS.get((dx, dy))
    if bits is None:
        return
    wall_bit, opp_bit = bits
    idx_a = ay * cols + ax
    idx_b = by * cols + bx
    walls[idx_a] &= ~wall_bit
    walls[idx_b] &= ~opp_bit


def close_passage(walls, cols, ax, ay, bx, by):
    """Close a passage between two adjacent cells"""
    dx = bx - ax
    dy = by - ay
    bits = DIR_TO_BITS.get((dx, dy))
    if bits is None:
        return
    wall_bit, opp_bit = bits
    idx_a = ay * cols + ax
    idx_b = by * cols + bx
    walls[idx_a] |= wall_bit
    walls[idx_b] |= opp_bit


def is_open_between(walls, cols, ax, ay, bx, by):
    """Check if passage is open between two adjacent cells"""
    dx = bx - ax
    dy = by - ay
    bits = DIR_TO_BITS.get((dx, dy))
    if bits is None:
        return False
    wall_bit, _ = bits
    idx_a = ay * cols + ax
    return (walls[idx_a] & wall_bit) == 0


def can_move(walls, cols, rows, x, y, dx, dy):
    """Check if player can move in direction (dx, dy) from (x, y)"""
    nx, ny = x + dx, y + dy
    if not (0 <= nx < cols and 0 <= ny < rows):
        return False

    idx = y * cols + x
    w = walls[idx]

    if dx == 0 and dy == -1:   # up
        return (w & TOP) == 0
    if dx == 1 and dy == 0:    # right
        return (w & RIGHT) == 0
    if dx == 0 and dy == 1:    # down
        return (w & BOTTOM) == 0
    if dx == -1 and dy == 0:   # left
        return (w & LEFT) == 0
    return False


def neighbors_open(walls, cols, rows, x, y):
    """Get list of open neighbor cells"""
    res = []
    if can_move(walls, cols, rows, x, y, 0, -1):
        res.append((x, y - 1))
    if can_move(walls, cols, rows, x, y, 1, 0):
        res.append((x + 1, y))
    if can_move(walls, cols, rows, x, y, 0, 1):
        res.append((x, y + 1))
    if can_move(walls, cols, rows, x, y, -1, 0):
        res.append((x - 1, y))
    return res


# ========== PATHFINDING ==========

def reconstruct_path(prev, goal):
    """Reconstruct path from prev dictionary"""
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def bfs_shortest_path(walls, cols, rows, start, goal):
    """BFS shortest path finder"""
    if start == goal:
        return [start]

    q = deque([start])
    prev = {start: None}

    while q:
        x, y = q.popleft()
        for n in neighbors_open(walls, cols, rows, x, y):
            if n not in prev:
                prev[n] = (x, y)
                if n == goal:
                    return reconstruct_path(prev, goal)
                q.append(n)
    return []


def manhattan(a, b):
    """Manhattan distance heuristic"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_shortest_path(walls, cols, rows, start, goal):
    """A* shortest path finder"""
    if start == goal:
        return [start]

    open_heap = []
    heapq.heappush(open_heap, (manhattan(start, goal), 0, start))

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
        for nxt in neighbors_open(walls, cols, rows, cx, cy):
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


# ========== BRAID MAZE (ADD LOOPS) ==========

def exits_count(w):
    """Count number of open sides in a cell"""
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


def braid_maze(walls, cols, rows, braid_chance):
    """
    Convert perfect maze to braided maze by adding loops
    braid_chance: 0.0-0.9 (probability of opening dead-ends)
    """
    if braid_chance <= 0:
        return

    for y in range(rows):
        for x in range(cols):
            idx = y * cols + x
            w = walls[idx]

            # Dead-end has only 1 exit
            if exits_count(w) == 1 and random.random() < braid_chance:
                candidates = []
                for dx, dy, wall_bit, opp_bit in DIRS:
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < cols and 0 <= ny < rows):
                        continue
                    # If wall exists, we can open it
                    if (w & wall_bit) != 0:
                        candidates.append((nx, ny, wall_bit, opp_bit))

                if candidates:
                    nx, ny, wall_bit, opp_bit = random.choice(candidates)
                    walls[idx] &= ~wall_bit
                    walls[ny * cols + nx] &= ~opp_bit


# ========== BORDER FIX ==========

def bfs_component_without_edge(walls, cols, rows, start, edge):
    """Find connected component without using a specific edge"""
    (ax, ay), (bx, by) = edge
    forbidden = {(ax, ay, bx, by), (bx, by, ax, ay)}
    q = deque([start])
    seen = {start}

    while q:
        x, y = q.popleft()
        for dx, dy, _, _ in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < cols and 0 <= ny < rows):
                continue
            if (x, y, nx, ny) in forbidden:
                continue
            if is_open_between(walls, cols, x, y, nx, ny) and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def get_adjacent_edges(cols, rows):
    """Get all adjacent cell pairs"""
    edges = []
    for y in range(rows):
        for x in range(cols):
            if x + 1 < cols:
                edges.append(((x, y), (x + 1, y)))
            if y + 1 < rows:
                edges.append(((x, y), (x, y + 1)))
    return edges


def swap_edge_to_break_corridor(walls, cols, rows, edge, adj_edges):
    """Swap edge to break long corridor on border"""
    comp = bfs_component_without_edge(walls, cols, rows, edge[0], edge)
    candidates = []

    for (u, v) in adj_edges:
        u_in = u in comp
        v_in = v in comp
        if u_in != v_in and not is_open_between(walls, cols, u[0], u[1], v[0], v[1]):
            candidates.append((u, v))

    if not candidates:
        return False

    (ux, uy), (vx, vy) = random.choice(candidates)
    carve_passage(walls, cols, ux, uy, vx, vy)
    (ax, ay), (bx, by) = edge
    close_passage(walls, cols, ax, ay, bx, by)
    return True


def fix_open_borders(walls, cols, rows):
    """Fix completely open borders (for Binary Tree and Sidewinder)"""
    adj_edges = get_adjacent_edges(cols, rows)

    top = [((x, 0), (x + 1, 0)) for x in range(cols - 1)]
    bottom = [((x, rows - 1), (x + 1, rows - 1)) for x in range(cols - 1)]
    left = [((0, y), (0, y + 1)) for y in range(rows - 1)]
    right = [((cols - 1, y), (cols - 1, y + 1)) for y in range(rows - 1)]

    for edges in (top, right, bottom, left):
        if edges and all(is_open_between(walls, cols, a[0], a[1], b[0], b[1]) for a, b in edges):
            for i, edge in enumerate(edges):
                if i % 2 == 0 and is_open_between(walls, cols, edge[0][0], edge[0][1], edge[1][0], edge[1][1]):
                    swap_edge_to_break_corridor(walls, cols, rows, edge, adj_edges)
