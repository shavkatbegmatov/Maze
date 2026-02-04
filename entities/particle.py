"""
Particle Effects System
Creates visual effects for various game events
"""

import pygame
import random
import math
from utils.constants import CELL_SIZE
from utils.colors import (
    COLOR_PARTICLE_PLAYER, COLOR_PARTICLE_ENEMY, COLOR_PARTICLE_POWERUP,
    COLOR_PARTICLE_EXPLOSION
)


class Particle:
    """
    Single particle
    """
    def __init__(self, x, y, vx, vy, color, size, lifetime):
        """
        Args:
            x, y: Starting position (pixels)
            vx, vy: Velocity
            color: RGB color
            size: Particle size
            lifetime: How long particle lives (seconds)
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.gravity = 0  # Optional gravity
        self.fade = True  # Fade out over time
        self.alive = True

    def update(self, dt):
        """Update particle"""
        if not self.alive:
            return

        # Update position
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60

        # Apply gravity
        if self.gravity != 0:
            self.vy += self.gravity * dt * 60

        # Update lifetime
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def render(self, screen):
        """Render particle"""
        if not self.alive:
            return

        # Calculate alpha based on lifetime
        if self.fade:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
        else:
            alpha = 255

        alpha = max(0, min(255, alpha))

        # Color with alpha
        if len(self.color) == 3:
            color = (*self.color, alpha)
        else:
            color = (*self.color[:3], alpha)

        # Draw particle
        try:
            # Create temporary surface for alpha blending
            surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (int(self.size), int(self.size)), int(self.size))
            screen.blit(surf, (int(self.x - self.size), int(self.y - self.size)))
        except:
            pass  # Skip if off screen


class ParticleSystem:
    """
    Manages all particles
    """
    def __init__(self):
        self.particles = []

    def add_particle(self, particle):
        """Add a particle"""
        self.particles.append(particle)

    def update(self, dt):
        """Update all particles"""
        for particle in self.particles[:]:
            particle.update(dt)
            if not particle.alive:
                self.particles.remove(particle)

    def render(self, screen):
        """Render all particles"""
        for particle in self.particles:
            particle.render(screen)

    def clear(self):
        """Remove all particles"""
        self.particles.clear()

    def __len__(self):
        return len(self.particles)


class ParticleEffects:
    """
    Helper class to create common particle effects
    """
    def __init__(self, particle_system):
        """
        Args:
            particle_system: ParticleSystem instance
        """
        self.system = particle_system

    def player_trail(self, x, y):
        """
        Create trail effect behind player

        Args:
            x, y: Grid position
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Small trail particles
        for _ in range(2):
            offset_x = random.uniform(-CELL_SIZE // 4, CELL_SIZE // 4)
            offset_y = random.uniform(-CELL_SIZE // 4, CELL_SIZE // 4)

            particle = Particle(
                cx + offset_x, cy + offset_y,
                random.uniform(-0.5, 0.5),
                random.uniform(-0.5, 0.5),
                COLOR_PARTICLE_PLAYER,
                random.uniform(2, 4),
                random.uniform(0.3, 0.6)
            )
            self.system.add_particle(particle)

    def collection_burst(self, x, y, color, count=15):
        """
        Burst effect when collecting items

        Args:
            x, y: Grid position
            color: Particle color
            count: Number of particles
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        for _ in range(count):
            # Random direction
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                cx, cy,
                vx, vy,
                color,
                random.uniform(3, 6),
                random.uniform(0.5, 1.0)
            )
            particle.gravity = 0.2
            self.system.add_particle(particle)

    def powerup_collection(self, x, y, powerup_type):
        """
        Effect when collecting power-up

        Args:
            x, y: Grid position
            powerup_type: Type of power-up
        """
        # Get color based on power-up type
        from utils.colors import (
            COLOR_POWERUP_SPEED, COLOR_POWERUP_VISION,
            COLOR_POWERUP_INVINCIBLE, COLOR_POWERUP_TELEPORT,
            COLOR_POWERUP_ENERGY, COLOR_POWERUP_XRAY
        )

        color_map = {
            'speed': COLOR_POWERUP_SPEED,
            'vision': COLOR_POWERUP_VISION,
            'invincible': COLOR_POWERUP_INVINCIBLE,
            'teleport': COLOR_POWERUP_TELEPORT,
            'energy': COLOR_POWERUP_ENERGY,
            'xray': COLOR_POWERUP_XRAY,
        }

        color = color_map.get(powerup_type, COLOR_PARTICLE_POWERUP)
        self.collection_burst(x, y, color, count=20)

    def key_collection(self, x, y, key_color):
        """
        Sparkle effect when collecting key

        Args:
            x, y: Grid position
            key_color: RGB color of key
        """
        self.collection_burst(x, y, key_color, count=25)
        self.sparkle_ring(x, y, key_color)

    def door_unlock(self, x, y, door_color):
        """
        Effect when unlocking door

        Args:
            x, y: Grid position
            door_color: RGB color of door
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Expanding ring
        for i in range(12):
            angle = (i / 12) * 2 * math.pi
            speed = 3

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                cx, cy,
                vx, vy,
                door_color,
                5,
                0.8
            )
            self.system.add_particle(particle)

    def trap_trigger(self, x, y, trap_type):
        """
        Effect when trap is triggered

        Args:
            x, y: Grid position
            trap_type: Type of trap
        """
        from utils.colors import (
            COLOR_TRAP_SPIKE, COLOR_TRAP_SLOW,
            COLOR_TRAP_CONFUSION, COLOR_TRAP_POISON
        )

        color_map = {
            'spike': COLOR_TRAP_SPIKE,
            'slow': COLOR_TRAP_SLOW,
            'confusion': COLOR_TRAP_CONFUSION,
            'poison': COLOR_TRAP_POISON,
        }

        color = color_map.get(trap_type, (255, 100, 100))

        if trap_type == 'spike':
            # Sharp burst upward
            self.spike_burst(x, y, color)
        elif trap_type == 'poison':
            # Green cloud
            self.poison_cloud(x, y, color)
        else:
            self.collection_burst(x, y, color, count=12)

    def spike_burst(self, x, y, color):
        """Spike trap effect"""
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        for _ in range(15):
            angle = random.uniform(-math.pi/3, -2*math.pi/3)  # Upward
            speed = random.uniform(3, 6)

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                cx, cy,
                vx, vy,
                color,
                random.uniform(2, 5),
                random.uniform(0.4, 0.8)
            )
            particle.gravity = 0.3
            self.system.add_particle(particle)

    def poison_cloud(self, x, y, color):
        """Poison cloud effect"""
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        for _ in range(25):
            offset_x = random.uniform(-CELL_SIZE // 2, CELL_SIZE // 2)
            offset_y = random.uniform(-CELL_SIZE // 2, CELL_SIZE // 2)

            particle = Particle(
                cx + offset_x, cy + offset_y,
                random.uniform(-0.5, 0.5),
                random.uniform(-1.0, 0.5),
                color,
                random.uniform(4, 8),
                random.uniform(1.0, 2.0)
            )
            particle.gravity = -0.1  # Float upward
            self.system.add_particle(particle)

    def enemy_damage(self, x, y):
        """
        Effect when enemy takes damage or is defeated

        Args:
            x, y: Grid position
        """
        self.collection_burst(x, y, COLOR_PARTICLE_ENEMY, count=10)

    def player_damage(self, x, y):
        """
        Effect when player takes damage

        Args:
            x, y: Grid position
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Red burst
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 7)

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                cx, cy,
                vx, vy,
                (255, 50, 50),
                random.uniform(3, 7),
                random.uniform(0.4, 0.8)
            )
            particle.gravity = 0.2
            self.system.add_particle(particle)

    def teleport_effect(self, x, y):
        """
        Effect when teleporting

        Args:
            x, y: Grid position
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Spiral particles
        for i in range(30):
            angle = (i / 30) * 4 * math.pi
            radius = (i / 30) * CELL_SIZE

            px = cx + math.cos(angle) * radius
            py = cy + math.sin(angle) * radius

            particle = Particle(
                px, py,
                0, 0,
                (200, 100, 255),
                random.uniform(3, 5),
                random.uniform(0.3, 0.6)
            )
            self.system.add_particle(particle)

    def sparkle_ring(self, x, y, color):
        """
        Sparkle ring effect

        Args:
            x, y: Grid position
            color: Sparkle color
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Ring of sparkles
        for i in range(8):
            angle = (i / 8) * 2 * math.pi
            radius = CELL_SIZE // 2

            px = cx + math.cos(angle) * radius
            py = cy + math.sin(angle) * radius

            particle = Particle(
                px, py,
                0, 0,
                color,
                4,
                0.5
            )
            self.system.add_particle(particle)

    def explosion(self, x, y, color=None):
        """
        Explosion effect

        Args:
            x, y: Grid position
            color: Optional color override
        """
        if color is None:
            color = COLOR_PARTICLE_EXPLOSION

        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Large burst
        for _ in range(40):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(4, 10)

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                cx, cy,
                vx, vy,
                color,
                random.uniform(4, 10),
                random.uniform(0.6, 1.2)
            )
            particle.gravity = 0.3
            self.system.add_particle(particle)

    def ambient_sparkle(self, x, y, color):
        """
        Gentle ambient sparkle (for power-ups, etc.)

        Args:
            x, y: Grid position
            color: Sparkle color
        """
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2

        # Single sparkle
        offset_x = random.uniform(-CELL_SIZE // 3, CELL_SIZE // 3)
        offset_y = random.uniform(-CELL_SIZE // 3, CELL_SIZE // 3)

        particle = Particle(
            cx + offset_x, cy + offset_y,
            0, random.uniform(-0.5, 0),
            color,
            random.uniform(2, 4),
            random.uniform(0.5, 1.0)
        )
        particle.gravity = -0.05  # Float up slowly
        self.system.add_particle(particle)
