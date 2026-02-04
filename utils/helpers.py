"""
Helper utility functions for Maze Game V3
"""

import random
import math


def clamp(value, min_value, max_value):
    """Clamp a value between min and max"""
    return max(min_value, min(value, max_value))


def lerp(a, b, t):
    """Linear interpolation between a and b by factor t (0-1)"""
    return a + (b - a) * t


def distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def manhattan_distance(x1, y1, x2, y2):
    """Calculate Manhattan distance between two points"""
    return abs(x2 - x1) + abs(y2 - y1)


def random_range(min_val, max_val):
    """Generate random float between min and max"""
    return random.uniform(min_val, max_val)


def random_int(min_val, max_val):
    """Generate random integer between min and max (inclusive)"""
    return random.randint(min_val, max_val)


def random_choice(items):
    """Safely choose random item from list"""
    if not items:
        return None
    return random.choice(items)


def format_time(seconds):
    """Format seconds to MM:SS string"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def format_score(score):
    """Format score with thousands separator"""
    return f"{score:,}"


def color_lerp(color1, color2, t):
    """Interpolate between two RGB colors"""
    r = int(lerp(color1[0], color2[0], t))
    g = int(lerp(color1[1], color2[1], t))
    b = int(lerp(color1[2], color2[2], t))
    return (r, g, b)


def ease_in_out(t):
    """Smooth easing function (0-1)"""
    return t * t * (3 - 2 * t)


def pulse(time, frequency=1.0):
    """Generate a pulsing value (0-1) over time"""
    return (math.sin(time * frequency * math.pi * 2) + 1) / 2


def rect_contains(rect_x, rect_y, rect_w, rect_h, point_x, point_y):
    """Check if a point is inside a rectangle"""
    return (rect_x <= point_x <= rect_x + rect_w and
            rect_y <= point_y <= rect_y + rect_h)


def circles_collide(x1, y1, r1, x2, y2, r2):
    """Check if two circles collide"""
    return distance(x1, y1, x2, y2) < (r1 + r2)
