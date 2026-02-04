"""
Power-up entities
Players can collect power-ups for temporary boosts
"""

from utils.colors import (
    COLOR_POWERUP_SPEED, COLOR_POWERUP_VISION, COLOR_POWERUP_INVINCIBLE,
    COLOR_POWERUP_TELEPORT, COLOR_POWERUP_ENERGY, COLOR_POWERUP_XRAY
)
from utils.constants import POWERUP_MIN_DURATION, POWERUP_MAX_DURATION


class PowerUp:
    """
    Base power-up class
    """
    def __init__(self, x, y, powerup_type, duration=10.0):
        """
        Args:
            x, y: Grid position
            powerup_type: Type of power-up ('speed', 'vision', 'invincible', 'teleport', 'energy', 'xray')
            duration: Effect duration in seconds
        """
        self.x = x
        self.y = y
        self.type = powerup_type
        self.duration = duration
        self.collected = False
        self.spawn_animation = 0.0  # Pulsing animation

    def get_color(self):
        """Get RGB color based on type"""
        colors = {
            'speed': COLOR_POWERUP_SPEED,
            'vision': COLOR_POWERUP_VISION,
            'invincible': COLOR_POWERUP_INVINCIBLE,
            'teleport': COLOR_POWERUP_TELEPORT,
            'energy': COLOR_POWERUP_ENERGY,
            'xray': COLOR_POWERUP_XRAY,
        }
        return colors.get(self.type, (255, 255, 255))

    def get_name(self):
        """Get human-readable name"""
        names = {
            'speed': 'Speed Boost',
            'vision': 'Vision Boost',
            'invincible': 'Invincibility',
            'teleport': 'Teleport',
            'energy': 'Energy Restore',
            'xray': 'Wall X-Ray',
        }
        return names.get(self.type, 'Unknown')

    def get_description(self):
        """Get power-up description"""
        descriptions = {
            'speed': '1.5x movement speed',
            'vision': '+5 vision range',
            'invincible': 'Immune to damage',
            'teleport': 'Teleport once',
            'energy': 'Restore 50 energy',
            'xray': 'See through walls',
        }
        return descriptions.get(self.type, '')

    def collect(self, player):
        """
        Collect power-up and apply effect to player

        Args:
            player: Player object

        Returns:
            True if collected successfully
        """
        if self.collected:
            return False

        self.collected = True

        # Apply effect based on type
        if self.type == 'speed':
            player.add_powerup('speed', self.duration)
        elif self.type == 'vision':
            player.add_powerup('vision', self.duration)
        elif self.type == 'invincible':
            player.add_powerup('invincible', self.duration)
        elif self.type == 'teleport':
            player.add_powerup('teleport', 0)  # No duration, instant charge
        elif self.type == 'energy':
            player.add_powerup('energy', 0)  # Instant effect
        elif self.type == 'xray':
            player.add_powerup('xray', self.duration)

        return True

    def is_at_position(self, x, y):
        """Check if power-up is at given position and not collected"""
        return self.x == x and self.y == y and not self.collected

    def update(self, dt):
        """Update power-up animation"""
        self.spawn_animation += dt * 2.0  # Pulsing speed
        if self.spawn_animation > 1.0:
            self.spawn_animation = 0.0

    def __repr__(self):
        return f"PowerUp(pos=({self.x},{self.y}), type={self.type}, collected={self.collected})"


class PowerUpManager:
    """
    Manages all power-ups in the level
    """
    def __init__(self):
        self.powerups = []

    def add_powerup(self, x, y, powerup_type, duration=None):
        """
        Add a power-up to the level

        Args:
            x, y: Grid position
            powerup_type: Type of power-up
            duration: Optional duration override

        Returns:
            PowerUp object
        """
        import random

        if duration is None:
            # Random duration between min and max
            duration = random.uniform(POWERUP_MIN_DURATION, POWERUP_MAX_DURATION)

        powerup = PowerUp(x, y, powerup_type, duration)
        self.powerups.append(powerup)
        return powerup

    def get_powerup_at(self, x, y):
        """Get uncollected power-up at position"""
        for powerup in self.powerups:
            if powerup.is_at_position(x, y):
                return powerup
        return None

    def collect_powerup(self, x, y, player):
        """
        Collect power-up at position and apply to player

        Args:
            x, y: Position to check
            player: Player object

        Returns:
            PowerUp object if collected, None otherwise
        """
        powerup = self.get_powerup_at(x, y)
        if powerup:
            powerup.collect(player)
            return powerup
        return None

    def update(self, dt):
        """Update all power-ups"""
        for powerup in self.powerups:
            if not powerup.collected:
                powerup.update(dt)

    def get_uncollected_powerups(self):
        """Get list of uncollected power-ups"""
        return [p for p in self.powerups if not p.collected]

    def reset(self):
        """Reset all power-ups"""
        for powerup in self.powerups:
            powerup.collected = False
            powerup.spawn_animation = 0.0

    def clear(self):
        """Remove all power-ups"""
        self.powerups.clear()

    def __repr__(self):
        return f"PowerUpManager(powerups={len(self.powerups)}, uncollected={len(self.get_uncollected_powerups())})"


# ========== POWER-UP TYPE HELPERS ==========

def create_random_powerup(x, y, available_types=None):
    """
    Create a random power-up

    Args:
        x, y: Position
        available_types: List of available types, or None for all

    Returns:
        PowerUp object
    """
    import random

    if available_types is None:
        available_types = ['speed', 'vision', 'invincible', 'teleport', 'energy', 'xray']

    powerup_type = random.choice(available_types)
    duration = random.uniform(POWERUP_MIN_DURATION, POWERUP_MAX_DURATION)

    return PowerUp(x, y, powerup_type, duration)


def get_powerup_tier(powerup_type):
    """
    Get power-up tier (rarity)

    Returns:
        Integer 1-3 (1=common, 2=uncommon, 3=rare)
    """
    tiers = {
        'energy': 1,      # Common
        'speed': 1,
        'vision': 2,      # Uncommon
        'invincible': 2,
        'teleport': 3,    # Rare
        'xray': 3,
    }
    return tiers.get(powerup_type, 1)
