"""
Display Manager - Handles fullscreen, windowed mode and window resizing
"""

import pygame
from utils.constants import DisplayMode, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT


class DisplayManager:
    """
    Manages display modes (fullscreen/windowed) and window resizing
    """
    def __init__(self):
        # Current display mode
        self.mode = DisplayMode.WINDOWED

        # Screen dimensions
        self.screen_width = 800
        self.screen_height = 600

        # Store windowed size for restoring from fullscreen
        self.windowed_width = 800
        self.windowed_height = 600

        # Native display resolution
        self.native_width = 1920
        self.native_height = 1080

        # Pygame screen surface
        self.screen = None

        # Callback for resize events
        self.resize_callback = None

        # Initialized flag
        self.initialized = False

    def initialize(self):
        """Initialize display manager and get native resolution"""
        if not pygame.display.get_init():
            pygame.display.init()

        # Get native display resolution
        info = pygame.display.Info()
        self.native_width = info.current_w
        self.native_height = info.current_h

        self.initialized = True

    def set_resize_callback(self, callback):
        """
        Set callback function for resize events

        Args:
            callback: Function(new_width, new_height) to call on resize
        """
        self.resize_callback = callback

    def create_screen(self, width, height, mode=None, title=None):
        """
        Create or recreate the display screen

        Args:
            width: Screen width
            height: Screen height
            mode: DisplayMode (optional, uses current mode if not specified)
            title: Window title (optional)

        Returns:
            pygame.Surface: The screen surface
        """
        if mode is not None:
            self.mode = mode

        # Clamp minimum size
        width = max(MIN_WINDOW_WIDTH, width)
        height = max(MIN_WINDOW_HEIGHT, height)

        if self.mode == DisplayMode.FULLSCREEN:
            # Use native resolution for fullscreen
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
            self.screen = pygame.display.set_mode(
                (self.native_width, self.native_height),
                flags
            )
            self.screen_width = self.native_width
            self.screen_height = self.native_height
        else:
            # Windowed mode with resize support
            flags = pygame.RESIZABLE
            self.screen = pygame.display.set_mode((width, height), flags)
            self.screen_width = width
            self.screen_height = height

            # Store windowed size
            self.windowed_width = width
            self.windowed_height = height

        if title:
            pygame.display.set_caption(title)

        return self.screen

    def toggle_fullscreen(self):
        """
        Toggle between fullscreen and windowed mode

        Returns:
            tuple: (new_width, new_height) after toggle
        """
        if self.mode == DisplayMode.FULLSCREEN:
            # Switch to windowed
            self.mode = DisplayMode.WINDOWED
            self.screen = self.create_screen(
                self.windowed_width,
                self.windowed_height,
                DisplayMode.WINDOWED
            )
        else:
            # Switch to fullscreen
            self.mode = DisplayMode.FULLSCREEN
            self.screen = self.create_screen(
                self.native_width,
                self.native_height,
                DisplayMode.FULLSCREEN
            )

        # Call resize callback
        if self.resize_callback:
            self.resize_callback(self.screen_width, self.screen_height)

        return (self.screen_width, self.screen_height)

    def handle_resize(self, event_w, event_h):
        """
        Handle VIDEORESIZE event

        Args:
            event_w: New window width from event
            event_h: New window height from event

        Returns:
            tuple: (new_width, new_height) after resize
        """
        # Ignore resize events in fullscreen mode
        if self.mode == DisplayMode.FULLSCREEN:
            return (self.screen_width, self.screen_height)

        # Clamp to minimum size
        new_width = max(MIN_WINDOW_WIDTH, event_w)
        new_height = max(MIN_WINDOW_HEIGHT, event_h)

        # Recreate screen with new size
        self.screen = pygame.display.set_mode(
            (new_width, new_height),
            pygame.RESIZABLE
        )

        self.screen_width = new_width
        self.screen_height = new_height
        self.windowed_width = new_width
        self.windowed_height = new_height

        # Call resize callback
        if self.resize_callback:
            self.resize_callback(new_width, new_height)

        return (new_width, new_height)

    def get_screen(self):
        """Get current screen surface"""
        return self.screen

    def get_size(self):
        """Get current screen size"""
        return (self.screen_width, self.screen_height)

    def is_fullscreen(self):
        """Check if currently in fullscreen mode"""
        return self.mode == DisplayMode.FULLSCREEN

    def get_mode(self):
        """Get current display mode"""
        return self.mode
