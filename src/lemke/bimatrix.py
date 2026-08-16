"""Bimatrix game representation and Nash equilibrium computation."""

import fractions
import random  # random.seed
from functools import wraps

import click
import numpy as np

from . import columnprint, lemke, randomstart, utils
from .randomstart import MAX_ACCURACY
from .utils import MAXDECIMALS

# defaults
# MAXDIM = 2000 # largest allowed value for m and n; not used yet


def rangesplit(s, endrange=50):
    """Parse a comma-separated range string
    such as "1-3,10,4-7" into a list of integers.
    Open-ended ranges like "5-" extend to `endrange`.
    """
    result = []
    for part in s.split(","):
        if part != "":
            if "-" in part:
                a, b = part.split("-")
                a = int(a)
                b = endrange if b == "" else int(b)
            else:
                a = int(part)
                b = a
            a = max(a, 1)
            b = min(b, endrange)  # a > endrange means empty range
            result.extend(range(a, b + 1))
    return result


class payoffmatrix:
    """A single player's payoff matrix, stored as exact fractions.

    Wraps a numerical matrix as an array of `fractions.Fraction` entries.

    Parameters
    ----------
    A : array_like
        Numerical payoff matrix of shape ``(m, n)``.
        Entries may be int, float, or Fraction;
        they are converted to `Fraction`.

    Attributes
    ----------
    numrows : int
        Number of rows, `m`.
    numcolumns : int
        Number of columns, `n`.
    matrix : numpy.ndarray of fractions.Fraction
        The payoff matrix as exact fractions.
    max : fractions.Fraction
        Running maximum entry of `matrix`.
    min : fractions.Fraction
        Running minimum entry of `matrix`.
    negshift : int
        ``int(max) + 1``, the shift used to make all entries positive.
    negmatrix : numpy.ndarray
        `matrix` shifted by `negshift` so all entries are positive
        (used when constructing the LCP).

    Examples
    --------
    >>> from lemke.bimatrix import payoffmatrix
    >>> payoffs = payoffmatrix([[3, 0], [0, 2]])
    >>> payoffs.numrows
    2
    >>> payoffs.max
    3
    """

    def __init__(self, A):
        AA = np.array(A)
        m, n = AA.shape
        self.numrows = m
        self.numcolumns = n
        self.matrix = np.zeros((m, n), dtype=fractions.Fraction)
        for i in range(m):
            for j in range(n):
                self.matrix[i][j] = utils.tofraction(AA[i][j])
        self.fullmaxmin()

    def __str__(self):
        buf = columnprint.columnprint(self.numcolumns)
        for i in range(self.numrows):
            for j in range(self.numcolumns):
                buf.sprint(str(self.matrix[i][j]))
        out = str(buf)
        out += "\n# max= " + str(self.max) + ", min= " + str(self.min)
        out += ", negshift= " + str(self.negshift)
        return out

    def updatemaxmin(self, fromrow, fromcol):
        """Update `max`, `min`, and `negmatrix` over a submatrix range.

        Recomputes `max`/`min` by scanning entries from
        ``(fromrow, fromcol)`` to the end of the matrix,
        then recomputes `negshift` and `negmatrix` from the result.

        Parameters
        ----------
        fromrow : int
            First row index to include in the scan.
        fromcol : int
            First column index to include in the scan.
        """
        m = self.numrows
        n = self.numcolumns
        for i in range(fromrow, m):
            for j in range(fromcol, n):
                elt = self.matrix[i][j]
                self.max = max(self.max, elt)
                self.min = min(self.min, elt)
        self.negshift = int(self.max) + 1
        self.negmatrix = np.full((m, n), self.negshift, dtype=int) - self.matrix

    def fullmaxmin(self):
        """Recompute `max` and `min` over the entire matrix."""
        self.max = self.matrix[0][0]
        self.min = self.matrix[0][0]
        self.updatemaxmin(0, 0)

    def addrow(self, row):
        """Append a row to the matrix and update max/min.

        Parameters
        ----------
        row : array_like
            Row to append; must have length `numcolumns`.
        """
        self.matrix = np.vstack([self.matrix, row])
        self.numrows += 1
        self.updatemaxmin(self.numrows - 1, 0)

    def addcolumn(self, col):
        """Append a column to the matrix and update max/min.

        Parameters
        ----------
        col : array_like
            Column to append; must have length `numrows`.
        """
        self.matrix = np.column_stack([self.matrix, col])
        self.numcolumns += 1
        self.updatemaxmin(0, self.numcolumns - 1)


class bimatrix:
    """A two-player bimatrix game and methods to find its equilibria.

    Parameters
    ----------
    A : payoffmatrix
        Row player's payoff matrix.
    B : payoffmatrix
        Column player's payoff matrix.

    Attributes
    ----------
    A : payoffmatrix
        Row player's payoff matrix.
    B : payoffmatrix
        Column player's payoff matrix.

    Examples
    --------
    >>> from lemke.bimatrix import bimatrix, payoffmatrix
    >>> game = bimatrix(
    ...     A=payoffmatrix([[3, 0], [0, 2]]),
    ...     B=payoffmatrix([[2, 0], [0, 7]]),
    ... )
    >>> game.A.numrows
    2
    """

    def __init__(self, A, B):
        self.A = A
        self.B = B

    @classmethod
    def from_file(cls, filename):
        """Create a bimatrix game from a text file.

        Expects the file format::

            <m> <n>
            m*n entries of A
            m*n entries of B

        Blank lines and lines starting with ``#`` are ignored.

        Parameters
        ----------
        filename : str or pathlib.Path
            Path to the game file.

        Returns
        -------
        bimatrix
            The game described by the file.

        Raises
        ------
        SystemExit
            If the number of payoff values in the file is incorrect.

        Examples
        --------
        Given a file ``game.txt`` containing::
            # m,n=
            2 2

            # A=
            3 0
            0 2

            # B=
            2 0
            0 7

        >>> from lemke.bimatrix import bimatrix
        >>> game = bimatrix.from_file("game.txt")
        >>> print(game.A.numrows)
        2
        """
        lines = utils.stripcomments(filename)
        # flatten into words
        words = utils.towords(lines)
        m = int(words[0])
        n = int(words[1])
        needfracs = 2 * m * n
        if len(words) != needfracs + 2:
            print("in bimatrix file " + repr(filename) + ":")
            print("m=", m, ", n=", n, ", need", needfracs, "payoffs, got", len(words) - 2)
            exit(1)
        k = 2
        C = utils.tomatrix(m, n, words, k)
        A = payoffmatrix(C)
        k += m * n
        C = utils.tomatrix(m, n, words, k)
        B = payoffmatrix(C)
        return cls(A, B)

    def __str__(self):
        out = "# m,n= \n" + str(self.A.numrows)
        out += " " + str(self.A.numcolumns)
        out += "\n# A= \n" + str(self.A)
        out += "\n# B= \n" + str(self.B)
        return out

    def createLCP(self):
        """Build the linear complementarity problem for this game.

        Returns
        -------
        lcp
            The LCP corresponding to this game.
        """

        m = self.A.numrows
        n = self.A.numcolumns
        lcpdim = m + n + 2

        q = [0 for _ in range(lcpdim)]
        M = [[0] * lcpdim for _ in range(lcpdim)]

        q[lcpdim - 2] = -1
        q[lcpdim - 1] = -1

        for i in range(m):
            M[lcpdim - 2][i] = 1
            M[i][lcpdim - 2] = -1
        for j in range(m, m + n):
            M[lcpdim - 1][j] = 1
            M[j][lcpdim - 1] = -1
        for i in range(m):
            for j in range(n):
                M[i][j + m] = self.A.negmatrix[i][j]
        for j in range(n):
            for i in range(m):
                M[j + m][i] = self.B.negmatrix[i][j]
        # d for now
        d = [1 for _ in range(lcpdim)]
        return lemke.lcp(M, q, d)

    def runLH(self, droppedlabel):
        """Run Lemke-Howson from a given dropped label.

        Parameters
        ----------
        droppedlabel : int
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
        lcp = self.createLCP()
        lcp.d[droppedlabel - 1] = 0  # subsidize this label
        # tabl.runlemke(verbose=True, lexstats=True, z0=gz0)

        result = lemke.runlemke(lcp=lcp)
        if result is None:
            raise RuntimeError("runlemke() failed to find a solution unexpectedly.")

        equilibrium = result[1: lcp.n - 1]
        return tuple(equilibrium)

    def LH(self, LHstring):
        """Find equilibria by running Lemke-Howson from several labels.

        Parameters
        ----------
        LHstring : str
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

        >>> from lemke.bimatrix import bimatrix
        >>> game = bimatrix.from_file("game.txt")
        >>> game.LH("1-")
        """
        m = self.A.numrows
        n = self.A.numcolumns
        lhset = {}  # dict of equilibria and list by which label found
        labels = rangesplit(LHstring, m + n)
        for k in labels:
            eq = self.runLH(k)
            if eq in lhset:
                lhset[eq].append(k)
            else:
                print("label", k, "found eq", str_eq(eq, m, n))
                lhset[eq] = [k]
        print("-------- equilibria found: --------")
        for eq in lhset:
            print(str_eq(eq, m, n), "found by labels", str(lhset[eq]))
        return lhset

    def runtrace(self, xprior, yprior):
        """Run the tracing procedure from a given prior.

        Parameters
        ----------
        xprior : array_like
            Row player's prior strategy (probabilities summing to 1).
        yprior : array_like
            Column player's prior strategy (probabilities summing to 1).

        Returns
        -------
        tuple of fractions.Fraction
            The equilibrium strategy pair found, as a tuple of length ``m + n``.

        Raises
        ------
        RuntimeError
            If the underlying Lemke's algorithm unexpectedly fails to find a solution.
        """
        lcp = self.createLCP()
        Ay = self.A.negmatrix @ yprior
        xB = xprior @ self.B.negmatrix
        lcp.d = np.hstack((Ay, xB, [1, 1]))

        result = lemke.runlemke(lcp=lcp)
        if result is None:
            raise RuntimeError("runlemke() failed to find a solution unexpectedly.")

        equilibrium = result[1: lcp.n - 1]
        return tuple(equilibrium)

    def trace_uniform_prior(self):
        """Run the tracing procedure once, starting from a uniform prior.

        Prints the resulting equilibrium.

        Examples
        --------
        Run the tracing procedure from a uniform prior
        and print the equilibrium found:

        >>> from lemke.bimatrix import bimatrix
        >>> game = bimatrix.from_file("game.txt")
        >>> game.trace_uniform_prior()
        """
        m = self.A.numrows
        n = self.A.numcolumns

        xprior = uniform(m)
        yprior = uniform(n)
        eq = self.runtrace(xprior, yprior)

        self._print_trace_results(
            equilibria={eq: 1},
            total_priors=1,
        )

    def trace_random_priors(self, trace, seed=None, accuracy=1000):
        """Run the tracing procedure from several random priors.

        Parameters
        ----------
        trace : int
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
            If `trace` is not a positive integer.

        Examples
        --------
        Run the tracing procedure from one random prior
        and print the equilibrium found:

        >>> from lemke.bimatrix import bimatrix
        >>> game = bimatrix.from_file("game.txt")
        >>> game.trace_random_priors(1)
        """
        if trace <= 0:
            raise ValueError("Number of priors must be a positive integer")
        m = self.A.numrows
        n = self.A.numcolumns
        trset = {}  # dict of equilibria, how often found

        for k in range(trace):
            if seed is not None:
                random.seed(10 * trace * seed + k)
            x = randomstart.randInSimplex(m)
            xprior = randomstart.roundArray(x, accuracy)
            y = randomstart.randInSimplex(n)
            yprior = randomstart.roundArray(y, accuracy)
            # print (f"{k=} {xprior=} {yprior=}")
            eq = self.runtrace(xprior, yprior)
            if eq in trset:
                trset[eq] += 1
            else:
                print("found eq", str_eq(eq, m, n), "index", self.eqindex(eq, m, n))
                trset[eq] = 1

        self._print_trace_results(trset, trace)

    def _print_trace_results(self, equilibria, total_priors):
        """Print a summary of equilibria found by a tracing run."""
        m = self.A.numrows
        n = self.A.numcolumns

        print("-------- statistics of equilibria found: --------")
        for eq, count in equilibria.items():
            print(count, "times found", str_eq(eq, m, n))
        print(total_priors, "total priors,", len(equilibria), "equilibria found")

    def eqindex(self, eq, m, n):
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
        rowset, colset = supports(eq, m, n)
        k, ell = len(rowset), len(colset)
        if k != ell:
            return 0
        A1 = submatrix(self.A.negmatrix, rowset, colset)
        DA = np.linalg.det(A1)
        B1 = submatrix(self.B.negmatrix, rowset, colset)
        DB = np.linalg.det(B1)
        sign = 2 * (k % 2) - 1  # -1 if even, 1 if odd
        if DA * DB == 0:
            return 0
        if DA * DB > 0:
            return sign
        return -sign


def uniform(n):
    """Return the uniform distribution over `n` outcomes as fractions."""
    return np.array([fractions.Fraction(1, n) for _ in range(n)])


def str_eq(eq, m, n):
    """Format an equilibrium strategy pair as a readable string."""
    x = "(" + ",".join([str(x) for x in eq[0:m]]) + ")"
    y = "(" + ",".join([str(x) for x in eq[m: m + n]]) + ")"
    rowset, colset = supports(eq, m, n)
    return x + "," + y + "\n    supports: " + str(rowset) + str(colset)


def supports(eq, m, n):
    """Return the index sets where each player's strategy is nonzero."""
    rowset = [i for i in range(m) if eq[i] != 0]
    colset = [j for j in range(n) if eq[m + j] != 0]
    return rowset, colset


def submatrix(A, rowset, colset):
    """Extract a submatrix at the given row and column indices."""
    k, ell = len(rowset), len(colset)
    B = np.zeros((k, ell))
    for i in range(k):
        for j in range(ell):
            B[i][j] = A[rowset[i]][colset[j]]
    return B


@click.group(
    context_settings={"help_option_names": ["-?", "-h", "--help"]},
)
def main():
    """Find Nash equilibria of a bimatrix game."""
    pass


def common_options(f):
    @click.argument(
        "filename",
        type=click.Path(exists=True, readable=True, file_okay=True, dir_okay=False),
    )
    @click.option(
        "--decimals",
        default=4,
        show_default=True,
        type=click.IntRange(min=0, max=MAXDECIMALS),
        metavar="INTEGER",
        help="Allowed payoff digits in input after decimal point",
    )
    # @click.option(
    #     "--z0",
    #     is_flag=True,
    #     help="Show value of z0 at each step",
    # )
    @wraps(f)
    def wrapper(*args, decimals, **kwargs):
        utils.setdecimals(decimals)
        return f(*args, **kwargs)
    return wrapper


@main.command()
@common_options
@click.option(
    "--labels",
    default="1-",
    help="Missing labels, e.g. 1,3-5,7-  "
         "[default: all labels]",
)
def lh(filename, labels):
    """Find equilibria using the Lemke-Howson algorithm."""

    G = bimatrix.from_file(filename)
    G.LH(labels)


@main.group()
def trace():
    """Find equilibria using the tracing procedure."""
    pass


@trace.command(name="uniform")
@common_options
def trace_uniform_cmd(filename):
    """Trace using a uniform prior."""

    G = bimatrix.from_file(filename)
    G.trace_uniform_prior()


@trace.command(name="random")
@common_options
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
    help="Denominator x: each coordinate of the prior is rounded to the nearest 1/x",
)
def trace_random_cmd(filename, priors, seed, accuracy):
    """Trace using random prior(s)."""

    G = bimatrix.from_file(filename)
    G.trace_random_priors(priors, seed, accuracy)
