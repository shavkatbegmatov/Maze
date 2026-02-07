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
                           num_rays, fish_eye_table,
                           walls, cols, rows):
    """
    Blok xaritada DDA algoritmi bilan nurlarni otish.

    Ikki bosqichli yondashuv:
    1. Blockmap DDA — yo'nalish filtri bilan (devorlar qalinligi uchun)
    2. Bitmask korreksiya — blockmap o'tkazib yuborgan yaqin devorlarni topish

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
        walls: 1D int32 massiv — original bitmask devorlar
        cols, rows: labirint o'lchamlari

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

        # ============================================================
        # BLOCKMAP DDA — yo'nalish filtri bilan
        # ============================================================
        hit = False
        side = int32(0)
        wall_dir = top

        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = int32(1)
                if step_x > 0:
                    wall_dir = left
                else:
                    wall_dir = right
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = int32(0)
                if step_y > 0:
                    wall_dir = top
                else:
                    wall_dir = bottom

            # Chegaradan chiqish
            if map_x < 0 or map_x >= bm_w or map_y < 0 or map_y >= bm_h:
                hit = True
                break

            # Yo'nalish filtri bilan solid tekshiruvi
            even_row = (map_y % 2 == 0)
            even_col = (map_x % 2 == 0)

            if not even_row and not even_col:
                # Ichki (toq, toq) — doim tekshirish
                if blockmap[map_y, map_x] > 0:
                    hit = True
            elif even_row and not even_col:
                # Gorizontal devor — faqat Y qadami
                if side == 0 and blockmap[map_y, map_x] > 0:
                    hit = True
            elif not even_row and even_col:
                # Vertikal devor — faqat X qadami
                if side == 1 and blockmap[map_y, map_x] > 0:
                    hit = True
            else:
                # Ustun (juft, juft) — yaqindagi devor segmentini tekshirish
                if side == 0:
                    if step_y > 0:
                        wwy = map_y // 2
                    else:
                        wwy = (map_y + 1) // 2
                    t_y = (wwy - py) / ray_dir_y
                    cwx = px + t_y * ray_dir_x
                    cx_floor = int32(int(math.floor(cwx)))
                    check_col = int32(2 * cx_floor + 1)
                    if 1 <= check_col < bm_w:
                        if blockmap[map_y, check_col] > 0:
                            hit = True
                elif side == 1:
                    if step_x > 0:
                        wwx = map_x // 2
                    else:
                        wwx = (map_x + 1) // 2
                    t_x = (wwx - px) / ray_dir_x
                    cwy = py + t_x * ray_dir_y
                    cy_floor = int32(int(math.floor(cwy)))
                    check_row = int32(2 * cy_floor + 1)
                    if 1 <= check_row < bm_h:
                        if blockmap[check_row, map_x] > 0:
                            hit = True

            # Maksimal masofa
            if side == 1:
                dist_check = side_dist_x
            else:
                dist_check = side_dist_y
            if dist_check > max_distance:
                break

        # World masofa hisoblash (blockmap DDA natijasi)
        if side == 1:
            if step_x > 0:
                wall_world_x = map_x // 2
            else:
                wall_world_x = (map_x + 1) // 2
            perp_wall_dist = (wall_world_x - px) / ray_dir_x
        else:
            if step_y > 0:
                wall_world_y = map_y // 2
            else:
                wall_world_y = (map_y + 1) // 2
            perp_wall_dist = (wall_world_y - py) / ray_dir_y

        if perp_wall_dist < 0.001:
            perp_wall_dist = 0.001

        # ============================================================
        # BITMASK KORREKSIYA — o'tkazib yuborilgan yaqin devorlarni topish
        # Blockmap DDA non-linear mapping tufayli ba'zi devorlarni
        # o'tkazib yuborishi mumkin. Original bitmask orqali tekshirish.
        # ============================================================
        bm_hit_x = px + perp_wall_dist * ray_dir_x
        bm_hit_y = py + perp_wall_dist * ray_dir_y

        # X yo'nalishida yaqinroq vertikal devor bormi?
        if ray_dir_x > 0:
            cx_start = int32(int(px)) + 1
            cx_end = int32(int(bm_hit_x)) + 1
            for cx in range(cx_start, cx_end):
                # Bu chegarada devor bormi?
                cell_left = int32(cx - 1)
                t_cross = (cx - px) / ray_dir_x
                cross_y = py + t_cross * ray_dir_y
                cell_y = int32(int(math.floor(cross_y)))
                if cell_y < 0:
                    cell_y = int32(0)
                if cell_y >= rows:
                    cell_y = int32(rows - 1)
                # Chap hujayraning RIGHT devori
                if 0 <= cell_left < cols:
                    idx = cell_y * cols + cell_left
                    if 0 <= idx < walls.shape[0]:
                        if (walls[idx] & right) != 0:
                            if t_cross < perp_wall_dist - 0.0001:
                                perp_wall_dist = t_cross
                                side = int32(1)
                                wall_dir = left
                                break
        else:
            cx_start = int32(int(px))
            cx_end = int32(int(math.floor(bm_hit_x)))
            for cx in range(cx_start, cx_end, -1):
                cell_right = int32(cx)
                t_cross = (cx - px) / ray_dir_x
                cross_y = py + t_cross * ray_dir_y
                cell_y = int32(int(math.floor(cross_y)))
                if cell_y < 0:
                    cell_y = int32(0)
                if cell_y >= rows:
                    cell_y = int32(rows - 1)
                # O'ng hujayraning LEFT devori
                if 0 <= cell_right < cols:
                    idx = cell_y * cols + cell_right
                    if 0 <= idx < walls.shape[0]:
                        if (walls[idx] & left) != 0:
                            if t_cross < perp_wall_dist - 0.0001:
                                perp_wall_dist = t_cross
                                side = int32(1)
                                wall_dir = right
                                break

        # Y yo'nalishida yaqinroq gorizontal devor bormi?
        if ray_dir_y > 0:
            cy_start = int32(int(py)) + 1
            cy_end = int32(int(bm_hit_y)) + 1
            for cy in range(cy_start, cy_end):
                cell_above = int32(cy - 1)
                t_cross = (cy - py) / ray_dir_y
                cross_x = px + t_cross * ray_dir_x
                cell_x = int32(int(math.floor(cross_x)))
                if cell_x < 0:
                    cell_x = int32(0)
                if cell_x >= cols:
                    cell_x = int32(cols - 1)
                if 0 <= cell_above < rows:
                    idx = cell_above * cols + cell_x
                    if 0 <= idx < walls.shape[0]:
                        if (walls[idx] & bottom) != 0:
                            if t_cross < perp_wall_dist - 0.0001:
                                perp_wall_dist = t_cross
                                side = int32(0)
                                wall_dir = top
                                break
        else:
            cy_start = int32(int(py))
            cy_end = int32(int(math.floor(bm_hit_y)))
            for cy in range(cy_start, cy_end, -1):
                cell_below = int32(cy)
                t_cross = (cy - py) / ray_dir_y
                cross_x = px + t_cross * ray_dir_x
                cell_x = int32(int(math.floor(cross_x)))
                if cell_x < 0:
                    cell_x = int32(0)
                if cell_x >= cols:
                    cell_x = int32(cols - 1)
                if 0 <= cell_below < rows:
                    idx = cell_below * cols + cell_x
                    if 0 <= idx < walls.shape[0]:
                        if (walls[idx] & top) != 0:
                            if t_cross < perp_wall_dist - 0.0001:
                                perp_wall_dist = t_cross
                                side = int32(0)
                                wall_dir = bottom
                                break

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
