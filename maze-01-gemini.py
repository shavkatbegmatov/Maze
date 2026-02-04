import tkinter as tk
import random

# Sozlamalar
WIDTH, HEIGHT = 600, 600
TILE = 30  # Katak o'lchami
COLS, ROWS = WIDTH // TILE, HEIGHT // TILE


class Cell:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.walls = {'top': True, 'right': True, 'bottom': True, 'left': True}
        self.visited = False

    def draw(self, canvas):
        x, y = self.x * TILE, self.y * TILE
        if self.visited:
            canvas.create_rectangle(x, y, x + TILE, y + TILE, fill="#2C3E50", outline="")

        # Devorlarni chizish
        if self.walls['top']:
            canvas.create_line(x, y, x + TILE, y, fill="orange", width=2)
        if self.walls['right']:
            canvas.create_line(x + TILE, y, x + TILE, y + TILE, fill="orange", width=2)
        if self.walls['bottom']:
            canvas.create_line(x + TILE, y + TILE, x, y + TILE, fill="orange", width=2)
        if self.walls['left']:
            canvas.create_line(x, y + TILE, x, y, fill="orange", width=2)


def remove_walls(current, next):
    dx = current.x - next.x
    if dx == 1:
        current.walls['left'] = False
        next.walls['right'] = False
    elif dx == -1:
        current.walls['right'] = False
        next.walls['left'] = False
    dy = current.y - next.y
    if dy == 1:
        current.walls['top'] = False
        next.walls['bottom'] = False
    elif dy == -1:
        current.walls['bottom'] = False
        next.walls['top'] = False


def generate():
    global current_cell
    current_cell.visited = True

    # Qo'shnilarni tekshirish
    neighbors = []
    x, y = current_cell.x, current_cell.y

    potential_neighbors = [
        (x, y - 1, 'top'), (x + 1, y, 'right'),
        (x, y + 1, 'bottom'), (x - 1, y, 'left')
    ]

    for nx, ny, wall in potential_neighbors:
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            neighbor = grid[ny][nx]
            if not neighbor.visited:
                neighbors.append(neighbor)

    if neighbors:
        next_cell = random.choice(neighbors)
        stack.append(current_cell)
        remove_walls(current_cell, next_cell)
        current_cell = next_cell
    elif stack:
        current_cell = stack.pop()

    # Grafikni yangilash
    canvas.delete("all")
    for row in grid:
        for cell in row:
            cell.draw(canvas)

    # Hozirgi nuqtani ko'rsatish
    cx, cy = current_cell.x * TILE, current_cell.y * TILE
    canvas.create_rectangle(cx + 4, cy + 4, cx + TILE - 4, cy + TILE - 4, fill="green", outline="")

    # Keyingi qadamni chaqirish (tezlikni millisekundda sozlash mumkin)
    root.after(30, generate)


# Asosiy oyna
root = tk.Tk()
root.title("Labirint Generator (Python 3.14)")

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#1A1A1A")
canvas.pack()

# To'rni yaratish
grid = [[Cell(col, row) for col in range(COLS)] for row in range(ROWS)]
current_cell = grid[0][0]
stack = []

# Algoritmni boshlash
generate()
root.mainloop()