"""Bimatrix game representation and Nash equilibrium computation."""

import fractions
import random  # random.seed
from collections.abc import Sequence
from functools import wraps
from pathlib import Path

import click
import numpy as np
import numpy.typing as npt

from . import columnprint, lemke, randomstart, utils
from .randomstart import MAX_ACCURACY

# defaults
# MAXDIM = 2000 # largest allowed value for m and n; not used yet


def _range_split(s: str, end_range: int = 50) -> list[int]:
    """Parse a comma-separated range string
    such as "1-3,10,4-7" into a list of integers.
    Open-ended ranges like "5-" extend to `end_range`.
    """
    result: list[int] = []
    for part in s.split(","):
        if part != "":
            if "-" in part:
                a_str, b_str = part.split("-")
                a = int(a_str)
                b = end_range if b_str == "" else int(b_str)
            else:
                a = int(part)
                b = a
            a = max(a, 1)
            b = min(b, end_range)  # a > end_range means empty range
            result.extend(range(a, b + 1))
    return result


class PayoffMatrix:
    """A single player's payoff matrix, stored as exact fractions.

    Wraps a matrix of `fractions.Fraction` entries as a NumPy array.

    Parameters
    ----------
    matrix : array_like of fractions.Fraction
        Payoff matrix of shape ``(m, n)``. Every entry must be a
        `fractions.Fraction`; ints and floats are not converted.

    Raises
    ------
    TypeError
        If any entry of `matrix` is not a `fractions.Fraction`.

    Attributes
    ----------
    num_rows : int
        Number of rows, `m`.
    num_columns : int
        Number of columns, `n`.
    matrix : numpy.ndarray of fractions.Fraction
        The payoff matrix as exact fractions.
    max : fractions.Fraction
        Running maximum entry of `matrix`.
    min : fractions.Fraction
        Running minimum entry of `matrix`.
    neg_shift : int
        ``int(max) + 1``, the shift used to make all entries positive.
    neg_matrix : numpy.ndarray
        `neg_shift` minus `matrix`, so all entries are positive
        (used when constructing the LCP).

    Examples
    --------
    >>> from fractions import Fraction as F
    >>> from lemke.bimatrix import PayoffMatrix
    >>> payoffs = PayoffMatrix([[F(3), F(0)], [F(0), F(2)]])
    >>> payoffs.num_rows
    2
    >>> print(payoffs.max)
    3
    """

    def __init__(self, matrix: npt.ArrayLike) -> None:
        array = np.array(matrix, dtype=object)
        if not all(isinstance(x, fractions.Fraction) for x in array.flat):
            raise TypeError("matrix must contain only Fraction values")
        m, n = array.shape
        self.num_rows: int = m
        self.num_columns: int = n
        self.matrix: npt.NDArray[np.object_] = array
        self._full_max_min()

    def __str__(self) -> str:
        buf = columnprint.ColumnPrint(self.num_columns)
        for i in range(self.num_rows):
            for j in range(self.num_columns):
                buf.sprint(str(self.matrix[i][j]))
        out = str(buf)
        out += "\n# max= " + str(self.max) + ", min= " + str(self.min)
        out += ", negshift= " + str(self.neg_shift)
        return out

    def _update_max_min(self, from_row: int, from_col: int) -> None:
        """Update `max`, `min`, and `neg_matrix` over a submatrix range.

        Recomputes `max`/`min` by scanning entries from
        ``(from_row, from_col)`` to the end of the matrix,
        then recomputes `neg_shift` and `neg_matrix` from the result.

        Parameters
        ----------
        from_row : int
            First row index to include in the scan.
        from_col : int
            First column index to include in the scan.
        """
        m = self.num_rows
        n = self.num_columns
        for i in range(from_row, m):
            for j in range(from_col, n):
                elt = self.matrix[i][j]
                self.max = max(self.max, elt)
                self.min = min(self.min, elt)
        self.neg_shift = int(self.max) + 1
        self.neg_matrix = np.full((m, n), self.neg_shift, dtype=int) - self.matrix

    def _full_max_min(self) -> None:
        """Recompute `max` and `min` over the entire matrix."""
        self.max: fractions.Fraction = self.matrix[0][0]
        self.min: fractions.Fraction = self.matrix[0][0]
        self._update_max_min(0, 0)

    def add_row(self, row: npt.ArrayLike) -> None:
        """Append a row to the matrix and update max/min.

        Parameters
        ----------
        row : array_like of fractions.Fraction
            Row to append; must have length `num_columns`.

        Raises
        ------
        TypeError
            If any entry of `row` is not a `fractions.Fraction`.
        """
        if not all(isinstance(x, fractions.Fraction) for x in row):
            raise TypeError("New row must contain only Fraction values")
        self.matrix = np.vstack([self.matrix, row])
        self.num_rows += 1
        self._update_max_min(self.num_rows - 1, 0)

    def add_column(self, col: npt.ArrayLike) -> None:
        """Append a column to the matrix and update max/min.

        Parameters
        ----------
        col : array_like of fractions.Fraction
            Column to append; must have length `num_rows`.

        Raises
        ------
        TypeError
            If any entry of `col` is not a `fractions.Fraction`.
        """
        if not all(isinstance(x, fractions.Fraction) for x in col):
            raise TypeError("New column must contain only Fraction values")
        self.matrix = np.column_stack([self.matrix, col])
        self.num_columns += 1
        self._update_max_min(0, self.num_columns - 1)


class Bimatrix:
    """A two-player bimatrix game and methods to find its equilibria.

    Parameters
    ----------
    A : PayoffMatrix
        Row player's payoff matrix.
    B : PayoffMatrix
        Column player's payoff matrix.

    Attributes
    ----------
    A : PayoffMatrix
        Row player's payoff matrix.
    B : PayoffMatrix
        Column player's payoff matrix.

    Examples
    --------
    >>> from fractions import Fraction as F
    >>> from lemke.bimatrix import Bimatrix, PayoffMatrix
    >>> game = Bimatrix(
    ...     A=PayoffMatrix([[F(3), F(0)], [F(0), F(2)]]),
    ...     B=PayoffMatrix([[F(2), F(0)], [F(0), F(7)]]),
    ... )
    >>> game.A.num_rows
    2
    """

    def __init__(self, A: PayoffMatrix, B: PayoffMatrix) -> None:
        self.A = A
        self.B = B

    @classmethod
    def from_file(
        cls,
        filename: str | Path,
        decimals: int = utils.DEFAULT_DECIMALS,
    ) -> "Bimatrix":
        """Create a bimatrix game from a text file.

        Read about how input files should be formatted
        :doc:`here <../file_formats>`.

        Parameters
        ----------
        filename : str or pathlib.Path
            Path to the game file.
        decimals : int, optional
            Number of decimal places to which payoffs written as decimals
            (e.g. ``0.145``) are rounded before conversion to fractions.
            Must be between 0 and `utils.MAX_DECIMALS`.
            Default is `utils.DEFAULT_DECIMALS`.

        Returns
        -------
        Bimatrix
            The game described by the file.

        Raises
        ------
        TypeError
            If `decimals` is not an integer.
        ValueError
            If `decimals` is out of range, the file doesn't contain
            the expected number of values, or contains an invalid number.

        Examples
        --------
        Given a file ``examples/game`` containing:

        .. literalinclude:: ../../examples/game
           :language: text

        >>> from lemke.bimatrix import Bimatrix
        >>> game = Bimatrix.from_file("examples/game")
        >>> print(game.A.num_rows)
        2
        """
        utils._validate_decimals(decimals)
        lines = utils._strip_comments(filename)
        # flatten into words
        words = utils._to_words(lines)
        m = int(words[0])
        n = int(words[1])
        need_fracs = 2 * m * n
        if len(words) != need_fracs + 2:
            raise ValueError(
                f"in bimatrix file {filename!r}: "
                f"m={m}, n={n}, need {need_fracs} payoffs, got {len(words) - 2}"
            )
        k = 2
        matrix = utils._to_matrix(m, n, words, k, decimals)
        a = PayoffMatrix(matrix)
        k += m * n
        matrix = utils._to_matrix(m, n, words, k, decimals)
        b = PayoffMatrix(matrix)
        return cls(a, b)

    def __str__(self) -> str:
        out = "# m,n= \n" + str(self.A.num_rows)
        out += " " + str(self.A.num_columns)
        out += "\n# A= \n" + str(self.A)
        out += "\n# B= \n" + str(self.B)
        return out

    def create_lcp(self) -> lemke.Lcp:
        """Build the linear complementarity problem for this game.

        Returns
        -------
        lemke.Lcp
            The LCP corresponding to this game.
        """

        m = self.A.num_rows
        n = self.A.num_columns
        lcp_dim = m + n + 2

        q = [0 for _ in range(lcp_dim)]
        M = [[0] * lcp_dim for _ in range(lcp_dim)]

        q[lcp_dim - 2] = -1
        q[lcp_dim - 1] = -1

        for i in range(m):
            M[lcp_dim - 2][i] = 1
            M[i][lcp_dim - 2] = -1
        for j in range(m, m + n):
            M[lcp_dim - 1][j] = 1
            M[j][lcp_dim - 1] = -1
        for i in range(m):
            for j in range(n):
                M[i][j + m] = self.A.neg_matrix[i][j]
        for j in range(n):
            for i in range(m):
                M[j + m][i] = self.B.neg_matrix[i][j]
        # d for now
        d = [1 for _ in range(lcp_dim)]
        return lemke.Lcp(M, q, d)

    def _run_lh(self, dropped_label: int) -> tuple[fractions.Fraction, ...]:
        """Run Lemke-Howson from a given dropped label.

        Parameters
        ----------
        dropped_label : int
            The label to drop as the starting label for the Lemke-Howson path.

        Returns
        -------
        tuple of fractions.Fraction
            The equilibrium strategy pair found, as a tuple of length ``m + n``.

        Raises
        ------
        RuntimeError
            If the underlying Lemke's algorithm unexpectedly fails to find a solution.
        """
        lcp = self.create_lcp()
        lcp.d[dropped_label - 1] = 0  # subsidize this label
        # tabl.runlemke(verbose=True, lexstats=True, z0=gz0)

        result = lemke.run_lemke(lcp=lcp)
        if not result.success:
            raise RuntimeError("run_lemke() failed to find a solution unexpectedly.")

        equilibrium = result.z[:-2]
        return tuple(equilibrium)

    def lh(
        self,
        lh_string: str,
    ) -> dict[tuple[fractions.Fraction, ...], list[int]]:
        """Find equilibria by running Lemke-Howson from several labels.

        Parameters
        ----------
        lh_string : str
            Range specification of labels to try, e.g. ``"1-3,7"``.

        Returns
        -------
        dict
            Mapping from each distinct equilibrium found (as a tuple)
            to the list of labels that produced it.
            Also printed to stdout as equilibria are found.

        Examples
        --------
        Run Lemke-Howson for all labels. This prints progress as each label
        is tried, then a summary of all distinct equilibria found with
        the list of labels that produced it:

        >>> from lemke.bimatrix import Bimatrix
        >>> game = Bimatrix.from_file("examples/game")
        >>> result = game.lh("1-")
        label 1 found eq (1,0),(1,0)
            supports: [0][0]
        label 2 found eq (0,1),(0,1)
            supports: [1][1]
        -------- equilibria found: --------
        (1,0),(1,0)
            supports: [0][0] found by labels [1, 3]
        (0,1),(0,1)
            supports: [1][1] found by labels [2, 4]
        """
        m = self.A.num_rows
        n = self.A.num_columns

        # equilibria and labels finding them
        lh_set: dict[tuple[fractions.Fraction, ...], list[int]] = {}

        labels = _range_split(lh_string, m + n)
        for k in labels:
            eq = self._run_lh(k)
            if eq in lh_set:
                lh_set[eq].append(k)
            else:
                print("label", k, "found eq", _str_eq(eq, m, n))
                lh_set[eq] = [k]
        print("-------- equilibria found: --------")
        for eq in lh_set:
            print(_str_eq(eq, m, n), "found by labels", str(lh_set[eq]))
        return lh_set

    def _run_trace(
        self,
        x_prior: list[fractions.Fraction] | npt.NDArray[np.object_],
        y_prior: list[fractions.Fraction] | npt.NDArray[np.object_],
    ) -> tuple[fractions.Fraction, ...]:
        """Run the tracing procedure from a given prior.

        Parameters
        ----------
        x_prior : array_like of fractions.Fraction
            Row player's prior strategy: ``m`` exact rational probabilities
            summing to 1, where ``m`` is the number of rows.
            Floats are not supported.
        y_prior : array_like of fractions.Fraction
            Column player's prior strategy: ``n`` exact rational probabilities
            summing to 1, where ``n`` is the number of columns.
            Floats are not supported.

        Returns
        -------
        tuple of fractions.Fraction
            The equilibrium strategy pair found, as a tuple of length ``m + n``.

        Raises
        ------
        RuntimeError
            If the underlying Lemke's algorithm unexpectedly fails to find a solution.
        """
        lcp = self.create_lcp()
        a_y = self.A.neg_matrix @ y_prior
        x_b = x_prior @ self.B.neg_matrix
        lcp.d = np.hstack((a_y, x_b, [1, 1])).tolist()

        result = lemke.run_lemke(lcp=lcp)
        if not result.success:
            raise RuntimeError("run_lemke() failed to find a solution unexpectedly.")

        equilibrium = result.z[:-2]
        return tuple(equilibrium)

    def trace_uniform_prior(self) -> None:
        """Run the tracing procedure once, starting from a uniform prior.

        Prints the resulting equilibrium.

        Examples
        --------
        Run the tracing procedure from a uniform prior
        and print the equilibrium found:

        >>> from lemke.bimatrix import Bimatrix
        >>> game = Bimatrix.from_file("examples/game")
        >>> game.trace_uniform_prior()
        -------- statistics of equilibria found: --------
        1 times found (0,1),(0,1)
            supports: [1][1]
        1 total priors, 1 equilibria found
        """
        m = self.A.num_rows
        n = self.A.num_columns

        x_prior = _uniform(m)
        y_prior = _uniform(n)
        eq = self._run_trace(x_prior, y_prior)

        self._print_trace_results(
            equilibria={eq: 1},
            total_priors=1,
        )

    def trace_random_priors(
        self,
        num_priors: int,
        seed: int | None = None,
        accuracy: int = 1000,
    ) -> None:
        """Run the tracing procedure from several random priors.

        Parameters
        ----------
        num_priors : int
            Number of random priors to try. Must be positive.
        seed : int, optional
            Random seed. If given, each prior `k` is seeded
            deterministically from `seed` and `k`, so results are
            reproducible. If None, priors are unseeded.
            Default is None.
        accuracy : int, optional
            Denominator used to round each random prior's coordinates
            to rational numbers. Default is 1000.

        Raises
        ------
        ValueError
            If `num_priors` is not a positive integer.

        Examples
        --------
        Run the tracing procedure from one random prior
        and print the equilibrium found:

        >>> from lemke.bimatrix import Bimatrix
        >>> game = Bimatrix.from_file("examples/game")
        >>> game.trace_random_priors(1, seed=1)
        found eq (0,1),(0,1)
            supports: [1][1] index 1
        -------- statistics of equilibria found: --------
        1 times found (0,1),(0,1)
            supports: [1][1]
        1 total priors, 1 equilibria found
        """
        if num_priors <= 0:
            raise ValueError("Number of priors must be a positive integer")
        m = self.A.num_rows
        n = self.A.num_columns

        # equilibria, how often found
        tr_set: dict[tuple[fractions.Fraction, ...], int] = {}

        for k in range(num_priors):
            if seed is not None:
                random.seed(10 * num_priors * seed + k)
            x = randomstart._rand_in_simplex(m)
            x_prior = randomstart._round_array(x, accuracy)
            y = randomstart._rand_in_simplex(n)
            y_prior = randomstart._round_array(y, accuracy)
            eq = self._run_trace(x_prior, y_prior)
            if eq in tr_set:
                tr_set[eq] += 1
            else:
                print("found eq", _str_eq(eq, m, n), "index", self.eq_index(eq, m, n))
                tr_set[eq] = 1

        self._print_trace_results(tr_set, num_priors)

    def _print_trace_results(
        self,
        equilibria: dict[tuple[fractions.Fraction, ...], int],
        total_priors: int,
    ) -> None:
        """Print a summary of equilibria found by a tracing run."""
        m = self.A.num_rows
        n = self.A.num_columns

        print("-------- statistics of equilibria found: --------")
        for eq, count in equilibria.items():
            print(count, "times found", _str_eq(eq, m, n))
        print(total_priors, "total priors,", len(equilibria), "equilibria found")

    def eq_index(
        self,
        eq: Sequence[fractions.Fraction],
        m: int,
        n: int,
    ) -> int:
        """Compute the index (+1/-1/0) of an equilibrium.

        Parameters
        ----------
        eq : sequence of fractions.Fraction
            Equilibrium strategy pair, flat tuple of length ``m + n``.
        m : int
            Number of rows (row player's strategies).
        n : int
            Number of columns (column player's strategies).

        Returns
        -------
        int
            ``+1`` or ``-1`` for a regular equilibrium,
            ``0`` if the equilibrium is degenerate
            (supports of unequal size or singular submatrices).
        """
        row_set, col_set = _supports(eq, m, n)
        k, ell = len(row_set), len(col_set)
        if k != ell:
            return 0
        sub_a = _submatrix(self.A.neg_matrix, row_set, col_set)
        det_a = np.linalg.det(sub_a)
        sub_b = _submatrix(self.B.neg_matrix, row_set, col_set)
        det_b = np.linalg.det(sub_b)
        sign = 2 * (k % 2) - 1  # -1 if even, 1 if odd
        if det_a * det_b == 0:
            return 0
        if det_a * det_b > 0:
            return sign
        return -sign


def _uniform(n: int) -> npt.NDArray[np.object_]:
    """Return the uniform distribution over `n` outcomes as fractions."""
    return np.array([fractions.Fraction(1, n) for _ in range(n)])


def _str_eq(
    eq: Sequence[fractions.Fraction],
    m: int,
    n: int,
) -> str:
    """Format an equilibrium strategy pair as a readable string."""
    x = "(" + ",".join([str(v) for v in eq[0:m]]) + ")"
    y = "(" + ",".join([str(v) for v in eq[m: m + n]]) + ")"
    row_set, col_set = _supports(eq, m, n)
    return x + "," + y + "\n    supports: " + str(row_set) + str(col_set)


def _supports(
    eq: Sequence[fractions.Fraction],
    m: int,
    n: int,
) -> tuple[list[int], list[int]]:
    """Return the index sets where each player's strategy is nonzero."""
    row_set = [i for i in range(m) if eq[i] != 0]
    col_set = [j for j in range(n) if eq[m + j] != 0]
    return row_set, col_set


def _submatrix(matrix, row_set, col_set):
    """Extract a submatrix at the given row and column indices."""
    k, ell = len(row_set), len(col_set)
    sub = np.zeros((k, ell))
    for i in range(k):
        for j in range(ell):
            sub[i][j] = matrix[row_set[i]][col_set[j]]
    return sub


@click.group(
    context_settings={"help_option_names": ["-?", "-h", "--help"]},
)
def main():
    """Find Nash equilibria of a bimatrix game."""
    pass


def _common_options(f):
    @click.argument(
        "filename",
        type=click.Path(exists=True, readable=True, file_okay=True, dir_okay=False),
    )
    @click.option(
        "--decimals",
        default=utils.DEFAULT_DECIMALS,
        show_default=True,
        type=click.IntRange(min=0, max=utils.MAX_DECIMALS),
        metavar="INTEGER",
        help="Allowed payoff digits in input after decimal point",
    )
    # @click.option(
    #     "--z0",
    #     is_flag=True,
    #     help="Show value of z0 at each step",
    # )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


@main.command(name="lh")
@_common_options
@click.option(
    "--labels",
    default="1-",
    help="Missing labels, e.g. 1,3-5,7-  "
         "[default: all labels]",
)
def lh_cmd(filename: str, decimals: int, labels: str) -> None:
    """Find equilibria using the Lemke-Howson algorithm."""

    game = Bimatrix.from_file(filename, decimals)
    game.lh(labels)


@main.group()
def trace() -> None:
    """Find equilibria using the tracing procedure."""
    pass


@trace.command(name="uniform")
@_common_options
def trace_uniform_cmd(filename: str, decimals: int) -> None:
    """Trace using a uniform prior."""

    game = Bimatrix.from_file(filename, decimals)
    game.trace_uniform_prior()


@trace.command(name="random")
@_common_options
@click.option(
    "--priors",
    default=1,
    show_default=True,
    type=click.IntRange(min=1),
    metavar="INTEGER",
    help="Number of random priors",
)
@click.option(
    "--seed",
    type=int,
    help="Random seed",
)
@click.option(
    "--accuracy",
    default=1000,
    show_default=True,
    type=click.IntRange(1, MAX_ACCURACY),
    metavar="INTEGER",
    help="Denominator x: prior coordinates are rounded to multiples of 1/x that sum to 1",
)
def trace_random_cmd(
    filename: str,
    decimals: int,
    priors: int,
    seed: int | None,
    accuracy: int,
) -> None:
    """Trace using random prior(s)."""

    game = Bimatrix.from_file(filename, decimals)
    game.trace_random_priors(priors, seed, accuracy)
