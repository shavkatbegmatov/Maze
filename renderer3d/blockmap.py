"""
Block Map - Bitmask devorlarni solid blok xaritaga aylantirish
Wolfenstein 3D yondashuvi: har bir devor segmenti to'liq katakchani egallaydi
Natija: devorlar har qanday burchakdan qalinlik bilan ko'rinadi
"""

import numpy as np
from numba import njit, int32


@njit(cache=True)
def walls_to_blockmap(walls, cols, rows):
    """
    1D bitmask walls massivni 2D blok xaritaga aylantiradi.

    Original labirint cols x rows.
    Blok xarita (2*cols+1) x (2*rows+1):
      - Burchaklar [2*cy, 2*cx]: yonida devor bo'lsa solid
      - Gorizontal devorlar [2*cy, 2*cx+1]: agar TOP/BOTTOM devor bo'lsa
      - Vertikal devorlar [2*cy+1, 2*cx]: agar LEFT/RIGHT devor bo'lsa
      - Ichki maydon [2*cx+1, 2*cy+1]: har doim bo'sh (koridor)

    Args:
        walls: 1D int32 massiv (rows*cols), har bir hujayra uchun bitmask
        cols: ustunlar soni
        rows: qatorlar soni

    Returns:
        grid: 2D int8 massiv (bh, bw), 1=solid, 0=bo'sh
    """
    top = int32(1)
    right = int32(2)
    bottom = int32(4)
    left = int32(8)

    bw = 2 * cols + 1
    bh = 2 * rows + 1
    grid = np.zeros((bh, bw), dtype=np.int8)

    for cy in range(rows):
        for cx in range(cols):
            idx = cy * cols + cx
            w = walls[idx]

            # TOP devor -> gorizontal segment [2*cy, 2*cx+1]
            if (w & top) != 0:
                grid[2 * cy, 2 * cx + 1] = 1

            # BOTTOM devor -> gorizontal segment [2*(cy+1), 2*cx+1]
            if (w & bottom) != 0:
                grid[2 * (cy + 1), 2 * cx + 1] = 1

            # LEFT devor -> vertikal segment [2*cy+1, 2*cx]
            if (w & left) != 0:
                grid[2 * cy + 1, 2 * cx] = 1

            # RIGHT devor -> vertikal segment [2*cy+1, 2*(cx+1)]
            if (w & right) != 0:
                grid[2 * cy + 1, 2 * (cx + 1)] = 1

    # Burchak ustunlarini shartli solid qilish:
    # faqat atrofidagi devor segmentlardan kamida bittasi solid bo'lsa
    for cy in range(rows + 1):
        for cx in range(cols + 1):
            r = 2 * cy
            c = 2 * cx
            has_wall = False
            if r > 0 and grid[r - 1, c] != 0:
                has_wall = True
            if not has_wall and r < bh - 1 and grid[r + 1, c] != 0:
                has_wall = True
            if not has_wall and c > 0 and grid[r, c - 1] != 0:
                has_wall = True
            if not has_wall and c < bw - 1 and grid[r, c + 1] != 0:
                has_wall = True
            if has_wall:
                grid[r, c] = 1

    return grid


def cell_to_grid(cx, cy):
    """Maze cell koordinatalarini grid koordinatalariga o'tkazadi.

    Args:
        cx, cy: maze cell koordinatalari (int)

    Returns:
        (gx, gy): grid koordinatalari (float) — hujayra markazi
    """
    return 2.0 * cx + 1.5, 2.0 * cy + 1.5
