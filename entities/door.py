"""
Key and Door entities
Keys must be collected to unlock matching colored doors
"""

from utils.colors import KEY_COLORS, DOOR_COLORS


class Key:
    """
    Collectible key with a color
    """
    def __init__(self, x, y, color):
        """
        Args:
            x, y: Grid position
            color: Key color ('red', 'blue', 'green', 'yellow', 'purple', 'cyan')
        """
        self.x = x
        self.y = y
        self.color = color
        self.collected = False

    def get_color_rgb(self):
        """Get RGB color for rendering"""
        return KEY_COLORS.get(self.color, (255, 255, 255))

    def collect(self):
        """Mark key as collected"""
        self.collected = True

    def is_at_position(self, x, y):
        """Check if key is at given position"""
        return self.x == x and self.y == y and not self.collected

    def __repr__(self):
        return f"Key(pos=({self.x},{self.y}), color={self.color}, collected={self.collected})"


class Door:
    """
    Door that blocks passage until unlocked with matching key
    """
    def __init__(self, x, y, color):
        """
        Args:
            x, y: Grid position
            color: Door color (must match key color)
        """
        self.x = x
        self.y = y
        self.color = color
        self.locked = True
        self.opening_animation = 0.0  # For visual effect

    def get_color_rgb(self):
        """Get RGB color for rendering"""
        return DOOR_COLORS.get(self.color, (150, 150, 150))

    def unlock(self):
        """Unlock the door"""
        self.locked = False

    def lock(self):
        """Lock the door"""
        self.locked = True

    def is_blocking(self, x, y):
        """Check if door is blocking given position"""
        return self.x == x and self.y == y and self.locked

    def is_at_position(self, x, y):
        """Check if door is at given position"""
        return self.x == x and self.y == y

    def update(self, dt):
        """
        Update door animation
        dt: delta time in seconds
        """
        if not self.locked and self.opening_animation < 1.0:
            self.opening_animation += dt * 2.0  # Animation speed
            if self.opening_animation > 1.0:
                self.opening_animation = 1.0

    def __repr__(self):
        return f"Door(pos=({self.x},{self.y}), color={self.color}, locked={self.locked})"


class DoorManager:
    """
    Manages all keys and doors in the level
    """
    def __init__(self):
        self.keys = []
        self.doors = []

    def add_key(self, x, y, color):
        """Add a key to the level"""
        key = Key(x, y, color)
        self.keys.append(key)
        return key

    def add_door(self, x, y, color):
        """Add a door to the level"""
        door = Door(x, y, color)
        self.doors.append(door)
        return door

    def get_key_at(self, x, y):
        """Get uncollected key at position"""
        for key in self.keys:
            if key.is_at_position(x, y):
                return key
        return None

    def get_door_at(self, x, y):
        """Get door at position"""
        for door in self.doors:
            if door.is_at_position(x, y):
                return door
        return None

    def is_blocked_by_door(self, x, y):
        """Check if position is blocked by a locked door"""
        for door in self.doors:
            if door.is_blocking(x, y):
                return True
        return False

    def try_unlock_door(self, x, y, player):
        """
        Try to unlock door at position using player's keys

        Args:
            x, y: Position to check
            player: Player object with inventory

        Returns:
            True if door was unlocked, False otherwise
        """
        door = self.get_door_at(x, y)
        if door and door.locked:
            # Check if player has matching key
            if player.has_key(door.color):
                player.use_key(door.color)
                door.unlock()
                return True
        return False

    def collect_key(self, x, y, player):
        """
        Collect key at position and add to player inventory

        Args:
            x, y: Position to check
            player: Player object

        Returns:
            True if key was collected, False otherwise
        """
        key = self.get_key_at(x, y)
        if key:
            key.collect()
            player.add_key(key.color)
            return True
        return False

    def update(self, dt):
        """Update all doors (animations, etc.)"""
        for door in self.doors:
            door.update(dt)

    def reset(self):
        """Reset all keys and doors"""
        for key in self.keys:
            key.collected = False
        for door in self.doors:
            door.lock()
            door.opening_animation = 0.0

    def get_uncollected_keys(self):
        """Get list of uncollected keys"""
        return [key for key in self.keys if not key.collected]

    def get_locked_doors(self):
        """Get list of locked doors"""
        return [door for door in self.doors if door.locked]

    def __repr__(self):
        return f"DoorManager(keys={len(self.keys)}, doors={len(self.doors)})"
