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

        # Last known size for detecting resize during drag
        self.last_width = 800
        self.last_height = 600

    def initialize(self):
        """Initialize display manager and get native resolution"""
        # Get native display resolution (pygame must be initialized already)
        info = pygame.display.Info()
        self.native_width = info.current_w
        self.native_height = info.current_h
        self.initialized = True
        self.last_width = self.screen_width
        self.last_height = self.screen_height

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
            self.last_width = width
            self.last_height = height

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

        if new_width == self.screen_width and new_height == self.screen_height:
            return (self.screen_width, self.screen_height)

        # In pygame 2 the display surface is usually resized automatically.
        surface = pygame.display.get_surface()
        if surface is not None and surface.get_size() == (new_width, new_height):
            self.screen = surface
        else:
            self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)
            new_width, new_height = self.screen.get_size()

        self.sync_size(new_width, new_height, surface=self.screen, trigger_callback=True)
        return (new_width, new_height)

    def sync_size(self, width, height, surface=None, trigger_callback=True):
        """
        Synchronize tracked display size with the actual window size.

        Args:
            width: New width
            height: New height
            surface: Optional pygame display surface
            trigger_callback: Whether to fire resize callback when changed

        Returns:
            tuple: (changed, width, height)
        """
        width = max(MIN_WINDOW_WIDTH, width)
        height = max(MIN_WINDOW_HEIGHT, height)

        changed = (width != self.screen_width or height != self.screen_height)

        if surface is not None:
            self.screen = surface
        elif self.screen is None:
            self.screen = pygame.display.get_surface()

        self.screen_width = width
        self.screen_height = height
        self.windowed_width = width
        self.windowed_height = height
        self.last_width = width
        self.last_height = height

        if changed and trigger_callback and self.resize_callback:
            self.resize_callback(width, height)

        return (changed, width, height)

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

    def check_live_resize(self):
        """
        Check if window was resized during drag (real-time resize detection).
        Call this every frame to detect resize while mouse button is held.

        Returns:
            tuple: (changed, new_width, new_height) - changed is True if size changed
        """
        # Skip in fullscreen mode
        if self.mode == DisplayMode.FULLSCREEN:
            return (False, self.screen_width, self.screen_height)

        # Get current actual window size
        surface = pygame.display.get_surface() or self.screen
        if surface:
            self.screen = surface
            current_w, current_h = surface.get_size()

            # Check if size changed
            if current_w != self.last_width or current_h != self.last_height:
                changed, new_width, new_height = self.sync_size(
                    current_w,
                    current_h,
                    surface=surface,
                    trigger_callback=True
                )
                return (changed, new_width, new_height)

        return (False, self.screen_width, self.screen_height)
