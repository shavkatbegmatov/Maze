"""
Boss Fight System - Final challenge for Nightmare difficulty
"""

import random
import math
from maze.maze_core import astar_shortest_path, neighbors_open


class Boss:
    """
    Boss enemy with multiple phases and special attacks
    """
    def __init__(self, x, y):
        """
        Args:
            x, y: Starting position (near goal)
        """
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y

        # Boss stats
        self.max_health = 300
        self.health = self.max_health
        self.damage = 25
        self.speed = 0.6

        # Phase system (3 phases)
        self.phase = 1  # 1, 2, or 3
        self.phase_health_thresholds = [0.66, 0.33, 0.0]  # Phase changes at 66% and 33%

        # State machine
        self.state = 'idle'  # 'idle', 'chase', 'attack', 'charge', 'summon', 'rage', 'stunned'
        self.state_timer = 0.0

        # Movement
        self.move_timer = 0.0
        self.move_cooldown = 0.5  # Slower than normal enemies

        # Attack system
        self.attack_cooldown = 0.0
        self.attack_delay = 2.0  # Time between attacks
        self.is_attacking = False
        self.attack_target = None
        self.attack_telegraph_timer = 0.0  # Warning before attack

        # Charge attack
        self.is_charging = False
        self.charge_direction = (0, 0)
        self.charge_speed = 3.0
        self.charge_distance = 0
        self.max_charge_distance = 8

        # Summon attack
        self.summon_cooldown = 0.0
        self.summon_delay = 10.0
        self.summoned_minions = []

        # Rage mode (Phase 3)
        self.rage_mode = False
        self.rage_timer = 0.0

        # Visual
        self.color = (180, 50, 50)  # Dark red
        self.glow_phase = 0.0
        self.flash_timer = 0.0
        self.size_multiplier = 1.0  # For pulsing effect

        # Status
        self.alive = True
        self.defeated = False
        self.invulnerable = False
        self.invulnerable_timer = 0.0

    def get_health_percent(self):
        """Get health as percentage"""
        return self.health / self.max_health

    def take_damage(self, amount):
        """
        Boss takes damage

        Args:
            amount: Damage amount

        Returns:
            True if boss died
        """
        if self.invulnerable or not self.alive:
            return False

        self.health -= amount
        self.flash_timer = 0.3  # Flash when hit

        # Brief invulnerability after hit
        self.invulnerable = True
        self.invulnerable_timer = 0.5

        # Check phase transition
        health_percent = self.get_health_percent()

        if self.phase == 1 and health_percent <= self.phase_health_thresholds[0]:
            self._enter_phase(2)
        elif self.phase == 2 and health_percent <= self.phase_health_thresholds[1]:
            self._enter_phase(3)

        # Check death
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.defeated = True
            return True

        return False

    def _enter_phase(self, new_phase):
        """Enter a new phase"""
        self.phase = new_phase
        self.state = 'stunned'
        self.state_timer = 2.0  # Stunned during phase transition

        if new_phase == 2:
            # Phase 2: Faster, can summon
            self.speed = 0.8
            self.damage = 30
            self.attack_delay = 1.5
            self.color = (200, 80, 50)  # Orange-red

        elif new_phase == 3:
            # Phase 3: Rage mode
            self.speed = 1.0
            self.damage = 35
            self.attack_delay = 1.0
            self.rage_mode = True
            self.color = (255, 50, 50)  # Bright red

    def update(self, dt, walls, cols, rows, player, enemy_manager=None):
        """
        Update boss AI

        Args:
            dt: Delta time
            walls: Maze walls
            cols, rows: Maze dimensions
            player: Player object
            enemy_manager: For summoning minions

        Returns:
            dict with events: {'attacked': bool, 'summoned': list, 'charged': bool}
        """
        events = {'attacked': False, 'summoned': [], 'charged': False}

        if not self.alive:
            return events

        # Update timers
        self.glow_phase += dt * 3.0
        self.move_timer += dt
        self.attack_cooldown -= dt
        self.summon_cooldown -= dt

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
            if self.invulnerable_timer <= 0:
                self.invulnerable = False

        if self.flash_timer > 0:
            self.flash_timer -= dt

        if self.attack_telegraph_timer > 0:
            self.attack_telegraph_timer -= dt
            if self.attack_telegraph_timer <= 0:
                # Execute attack
                events['attacked'] = self._execute_attack(player)

        # State machine
        if self.state == 'stunned':
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = 'idle'

        elif self.state == 'idle':
            # Decide next action
            self._decide_action(player, walls, cols, rows)

        elif self.state == 'chase':
            # Chase player
            if self.move_timer >= self.move_cooldown:
                self.move_timer = 0
                self._move_toward_player(player, walls, cols, rows)

            # Check if can attack
            dist = abs(self.x - player.x) + abs(self.y - player.y)
            if dist <= 2 and self.attack_cooldown <= 0:
                self._start_attack(player)

        elif self.state == 'charge':
            # Charging attack
            events['charged'] = self._update_charge(dt, player, walls, cols, rows)

        elif self.state == 'summon':
            # Summoning minions
            self.state_timer -= dt
            if self.state_timer <= 0:
                events['summoned'] = self._summon_minions(walls, cols, rows, enemy_manager)
                self.state = 'idle'
                self.summon_cooldown = self.summon_delay

        elif self.state == 'rage':
            # Rage mode - aggressive chase
            self.rage_timer -= dt
            if self.move_timer >= self.move_cooldown * 0.5:  # Faster movement
                self.move_timer = 0
                self._move_toward_player(player, walls, cols, rows)

            # Quick attacks
            dist = abs(self.x - player.x) + abs(self.y - player.y)
            if dist <= 1:
                events['attacked'] = True
                player.take_damage(self.damage)

            if self.rage_timer <= 0:
                self.state = 'idle'

        # Pulsing size effect
        self.size_multiplier = 1.0 + 0.1 * math.sin(self.glow_phase)

        return events

    def _decide_action(self, player, walls, cols, rows):
        """Decide next action based on phase and situation"""
        dist = abs(self.x - player.x) + abs(self.y - player.y)

        # Phase-based decisions
        if self.phase == 1:
            # Phase 1: Simple chase
            self.state = 'chase'

        elif self.phase == 2:
            # Phase 2: Mix of chase and abilities
            if self.summon_cooldown <= 0 and random.random() < 0.3:
                self.state = 'summon'
                self.state_timer = 1.5  # Summon cast time
            elif dist > 5 and random.random() < 0.4:
                self._start_charge(player)
            else:
                self.state = 'chase'

        elif self.phase == 3:
            # Phase 3: Aggressive with rage
            if random.random() < 0.2:
                self.state = 'rage'
                self.rage_timer = 3.0
            elif self.summon_cooldown <= 0:
                self.state = 'summon'
                self.state_timer = 1.0  # Faster summon
            elif dist > 4 and random.random() < 0.5:
                self._start_charge(player)
            else:
                self.state = 'chase'

    def _move_toward_player(self, player, walls, cols, rows):
        """Move one step toward player"""
        path = astar_shortest_path(walls, cols, rows, (self.x, self.y), (player.x, player.y))
        if path and len(path) > 1:
            self.x, self.y = path[1]

    def _start_attack(self, player):
        """Start an attack with telegraph"""
        self.is_attacking = True
        self.attack_target = (player.x, player.y)
        self.attack_telegraph_timer = 0.5  # Warning time
        self.attack_cooldown = self.attack_delay

    def _execute_attack(self, player):
        """Execute the attack"""
        self.is_attacking = False

        # Check if player is still in range
        dist = abs(self.x - player.x) + abs(self.y - player.y)
        if dist <= 2:
            player.take_damage(self.damage)
            return True
        return False

    def _start_charge(self, player):
        """Start a charge attack toward player"""
        self.state = 'charge'
        self.is_charging = True
        self.charge_distance = 0

        # Calculate direction
        dx = player.x - self.x
        dy = player.y - self.y

        # Normalize to one direction (horizontal or vertical)
        if abs(dx) > abs(dy):
            self.charge_direction = (1 if dx > 0 else -1, 0)
        else:
            self.charge_direction = (0, 1 if dy > 0 else -1)

    def _update_charge(self, dt, player, walls, cols, rows):
        """Update charge attack"""
        if not self.is_charging:
            self.state = 'idle'
            return False

        # Move in charge direction
        self.move_timer += dt * self.charge_speed
        if self.move_timer >= 0.1:  # Fast movement during charge
            self.move_timer = 0

            new_x = self.x + self.charge_direction[0]
            new_y = self.y + self.charge_direction[1]

            # Check bounds
            if 0 <= new_x < cols and 0 <= new_y < rows:
                # Check if can move (ignore walls during charge - boss breaks through!)
                self.x = new_x
                self.y = new_y
                self.charge_distance += 1

                # Check if hit player
                if self.x == player.x and self.y == player.y:
                    player.take_damage(self.damage * 1.5)  # Extra damage on charge
                    self.is_charging = False
                    self.state = 'stunned'
                    self.state_timer = 1.0  # Brief stun after charge
                    return True

            else:
                # Hit wall/boundary
                self.is_charging = False
                self.state = 'stunned'
                self.state_timer = 1.5
                return False

            # Check max distance
            if self.charge_distance >= self.max_charge_distance:
                self.is_charging = False
                self.state = 'idle'

        return False

    def _summon_minions(self, walls, cols, rows, enemy_manager):
        """Summon minion enemies"""
        summoned = []

        if enemy_manager is None:
            return summoned

        # Summon 2-3 minions near boss
        num_minions = 2 if self.phase == 2 else 3

        for _ in range(num_minions):
            # Find valid spawn position near boss
            neighbors = neighbors_open(walls, cols, rows, self.x, self.y)
            if neighbors:
                spawn_pos = random.choice(neighbors)
                # Create patrol enemy as minion
                enemy = enemy_manager.add_enemy(spawn_pos[0], spawn_pos[1], 'chase')
                summoned.append(enemy)

        return summoned

    def get_color(self):
        """Get current color with effects"""
        if self.flash_timer > 0:
            return (255, 255, 255)  # Flash white when hit

        # Glow effect
        glow = int(abs(math.sin(self.glow_phase)) * 30)

        if self.rage_mode and self.state == 'rage':
            # Pulsing red in rage
            return (min(255, self.color[0] + glow + 50), self.color[1], self.color[2])

        return (
            min(255, self.color[0] + glow),
            self.color[1],
            self.color[2]
        )

    def is_telegraphing(self):
        """Check if boss is telegraphing an attack"""
        return self.attack_telegraph_timer > 0 or self.is_charging

    def reset(self):
        """Reset boss to initial state"""
        self.x = self.start_x
        self.y = self.start_y
        self.health = self.max_health
        self.phase = 1
        self.state = 'idle'
        self.alive = True
        self.defeated = False
        self.speed = 0.6
        self.damage = 25
        self.color = (180, 50, 50)
        self.rage_mode = False

    def __repr__(self):
        return f"Boss(pos=({self.x},{self.y}), hp={self.health}/{self.max_health}, phase={self.phase})"


class BossManager:
    """
    Manages boss encounters
    """
    def __init__(self):
        self.boss = None
        self.active = False
        self.boss_defeated = False
        self.fight_started = False
        self.arena_cells = []  # Cells that are part of boss arena

    def create_boss(self, goal_x, goal_y, walls, cols, rows):
        """
        Create boss near goal

        Args:
            goal_x, goal_y: Goal position
            walls: Maze walls
            cols, rows: Maze dimensions
        """
        # Find position near goal but not on it
        candidates = []
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                nx, ny = goal_x + dx, goal_y + dy
                if (0 <= nx < cols and 0 <= ny < rows and
                    (nx, ny) != (goal_x, goal_y)):
                    # Check if accessible
                    neighbors = neighbors_open(walls, cols, rows, nx, ny)
                    if len(neighbors) >= 2:
                        candidates.append((nx, ny))

        if candidates:
            boss_x, boss_y = random.choice(candidates)
            self.boss = Boss(boss_x, boss_y)
            self.active = True
            self.boss_defeated = False
            self.fight_started = False

            # Define arena around goal
            self._create_arena(goal_x, goal_y, cols, rows)

    def _create_arena(self, goal_x, goal_y, cols, rows):
        """Create arena cells around goal"""
        self.arena_cells = []
        arena_radius = 5

        for dy in range(-arena_radius, arena_radius + 1):
            for dx in range(-arena_radius, arena_radius + 1):
                nx, ny = goal_x + dx, goal_y + dy
                if 0 <= nx < cols and 0 <= ny < rows:
                    self.arena_cells.append((nx, ny))

    def is_in_arena(self, x, y):
        """Check if position is in boss arena"""
        return (x, y) in self.arena_cells

    def update(self, dt, walls, cols, rows, player, enemy_manager):
        """
        Update boss fight

        Returns:
            dict with events
        """
        events = {
            'boss_attacked': False,
            'minions_summoned': [],
            'boss_charged': False,
            'boss_defeated': False,
            'fight_started': False
        }

        if not self.active or not self.boss or not self.boss.alive:
            return events

        # Check if player entered arena
        if not self.fight_started and self.is_in_arena(player.x, player.y):
            self.fight_started = True
            events['fight_started'] = True

        # Update boss
        if self.fight_started:
            boss_events = self.boss.update(dt, walls, cols, rows, player, enemy_manager)
            events['boss_attacked'] = boss_events['attacked']
            events['minions_summoned'] = boss_events['summoned']
            events['boss_charged'] = boss_events['charged']

            if self.boss.defeated:
                self.boss_defeated = True
                events['boss_defeated'] = True

        return events

    def damage_boss(self, amount):
        """
        Damage the boss

        Returns:
            True if boss died
        """
        if self.boss and self.boss.alive:
            return self.boss.take_damage(amount)
        return False

    def get_boss(self):
        """Get the boss object"""
        return self.boss

    def is_boss_alive(self):
        """Check if boss is alive"""
        return self.boss is not None and self.boss.alive

    def reset(self):
        """Reset boss fight"""
        if self.boss:
            self.boss.reset()
        self.fight_started = False
        self.boss_defeated = False

    def clear(self):
        """Remove boss"""
        self.boss = None
        self.active = False
        self.boss_defeated = False
        self.fight_started = False
        self.arena_cells = []
