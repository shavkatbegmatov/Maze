"""
Combat Manager - Dushman otish tizimi, LOS tekshiruv, damage effektlari
"""

import math
import random
import pygame
from utils.constants import (
    ENEMY_FIRE_RATE, ENEMY_ACCURACY, ENEMY_SHOOT_RANGE, ENEMY_SHOOT_DAMAGE
)
from utils.colors import COLOR_DAMAGE_OVERLAY


class CombatManager:
    """Jang menejeri — dushmanlarning qaytib otishi va damage effektlari"""

    def __init__(self):
        self.enemy_fire_cooldowns = {}  # {id(enemy): float}
        self.damage_flash_timer = 0.0   # qizil ekran effekti

    def update(self, dt, enemy_manager, boss_manager, player_3d, player_2d,
               grid, grid_cols, grid_rows):
        """
        Dushmanlar otish logikasi

        Args:
            dt: delta time
            enemy_manager: EnemyManager
            boss_manager: BossManager
            player_3d: Player3D
            player_2d: Player (2D stats uchun)
            grid: 2D grid massiv
            grid_cols, grid_rows: grid o'lchamlari
        """
        # Damage flash timer
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= dt

        # Har bir tirik dushman uchun
        for enemy in enemy_manager.get_alive_enemies():
            eid = id(enemy)

            # Cooldown kamayish
            if eid in self.enemy_fire_cooldowns:
                self.enemy_fire_cooldowns[eid] -= dt
            else:
                self.enemy_fire_cooldowns[eid] = ENEMY_FIRE_RATE

            if self.enemy_fire_cooldowns[eid] > 0:
                continue

            # Dushman otish mumkinmi?
            if self._enemy_can_shoot(enemy, player_3d, grid, grid_cols, grid_rows):
                self._enemy_attempt_shot(enemy, player_2d)
                self.enemy_fire_cooldowns[eid] = ENEMY_FIRE_RATE

    def _enemy_can_shoot(self, enemy, player_3d, grid, grid_cols, grid_rows):
        """Dushman ko'rish chizig'i ochiqmi va masofa yetarlimi?"""
        # Dushman world pozitsiyasi
        ex = 2 * enemy.x + 1.5
        ey = 2 * enemy.y + 1.5

        px, py = player_3d.world_x, player_3d.world_y

        # Masofa tekshiruvi
        dx = px - ex
        dy = py - ey
        dist = math.sqrt(dx * dx + dy * dy)

        shoot_range = ENEMY_SHOOT_RANGE.get(enemy.type, 5.0)
        # Grid masofaga konvertatsiya (grid birlik ~ 2 world birlik)
        if dist > shoot_range * 2:
            return False

        # LOS DDA tekshiruv
        return self._check_los(ex, ey, px, py, grid, grid_cols, grid_rows)

    def _check_los(self, x1, y1, x2, y2, grid, grid_cols, grid_rows):
        """DDA bilan devor to'sqinlik qiladimi tekshirish"""
        dx = x2 - x1
        dy = y2 - y1
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 0.01:
            return True

        ray_dx = dx / dist
        ray_dy = dy / dist

        map_x = int(x1)
        map_y = int(y1)

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
            side_dist_x = (x1 - map_x) * delta_x
        else:
            step_x = 1
            side_dist_x = (map_x + 1.0 - x1) * delta_x

        if ray_dy < 0:
            step_y = -1
            side_dist_y = (y1 - map_y) * delta_y
        else:
            step_y = 1
            side_dist_y = (map_y + 1.0 - y1) * delta_y

        max_steps = int(dist * 2) + 2
        for _ in range(max_steps):
            if side_dist_x < side_dist_y:
                current_dist = side_dist_x
                side_dist_x += delta_x
                map_x += step_x
            else:
                current_dist = side_dist_y
                side_dist_y += delta_y
                map_y += step_y

            if current_dist >= dist:
                return True  # Player'ga yetdi, devor yo'q

            if map_x < 0 or map_x >= grid_cols or map_y < 0 or map_y >= grid_rows:
                return False

            if grid[map_y][map_x] == 1:
                return False  # Devor to'sqinlik qiladi

        return True

    def _enemy_attempt_shot(self, enemy, player_2d):
        """Dushman otish urinishi — accuracy tekshiruvi"""
        accuracy = ENEMY_ACCURACY.get(enemy.type, 0.2)

        # Masofaga qarab accuracy kamayadi
        dist = abs(enemy.x - player_2d.x) + abs(enemy.y - player_2d.y)
        max_range = ENEMY_SHOOT_RANGE.get(enemy.type, 5.0)
        range_factor = max(0.2, 1.0 - dist / (max_range * 2))
        final_accuracy = accuracy * range_factor

        if random.random() < final_accuracy:
            # Hit!
            damage = ENEMY_SHOOT_DAMAGE.get(enemy.type, 5)
            player_2d.take_damage(damage)
            self.trigger_player_damage_flash()

    def register_enemy_hit(self, enemy):
        """Dushman otib tegildi — flash boshlash"""
        enemy.flash_timer = 0.15

    def trigger_player_damage_flash(self):
        """Qizil ekran flash boshlash"""
        self.damage_flash_timer = 0.3

    def draw_damage_overlay(self, screen, w, h):
        """Qizil vignette effekti — player zarar olganda"""
        if self.damage_flash_timer <= 0:
            return

        alpha = int(80 * (self.damage_flash_timer / 0.3))
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        # Vignette: chetlarda kuchli, markazda zaif
        # Oddiy rect overlay
        overlay.fill((*COLOR_DAMAGE_OVERLAY, alpha))

        # Markazda shaffofroq
        center_rect = pygame.Rect(w // 4, h // 4, w // 2, h // 2)
        pygame.draw.rect(overlay, (0, 0, 0, alpha // 2), center_rect)

        screen.blit(overlay, (0, 0))
