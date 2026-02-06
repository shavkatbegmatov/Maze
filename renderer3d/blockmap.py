"""
Block Map - Bitmask devorlarni solid blok xaritaga aylantirish
Wolfenstein 3D yondashuvi: har bir devor segmenti to'liq katakchani egallaydi
Natija: devorlar har qanday burchakdan qalinlik bilan ko'rinadi
"""

import math
import numpy as np
from numba import njit, int32, float64


@njit(cache=True)
def walls_to_blockmap(walls, cols, rows):
    """
    1D bitmask walls massivni 2D blok xaritaga aylantiradi.

    Original labirint cols x rows.
    Blok xarita (2*cols+1) x (2*rows+1):
      - Burchaklar [2*cx, 2*cy]: yonida devor bo'lsa solid
      - Gorizontal devorlar [2*cx+1, 2*cy]: agar TOP/BOTTOM devor bo'lsa
      - Vertikal devorlar [2*cx, 2*cy+1]: agar LEFT/RIGHT devor bo'lsa
      - Ichki maydon [2*cx+1, 2*cy+1]: har doim bo'sh

    Args:
        walls: 1D int32 massiv (rows*cols), har bir hujayra uchun bitmask
        cols: ustunlar soni
        rows: qatorlar soni

    Returns:
        blockmap: 2D int32 massiv (bm_h, bm_w), 1=solid, 0=bo'sh
    """
    top = int32(1)
    right = int32(2)
    bottom = int32(4)
    left = int32(8)

    bm_w = 2 * cols + 1
    bm_h = 2 * rows + 1
    blockmap = np.zeros((bm_h, bm_w), dtype=np.int32)

    # Har bir hujayra uchun devorlarni tekshirish
    for cy in range(rows):
        for cx in range(cols):
            idx = cy * cols + cx
            w = walls[idx]

            # TOP devor -> gorizontal segment [2*cy, 2*cx+1]
            if (w & top) != 0:
                blockmap[2 * cy, 2 * cx + 1] = int32(1)

            # BOTTOM devor -> gorizontal segment [2*(cy+1), 2*cx+1]
            if (w & bottom) != 0:
                blockmap[2 * (cy + 1), 2 * cx + 1] = int32(1)

            # LEFT devor -> vertikal segment [2*cy+1, 2*cx]
            if (w & left) != 0:
                blockmap[2 * cy + 1, 2 * cx] = int32(1)

            # RIGHT devor -> vertikal segment [2*cy+1, 2*(cx+1)]
            if (w & right) != 0:
                blockmap[2 * cy + 1, 2 * (cx + 1)] = int32(1)

    # Burchak ustunlarini shartli solid qilish:
    # faqat atrofidagi devor segmentlardan kamida bittasi solid bo'lsa
    for cy in range(rows + 1):
        for cx in range(cols + 1):
            bx = 2 * cx
            by = 2 * cy
            has_neighbor = False
            if by > 0 and blockmap[by - 1, bx] > 0:
                has_neighbor = True
            if not has_neighbor and by < bm_h - 1 and blockmap[by + 1, bx] > 0:
                has_neighbor = True
            if not has_neighbor and bx > 0 and blockmap[by, bx - 1] > 0:
                has_neighbor = True
            if not has_neighbor and bx < bm_w - 1 and blockmap[by, bx + 1] > 0:
                has_neighbor = True
            if has_neighbor:
                blockmap[by, bx] = int32(1)

    return blockmap


@njit(cache=True)
def pos_to_blockmap(wx, wy):
    """
    O'yinchi pozitsiyasini (world koordinata) blok xarita koordinatalariga o'tkazadi.

    Formulasi: block_pos = 2 * floor(world_pos) + 1 + frac(world_pos)
    Bu o'yinchini ichki maydon hujayrasining (toq ustun/qator) markaziga joylashtiradi.
    Masalan: world (1.5, 1.5) -> blockmap (3.5, 3.5) — col 3 (toq, ichki) markazi.

    Args:
        wx, wy: world koordinatalari (float)

    Returns:
        bx, by: blok xarita koordinatalari (float)
    """
    fx = math.floor(wx)
    fy = math.floor(wy)
    frac_x = wx - fx
    frac_y = wy - fy
    bx = 2.0 * fx + 1.0 + frac_x
    by = 2.0 * fy + 1.0 + frac_y
    return bx, by


@njit(cache=True)
def blockmap_cast_all_rays(blockmap, bm_w, bm_h, bpx, bpy, px, py,
                           player_angle, fov_rad, half_fov_rad,
                           num_rays, fish_eye_table):
    """
    Blok xaritada DDA algoritmi bilan nurlarni otish.

    DDA blockmap koordinatalarida ishlaydi (hit detection uchun).
    Masofalar world koordinatalarida hisoblanadi (map_x/2 formulasi bilan).

    Args:
        blockmap: 2D int32 massiv (bm_h, bm_w)
        bm_w, bm_h: blok xarita o'lchamlari
        bpx, bpy: o'yinchi pozitsiyasi blok xarita koordinatalarida
        px, py: o'yinchi pozitsiyasi world koordinatalarida
        player_angle: o'yinchining ko'rish burchagi (radyan)
        fov_rad: ko'rish maydoni (radyan)
        half_fov_rad: yarim ko'rish maydoni
        num_rays: nur soni
        fish_eye_table: baliq ko'zi korreksiyasi jadvali

    Returns:
        results: (num_rays, 6) massiv
                 [dist, side, hit_x, hit_y, wall_dir, corrected_dist]
    """
    results = np.empty((num_rays, 6), dtype=np.float64)

    angle_step = fov_rad / num_rays
    start_angle = player_angle - half_fov_rad

    top = int32(1)
    right = int32(2)
    bottom = int32(4)
    left = int32(8)

    max_distance = 200.0

    for i in range(num_rays):
        ray_angle = start_angle + i * angle_step

        ray_dir_x = math.cos(ray_angle)
        ray_dir_y = math.sin(ray_angle)

        # Nolga bo'linishdan saqlanish
        if abs(ray_dir_x) < 1e-10:
            if ray_dir_x >= 0:
                ray_dir_x = 1e-10
            else:
                ray_dir_x = -1e-10
        if abs(ray_dir_y) < 1e-10:
            if ray_dir_y >= 0:
                ray_dir_y = 1e-10
            else:
                ray_dir_y = -1e-10

        # Joriy hujayra (blockmap koordinatalarida)
        map_x = int32(int(bpx))
        map_y = int32(int(bpy))

        # Delta masofalar
        delta_dist_x = abs(1.0 / ray_dir_x)
        delta_dist_y = abs(1.0 / ray_dir_y)

        # Qadam yo'nalishi
        if ray_dir_x >= 0:
            step_x = int32(1)
            side_dist_x = (map_x + 1.0 - bpx) * delta_dist_x
        else:
            step_x = int32(-1)
            side_dist_x = (bpx - map_x) * delta_dist_x

        if ray_dir_y >= 0:
            step_y = int32(1)
            side_dist_y = (map_y + 1.0 - bpy) * delta_dist_y
        else:
            step_y = int32(-1)
            side_dist_y = (bpy - map_y) * delta_dist_y

        # DDA loop — blockmap da hit detection
        hit = False
        side = int32(0)
        wall_dir = top

        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = int32(1)  # E/W devor
                if step_x > 0:
                    wall_dir = left
                else:
                    wall_dir = right
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = int32(0)  # N/S devor
                if step_y > 0:
                    wall_dir = top
                else:
                    wall_dir = bottom

            # Chegaradan chiqish tekshiruvi
            if map_x < 0 or map_x >= bm_w or map_y < 0 or map_y >= bm_h:
                hit = True
                break

            # Solid blok tekshiruvi
            if blockmap[map_y, map_x] > 0:
                hit = True

            # Maksimal masofa xavfsizligi
            if side == 1:
                dist_check = side_dist_x
            else:
                dist_check = side_dist_y
            if dist_check > max_distance:
                break

        # World perpendicular masofa hisoblash
        # Juft ustun/qator = devor/ustun, world chegarasi = index / 2
        if side == 1:
            wall_world_x = map_x / 2.0
            perp_wall_dist = (wall_world_x - px) / ray_dir_x
        else:
            wall_world_y = map_y / 2.0
            perp_wall_dist = (wall_world_y - py) / ray_dir_y

        if perp_wall_dist < 0.001:
            perp_wall_dist = 0.001

        # Urilish nuqtasi (world koordinatalarida)
        hit_x = px + perp_wall_dist * ray_dir_x
        hit_y = py + perp_wall_dist * ray_dir_y

        # Fish-eye korreksiyasi
        corrected_dist = perp_wall_dist * fish_eye_table[i]

        results[i, 0] = perp_wall_dist
        results[i, 1] = float64(side)
        results[i, 2] = hit_x
        results[i, 3] = hit_y
        results[i, 4] = float64(wall_dir)
        results[i, 5] = corrected_dist

    return results
