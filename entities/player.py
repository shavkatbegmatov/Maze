"""
Player entity with health, energy, inventory, and effects
"""

from utils.constants import (
    PLAYER_MAX_HEALTH, PLAYER_MAX_ENERGY, PLAYER_BASE_SPEED,
    PLAYER_ENERGY_REGEN_RATE, PLAYER_ENERGY_COST_MOVE,
    DEFAULT_VISION_RANGE, INVULNERABILITY_DURATION
)
from maze.maze_core import can_move


class Player:
    """
    Player entity with stats, inventory, and effects
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.prev_x = x
        self.prev_y = y

        # Trail for visual effect
        self.trail = [(x, y)]
        self.max_trail_length = 30

        # Inventory
        self.inventory = {
            'keys': [],  # List of key colors ['red', 'blue', etc.]
            'powerups_active': []  # Currently active powerups
        }

        # Stats
        self.stats = {
            'health': PLAYER_MAX_HEALTH,
            'max_health': PLAYER_MAX_HEALTH,
            'energy': PLAYER_MAX_ENERGY,
            'max_energy': PLAYER_MAX_ENERGY,
            'speed_multiplier': PLAYER_BASE_SPEED,
            'vision_range': DEFAULT_VISION_RANGE,
            'invulnerable_timer': 0,
            'teleport_charges': 0,  # Teleport powerup charges
        }

        # Effects (status effects from traps/powerups)
        self.effects = []  # List of {type, timer, data}

        # Gameplay tracking
        self.last_damage_time = 0
        self.moves = 0
        self.damage_taken = 0
        self.enemies_dodged = 0

    def move(self, dx, dy, walls, cols, rows):
        """
        Move player in direction (dx, dy)
        Returns True if move was successful
        """
        # Check energy
        if self.stats['energy'] < PLAYER_ENERGY_COST_MOVE:
            return False

        # Check confusion effect (reverses controls)
        if self.has_effect('confusion'):
            dx, dy = -dx, -dy

        # Check if move is valid
        if can_move(walls, cols, rows, self.x, self.y, dx, dy):
            self.prev_x, self.prev_y = self.x, self.y
            self.x += dx
            self.y += dy
            self.trail.append((self.x, self.y))

            # Limit trail length
            if len(self.trail) > self.max_trail_length:
                self.trail.pop(0)

            # Consume energy (affected by slow effect)
            energy_cost = PLAYER_ENERGY_COST_MOVE
            if self.has_effect('slow'):
                energy_cost *= 1.5

            self.stats['energy'] -= energy_cost
            self.stats['energy'] = max(0, self.stats['energy'])

            self.moves += 1
            return True

        return False

    def take_damage(self, amount):
        """
        Take damage
        Returns True if player died
        """
        if self.stats['invulnerable_timer'] > 0:
            return False

        self.stats['health'] -= amount
        self.damage_taken += amount
        self.stats['invulnerable_timer'] = INVULNERABILITY_DURATION

        if self.stats['health'] <= 0:
            self.stats['health'] = 0
            return True  # Dead

        return False

    def heal(self, amount):
        """Heal player"""
        self.stats['health'] += amount
        self.stats['health'] = min(self.stats['health'], self.stats['max_health'])

    def restore_energy(self, amount):
        """Restore energy"""
        self.stats['energy'] += amount
        self.stats['energy'] = min(self.stats['energy'], self.stats['max_energy'])

    def add_key(self, color):
        """Add a key to inventory"""
        if color not in self.inventory['keys']:
            self.inventory['keys'].append(color)

    def has_key(self, color):
        """Check if player has a specific key"""
        return color in self.inventory['keys']

    def use_key(self, color):
        """Use a key (remove from inventory)"""
        if color in self.inventory['keys']:
            self.inventory['keys'].remove(color)
            return True
        return False

    def add_powerup(self, powerup_type, duration, data=None):
        """
        Add a power-up effect
        powerup_type: 'speed', 'vision', 'invincible', 'teleport', 'energy', 'xray'
        """
        effect = {
            'type': powerup_type,
            'timer': duration,
            'data': data or {}
        }

        # Handle special powerups
        if powerup_type == 'speed':
            self.stats['speed_multiplier'] = 1.5
        elif powerup_type == 'vision':
            self.stats['vision_range'] += 5
        elif powerup_type == 'invincible':
            self.stats['invulnerable_timer'] = duration
        elif powerup_type == 'teleport':
            self.stats['teleport_charges'] += 1
            return  # Teleport doesn't have a timer
        elif powerup_type == 'energy':
            self.restore_energy(50)
            return  # Instant effect

        self.effects.append(effect)

    def add_effect(self, effect_type, duration, data=None):
        """
        Add a negative effect (from traps)
        effect_type: 'slow', 'confusion', 'poison'
        """
        effect = {
            'type': effect_type,
            'timer': duration,
            'data': data or {}
        }

        if effect_type == 'slow':
            self.stats['speed_multiplier'] = 0.5

        self.effects.append(effect)

    def has_effect(self, effect_type):
        """Check if player has a specific effect"""
        return any(e['type'] == effect_type for e in self.effects)

    def teleport_to(self, x, y):
        """Teleport player to a position"""
        if self.stats['teleport_charges'] > 0:
            self.x = x
            self.y = y
            self.trail.append((x, y))
            self.stats['teleport_charges'] -= 1
            return True
        return False

    def update(self, dt):
        """
        Update player state
        dt: delta time in seconds
        """
        # Energy regeneration
        if self.stats['energy'] < self.stats['max_energy']:
            regen_rate = PLAYER_ENERGY_REGEN_RATE
            # Slower regen if poisoned
            if self.has_effect('poison'):
                regen_rate *= 0.5

            self.stats['energy'] += regen_rate * dt
            self.stats['energy'] = min(self.stats['energy'], self.stats['max_energy'])

        # Invulnerability timer
        if self.stats['invulnerable_timer'] > 0:
            self.stats['invulnerable_timer'] -= dt
            self.stats['invulnerable_timer'] = max(0, self.stats['invulnerable_timer'])

        # Update effects
        for effect in self.effects[:]:
            effect['timer'] -= dt

            # Poison damage over time
            if effect['type'] == 'poison':
                damage = effect['data'].get('damage_per_sec', 5)
                self.stats['health'] -= damage * dt
                self.stats['health'] = max(0, self.stats['health'])

            # Remove expired effects
            if effect['timer'] <= 0:
                self._remove_effect(effect)
                self.effects.remove(effect)

    def _remove_effect(self, effect):
        """Remove effect and revert its changes"""
        effect_type = effect['type']

        if effect_type == 'speed':
            self.stats['speed_multiplier'] = PLAYER_BASE_SPEED
        elif effect_type == 'vision':
            self.stats['vision_range'] = DEFAULT_VISION_RANGE
        elif effect_type == 'slow':
            self.stats['speed_multiplier'] = PLAYER_BASE_SPEED

    def reset_position(self, x, y):
        """Reset player to starting position"""
        self.x = x
        self.y = y
        self.prev_x = x
        self.prev_y = y
        self.trail = [(x, y)]
        self.moves = 0

    def get_health_percent(self):
        """Get health as percentage (0-1)"""
        return self.stats['health'] / self.stats['max_health']

    def get_energy_percent(self):
        """Get energy as percentage (0-1)"""
        return self.stats['energy'] / self.stats['max_energy']

    def is_alive(self):
        """Check if player is alive"""
        return self.stats['health'] > 0

    def is_invulnerable(self):
        """Check if player is currently invulnerable"""
        return self.stats['invulnerable_timer'] > 0 or self.has_effect('invincible')

    def get_active_effects(self):
        """Get list of active effect types"""
        return [e['type'] for e in self.effects]

    def __repr__(self):
        return f"Player(pos=({self.x},{self.y}), hp={self.stats['health']:.1f}, energy={self.stats['energy']:.1f})"
