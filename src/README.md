# Lemke Source Code

This directory contains the core implementation of the Lemke package.

## Package Structure

- `lemke/`: The main package containing the solver logic.
    - `lemke.py`: Implementation of the LCP algorithm and `tableau` class.
    - `bimatrix.py`: Game theory extensions for bimatrix games.
    - `exceptions.py`: Custom exception classes for error handling.
    - `utils.py`: Utilities for arithmetic, file parsing, and configuration.
    - `columnprint.py`: Helper for pretty-printing results in columns.
    - `randomstart.py`: Utils for randomizing start points in game solving.

## Development

The package is designed to be modular and thread-safe by avoiding global state. Most major classes now include factory methods like `from_file` for convenient initialization.

For detailed usage, see the root [README](../README.md).
