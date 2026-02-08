"""
Weapon System - Hitscan shooting with procedural gun rendering
"""

import math
import pygame
from utils.constants import (
    WEAPON_DAMAGE, WEAPON_FIRE_RATE, WEAPON_ENERGY_COST,
    WEAPON_MAX_RANGE, WEAPON_HIT_RADIUS, WEAPON_RECOIL_DURATION
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

    def can_fire(self, player_energy):
        """Otish mumkinmi?"""
        return self.fire_cooldown <= 0 and player_energy >= self.energy_cost

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
        if self.recoil_timer <= 0:
            self.is_firing = False

    def draw_gun(self, screen, w, h):
        """Protsedural qurol chizish"""
        # Recoil effekti
        recoil_offset = 0
        if self.recoil_timer > 0:
            t = self.recoil_timer / WEAPON_RECOIL_DURATION
            recoil_offset = int(t * 15)

        # Qurol markazdan biroz o'ngda
        gun_x = w // 2 + 60
        gun_y = h - 80 - recoil_offset

        # Barrel (gorizontal to'rtburchak)
        barrel_rect = pygame.Rect(gun_x - 8, gun_y - 30, 16, 35)
        pygame.draw.rect(screen, COLOR_GUN_BARREL, barrel_rect, border_radius=3)

        # Body (kattaroq to'rtburchak)
        body_rect = pygame.Rect(gun_x - 15, gun_y + 5, 30, 25)
        pygame.draw.rect(screen, COLOR_GUN_BODY, body_rect, border_radius=4)

        # Grip (pastga qarab kengayadigan polygon)
        grip_points = [
            (gun_x - 10, gun_y + 30),
            (gun_x + 10, gun_y + 30),
            (gun_x + 15, gun_y + 60),
            (gun_x - 5, gun_y + 60),
        ]
        pygame.draw.polygon(screen, COLOR_GUN_GRIP, grip_points)

        # Barrel uchi (highlight)
        pygame.draw.rect(screen, (120, 125, 130), pygame.Rect(gun_x - 6, gun_y - 30, 12, 4), border_radius=2)

    def draw_muzzle_flash(self, screen, w, h):
        """Muzzle flash effekti"""
        if self.muzzle_flash_timer <= 0:
            return

        recoil_offset = 0
        if self.recoil_timer > 0:
            t = self.recoil_timer / WEAPON_RECOIL_DURATION
            recoil_offset = int(t * 15)

        gun_x = w // 2 + 60
        gun_y = h - 80 - recoil_offset

        flash_alpha = int(255 * (self.muzzle_flash_timer / 0.06))
        flash_size = 20

        flash_surf = pygame.Surface((flash_size * 2, flash_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(flash_surf, (*COLOR_MUZZLE_FLASH, flash_alpha),
                          (flash_size, flash_size), flash_size)
        # Inner bright core
        pygame.draw.circle(flash_surf, (255, 255, 220, flash_alpha),
                          (flash_size, flash_size), flash_size // 2)

        screen.blit(flash_surf, (gun_x - flash_size, gun_y - 30 - flash_size))

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
