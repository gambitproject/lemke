"""File utilities: reading input files and converting words to exact numbers."""

import fractions
from decimal import (
    ROUND_HALF_UP,
    Decimal,
    InvalidOperation,
)
from pathlib import Path

import numpy as np
import numpy.typing as npt

# global constants, mutable
# https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python
DEFAULT_DECIMALS = 4
MAX_DECIMALS = 20
# ROUNDING_WARN = False


COMMENT_CHARS = "#%*"  # lines starting with these are ignored


def _validate_decimals(decimals: int) -> None:
    if not isinstance(decimals, int):
        raise TypeError("decimals must be an integer")
    if decimals < 0 or decimals > MAX_DECIMALS:
        raise ValueError(
            f"{decimals} as number of decimals not in allowed range 0 to {MAX_DECIMALS}"
        )


def _strip_comments(filename: str | Path) -> list[str]:
    """Read file into list of line-strings, truncate leading and trailing blanks,
    ignore blank lines and lines starting with COMMENT_CHARS."""

    # http://stackoverflow.com/questions/12330522/reading-a-file-without-newlines
    new_list: list[str] = []
    with open(filename) as file:
        lines = file.read().splitlines()
    # strip comments
    for line in lines:
        line = line.strip()
        if line != "" and line[0] not in COMMENT_CHARS:
            new_list.append(line)
    return new_list


def _to_words(lines: list[str]) -> list[str]:
    """Convert lines to words."""
    words: list[str] = []
    for line in lines:
        words.extend(line.split())
    return words


def _to_fraction(s: str, decimals: int) -> fractions.Fraction:
    """Convert a string to an exact Fraction.

    If `s` contains '.', it's treated as a decimal literal and
    rounded to `decimals` places (half away from zero).
    Otherwise, it's parsed as an integer or 'p/q' fraction string.
    """
    if not isinstance(s, str):
        raise TypeError(
            f"_to_fraction expects a string, got {type(s).__name__}: {s!r}"
        )

    if "." in s:
        try:
            d = Decimal(s)
        except InvalidOperation as e:
            raise ValueError(f"{s!r} is not a valid decimal number") from e
        denominator = 10 ** decimals
        scaled = (d * denominator).to_integral_value(rounding=ROUND_HALF_UP)
        return fractions.Fraction(int(scaled), denominator)

    try:
        return fractions.Fraction(s)
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError(f"{s!r} is not a valid number or fraction: {e}") from e


def _to_vector(
    n: int,
    words: list[str],
    start: int,
    decimals: int,
) -> npt.NDArray[np.object_]:
    """Create n-vector of fractions from words[start,start+n)."""
    vector = np.zeros(n, dtype=fractions.Fraction)
    for i in range(n):
        vector[i] = _to_fraction(words[start + i], decimals)
    return vector


def _to_matrix(
    m: int,
    n: int,
    words: list[str],
    start: int,
    decimals: int,
) -> npt.NDArray[np.object_]:
    """Create (m,n)-matrix of fractions from words[start,start+m*n)."""
    matrix = np.zeros((m, n), dtype=fractions.Fraction)
    k = start
    for i in range(m):
        for j in range(n):
            matrix[i][j] = _to_fraction(words[k], decimals)
            k += 1
    return matrix
