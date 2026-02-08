"""
Weapon System - Hitscan shooting with procedural gun rendering
Professional pistol vizual, ammo/reload tizimi, bob/sway effektlari
"""

import math
import pygame
from utils.constants import (
    WEAPON_DAMAGE, WEAPON_FIRE_RATE, WEAPON_ENERGY_COST,
    WEAPON_MAX_RANGE, WEAPON_HIT_RADIUS, WEAPON_RECOIL_DURATION,
    AMMO_MAX_MAGAZINE, AMMO_MAX_RESERVE, AMMO_START_MAGAZINE,
    AMMO_START_RESERVE, AMMO_RELOAD_TIME
)
from utils.colors import (
    COLOR_GUN_BARREL, COLOR_GUN_BODY, COLOR_GUN_GRIP,
    COLOR_MUZZLE_FLASH, COLOR_HIT_MARKER
)


class Weapon:
    """Hitscan qurol tizimi"""

    def __init__(self):
        self.damage = WEAPON_DAMAGE
        self.fire_rate = WEAPON_FIRE_RATE
        self.energy_cost = WEAPON_ENERGY_COST
        self.max_range = WEAPON_MAX_RANGE
        self.hit_radius = WEAPON_HIT_RADIUS

        # Taymerlar
        self.fire_cooldown = 0.0
        self.is_firing = False
        self.recoil_timer = 0.0
        self.muzzle_flash_timer = 0.0
        self.hit_marker_timer = 0.0
        self.last_hit_enemy = None

        # Ammo
        self.magazine_ammo = AMMO_START_MAGAZINE
        self.reserve_ammo = AMMO_START_RESERVE
        self.max_magazine = AMMO_MAX_MAGAZINE
        self.max_reserve = AMMO_MAX_RESERVE
        self.reload_timer = 0.0
        self.is_reloading = False

        # Bob/sway
        self.bob_timer = 0.0
        self.sway_offset_x = 0.0
        self.sway_offset_y = 0.0
        self.is_moving = False

        # Bullet trail
        self.trail_timer = 0.0
        self.trail_duration = 0.12
        self.trail_hit = False

    def can_fire(self, player_energy=None):
        """Otish mumkinmi?"""
        if self.is_reloading:
            return False
        if self.magazine_ammo <= 0:
            return False
        return self.fire_cooldown <= 0

    def fire(self, player_3d, player_2d, enemy_manager, boss_manager, grid, grid_cols, grid_rows):
        """
        Otish — hitscan algoritmi

        Returns:
            dict: {'hit': bool, 'enemy': Enemy or None, 'boss_hit': bool, 'distance': float}
        """
        self.fire_cooldown = self.fire_rate
        self.is_firing = True
        self.recoil_timer = WEAPON_RECOIL_DURATION
        self.muzzle_flash_timer = 0.06
        self.trail_timer = self.trail_duration

        # Ammo kamayish
        self.magazine_ammo -= 1
        if self.magazine_ammo <= 0 and self.reserve_ammo > 0:
            self.start_reload()

        result = {'hit': False, 'enemy': None, 'boss_hit': False, 'distance': 0.0}

        px, py = player_3d.world_x, player_3d.world_y
        angle = player_3d.angle
        ray_dx = math.cos(angle)
        ray_dy = math.sin(angle)

        # 1. DDA bilan devor masofasini top
        wall_dist = self._cast_wall_ray(px, py, ray_dx, ray_dy, grid, grid_cols, grid_rows)

        # 2. Har bir tirik dushman uchun tekshir
        best_dist = wall_dist
        best_enemy = None

        for enemy in enemy_manager.get_alive_enemies():
            # Dushman world pozitsiyasi
            ex = 2 * enemy.x + 1.5
            ey = 2 * enemy.y + 1.5

            hit, dist = self._check_hit(px, py, ray_dx, ray_dy, ex, ey, self.hit_radius)
            if hit and dist < best_dist and dist <= self.max_range:
                best_dist = dist
                best_enemy = enemy

        # 3. Boss tekshiruvi
        if boss_manager.active:
            boss = boss_manager.get_boss()
            if boss and boss.alive:
                bx = 2 * boss.x + 1.5
                by = 2 * boss.y + 1.5
                hit, dist = self._check_hit(px, py, ray_dx, ray_dy, bx, by, 0.6)
                if hit and dist < best_dist and dist <= self.max_range:
                    best_dist = dist
                    best_enemy = None  # boss ayriq
                    result['boss_hit'] = True
                    result['hit'] = True
                    result['distance'] = dist
                    self.hit_marker_timer = 0.2

        # 4. Dushman hit
        if best_enemy is not None:
            result['hit'] = True
            result['enemy'] = best_enemy
            result['distance'] = best_dist
            self.hit_marker_timer = 0.2
            self.last_hit_enemy = best_enemy

        return result

    def _cast_wall_ray(self, px, py, ray_dx, ray_dy, grid, grid_cols, grid_rows):
        """DDA bilan devor masofasini aniqlash"""
        map_x = int(px)
        map_y = int(py)

        if abs(ray_dx) < 1e-10:
            delta_x = 1e10
        else:
            delta_x = abs(1.0 / ray_dx)
        if abs(ray_dy) < 1e-10:
            delta_y = 1e10
        else:
            delta_y = abs(1.0 / ray_dy)

        if ray_dx < 0:
            step_x = -1
            side_dist_x = (px - map_x) * delta_x
        else:
            step_x = 1
            side_dist_x = (map_x + 1.0 - px) * delta_x

        if ray_dy < 0:
            step_y = -1
            side_dist_y = (py - map_y) * delta_y
        else:
            step_y = 1
            side_dist_y = (map_y + 1.0 - py) * delta_y

        max_steps = int(self.max_range * 3)
        for _ in range(max_steps):
            if side_dist_x < side_dist_y:
                side_dist_x += delta_x
                map_x += step_x
                side = 1
            else:
                side_dist_y += delta_y
                map_y += step_y
                side = 0

            if map_x < 0 or map_x >= grid_cols or map_y < 0 or map_y >= grid_rows:
                return self.max_range

            if grid[map_y][map_x] == 1:
                if side == 1:
                    dist = side_dist_x - delta_x
                else:
                    dist = side_dist_y - delta_y
                return max(0.1, dist)

        return self.max_range

    def _check_hit(self, px, py, ray_dx, ray_dy, tx, ty, radius):
        """
        Nur chizig'idan target markaziga perpendicular masofa
        Returns: (hit: bool, distance: float)
        """
        # Vektor player -> target
        dx = tx - px
        dy = ty - py

        # Target oldindami?
        dot = dx * ray_dx + dy * ray_dy
        if dot <= 0:
            return False, 0.0

        # Eng yaqin nuqta
        proj_x = px + ray_dx * dot
        proj_y = py + ray_dy * dot

        # Perpendicular masofa
        perp_dx = tx - proj_x
        perp_dy = ty - proj_y
        perp_dist = math.sqrt(perp_dx * perp_dx + perp_dy * perp_dy)

        if perp_dist <= radius:
            return True, dot  # dot = masofa nur bo'ylab
        return False, 0.0

    def can_reload(self):
        """Reload qilish mumkinmi?"""
        return not self.is_reloading and self.magazine_ammo < self.max_magazine and self.reserve_ammo > 0

    def start_reload(self):
        """Reload boshlash"""
        if self.is_reloading or self.magazine_ammo >= self.max_magazine or self.reserve_ammo <= 0:
            return
        self.is_reloading = True
        self.reload_timer = AMMO_RELOAD_TIME

    def _finish_reload(self):
        """Reload tugashi"""
        needed = self.max_magazine - self.magazine_ammo
        transfer = min(needed, self.reserve_ammo)
        self.magazine_ammo += transfer
        self.reserve_ammo -= transfer
        self.is_reloading = False

    def add_ammo(self, amount):
        """Ammo qo'shish"""
        self.reserve_ammo = min(self.reserve_ammo + amount, self.max_reserve)

    def set_moving(self, moving):
        """Harakatlanish holatini belgilash"""
        self.is_moving = moving

    def update(self, dt):
        """Taymerlarni yangilash"""
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        if self.recoil_timer > 0:
            self.recoil_timer -= dt
        if self.muzzle_flash_timer > 0:
            self.muzzle_flash_timer -= dt
        if self.hit_marker_timer > 0:
            self.hit_marker_timer -= dt
        if self.trail_timer > 0:
            self.trail_timer -= dt
        if self.recoil_timer <= 0:
            self.is_firing = False

        # Reload
        if self.is_reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self._finish_reload()

        # Bob/sway
        if self.is_moving:
            self.bob_timer += dt * 8.0
            self.sway_offset_x = math.sin(self.bob_timer) * 4.0
            self.sway_offset_y = abs(math.cos(self.bob_timer)) * 6.0
        else:
            self.bob_timer += dt * 1.5
            self.sway_offset_x = math.sin(self.bob_timer * 0.5) * 1.0
            self.sway_offset_y = abs(math.cos(self.bob_timer * 0.5)) * 1.5

    def draw_gun(self, screen, w, h):
        """Professional pistol chizish"""
        # Recoil effekti — smooth quadratic
        recoil_x = 0
        recoil_y = 0
        if self.recoil_timer > 0:
            t = self.recoil_timer / WEAPON_RECOIL_DURATION
            # Quadratic ease out
            recoil_y = int(t * t * 20)
            recoil_x = int(t * t * 3)

        # Bob/sway offset
        sway_x = int(self.sway_offset_x)
        sway_y = int(self.sway_offset_y)

        # Qurol pozitsiyasi
        gun_x = w // 2 + 70 + sway_x + recoil_x
        gun_y = h - 90 - recoil_y + sway_y

        # Reload animatsiya — qurol pastga tushadi
        if self.is_reloading:
            reload_progress = self.reload_timer / AMMO_RELOAD_TIME
            # Parabola: pastga tushib qaytadi
            reload_offset = int(math.sin(reload_progress * math.pi) * 40)
            gun_y += reload_offset

        # === SLIDE (barrel ustki metall qism) ===
        slide_w, slide_h = 20, 45
        slide_x = gun_x - slide_w // 2
        slide_y = gun_y - 30
        slide_color = (85, 90, 95)
        pygame.draw.rect(screen, slide_color,
                         (slide_x, slide_y, slide_w, slide_h), border_radius=3)

        # Slide highlight (chap tomonda yorug' chiziq)
        pygame.draw.line(screen, (120, 125, 130),
                         (slide_x + 2, slide_y + 3),
                         (slide_x + 2, slide_y + slide_h - 3), 1)
        # Slide shadow (o'ng tomonda qorong'i chiziq)
        pygame.draw.line(screen, (55, 58, 62),
                         (slide_x + slide_w - 2, slide_y + 3),
                         (slide_x + slide_w - 2, slide_y + slide_h - 3), 1)

        # Slide serration chiziqlari (tepa qism)
        for i in range(4):
            ly = slide_y + 4 + i * 3
            pygame.draw.line(screen, (70, 73, 78),
                             (slide_x + 3, ly), (slide_x + slide_w - 3, ly), 1)

        # === EJECTION PORT ===
        ej_w, ej_h = 6, 10
        ej_x = slide_x + slide_w - ej_w - 2
        ej_y = slide_y + 16
        pygame.draw.rect(screen, (40, 42, 45), (ej_x, ej_y, ej_w, ej_h), border_radius=1)

        # === BARREL (tepa qism) ===
        barrel_w, barrel_h = 10, 14
        barrel_x = gun_x - barrel_w // 2
        barrel_y = slide_y - barrel_h + 2
        pygame.draw.rect(screen, (75, 78, 82),
                         (barrel_x, barrel_y, barrel_w, barrel_h), border_radius=2)

        # Barrel teshigi
        pygame.draw.circle(screen, (25, 25, 30),
                           (gun_x, barrel_y + 3), 3)
        pygame.draw.circle(screen, (15, 15, 18),
                           (gun_x, barrel_y + 3), 2)

        # === FRONT SIGHT ===
        sight_w, sight_h = 4, 6
        pygame.draw.rect(screen, (60, 63, 68),
                         (gun_x - sight_w // 2, barrel_y - sight_h + 2, sight_w, sight_h))

        # === REAR SIGHT ===
        rear_y = slide_y + 2
        pygame.draw.rect(screen, (60, 63, 68),
                         (slide_x + 2, rear_y, 4, 5))
        pygame.draw.rect(screen, (60, 63, 68),
                         (slide_x + slide_w - 6, rear_y, 4, 5))

        # === FRAME / BODY ===
        frame_w, frame_h = 24, 20
        frame_x = gun_x - frame_w // 2
        frame_y = slide_y + slide_h - 2
        frame_color = (70, 72, 76)
        pygame.draw.rect(screen, frame_color,
                         (frame_x, frame_y, frame_w, frame_h), border_radius=2)

        # === TRIGGER GUARD ===
        guard_y = frame_y + 6
        # Arc shakl
        pygame.draw.arc(screen, (80, 83, 88),
                        (frame_x + 2, guard_y, frame_w - 4, 16),
                        math.pi, 2 * math.pi, 2)
        # Pastki chiziq
        pygame.draw.line(screen, (80, 83, 88),
                         (frame_x + 2, guard_y + 8),
                         (frame_x + frame_w - 2, guard_y + 8), 2)

        # === TRIGGER ===
        trigger_x = gun_x - 1
        trigger_y1 = guard_y + 2
        trigger_y2 = guard_y + 7
        pygame.draw.line(screen, (100, 100, 105),
                         (trigger_x, trigger_y1),
                         (trigger_x - 2, trigger_y2), 2)

        # === GRIP ===
        grip_top_y = frame_y + frame_h - 2
        grip_points = [
            (gun_x - 10, grip_top_y),
            (gun_x + 12, grip_top_y),
            (gun_x + 16, grip_top_y + 35),
            (gun_x - 4, grip_top_y + 35),
        ]
        grip_color = (50, 45, 40)
        pygame.draw.polygon(screen, grip_color, grip_points)

        # Grip texture chiziqlari
        for i in range(6):
            gy = grip_top_y + 5 + i * 5
            # Interpolated x positions
            t = (gy - grip_top_y) / 35.0
            lx = int(gun_x - 10 + t * (gun_x - 4 - (gun_x - 10)))
            rx = int(gun_x + 12 + t * (gun_x + 16 - (gun_x + 12)))
            pygame.draw.line(screen, (60, 55, 50),
                             (lx + 2, gy), (rx - 2, gy), 1)

        # Grip highlight (chap chekka)
        pygame.draw.line(screen, (70, 65, 58),
                         (gun_x - 9, grip_top_y + 2),
                         (gun_x - 5, grip_top_y + 33), 1)

        # === MAGAZINE BASE ===
        mag_w = 14
        mag_h = 5
        mag_x = gun_x - mag_w // 2 + 3
        mag_y = grip_top_y + 33
        pygame.draw.rect(screen, (65, 68, 72),
                         (mag_x, mag_y, mag_w, mag_h), border_radius=2)

    def draw_muzzle_flash(self, screen, w, h):
        """Multi-layer muzzle flash effekti"""
        if self.muzzle_flash_timer <= 0:
            return

        recoil_y = 0
        if self.recoil_timer > 0:
            t = self.recoil_timer / WEAPON_RECOIL_DURATION
            recoil_y = int(t * t * 20)

        sway_x = int(self.sway_offset_x)
        sway_y = int(self.sway_offset_y)

        gun_x = w // 2 + 70 + sway_x
        gun_y = h - 90 - recoil_y + sway_y

        # Flash barrel uchiga
        flash_cx = gun_x
        flash_cy = gun_y - 42

        flash_alpha = int(255 * (self.muzzle_flash_timer / 0.06))
        flash_alpha = min(255, flash_alpha)

        # 1. Tashqi glow (katta, past alpha)
        glow_size = 30
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 200, 100, flash_alpha // 3),
                           (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (flash_cx - glow_size, flash_cy - glow_size))

        # 2. O'rta doira
        mid_size = 16
        mid_surf = pygame.Surface((mid_size * 2, mid_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(mid_surf, (255, 220, 150, flash_alpha),
                           (mid_size, mid_size), mid_size)
        screen.blit(mid_surf, (flash_cx - mid_size, flash_cy - mid_size))

        # 3. 4 ta yulduz nuri
        ray_len = 22
        ray_surf = pygame.Surface((ray_len * 2 + 4, ray_len * 2 + 4), pygame.SRCALPHA)
        rc = ray_len + 2
        ray_color = (255, 240, 200, flash_alpha)
        # Vertikal
        pygame.draw.line(ray_surf, ray_color, (rc, rc - ray_len), (rc, rc + ray_len), 2)
        # Gorizontal
        pygame.draw.line(ray_surf, ray_color, (rc - ray_len, rc), (rc + ray_len, rc), 2)
        # Diagonal
        d = int(ray_len * 0.6)
        pygame.draw.line(ray_surf, ray_color, (rc - d, rc - d), (rc + d, rc + d), 1)
        pygame.draw.line(ray_surf, ray_color, (rc + d, rc - d), (rc - d, rc + d), 1)
        screen.blit(ray_surf, (flash_cx - rc, flash_cy - rc))

        # 4. Markaziy oq nuqta
        core_size = 5
        core_surf = pygame.Surface((core_size * 2, core_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(core_surf, (255, 255, 240, flash_alpha),
                           (core_size, core_size), core_size)
        screen.blit(core_surf, (flash_cx - core_size, flash_cy - core_size))

    def draw_hit_marker(self, screen, w, h):
        """Hit marker effekti (X shakli)"""
        if self.hit_marker_timer <= 0:
            return

        cx, cy = w // 2, h // 2
        alpha = int(255 * (self.hit_marker_timer / 0.2))
        size = 10

        hit_surf = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        center = size + 2
        color = (*COLOR_HIT_MARKER, alpha)
        pygame.draw.line(hit_surf, color, (center - size, center - size),
                        (center + size, center + size), 2)
        pygame.draw.line(hit_surf, color, (center + size, center - size),
                        (center - size, center + size), 2)
        screen.blit(hit_surf, (cx - center, cy - center))

    def draw_bullet_trail(self, screen, w, h):
        """O'q izi effekti — barrel dan ekran markaziga uchuvchi tracer"""
        if self.trail_timer <= 0:
            return

        alpha = int(255 * (self.trail_timer / self.trail_duration))

        # Barrel uchi pozitsiyasi (draw_gun bilan sinxron)
        sway_x = int(self.sway_offset_x)
        sway_y = int(self.sway_offset_y)
        barrel_x = w // 2 + 70 + sway_x
        barrel_y = h - 90 + sway_y - 42

        # Target — ekran markazi (crosshair)
        target_x = w // 2
        target_y = h // 2

        # Trail progress (barrel → target animatsiya)
        progress = 1.0 - (self.trail_timer / self.trail_duration)

        # Tracer head (uchib borayotgan nuqta)
        head_x = int(barrel_x + (target_x - barrel_x) * progress)
        head_y = int(barrel_y + (target_y - barrel_y) * progress)

        # Tracer tail (orqada qoladigan chiziq)
        tail_progress = max(0.0, progress - 0.4)
        tail_x = int(barrel_x + (target_x - barrel_x) * tail_progress)
        tail_y = int(barrel_y + (target_y - barrel_y) * tail_progress)

        # Rang: sariq (normal), qizil-sariq (hit)
        if self.trail_hit:
            outer_color = (255, 180, 80, alpha // 2)
            inner_color = (255, 255, 200, alpha)
        else:
            outer_color = (255, 220, 100, alpha // 2)
            inner_color = (255, 255, 220, alpha)

        # Tashqi glow (keng, past alpha)
        trail_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.line(trail_surf, outer_color, (tail_x, tail_y), (head_x, head_y), 4)
        # Ichki yorug' yadro
        pygame.draw.line(trail_surf, inner_color, (tail_x, tail_y), (head_x, head_y), 2)
        screen.blit(trail_surf, (0, 0))
