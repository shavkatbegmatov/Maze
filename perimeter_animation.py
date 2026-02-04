import pygame
import math

pygame.init()
screen = pygame.display.set_mode((900, 360))
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20, bold=True)

# Perimeters from the task
P1 = 37
P2 = 63

# Given: 1 cell (perimeter 4) -> 2 minutes => 0.5 min per unit edge
MIN_PER_UNIT = 0.5

T1 = P1 * MIN_PER_UNIT
T2 = P2 * MIN_PER_UNIT
DIFF = abs(T2 - T1)

# Animation speed (visual, not real minutes)
UNITS_PER_SEC = 20  # how many perimeter-units per second

def draw_loop(cx, cy, r, progress, color):
    # Draw circle as "loop", and a moving runner point along it
    pygame.draw.circle(screen, (200, 200, 200), (cx, cy), r, 3)
    ang = (progress % 1.0) * 2 * math.pi
    x = cx + int(r * math.cos(ang))
    y = cy + int(r * math.sin(ang))
    pygame.draw.circle(screen, color, (x, y), 8)

def main():
    t = 0.0
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        t += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        screen.fill((18, 20, 26))

        # progress in "units"
        u1 = (t * UNITS_PER_SEC) % P1
        u2 = (t * UNITS_PER_SEC) % P2

        # normalized progress 0..1
        p1 = u1 / P1
        p2 = u2 / P2

        draw_loop(220, 170, 90, p1, (70, 140, 255))   # lake 1 runner
        draw_loop(650, 170, 120, p2, (60, 200, 120))  # lake 2 runner

        txt1 = f"Lake 1: P={P1}, T={T1:.1f} min"
        txt2 = f"Lake 2: P={P2}, T={T2:.1f} min"
        txt3 = f"Difference: {DIFF:.0f} min"

        screen.blit(font.render(txt1, True, (230, 230, 230)), (40, 20))
        screen.blit(font.render(txt2, True, (230, 230, 230)), (470, 20))
        screen.blit(font.render(txt3, True, (255, 220, 120)), (330, 320))
        screen.blit(font.render("ESC: exit", True, (160, 160, 160)), (760, 320))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
