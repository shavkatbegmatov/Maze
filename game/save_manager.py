"""
Save/Load System - Saves and loads game state to/from JSON
"""

import json
import os
from pathlib import Path
from datetime import datetime


class SaveManager:
    """
    Manages game save and load operations
    """
    def __init__(self, save_dir="saves"):
        """
        Args:
            save_dir: Directory to store save files
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.current_slot = None

    def save_game(self, level, player, game_state, slot_name="autosave"):
        """
        Save current game state

        Args:
            level: Current Level object
            player: Player object
            game_state: GameStateManager object
            slot_name: Save slot name

        Returns:
            bool: True if save successful
        """
        try:
            save_data = self._serialize_game_state(level, player, game_state)

            # Add metadata
            save_data['metadata'] = {
                'slot_name': slot_name,
                'timestamp': datetime.now().isoformat(),
                'version': '3.0.0'
            }

            # Save to file
            save_path = self.save_dir / f"{slot_name}.json"
            with open(save_path, 'w') as f:
                json.dump(save_data, f, indent=2)

            self.current_slot = slot_name
            return True

        except Exception as e:
            print(f"Save failed: {e}")
            return False

    def load_game(self, slot_name="autosave"):
        """
        Load game state from save file

        Args:
            slot_name: Save slot name

        Returns:
            dict: Save data or None if load failed
        """
        try:
            save_path = self.save_dir / f"{slot_name}.json"

            if not save_path.exists():
                print(f"Save file not found: {save_path}")
                return None

            with open(save_path, 'r') as f:
                save_data = json.load(f)

            return save_data

        except Exception as e:
            print(f"Load failed: {e}")
            return None

    def _serialize_game_state(self, level, player, game_state):
        """
        Serialize game state to dictionary

        Args:
            level: Level object
            player: Player object
            game_state: GameStateManager object

        Returns:
            dict: Serialized game state
        """
        data = {
            'level': self._serialize_level(level),
            'player': self._serialize_player(player),
            'game_state': {
                'current_state': game_state.current_state.name,
                'state_data': game_state.state_data
            }
        }
        return data

    def _serialize_level(self, level):
        """Serialize level data"""
        return {
            'difficulty_level': level.difficulty_level,
            'generator_index': level.generator_index,
            'cols': level.cols,
            'rows': level.rows,
            'walls': level.walls,
            'start_pos': level.start_pos,
            'goal_pos': level.goal_pos,
            'time_elapsed': level.time_elapsed,
            'completed': level.completed,
            'entities': {
                'enemies': self._serialize_enemies(level.enemy_manager),
                'powerups': self._serialize_powerups(level.powerup_manager),
                'traps': self._serialize_traps(level.trap_manager),
                'keys': self._serialize_keys(level.door_manager),
                'doors': self._serialize_doors(level.door_manager),
            }
        }

    def _serialize_player(self, player):
        """Serialize player data"""
        return {
            'x': player.x,
            'y': player.y,
            'prev_x': player.prev_x,
            'prev_y': player.prev_y,
            'inventory': {
                'keys': player.inventory['keys'],
                'powerups_active': []  # Don't save active powerups
            },
            'stats': player.stats,
            'moves': player.moves,
            'damage_taken': player.damage_taken,
            'enemies_dodged': player.enemies_dodged,
            'trail': player.trail[-10:]  # Only save last 10 trail points
        }

    def _serialize_enemies(self, enemy_manager):
        """Serialize enemies"""
        enemies = []
        for enemy in enemy_manager.enemies:
            enemies.append({
                'x': enemy.x,
                'y': enemy.y,
                'start_x': enemy.start_x,
                'start_y': enemy.start_y,
                'type': enemy.type,
                'state': enemy.state
            })
        return enemies

    def _serialize_powerups(self, powerup_manager):
        """Serialize powerups"""
        powerups = []
        for powerup in powerup_manager.powerups:
            powerups.append({
                'x': powerup.x,
                'y': powerup.y,
                'type': powerup.type,
                'duration': powerup.duration,
                'collected': powerup.collected
            })
        return powerups

    def _serialize_traps(self, trap_manager):
        """Serialize traps"""
        traps = []
        for trap in trap_manager.traps:
            traps.append({
                'x': trap.x,
                'y': trap.y,
                'type': trap.type,
                'triggered': trap.triggered,
                'visible': trap.visible
            })
        return traps

    def _serialize_keys(self, door_manager):
        """Serialize keys"""
        keys = []
        for key in door_manager.keys:
            keys.append({
                'x': key.x,
                'y': key.y,
                'color': key.color,
                'collected': key.collected
            })
        return keys

    def _serialize_doors(self, door_manager):
        """Serialize doors"""
        doors = []
        for door in door_manager.doors:
            doors.append({
                'x': door.x,
                'y': door.y,
                'color': door.color,
                'locked': door.locked
            })
        return doors

    def restore_game_state(self, save_data, level_manager):
        """
        Restore game state from save data

        Args:
            save_data: Loaded save data
            level_manager: LevelManager to restore into

        Returns:
            tuple: (level, success)
        """
        try:
            level_data = save_data['level']
            player_data = save_data['player']

            # Create level with saved difficulty
            from game.level_manager import Level
            level = Level(
                level_data['difficulty_level'],
                level_data['generator_index']
            )

            # Restore maze
            level.cols = level_data['cols']
            level.rows = level_data['rows']
            level.walls = level_data['walls']
            level.start_pos = tuple(level_data['start_pos'])
            level.goal_pos = tuple(level_data['goal_pos'])
            level.time_elapsed = level_data['time_elapsed']
            level.completed = level_data['completed']
            level.generation_complete = True

            # Restore player
            from entities.player import Player
            player = Player(player_data['x'], player_data['y'])
            player.prev_x = player_data['prev_x']
            player.prev_y = player_data['prev_y']
            player.inventory = player_data['inventory']
            player.stats = player_data['stats']
            player.moves = player_data['moves']
            player.damage_taken = player_data['damage_taken']
            player.enemies_dodged = player_data['enemies_dodged']
            player.trail = [tuple(pos) for pos in player_data['trail']]

            level.player = player

            # Restore entities
            self._restore_enemies(level, level_data['entities']['enemies'])
            self._restore_powerups(level, level_data['entities']['powerups'])
            self._restore_traps(level, level_data['entities']['traps'])
            self._restore_keys(level, level_data['entities']['keys'])
            self._restore_doors(level, level_data['entities']['doors'])

            return level, True

        except Exception as e:
            print(f"Restore failed: {e}")
            import traceback
            traceback.print_exc()
            return None, False

    def _restore_enemies(self, level, enemies_data):
        """Restore enemies"""
        from entities.enemy import Enemy
        level.enemy_manager.clear()

        for data in enemies_data:
            enemy = Enemy(data['x'], data['y'], data['type'])
            enemy.start_x = data['start_x']
            enemy.start_y = data['start_y']
            enemy.state = data['state']
            level.enemy_manager.enemies.append(enemy)

    def _restore_powerups(self, level, powerups_data):
        """Restore powerups"""
        level.powerup_manager.clear()

        for data in powerups_data:
            powerup = level.powerup_manager.add_powerup(
                data['x'], data['y'], data['type'], data['duration']
            )
            powerup.collected = data['collected']

    def _restore_traps(self, level, traps_data):
        """Restore traps"""
        level.trap_manager.clear()

        for data in traps_data:
            trap = level.trap_manager.add_trap(data['x'], data['y'], data['type'])
            trap.triggered = data['triggered']
            trap.visible = data['visible']

    def _restore_keys(self, level, keys_data):
        """Restore keys"""
        level.door_manager.keys.clear()

        for data in keys_data:
            key = level.door_manager.add_key(data['x'], data['y'], data['color'])
            key.collected = data['collected']

    def _restore_doors(self, level, doors_data):
        """Restore doors"""
        level.door_manager.doors.clear()

        for data in doors_data:
            door = level.door_manager.add_door(data['x'], data['y'], data['color'])
            door.locked = data['locked']

    def get_save_files(self):
        """
        Get list of available save files

        Returns:
            list: List of (slot_name, metadata) tuples
        """
        saves = []

        for save_file in self.save_dir.glob("*.json"):
            try:
                with open(save_file, 'r') as f:
                    data = json.load(f)
                    metadata = data.get('metadata', {})
                    slot_name = save_file.stem
                    saves.append((slot_name, metadata))
            except:
                pass

        return saves

    def delete_save(self, slot_name):
        """
        Delete a save file

        Args:
            slot_name: Save slot name

        Returns:
            bool: True if deleted successfully
        """
        try:
            save_path = self.save_dir / f"{slot_name}.json"
            if save_path.exists():
                save_path.unlink()
                return True
            return False
        except:
            return False

    def auto_save(self, level, player, game_state):
        """
        Auto-save the game

        Args:
            level: Current level
            player: Player object
            game_state: GameStateManager object

        Returns:
            bool: True if save successful
        """
        return self.save_game(level, player, game_state, slot_name="autosave")
