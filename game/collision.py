"""
Collision detection and handling
"""


class CollisionHandler:
    """
    Handles all collision detection and response in the game
    """
    def __init__(self):
        self.last_collision = None

    def check_player_position(self, player, enemy_manager, powerup_manager, trap_manager, door_manager, walls, cols, rows):
        """
        Check player's current position for collisions with entities

        Args:
            player: Player object
            enemy_manager: EnemyManager object
            powerup_manager: PowerUpManager object
            trap_manager: TrapManager object
            door_manager: DoorManager object
            walls: Maze walls
            cols, rows: Maze dimensions

        Returns:
            Dictionary with collision results:
            {
                'enemy': Enemy or None,
                'powerup': PowerUp or None,
                'trap': Trap or None,
                'key': Key or None,
                'door': Door or None,
                'player_died': bool
            }
        """
        result = {
            'enemy': None,
            'powerup': None,
            'trap': None,
            'key': None,
            'door': None,
            'player_died': False
        }

        px, py = player.x, player.y

        # Check enemy collision
        enemy = enemy_manager.check_collision_with_player(px, py)
        if enemy:
            result['enemy'] = enemy
            if not player.is_invulnerable():
                player_died = player.take_damage(enemy.damage)
                result['player_died'] = player_died

        # Check power-up collection
        powerup = powerup_manager.collect_powerup(px, py, player)
        if powerup:
            result['powerup'] = powerup

        # Check trap trigger
        trap = trap_manager.check_trigger(px, py, player, walls, cols, rows)
        if trap:
            result['trap'] = trap
            # Check if trap killed player
            if player.stats['health'] <= 0:
                result['player_died'] = True

        # Check key collection
        if door_manager.collect_key(px, py, player):
            key = door_manager.get_key_at(px, py)
            result['key'] = key

        # Check door interaction (auto-unlock if player has key)
        if door_manager.is_blocked_by_door(px, py):
            if door_manager.try_unlock_door(px, py, player):
                door = door_manager.get_door_at(px, py)
                result['door'] = door

        self.last_collision = result
        return result

    def check_path_for_doors(self, start_x, start_y, end_x, end_y, door_manager):
        """
        Check if a movement path crosses a locked door

        Args:
            start_x, start_y: Starting position
            end_x, end_y: Ending position
            door_manager: DoorManager object

        Returns:
            True if path is blocked by a locked door
        """
        # For now, just check end position
        # In the future, could interpolate path for diagonal moves
        return door_manager.is_blocked_by_door(end_x, end_y)

    def is_position_safe(self, x, y, enemy_manager, trap_manager, safe_distance=2):
        """
        Check if a position is "safe" (no nearby enemies or visible traps)

        Args:
            x, y: Position to check
            enemy_manager: EnemyManager
            trap_manager: TrapManager
            safe_distance: Minimum distance from enemies

        Returns:
            bool: True if position is safe
        """
        # Check enemies
        nearby_enemies = enemy_manager.get_enemies_in_range(x, y, safe_distance)
        if nearby_enemies:
            return False

        # Check visible traps
        trap = trap_manager.get_trap_at(x, y)
        if trap and trap.visible:
            return False

        return True

    def get_nearest_enemy(self, x, y, enemy_manager):
        """
        Get nearest enemy to a position

        Returns:
            (enemy, distance) tuple or (None, float('inf'))
        """
        nearest = None
        min_dist = float('inf')

        for enemy in enemy_manager.enemies:
            dist = abs(enemy.x - x) + abs(enemy.y - y)
            if dist < min_dist:
                min_dist = dist
                nearest = enemy

        return nearest, min_dist

    def get_threats_in_vision(self, player, enemy_manager, trap_manager):
        """
        Get all threats visible to player

        Returns:
            Dictionary with 'enemies' and 'traps' lists
        """
        vision_range = player.stats['vision_range']

        threats = {
            'enemies': [],
            'traps': []
        }

        # Get enemies in vision
        threats['enemies'] = enemy_manager.get_enemies_in_range(
            player.x, player.y, vision_range
        )

        # Get visible traps in vision
        for trap in trap_manager.get_visible_traps():
            dist = abs(trap.x - player.x) + abs(trap.y - player.y)
            if dist <= vision_range:
                threats['traps'].append(trap)

        return threats


# Singleton instance
collision_handler = CollisionHandler()
