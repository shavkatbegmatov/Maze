"""
Procedural Texture Generation for 3D Maze
Generates brick and stone textures without external files
"""

import pygame
import random
import math


class TextureManager:
    """
    Manages procedural texture generation and caching
    """

    def __init__(self, texture_size=64):
        """
        Initialize texture manager

        Args:
            texture_size: Size of textures (width and height)
        """
        self.texture_size = texture_size
        self._cache = {}
        self._seed = 42  # For reproducible textures

    def get_texture(self, texture_type, base_color=None):
        """
        Get or generate a texture

        Args:
            texture_type: 'brick', 'stone', 'metal', 'wood'
            base_color: Base color tuple (R, G, B), or None for default

        Returns:
            pygame.Surface with the texture
        """
        cache_key = (texture_type, base_color, self.texture_size)

        if cache_key not in self._cache:
            if texture_type == 'brick':
                self._cache[cache_key] = self._generate_brick(base_color)
            elif texture_type == 'stone':
                self._cache[cache_key] = self._generate_stone(base_color)
            elif texture_type == 'metal':
                self._cache[cache_key] = self._generate_metal(base_color)
            elif texture_type == 'wood':
                self._cache[cache_key] = self._generate_wood(base_color)
            else:
                # Default solid color
                self._cache[cache_key] = self._generate_solid(base_color or (128, 128, 128))

        return self._cache[cache_key]

    def _generate_brick(self, base_color=None):
        """
        Generate brick texture

        Args:
            base_color: Base brick color, default reddish-brown

        Returns:
            pygame.Surface
        """
        if base_color is None:
            base_color = (140, 80, 60)

        size = self.texture_size
        surface = pygame.Surface((size, size))

        # Mortar color (darker)
        mortar_color = (60, 55, 50)

        # Fill with mortar
        surface.fill(mortar_color)

        # Brick dimensions
        brick_w = size // 4
        brick_h = size // 8
        mortar_gap = 2

        random.seed(self._seed)

        # Draw bricks
        for row in range(size // brick_h + 1):
            # Offset every other row
            offset = (brick_w // 2) if row % 2 == 1 else 0

            for col in range(-1, size // brick_w + 2):
                x = col * brick_w + offset
                y = row * brick_h

                # Skip if completely out of bounds
                if x + brick_w < 0 or x >= size:
                    continue
                if y + brick_h < 0 or y >= size:
                    continue

                # Vary brick color slightly
                r = max(0, min(255, base_color[0] + random.randint(-20, 20)))
                g = max(0, min(255, base_color[1] + random.randint(-15, 15)))
                b = max(0, min(255, base_color[2] + random.randint(-15, 15)))
                brick_color = (r, g, b)

                # Draw brick with gap for mortar
                rect = pygame.Rect(
                    x + mortar_gap // 2,
                    y + mortar_gap // 2,
                    brick_w - mortar_gap,
                    brick_h - mortar_gap
                )

                # Clip to surface
                rect = rect.clip(pygame.Rect(0, 0, size, size))
                if rect.width > 0 and rect.height > 0:
                    pygame.draw.rect(surface, brick_color, rect)

                    # Add some noise for texture
                    for _ in range(brick_w * brick_h // 20):
                        px = x + mortar_gap + random.randint(0, max(1, brick_w - mortar_gap * 2 - 1))
                        py = y + mortar_gap + random.randint(0, max(1, brick_h - mortar_gap * 2 - 1))
                        if 0 <= px < size and 0 <= py < size:
                            noise = random.randint(-30, 30)
                            nr = max(0, min(255, r + noise))
                            ng = max(0, min(255, g + noise))
                            nb = max(0, min(255, b + noise))
                            surface.set_at((px, py), (nr, ng, nb))

        return surface

    def _generate_stone(self, base_color=None):
        """
        Generate stone/cobble texture

        Args:
            base_color: Base stone color, default gray

        Returns:
            pygame.Surface
        """
        if base_color is None:
            base_color = (100, 100, 110)

        size = self.texture_size
        surface = pygame.Surface((size, size))

        # Fill with base
        surface.fill(base_color)

        random.seed(self._seed + 1)

        # Generate irregular stone pattern
        num_stones = 8
        stone_centers = []

        # Generate stone centers using Voronoi-like pattern
        for _ in range(num_stones):
            cx = random.randint(0, size - 1)
            cy = random.randint(0, size - 1)
            # Vary color
            r = max(0, min(255, base_color[0] + random.randint(-30, 30)))
            g = max(0, min(255, base_color[1] + random.randint(-30, 30)))
            b = max(0, min(255, base_color[2] + random.randint(-30, 30)))
            stone_centers.append((cx, cy, (r, g, b)))

        # Color each pixel based on nearest stone center
        for y in range(size):
            for x in range(size):
                min_dist = float('inf')
                nearest_color = base_color

                for cx, cy, color in stone_centers:
                    # Wrap-around distance for seamless tiling
                    dx = min(abs(x - cx), size - abs(x - cx))
                    dy = min(abs(y - cy), size - abs(y - cy))
                    dist = dx * dx + dy * dy

                    if dist < min_dist:
                        min_dist = dist
                        nearest_color = color

                # Add noise
                noise = random.randint(-10, 10)
                r = max(0, min(255, nearest_color[0] + noise))
                g = max(0, min(255, nearest_color[1] + noise))
                b = max(0, min(255, nearest_color[2] + noise))

                surface.set_at((x, y), (r, g, b))

        # Draw cracks/edges between stones
        gap_color = (50, 50, 55)
        for y in range(size):
            for x in range(size):
                # Check if this is an edge pixel
                distances = []
                for cx, cy, _ in stone_centers:
                    dx = min(abs(x - cx), size - abs(x - cx))
                    dy = min(abs(y - cy), size - abs(y - cy))
                    distances.append(dx * dx + dy * dy)

                distances.sort()
                if len(distances) >= 2:
                    # If close to boundary between two stones
                    if distances[1] - distances[0] < 50:
                        # Darken this pixel (crack)
                        current = surface.get_at((x, y))
                        r = max(0, current[0] - 40)
                        g = max(0, current[1] - 40)
                        b = max(0, current[2] - 40)
                        surface.set_at((x, y), (r, g, b))

        return surface

    def _generate_metal(self, base_color=None):
        """
        Generate metal/steel texture

        Args:
            base_color: Base metal color, default blue-gray

        Returns:
            pygame.Surface
        """
        if base_color is None:
            base_color = (80, 85, 100)

        size = self.texture_size
        surface = pygame.Surface((size, size))
        surface.fill(base_color)

        random.seed(self._seed + 2)

        # Add horizontal streaks (brushed metal effect)
        for y in range(size):
            streak_intensity = random.randint(-15, 15)
            for x in range(size):
                noise = random.randint(-5, 5) + streak_intensity
                r = max(0, min(255, base_color[0] + noise))
                g = max(0, min(255, base_color[1] + noise))
                b = max(0, min(255, base_color[2] + noise))
                surface.set_at((x, y), (r, g, b))

        # Add some rivets
        rivet_color = (60, 65, 80)
        rivet_positions = [
            (size // 8, size // 8),
            (size * 7 // 8, size // 8),
            (size // 8, size * 7 // 8),
            (size * 7 // 8, size * 7 // 8),
        ]

        for rx, ry in rivet_positions:
            pygame.draw.circle(surface, rivet_color, (rx, ry), 3)
            # Highlight
            pygame.draw.circle(surface, (100, 105, 120), (rx - 1, ry - 1), 1)

        return surface

    def _generate_wood(self, base_color=None):
        """
        Generate wood texture

        Args:
            base_color: Base wood color, default brown

        Returns:
            pygame.Surface
        """
        if base_color is None:
            base_color = (120, 80, 50)

        size = self.texture_size
        surface = pygame.Surface((size, size))
        surface.fill(base_color)

        random.seed(self._seed + 3)

        # Generate wood grain
        for y in range(size):
            # Wood rings
            ring_offset = math.sin(y * 0.3) * 10

            for x in range(size):
                # Grain pattern
                grain = math.sin((x + ring_offset) * 0.5) * 15
                noise = random.randint(-8, 8)

                r = max(0, min(255, base_color[0] + int(grain) + noise))
                g = max(0, min(255, base_color[1] + int(grain * 0.7) + noise))
                b = max(0, min(255, base_color[2] + int(grain * 0.5) + noise))

                surface.set_at((x, y), (r, g, b))

        # Add some knots
        num_knots = random.randint(0, 2)
        for _ in range(num_knots):
            kx = random.randint(size // 4, size * 3 // 4)
            ky = random.randint(size // 4, size * 3 // 4)
            kr = random.randint(3, 6)

            knot_color = (base_color[0] - 30, base_color[1] - 25, base_color[2] - 15)
            pygame.draw.circle(surface, knot_color, (kx, ky), kr)

        return surface

    def _generate_solid(self, color):
        """Generate solid color texture"""
        surface = pygame.Surface((self.texture_size, self.texture_size))
        surface.fill(color)
        return surface

    def get_wall_textures(self):
        """
        Get a set of wall textures for different wall directions

        Returns:
            dict with 'ns' (north/south) and 'ew' (east/west) textures
        """
        return {
            'ns': self.get_texture('brick', (140, 80, 60)),  # Brighter brick for N/S
            'ew': self.get_texture('stone', (90, 90, 100)),  # Darker stone for E/W
        }

    def get_darken_texture(self, texture, factor=0.7):
        """
        Create a darkened version of a texture (for shading)

        Args:
            texture: Source pygame.Surface
            factor: Darkening factor (0.0 = black, 1.0 = original)

        Returns:
            Darkened pygame.Surface
        """
        cache_key = (id(texture), factor, 'darkened')

        if cache_key not in self._cache:
            darkened = texture.copy()
            dark_surface = pygame.Surface(texture.get_size())
            dark_surface.fill((0, 0, 0))
            dark_surface.set_alpha(int(255 * (1 - factor)))
            darkened.blit(dark_surface, (0, 0))
            self._cache[cache_key] = darkened

        return self._cache[cache_key]

    def clear_cache(self):
        """Clear texture cache"""
        self._cache.clear()
