# Morabaraba AI Agent

A self-learning game-playing agent for **Morabaraba** (also known as Twelve Men's Morris), built as an exploration of reinforcement learning through tabular Q-learning and self-play.

## Overview

Morabaraba is a traditional South African strategy board game in the "mill" family of games (related to Nine Men's Morris), played by placing and moving pieces to form "mills" (three in a row) that let a player remove an opponent's piece. This project implements an agent that learns to play Morabaraba from scratch through self-play, without hand-coded strategy — it improves purely by playing against itself and updating its value estimates over time.

The project was developed as part of a university AI module and follows a formal **TEP (Task, Environment, Performance)** framing:

| | |
|---|---|
| **Task** | Learn a policy for playing Morabaraba that maximizes win rate against an opponent |
| **Environment** | The Morabaraba board, its placement/movement/mill/flying rules, and the opposing player (self-play during training) |
| **Performance** | Win rate, and quality of learned policy over successive training generations |

## Features

- 🎮 Playable Morabaraba implementation with a **Python/Tkinter GUI**
- 🧠 **Tabular Q-learning** agent with epsilon-greedy exploration
- 🔁 **Self-play training loop** — the agent improves by playing against itself
- 💾 **JSON-based model export/import** — trained "brains" can be saved and reloaded without retraining
- 📊 Supports experimental evaluation of the trained agent's performance

## Tech Stack

- **Python** — core game logic and agent
- **Tkinter** — graphical interface
- **JSON** — model (Q-table) serialization

## Getting Started

### Prerequisites

- Python 3.x (Tkinter ships with most standard Python installations)

### Installation

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
python main.py
```

> Replace `main.py` above with the actual entry-point filename in this repo.

### Playing the Game

Run the entry-point script to launch the GUI, then follow the on-screen prompts to place and move pieces according to standard Morabaraba rules.

### Training the Agent

The agent is trained via self-play, updating a Q-table over many simulated games. To retrain from scratch (or continue training):

```bash
python <training_script>.py
```

Trained models are saved as JSON files and can be loaded back in without needing to retrain.

> Replace `<training_script>.py` with the actual filename, and adjust any training parameters (episode count, epsilon decay, learning rate) documented in the script.

## How It Works

The agent uses **tabular Q-learning**: it maintains a table of estimated values (Q-values) for state-action pairs and updates them using the standard Q-learning update rule as it plays. During training, it follows an **epsilon-greedy** policy — mostly acting on its current best-known move, but occasionally exploring randomly — with epsilon typically decaying over time to shift from exploration toward exploitation as the agent improves.

## Project Structure

```
├── main.py                # Entry point / GUI launcher
├── agent.py                # Q-learning agent implementation
├── game.py                 # Morabaraba game rules and board logic
├── train.py                 # Self-play training loop
├── models/                  # Saved trained agent(s) as JSON
└── README.md
```

> Update this tree to match your actual file layout.

## Results

A written technical report accompanying this project covers the TEP framework definition, implementation details, and experimental evaluation of the trained agent's performance.

> Link or attach the report here if you'd like it referenced from the README.

## Acknowledgments

Developed as part of a university Artificial Intelligence module assignment.

## License

> Add a license (e.g. MIT) if you'd like others to know how they can use this code.
