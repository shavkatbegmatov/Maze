"""
Game State Machine - manages different game states and transitions
"""

from enum import Enum, auto


class GameState(Enum):
    """Game states"""
    MENU = auto()
    DIFFICULTY_SELECT = auto()
    GENERATING = auto()
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_COMPLETE = auto()
    GAME_OVER = auto()
    WIN = auto()


class GameStateManager:
    """
    Manages game state transitions and flow
    """
    def __init__(self):
        self.current_state = GameState.MENU
        self.previous_state = None
        self.state_data = {}  # For passing data between states

    def transition_to(self, new_state, **kwargs):
        """
        Transition to a new state

        Args:
            new_state: GameState enum value
            **kwargs: Additional data to pass to new state
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_data = kwargs

        # State entry callbacks
        self._on_state_enter(new_state)

    def _on_state_enter(self, state):
        """Called when entering a new state"""
        if state == GameState.MENU:
            self._enter_menu()
        elif state == GameState.DIFFICULTY_SELECT:
            self._enter_difficulty_select()
        elif state == GameState.GENERATING:
            self._enter_generating()
        elif state == GameState.PLAYING:
            self._enter_playing()
        elif state == GameState.PAUSED:
            self._enter_paused()
        elif state == GameState.LEVEL_COMPLETE:
            self._enter_level_complete()
        elif state == GameState.GAME_OVER:
            self._enter_game_over()
        elif state == GameState.WIN:
            self._enter_win()

    def _enter_menu(self):
        """Enter menu state"""
        pass

    def _enter_difficulty_select(self):
        """Enter difficulty selection state"""
        pass

    def _enter_generating(self):
        """Enter maze generation state"""
        pass

    def _enter_playing(self):
        """Enter playing state"""
        pass

    def _enter_paused(self):
        """Enter paused state"""
        pass

    def _enter_level_complete(self):
        """Enter level complete state"""
        # Calculate score
        if 'level' in self.state_data and 'player' in self.state_data:
            level = self.state_data['level']
            player = self.state_data['player']
            score = self._calculate_score(level, player)
            self.state_data['score'] = score

    def _enter_game_over(self):
        """Enter game over state"""
        pass

    def _enter_win(self):
        """Enter win state"""
        pass

    def _calculate_score(self, level, player):
        """
        Calculate player score

        Score formula:
        - Base: 1000 × difficulty_multiplier
        - Time bonus: time_remaining × 10
        - Health bonus: health × 5
        - No damage bonus: +500 if no damage taken
        - Penalty: deaths × 200
        """
        from utils.constants import SCORE_BASE_MULTIPLIER, SCORE_TIME_BONUS, SCORE_HEALTH_BONUS, SCORE_NO_DAMAGE_BONUS

        score = 0

        # Base score
        score += SCORE_BASE_MULTIPLIER * level.config.score_multiplier

        # Time bonus
        if level.time_limit:
            time_remaining = level.get_time_remaining()
            score += time_remaining * SCORE_TIME_BONUS

        # Health bonus
        score += player.stats['health'] * SCORE_HEALTH_BONUS

        # No damage bonus
        if player.damage_taken == 0:
            score += SCORE_NO_DAMAGE_BONUS

        # Enemy dodge bonus
        score += player.enemies_dodged * 50

        return int(score)

    def is_state(self, state):
        """Check if current state matches"""
        return self.current_state == state

    def can_pause(self):
        """Check if game can be paused"""
        return self.current_state == GameState.PLAYING

    def can_resume(self):
        """Check if game can be resumed"""
        return self.current_state == GameState.PAUSED

    def get_state_name(self):
        """Get current state name"""
        return self.current_state.name

    def __repr__(self):
        return f"GameStateManager(state={self.current_state.name})"


class GameFlow:
    """
    High-level game flow controller
    Works with GameStateManager and LevelManager
    """
    def __init__(self, level_manager, state_manager):
        """
        Args:
            level_manager: LevelManager instance
            state_manager: GameStateManager instance
        """
        self.level_manager = level_manager
        self.state_manager = state_manager

        # Settings
        self.selected_difficulty = 0
        self.selected_generator = 0
        self.animated_generation = True

    def start_new_game(self, difficulty, generator_index=0, animated=True):
        """
        Start a new game

        Args:
            difficulty: Difficulty level (0-4)
            generator_index: Maze generator algorithm index
            animated: Use animated generation
        """
        self.selected_difficulty = difficulty
        self.selected_generator = generator_index
        self.animated_generation = animated

        # Transition to generating state
        self.state_manager.transition_to(GameState.GENERATING)

        # Create level
        if animated:
            level, generator = self.level_manager.create_level(
                difficulty, generator_index, animated=True
            )
            return level, generator
        else:
            level = self.level_manager.create_level(
                difficulty, generator_index, animated=False
            )
            # Skip to playing
            self.state_manager.transition_to(GameState.PLAYING)
            return level, None

    def generation_complete(self):
        """Called when maze generation completes"""
        self.state_manager.transition_to(GameState.PLAYING)

    def pause_game(self):
        """Pause the game"""
        if self.state_manager.can_pause():
            self.state_manager.transition_to(GameState.PAUSED)
            return True
        return False

    def resume_game(self):
        """Resume the game"""
        if self.state_manager.can_resume():
            self.state_manager.transition_to(GameState.PLAYING)
            return True
        return False

    def level_completed(self, level, player):
        """Called when level is completed"""
        self.state_manager.transition_to(
            GameState.LEVEL_COMPLETE,
            level=level,
            player=player
        )

    def game_over(self, reason='died'):
        """Called when game is over"""
        self.state_manager.transition_to(
            GameState.GAME_OVER,
            reason=reason
        )

    def player_won(self, level, player):
        """Called when player wins"""
        self.state_manager.transition_to(
            GameState.WIN,
            level=level,
            player=player
        )

    def return_to_menu(self):
        """Return to main menu"""
        self.state_manager.transition_to(GameState.MENU)

    def retry_level(self):
        """Retry current level"""
        level = self.level_manager.get_current_level()
        if level:
            level.reset()
            self.state_manager.transition_to(GameState.PLAYING)

    def next_level(self):
        """Progress to next difficulty level"""
        # For now, just return to menu
        # In full version, this would advance to next level
        self.return_to_menu()

    def update(self, dt):
        """
        Update game flow

        Args:
            dt: Delta time in seconds

        Returns:
            State change information or None
        """
        if self.state_manager.is_state(GameState.PLAYING):
            # Update level
            result = self.level_manager.update_current_level(dt)

            if result == 'complete':
                level = self.level_manager.get_current_level()
                self.level_completed(level, level.player)
                return {'event': 'level_complete'}

            elif result == 'game_over':
                self.game_over('died')
                return {'event': 'game_over', 'reason': 'died'}

            elif result == 'time_up':
                self.game_over('time_up')
                return {'event': 'game_over', 'reason': 'time_up'}

        return None

    def __repr__(self):
        return f"GameFlow(state={self.state_manager.get_state_name()}, difficulty={self.selected_difficulty})"
