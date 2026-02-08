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

    def save_game(self, level, player, game_state, slot_name="autosave",
                  game_mode=0, player_3d=None):
        """
        Save current game state

        Args:
            level: Current Level object
            player: Player object
            game_state: GameStateManager object
            slot_name: Save slot name
            game_mode: 0=2D, 1=3D
            player_3d: Player3D object (3D rejim uchun)

        Returns:
            bool: True if save successful
        """
        try:
            save_data = self._serialize_game_state(
                level, player, game_state, game_mode, player_3d
            )

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

    def _serialize_game_state(self, level, player, game_state,
                              game_mode=0, player_3d=None):
        """
        Serialize game state to dictionary
        """
        data = {
            'level': self._serialize_level(level),
            'player': self._serialize_player(player),
            'game_state': {
                'current_state': game_state.current_state.name,
                'state_data': game_state.state_data
            },
            'game_mode': game_mode,
            'player_3d': self._serialize_player_3d(player_3d),
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
            },
            'moving_walls': self._serialize_moving_walls(level.moving_wall_manager),
            'boss': self._serialize_boss(level.boss_manager),
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

    def _serialize_player_3d(self, player_3d):
        """Serialize Player3D holati"""
        if player_3d is None:
            return None
        return {
            'world_x': player_3d.world_x,
            'world_y': player_3d.world_y,
            'grid_x': player_3d.grid_x,
            'grid_y': player_3d.grid_y,
            'angle': player_3d.angle,
            'pitch': player_3d.pitch,
        }

    def _serialize_moving_walls(self, moving_wall_manager):
        """Serialize moving walls"""
        walls = []
        for wall in moving_wall_manager.walls:
            walls.append({
                'x': wall.x,
                'y': wall.y,
                'start_x': wall.start_x,
                'start_y': wall.start_y,
                'direction': wall.direction,
                'speed': wall.speed,
                'path': wall.path,
                'path_index': wall.path_index,
                'forward': wall.forward,
            })
        return walls

    def _serialize_boss(self, boss_manager):
        """Serialize boss holati"""
        if not boss_manager.active:
            return None

        boss = boss_manager.get_boss()
        if not boss:
            return None

        return {
            'active': boss_manager.active,
            'fight_started': boss_manager.fight_started,
            'boss_defeated': boss_manager.boss_defeated,
            'arena_cells': boss_manager.arena_cells,
            'boss': {
                'x': boss.x,
                'y': boss.y,
                'start_x': boss.start_x,
                'start_y': boss.start_y,
                'health': boss.health,
                'max_health': boss.max_health,
                'phase': boss.phase,
                'state': boss.state,
                'alive': boss.alive,
                'defeated': boss.defeated,
                'rage_mode': boss.rage_mode,
            }
        }

    def restore_game_state(self, save_data, level_manager):
        """
        Restore game state from save data

        Returns:
            tuple: (level, success, extra_data)
            extra_data = {'game_mode': int, 'player_3d': dict or None}
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

            # Grid qayta hisoblash (3D raycasting uchun kerak)
            level._build_grid()

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

            # Restore moving walls
            moving_walls_data = level_data.get('moving_walls', [])
            self._restore_moving_walls(level, moving_walls_data)

            # Restore boss
            boss_data = level_data.get('boss')
            if boss_data:
                self._restore_boss(level, boss_data)

            # Extra data (game_mode, player_3d)
            extra_data = {
                'game_mode': save_data.get('game_mode', 0),
                'player_3d': save_data.get('player_3d'),
            }

            return level, True, extra_data

        except Exception as e:
            print(f"Restore failed: {e}")
            import traceback
            traceback.print_exc()
            return None, False, {}

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

    def _restore_moving_walls(self, level, walls_data):
        """Restore moving walls"""
        from entities.moving_wall import MovingWall
        level.moving_wall_manager.walls.clear()

        for data in walls_data:
            wall = MovingWall(
                data['start_x'], data['start_y'],
                data['direction'], data['speed']
            )
            wall.x = data['x']
            wall.y = data['y']
            wall.path = [tuple(p) if isinstance(p, list) else p for p in data['path']]
            wall.path_index = data['path_index']
            wall.forward = data['forward']
            level.moving_wall_manager.walls.append(wall)

    def _restore_boss(self, level, boss_data):
        """Restore boss holati"""
        from entities.boss import Boss
        boss_info = boss_data['boss']

        boss = Boss(boss_info['x'], boss_info['y'])
        boss.start_x = boss_info['start_x']
        boss.start_y = boss_info['start_y']
        boss.health = boss_info['health']
        boss.max_health = boss_info['max_health']
        boss.phase = boss_info['phase']
        boss.state = boss_info['state']
        boss.alive = boss_info['alive']
        boss.defeated = boss_info['defeated']
        boss.rage_mode = boss_info['rage_mode']

        level.boss_manager.boss = boss
        level.boss_manager.active = boss_data['active']
        level.boss_manager.fight_started = boss_data['fight_started']
        level.boss_manager.boss_defeated = boss_data['boss_defeated']
        level.boss_manager.arena_cells = [
            tuple(c) if isinstance(c, list) else c
            for c in boss_data.get('arena_cells', [])
        ]

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

    def auto_save(self, level, player, game_state, game_mode=0, player_3d=None):
        """
        Auto-save the game
        """
        return self.save_game(level, player, game_state, slot_name="autosave",
                              game_mode=game_mode, player_3d=player_3d)
