"""
Camera/Viewport System - Handles screen scaling and camera following for large mazes
"""

import pygame


class Camera:
    """
    Manages viewport and camera position for rendering large mazes
    """
    def __init__(self):
        # Screen info
        self.screen_width = 800
        self.screen_height = 600
        self.max_screen_width = 1920
        self.max_screen_height = 1080

        # Maze info
        self.maze_cols = 0
        self.maze_rows = 0

        # Cell size limits
        self.min_cell_size = 12  # Minimum readable cell size
        self.max_cell_size = 50  # Maximum cell size
        self.default_cell_size = 35

        # Calculated values
        self.cell_size = self.default_cell_size
        self.panel_height = 80  # HUD panel

        # Camera position (top-left corner of viewport in maze coordinates)
        self.camera_x = 0.0
        self.camera_y = 0.0

        # Viewport dimensions in cells
        self.viewport_cols = 0
        self.viewport_rows = 0

        # Camera mode
        self.use_camera = False  # If True, maze doesn't fit on screen
        self.camera_smoothing = 8.0  # Camera follow smoothness

        # Screen margins
        self.screen_margin = 50  # Margin from screen edges

    def get_display_info(self):
        """Get the current display resolution"""
        pygame.display.init()
        info = pygame.display.Info()
        return info.current_w, info.current_h

    def calculate_optimal_settings(self, maze_cols, maze_rows, panel_height=80):
        """
        Calculate optimal cell size and screen dimensions for the maze

        Args:
            maze_cols: Number of maze columns
            maze_rows: Number of maze rows
            panel_height: Height of HUD panel

        Returns:
            tuple: (screen_width, screen_height, cell_size, use_camera)
        """
        self.maze_cols = maze_cols
        self.maze_rows = maze_rows
        self.panel_height = panel_height

        # Get actual screen resolution
        display_w, display_h = self.get_display_info()

        # Be conservative with available space
        # Account for window decorations, taskbar, and extra margins
        # Use at most 85% of screen to ensure it fits comfortably
        available_w = int(display_w * 0.85) - self.screen_margin
        available_h = int(display_h * 0.85) - self.screen_margin - 80  # Extra for taskbar

        # Maximum window size limits
        max_window_w = min(available_w, 1400)
        max_window_h = min(available_h, 900)

        # Calculate maximum cell size that would fit the entire maze
        max_cell_for_width = max_window_w / maze_cols
        max_cell_for_height = (max_window_h - panel_height) / maze_rows

        # Use the smaller of the two to ensure both dimensions fit
        optimal_cell_size = min(max_cell_for_width, max_cell_for_height)

        # Clamp to our limits
        optimal_cell_size = max(self.min_cell_size, min(self.max_cell_size, optimal_cell_size))

        # Round down to integer
        self.cell_size = int(optimal_cell_size)

        # Calculate resulting screen dimensions
        maze_width = maze_cols * self.cell_size
        maze_height = maze_rows * self.cell_size

        # Check if we need camera mode
        # Use camera if:
        # 1. Maze is too big even with minimum cell size
        # 2. Window would be larger than our max limits
        # 3. Cell size would be too small for comfortable play (< 20)
        preferred_min_cell = 20  # Minimum comfortable cell size
        needs_camera = (
            (maze_cols * self.min_cell_size > max_window_w) or
            (maze_rows * self.min_cell_size > max_window_h - panel_height) or
            (maze_width > max_window_w) or
            (maze_height > max_window_h - panel_height) or
            (self.cell_size < preferred_min_cell)  # Cell too small, use camera instead
        )

        if needs_camera:
            self.use_camera = True

            # In camera mode, use a comfortable cell size
            self.cell_size = max(20, min(30, self.cell_size))

            # Set screen to max window size
            self.screen_width = max_window_w
            self.screen_height = max_window_h

            # Calculate viewport size in cells
            self.viewport_cols = self.screen_width // self.cell_size
            self.viewport_rows = (self.screen_height - panel_height) // self.cell_size
        else:
            self.use_camera = False
            self.screen_width = maze_width
            self.screen_height = maze_height + panel_height
            self.viewport_cols = maze_cols
            self.viewport_rows = maze_rows

        # Ensure minimum window size
        self.screen_width = max(600, self.screen_width)
        self.screen_height = max(500, self.screen_height)

        return (self.screen_width, self.screen_height, self.cell_size, self.use_camera)

    def update(self, dt, player_x, player_y):
        """
        Update camera position to follow player

        Args:
            dt: Delta time
            player_x: Player X position in cells
            player_y: Player Y position in cells
        """
        if not self.use_camera:
            self.camera_x = 0
            self.camera_y = 0
            return

        # Target camera position (center player in viewport)
        target_x = player_x - self.viewport_cols / 2
        target_y = player_y - self.viewport_rows / 2

        # Clamp to maze bounds
        target_x = max(0, min(self.maze_cols - self.viewport_cols, target_x))
        target_y = max(0, min(self.maze_rows - self.viewport_rows, target_y))

        # Smooth camera movement
        self.camera_x += (target_x - self.camera_x) * self.camera_smoothing * dt
        self.camera_y += (target_y - self.camera_y) * self.camera_smoothing * dt

        # Final clamp
        self.camera_x = max(0, min(self.maze_cols - self.viewport_cols, self.camera_x))
        self.camera_y = max(0, min(self.maze_rows - self.viewport_rows, self.camera_y))

    def world_to_screen(self, world_x, world_y):
        """
        Convert world (maze cell) coordinates to screen coordinates

        Args:
            world_x: X position in cells
            world_y: Y position in cells

        Returns:
            tuple: (screen_x, screen_y) in pixels
        """
        screen_x = (world_x - self.camera_x) * self.cell_size
        screen_y = (world_y - self.camera_y) * self.cell_size
        return screen_x, screen_y

    def screen_to_world(self, screen_x, screen_y):
        """
        Convert screen coordinates to world (maze cell) coordinates

        Args:
            screen_x: X position in pixels
            screen_y: Y position in pixels

        Returns:
            tuple: (world_x, world_y) in cells
        """
        world_x = screen_x / self.cell_size + self.camera_x
        world_y = screen_y / self.cell_size + self.camera_y
        return world_x, world_y

    def is_visible(self, world_x, world_y, margin=1):
        """
        Check if a world position is visible in the current viewport

        Args:
            world_x: X position in cells
            world_y: Y position in cells
            margin: Extra cells to include around viewport

        Returns:
            bool: True if visible
        """
        if not self.use_camera:
            return True

        left = self.camera_x - margin
        right = self.camera_x + self.viewport_cols + margin
        top = self.camera_y - margin
        bottom = self.camera_y + self.viewport_rows + margin

        return left <= world_x < right and top <= world_y < bottom

    def get_visible_range(self):
        """
        Get the range of visible cells

        Returns:
            tuple: (min_x, max_x, min_y, max_y) in cells
        """
        if not self.use_camera:
            return (0, self.maze_cols, 0, self.maze_rows)

        min_x = max(0, int(self.camera_x) - 1)
        max_x = min(self.maze_cols, int(self.camera_x + self.viewport_cols) + 2)
        min_y = max(0, int(self.camera_y) - 1)
        max_y = min(self.maze_rows, int(self.camera_y + self.viewport_rows) + 2)

        return (min_x, max_x, min_y, max_y)

    def get_maze_area_height(self):
        """Get the height of the maze rendering area in pixels"""
        if self.use_camera:
            return self.screen_height - self.panel_height
        return self.maze_rows * self.cell_size

    def reset(self):
        """Reset camera to origin"""
        self.camera_x = 0
        self.camera_y = 0


class CameraManager:
    """
    High-level manager for camera operations
    """
    def __init__(self):
        self.camera = Camera()
        self.initialized = False

    def setup_for_level(self, maze_cols, maze_rows, panel_height=80):
        """
        Setup camera for a new level

        Args:
            maze_cols: Number of maze columns
            maze_rows: Number of maze rows
            panel_height: Height of HUD panel

        Returns:
            tuple: (screen_width, screen_height, cell_size, use_camera)
        """
        result = self.camera.calculate_optimal_settings(maze_cols, maze_rows, panel_height)
        self.initialized = True
        return result

    def update(self, dt, player):
        """
        Update camera to follow player

        Args:
            dt: Delta time
            player: Player object with x, y attributes
        """
        if self.initialized and player:
            self.camera.update(dt, player.x, player.y)

    def get_cell_size(self):
        """Get current cell size"""
        return self.camera.cell_size

    def world_to_screen(self, x, y):
        """Convert world to screen coordinates"""
        return self.camera.world_to_screen(x, y)

    def is_visible(self, x, y):
        """Check if position is visible"""
        return self.camera.is_visible(x, y)

    def get_visible_range(self):
        """Get visible cell range"""
        return self.camera.get_visible_range()

    def uses_camera(self):
        """Check if camera mode is active"""
        return self.camera.use_camera

    def get_screen_size(self):
        """Get calculated screen size"""
        return (self.camera.screen_width, self.camera.screen_height)

    def get_maze_area_height(self):
        """Get maze rendering area height"""
        return self.camera.get_maze_area_height()

    def reset(self):
        """Reset camera position"""
        self.camera.reset()
