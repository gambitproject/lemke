# Lemke: A Pure Python LCP Solver

A modernized, pure Python implementation of **Lemke's algorithm** for solving **Linear Complementarity Problems (LCPs)** and finding Nash equilibria in bimatrix games.

## Features

- **Pure Python**: No C extensions required.
- **Exact Arithmetic**: Uses Python's `fractions.Fraction` for high precision.
- **Modern CLI**: Powered by `click` for a robust command-line experience.
- **Library-Ready**: Refactored to remove global state, making it suitable for integration into larger projects like Gambit.
- **Flexible**: Supports standalone LCP solving and bimatrix game analysis (Lemke-Howson and Tracing procedures).

## Installation

```bash
# Clone the repository
git clone https://github.com/gambitproject/lemke.git
cd lemke

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install .
```

## Usage

### Command Line Interface

The package provides two main entry points:

#### 1. Solve an LCP
```bash
python -m lemke.lemke path/to/lcp_file
```
**Options:**
- `-v, --verbose`: Print intermediate tableaus.
- `-s, --silent`: Redirect output to a file.
- `-z0`: Show the value of the artificial variable `z0` at each step.
- `--decimals <int>`: Precision for converting floats to fractions (default: 4).

#### 2. Find Nash Equilibria (Bimatrix Games)
```bash
python -m lemke.bimatrix path/to/game_file
```
**Options:**
- `-LH <labels>`: Run the Lemke-Howson algorithm (e.g., `-LH 1,3-5`).
- `--trace <counts>`: Run the tracing procedure with `<counts>` random priors.
- `--seed <int>`: Set a random seed for reproducible results.

### Using as a Library

```python
from lemke.lemke import lcp, tableau, SolverConfig

# Load an LCP from file
problem = lcp.from_file("examples/lcp")

# Or create one manually
# problem = lcp(n=3)
# problem.M = ...
# problem.q = ...

# Setup configuration
config = SolverConfig(verbose=True)

# Run the solver
tabl = tableau(problem)
tabl.runlemke(config)

# Get the solution
print(tabl.solution)
```

## Project Structure

- `src/lemke/lemke.py`: Core LCP algorithm.
- `src/lemke/bimatrix.py`: Game theory extensions (Lemke-Howson, Tracing).
- `src/lemke/exceptions.py`: Custom error types.
- `src/lemke/utils.py`: File I/O and arithmetic utilities.
- `examples/`: Sample LCP and bimatrix game files.

## Credits

Original implementation by **Bernhard von Stengel**.

