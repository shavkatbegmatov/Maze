# Maze Game V3 - Nightmare Edition

## Project Overview
This is a comprehensive Maze Game built with Python and Pygame. It features both a classic 2D top-down view and a retro-style 3D first-person view (using raycasting). The game includes advanced features like procedural maze generation, fog of war, boss fights, enemy AI, and a save/load system.

## Getting Started

### Prerequisites
*   Python 3.x
*   pip (Python package manager)

### Installation
1.  Clone the repository or download the source code.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Game
To start the game, run the `main.py` file:
```bash
python main.py
```

## Controls

### General
*   **WASD / Arrow Keys**: Move player / Navigate menus
*   **Space**: Attack (if near boss) / Skip generation animation
*   **P / ESC**: Pause Game / Open Menu
*   **R**: Retry Level (when dead)
*   **Enter**: Select menu item
*   **Alt + Enter**: Toggle Fullscreen

### Save/Load
*   **F5**: Quick Save
*   **F9**: Quick Load

### 3D Mode Specific
*   **Mouse**: Look around
*   **W/S**: Move Forward/Backward
*   **A/D**: Strafe Left/Right

## Project Structure

*   **`main.py`**: The entry point of the application. Handles the main game loop, initialization, and high-level event management.
*   **`config.py`**: Global configuration settings (Title, Version, Debug mode).
*   **`requirements.txt`**: List of Python dependencies.
*   **`game/`**: Core game logic and managers.
    *   `game_state.py`: Manages game states (Menu, Playing, Paused, etc.).
    *   `level_manager.py`: Handles level creation and progression.
    *   `collision.py`: Handles collision detection between entities.
    *   `fog_of_war.py`: Implements the visibility system.
    *   `renderer3d/`: Contains the raycasting engine and 3D rendering logic.
*   **`entities/`**: Game object definitions.
    *   `player.py`, `enemy.py`, `boss.py`: Character logic.
    *   `trap.py`, `door.py`, `powerup.py`: Interactive elements.
*   **`maze/`**: Maze generation algorithms.
    *   `generator.py`: Implements different maze generation algorithms (DFS, Prim's, etc.).
*   **`utils/`**: Helper functions and constants (`colors.py`, `constants.py`).

## Features
*   **Multiple Game Modes**: 2D and 3D (Raycasting).
*   **Procedural Generation**: Various algorithms to create unique mazes.
*   **Difficulty Levels**: From Easy to Nightmare.
*   **Combat System**: Enemies and Boss fights with mechanics.
*   **Visual Effects**: Particle systems, dynamic lighting/fog, and animations.
