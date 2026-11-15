# Invisible Maze

**A 2D platformer that teaches Decision Tree Classification by making you use it.**

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Pygame](https://img.shields.io/badge/pygame-ce-green) ![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-orange) ![tests](https://img.shields.io/badge/tests-71%20passing-brightgreen)

You are **Alex**, a young data explorer, guided by **DAT** (Data Analysis Tutor), a floating robot.
There are no walls in the Invisible Maze, only questions. Answer them like a decision tree and the path opens.
At the end waits **The Guardian**, who yields only to someone who can classify the unknown.

Every number in the game (entropy, Gini impurity, information gain, accuracy, confusion matrix, tree diagrams,
depth curves) is **computed live from real CSV data** with pandas, NumPy and scikit-learn. Nothing is hard-coded,
and no panel shows the answer before you try.

<!-- Add a screenshot or GIF here: ![Gameplay](docs/screenshot.png) -->

## Features

- 5 levels covering tree structure, features and targets, impurity and information gain, overfitting and pruning, and model evaluation
- A 3-stage boss fight where The Guardian is hurt only by correct classifications
- Real data science: trees are trained with `DecisionTreeClassifier`; the best split is `argmax(information gain)`
- Clear guidance: a goal banner, an arrow to the next objective, a "YOUR TASK" line on every puzzle and a How To Play screen
- No asset files: sprites, tiles, music and sound effects are all generated in code
- Auto-save with checkpoints, XP, badges and an achievements screen
- 71 automated tests, including scripted playthroughs of every level

## Quick start

Requires **Python 3.10 or newer**.

```bash
git clone https://github.com/<your-username>/invisible-maze.git
cd invisible-maze
pip install -r requirements.txt
python main.py
```

On Windows, use `py` if `python` or `pip` is not recognised:

```powershell
py -m pip install -r requirements.txt
py main.py
```

> **Python 3.13 / 3.14:** the requirements use `pygame-ce`, which installs prebuilt wheels on newer Python versions.
> If the install still fails, use Python 3.12.

Options:

| Command | What it does |
|---|---|
| `python main.py --level 3` | Start directly in level 3 |
| `python main.py --fullscreen` | Start in fullscreen |
| `python main.py --save my.json` | Use a different save file |

## How to play

Every level follows the same loop:

1. **Walk to the glowing terminal.** The gold banner at the top tells you what to do, and an arrow points the way.
2. **Press `E` and answer the puzzle.** The "YOUR TASK" line under the window says what to click. Wrong answers are fine: you get a hint and try again.
3. **The path opens.** Solve every terminal, then enter the golden portal.

Stuck? Press `H` and DAT gives a hint for exactly where you are.

### Controls

| Action | Keys |
|---|---|
| Move | `A` / `D` or Left / Right |
| Jump (hold = higher) | `Space`, `W` or Up |
| Dash | `Shift` |
| Attack (also destroys boss orbs) | `F` or `K` |
| Use a terminal | `E` |
| Hint from DAT | `H` |
| Pause, achievements, sound | `Esc` or `P` |
| Mute | `M` |
| Menus and dialogue | mouse, arrows, `Enter` |

Stomp on enemies from above or strike them. Hearts are your health, and you have 3 lives per attempt.
You respawn at your last checkpoint flag. Falling into a pit costs one heart.

## The levels

| # | Level | What you learn | Reward |
|---|---|---|---|
| 1 | The First Junction | Tree structure: root, branch, leaf. Yes/No doors follow real values on creature cards. | 100 XP, Path Finder |
| 2 | The Creature Chamber | Features vs target, classification, which features matter, classifying unseen creatures. | 150 XP, Creature Classifier |
| 3 | The Split Path | Entropy, Gini impurity, weighted impurity, information gain. Build the bridge with the best split. | 200 XP, Pattern Seeker |
| 4 | The Overgrown Tree | Overfitting, depth, pruning, underfitting vs overfitting with real scikit-learn trees. | 250 XP, Tree Guardian |
| 5 | The Guardian's Trial | Feature selection, train vs test data, accuracy, confusion matrix, then the boss fight. | 300 XP, Master Classifier |

Total: 1000 XP, 5 badges, and the final title **Master Classifier**.

## How the data science works

- `data/mystic_creatures.csv`: the hand-built Mystic Creatures dataset (24 records; `Has_wings`, `Has_venom`, `Aggressive` to `Dangerous`).
- `data/mystic_creatures_large.csv` (300 rows), `data/guardian_training.csv` (200) and `data/guardian_testing.csv` (60) are generated with fixed
  seeds by `tools/generate_datasets.py`. They add numeric features (`Size_cm`, `Speed_kmh`, `Glow_level`, `Age_years`) and a little label
  noise so overfitting and feature selection are real.
- `ds/impurity.py`: entropy `H = -sum(p log2 p)`, Gini `1 - sum(p^2)`, weighted child impurity, information gain. Pure and empty nodes are handled.
- `ds/tree_model.py`: `DecisionTreeClassifier(random_state=42)`, stratified train/test split, depth sweep, cost-complexity pruning
  (alpha chosen by cross-validation on training data only) and decision paths.
- `ds/evaluation.py`: accuracy, 2x2 confusion matrix, prediction tables.
- `ds/visualise.py`: Matplotlib (Agg) figures rendered onto Pygame surfaces.
- Level 3: the best split is `argmax(information gain)` on the node's data, so changing the CSV changes the correct answer.
- Level 4: the best depth is the one with the highest accuracy on held-out data. The deepest tree scores 100% on training and about 69% on unseen data.
- Level 5: the model you train decides what the boss window suggests, and the final report shows your real unseen-data accuracy.

Every split, tree and shuffle uses a fixed seed, so the same inputs always give the same numbers.
To regenerate the datasets: `python tools/generate_datasets.py`.

## Project structure

```
main.py                 entry point
data/                   CSV datasets
ds/                     data-science core (pure Python, no pygame)
  impurity.py           entropy, Gini, information gain
  tree_model.py         training, depth sweep, pruning
  evaluation.py         accuracy, confusion matrix
  visualise.py          Matplotlib figures for the game
game/
  settings.py           constants, palette, key bindings
  app.py                window, main loop, scene fades
  scenes.py             menu, how to play, story, map, gameplay, completion, victory
  level.py, levels/     level base class and the five levels
  world.py              tile grid, collisions, level builder, reachability validator
  entities.py           player, enemies, platforms, gates, terminals
  panels.py             the data-science puzzle panels
  ui.py, assets.py      widgets and procedural pixel art
  audio.py              synthesised sound effects and music
  save.py               JSON save system
tests/                  unit, physics and end-to-end tests
tools/                  dataset generator
```

## Tests

```bash
python -m pytest -q
```

The 71 tests cover entropy, Gini and information gain (including pure and empty nodes), dataset validation and regeneration,
reproducible training, the overfitting and pruning experiments, accuracy and the confusion matrix, physics (jump height,
coyote time, moving platforms, spikes, dash), a check that every terminal, checkpoint, gem and exit is reachable, and scripted
playthroughs of all five levels through the real scene and panel code.

## Troubleshooting

- **No sound?** The game runs silently if no audio device is found. `M` toggles mute.
- **Window too big or small?** It is resizable and scales the 960x540 view.
- **Reset progress:** choose NEW GAME in the menu, or delete `saves/save.json`.
- **`pip install` fails to build pygame:** use `pygame-ce` (already in `requirements.txt`) or Python 3.12.

## License

Add a license of your choice (for example MIT) before publishing.
