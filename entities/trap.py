"""
Trap entities
Traps damage or debuff the player when triggered
"""

import random
from utils.colors import (
    COLOR_TRAP_SPIKE, COLOR_TRAP_TELEPORT, COLOR_TRAP_SLOW,
    COLOR_TRAP_CONFUSION, COLOR_TRAP_POISON
)
from utils.constants import TRAP_COOLDOWN


class Trap:
    """
    Base trap class
    """
    def __init__(self, x, y, trap_type):
        """
        Args:
            x, y: Grid position
            trap_type: Type of trap ('spike', 'teleport_trap', 'slow', 'confusion', 'poison')
        """
        self.x = x
        self.y = y
        self.type = trap_type
        self.triggered = False
        self.cooldown = 0.0  # Cooldown before trap can trigger again
        self.visible = self._get_visibility()  # Some traps are invisible
        self.animation = 0.0

    def _get_visibility(self):
        """Determine if trap is visible"""
        # Teleport traps are invisible until triggered
        if self.type == 'teleport_trap':
            return False
        return True

    def get_color(self):
        """Get RGB color for rendering"""
        colors = {
            'spike': COLOR_TRAP_SPIKE,
            'teleport_trap': COLOR_TRAP_TELEPORT,
            'slow': COLOR_TRAP_SLOW,
            'confusion': COLOR_TRAP_CONFUSION,
            'poison': COLOR_TRAP_POISON,
        }
        return colors.get(self.type, (200, 100, 100))

    def get_name(self):
        """Get human-readable name"""
        names = {
            'spike': 'Spike Trap',
            'teleport_trap': 'Teleport Trap',
            'slow': 'Slow Trap',
            'confusion': 'Confusion Trap',
            'poison': 'Poison Trap',
        }
        return names.get(self.type, 'Unknown Trap')

    def can_trigger(self):
        """Check if trap can be triggered"""
        return self.cooldown <= 0

    def trigger(self, player, walls, cols, rows):
        """
        Trigger trap effect on player

        Args:
            player: Player object
            walls: Maze walls
            cols, rows: Maze dimensions

        Returns:
            True if trap was triggered successfully
        """
        if not self.can_trigger():
            return False

        self.triggered = True
        self.cooldown = TRAP_COOLDOWN
        self.visible = True  # Reveal trap after triggering

        # Apply effect based on type
        if self.type == 'spike':
            # Direct damage
            player.take_damage(20)

        elif self.type == 'teleport_trap':
            # Teleport to random position
            new_x = random.randint(0, cols - 1)
            new_y = random.randint(0, rows - 1)
            player.x = new_x
            player.y = new_y
            player.trail.append((new_x, new_y))

        elif self.type == 'slow':
            # Slow effect + damage
            player.take_damage(5)
            player.add_effect('slow', 5.0)  # 5 seconds

        elif self.type == 'confusion':
            # Confusion (reverses controls)
            player.add_effect('confusion', 8.0)  # 8 seconds

        elif self.type == 'poison':
            # Poison (damage over time)
            player.add_effect('poison', 10.0, {'damage_per_sec': 5})

        return True

    def is_at_position(self, x, y):
        """Check if trap is at given position"""
        return self.x == x and self.y == y

    def update(self, dt):
        """
        Update trap state

        Args:
            dt: Delta time in seconds
        """
        # Update cooldown
        if self.cooldown > 0:
            self.cooldown -= dt
            if self.cooldown < 0:
                self.cooldown = 0
                self.triggered = False

        # Update animation
        self.animation += dt * 3.0  # Animation speed
        if self.animation > 1.0:
            self.animation = 0.0

    def reset(self):
        """Reset trap to initial state"""
        self.triggered = False
        self.cooldown = 0.0
        self.visible = self._get_visibility()
        self.animation = 0.0

    def __repr__(self):
        return f"Trap(pos=({self.x},{self.y}), type={self.type}, triggered={self.triggered})"


class TrapManager:
    """
    Manages all traps in the level
    """
    def __init__(self):
        self.traps = []

    def add_trap(self, x, y, trap_type):
        """
        Add a trap to the level

        Args:
            x, y: Grid position
            trap_type: Type of trap

        Returns:
            Trap object
        """
        trap = Trap(x, y, trap_type)
        self.traps.append(trap)
        return trap

    def get_trap_at(self, x, y):
        """Get trap at position"""
        for trap in self.traps:
            if trap.is_at_position(x, y):
                return trap
        return None

    def check_trigger(self, x, y, player, walls, cols, rows):
        """
        Check if player stepped on a trap and trigger it

        Args:
            x, y: Player position
            player: Player object
            walls: Maze walls
            cols, rows: Maze dimensions

        Returns:
            Trap object if triggered, None otherwise
        """
        trap = self.get_trap_at(x, y)
        if trap and trap.can_trigger():
            trap.trigger(player, walls, cols, rows)
            return trap
        return None

    def update(self, dt):
        """Update all traps"""
        for trap in self.traps:
            trap.update(dt)

    def get_active_traps(self):
        """Get list of traps not on cooldown"""
        return [t for t in self.traps if t.can_trigger()]

    def get_visible_traps(self):
        """Get list of visible traps"""
        return [t for t in self.traps if t.visible]

    def reset(self):
        """Reset all traps"""
        for trap in self.traps:
            trap.reset()

    def clear(self):
        """Remove all traps"""
        self.traps.clear()

    def __repr__(self):
        return f"TrapManager(traps={len(self.traps)}, active={len(self.get_active_traps())})"


# ========== TRAP TYPE HELPERS ==========

def get_trap_danger_level(trap_type):
    """
    Get trap danger level

    Returns:
        Integer 1-3 (1=low, 2=medium, 3=high)
    """
    danger = {
        'spike': 2,           # Medium - visible and direct damage
        'teleport_trap': 1,   # Low - no damage, just teleports
        'slow': 1,            # Low - debuff only
        'confusion': 3,       # High - very disorienting
        'poison': 3,          # High - persistent damage
    }
    return danger.get(trap_type, 1)


def get_trap_description(trap_type):
    """Get detailed description of trap effect"""
    descriptions = {
        'spike': '20 damage when stepped on',
        'teleport_trap': 'Teleports you to a random location (invisible)',
        'slow': '5 damage + slows movement for 5 seconds',
        'confusion': 'Reverses controls for 8 seconds',
        'poison': '5 damage/sec for 10 seconds',
    }
    return descriptions.get(trap_type, 'Unknown trap effect')


def create_random_trap(x, y, available_types=None):
    """
    Create a random trap

    Args:
        x, y: Position
        available_types: List of available types, or None for all

    Returns:
        Trap object
    """
    if available_types is None:
        available_types = ['spike', 'teleport_trap', 'slow', 'confusion', 'poison']

    trap_type = random.choice(available_types)
    return Trap(x, y, trap_type)
