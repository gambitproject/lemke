"""Lemke's algorithm for solving linear complementarity problems (LCPs)."""

import fractions
import math  # gcd
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import click

from . import columnprint, utils


class Lcp:
    r"""A linear complementarity problem instance `(M, q, d)`.

    Represents the LCP :math:`w = q + Mz,\ w, z \ge 0,\ z^T w = 0`,
    together with a covering vector `d` used to start Lemke's algorithm.

    Can be constructed directly from `M`, `q`, `d`,
    or via `from_file` for problems stored in the LCP file format.

    Parameters
    ----------
    M : list of list of int or fractions.Fraction
        Square matrix `M` of shape `(n, n)`, given as the list of its `n` rows,
        so ``M[i][j]`` is the entry in row `i` and column `j`.
    q : list of int or fractions.Fraction
        Vector of length `n`.
    d : list of int or fractions.Fraction
        Covering vector of length `n`.

    Attributes
    ----------
    M : list of list of int or fractions.Fraction
        As passed in.
    q, d : list of int or fractions.Fraction
        As passed in.
    n : int
        Dimension of the problem.

    Examples
    --------
    >>> from fractions import Fraction as F
    >>> from lemke.lemke import Lcp
    >>> problem = Lcp(
    ...     M=[[F(2), F(1)], [F(1), F(2)]],
    ...     q=[F(-1), F(-1)],
    ...     d=[F(1), F(1)],
    ... )
    >>> problem.n
    2
    """

    def __init__(
        self,
        M: Sequence[Sequence[int | fractions.Fraction]],
        q: Sequence[int | fractions.Fraction],
        d: Sequence[int | fractions.Fraction],
    ) -> None:
        self.M: list[list[int | fractions.Fraction]] = [list(row) for row in M]
        self.q: list[int | fractions.Fraction] = list(q)
        self.d: list[int | fractions.Fraction] = list(d)
        self.n: int = len(self.d)

    @classmethod
    def from_file(
        cls,
        filename: str | Path,
        decimals: int = utils.DEFAULT_DECIMALS,
    ) -> "Lcp":
        """Create an LCP instance from a text file.

        Read about how input files should be formatted
        :doc:`here <../file_formats>`.

        Parameters
        ----------
        filename : str or pathlib.Path
            Path to the LCP file.
        decimals : int, optional
            Number of decimal places to which numbers written as decimals
            (e.g. ``0.145``) are rounded before conversion to fractions.
            Must be between 0 and `utils.MAX_DECIMALS`.
            Default is `utils.DEFAULT_DECIMALS`.

        Returns
        -------
        Lcp
            The LCP described by the file.

        Raises
        ------
        TypeError
            If `decimals` is not an integer.
        ValueError
            If `decimals` is out of range, the file does not start with ``n=``,
            doesn't contain the expected number of values, has an unrecognized
            keyword, or contains an invalid number.

        Examples
        --------
        Given a file ``examples/lcp_2x2`` containing:

        .. literalinclude:: ../../examples/lcp_2x2
           :language: text

        >>> from lemke.lemke import Lcp
        >>> problem = Lcp.from_file("examples/lcp_2x2")
        >>> print(problem.n)
        2
        """
        utils._validate_decimals(decimals)
        lines = utils._strip_comments(filename)
        # flatten into words
        words = utils._to_words(lines)
        if words[0] != "n=":
            raise ValueError(
                f"lcp file {filename!r} must start with 'n=' lcpdim, e.g. 'n= 5', "
                f"not {words[0]!r}"
            )
        n = int(words[1])
        need_fracs = n * n + 2 * n
        if len(words) != need_fracs + 5:
            # printout("in lcp file '",filename,"':")
            raise ValueError(
                f"in lcp file {filename!r}: "
                f"n={n}, need keywords 'M=' 'q=' 'd=' and "
                f"n*n + n + n = {need_fracs} fractions, got {len(words) - 5}"
            )
        if any(words.count(keyword) != 1 for keyword in ("M=", "q=", "d=")):
            raise ValueError(
                f"in lcp file {filename!r}: expected exactly one 'M=', 'q=', and 'd='"
            )

        k = 2  # index in words
        while k < len(words):
            if words[k] == "M=":
                k += 1
                M = utils._to_matrix(n, n, words, k, decimals).tolist()
                k += n * n
            elif words[k] == "q=":
                k += 1
                q = utils._to_vector(n, words, k, decimals).tolist()
                k += n
            elif words[k] == "d=":
                k += 1
                d = utils._to_vector(n, words, k, decimals).tolist()
                k += n
            else:
                raise ValueError(
                    f"in lcp file {filename!r}: expected one of 'M=' 'q=' 'd=', "
                    f"got {words[k]!r}"
                )
        return cls(M, q, d)

    def __str__(self):
        n = self.n
        M = self.M
        q = self.q
        d = self.d
        m = columnprint.ColumnPrint(n)
        m.make_left(0)
        m.sprint("M=")
        m.newline()
        for i in range(n):
            for j in range(n):
                m.sprint(str(M[i][j]))
        m.sprint("q=")
        m.newline()
        for i in range(n):
            m.sprint(str(q[i]))
        m.sprint("d=")
        m.newline()
        for i in range(n):
            m.sprint(str(d[i]))
        # printout("M[0][0]", type(M[0][0]))
        return "n= " + str(n) + "\n" + str(m)
    #  end of class Lcp


class Tableau:
    """The tableau used to run Lemke's pivoting algorithm.

    Stores the LCP data as a scaled integer tableau
    (to allow exact arithmetic during pivoting)
    and keeps track of which variables are currently basic/cobasic.

    Parameters
    ----------
    lcp : Lcp
        The LCP instance to build the tableau from.

    Attributes
    ----------
    n : int
        Problem dimension.
    A : list of list of int
        The scaled tableau, shape `(n, n + 2)`
        (columns correspond to `n + 1` cobasic variables, plus RHS).
    determinant : int
        Current tableau determinant (always positive after pivoting).
    scale_factor : list of int
        Per-column scale factors (LCM of denominators) used to keep
        the tableau in exact integer arithmetic.
    bas_cobas : list of int
        Location for each variable index: its tableau row (if basic) or
        ``n + column`` (if cobasic).
    which_var : list of int
        Inverse of `bas_cobas`: which variable occupies each row or column.
    pivot_count : int
        Number of pivots performed so far.
    lex_tested, lex_comparisons : list of int
        Per-column statistics from the lexicographic minimum-ratio test.
    """

    def __init__(self, lcp: Lcp) -> None:
        self.n: int = lcp.n
        n = self.n

        self.scale_factor: list[int] = [0] * (n + 2)  # 0 for z0, n+1 for RHS
        # tableau, long integer entries
        self.A: list[list[int]] = [[0] * (n + 2) for _ in range(n)]
        self.determinant: int = 1
        self.lex_tested: list[int] = [0] * (n + 1)
        self.lex_comparisons: list[int] = [0] * (n + 1)
        self.pivot_count: int = 0

        # variable encodings: VARS = 0..2n = Z(0) .. Z(n) W(1) .. W(n)
        # tableau columns: RHS n+1
        # bas_cobas[v] in 0..n-1: basic,   bas_cobas[v]   = tableau row
        # bas_cobas[v] in n..2n:  cobasic, bas_cobas[v]-n = tableau col
        self.bas_cobas: list[int] = [0] * (2 * n + 1)
        # which_var inverse of bas_cobas, shows which basic/cobasic vars
        self.which_var: list[int] = [0] * (2 * n + 1)
        for i in range(n + 1):  # variables Z(i) all cobasic
            self.bas_cobas[i] = n + i
            self.which_var[n + i] = i
        for i in range(n):  # variables W(i+1) all basic
            self.bas_cobas[n + 1 + i] = i
            self.which_var[i] = n + 1 + i
        # determine scale factors, lcm of denominators
        for j in range(n + 2):
            factor = 1
            for i in range(n):
                if j == 0:
                    den = lcp.d[i].denominator
                elif j == n + 1:  # RHS
                    den = lcp.q[i].denominator
                else:
                    den = lcp.M[i][j - 1].denominator
                # least common multiple
                factor *= den // math.gcd(factor, den)
            self.scale_factor[j] = factor
            # fill in column j of the tableau
            for i in range(n):
                if j == 0:
                    den = lcp.d[i].denominator
                    num = lcp.d[i].numerator
                elif j == n + 1:  # RHS
                    den = lcp.q[i].denominator
                    num = lcp.q[i].numerator
                else:
                    den = lcp.M[i][j - 1].denominator
                    num = lcp.M[i][j - 1].numerator
                self.A[i][j] = (factor // den) * num
            self.determinant = -1

    def __str__(self):
        out = "Determinant: " + str(self.determinant)
        n = self.n
        table = columnprint.ColumnPrint(n + 3)
        table.make_left(0)
        table.sprint("var")  # headers
        for j in range(n + 1):
            table.sprint(self.var_name(self.which_var[j + n]))
        table.sprint("RHS")
        table.sprint("scfa")  # scale factors
        for j in range(n + 2):
            if j == n + 1:  # RHS
                table.sprint(str(self.scale_factor[n + 1]))
            elif self.which_var[j + n] > n:  # col  j  is some  W
                table.sprint("1")
            else:
                table.sprint(str(self.scale_factor[self.which_var[j + n]]))
        table.newline()  # blank line
        for i in range(n):
            table.sprint(self.var_name(self.which_var[i]))
            for j in range(n + 2):
                s = str(self.A[i][j])
                if s == "0":
                    s = "."  # replace 0 by dot
                table.sprint(s)
        out += "\n" + str(table)
        out += "\n" + "-----------------end of tableau-----------------"
        return out

    def var_name(self, v: int) -> str:
        """Return the display name of variable index `v`, e.g. "z0" or "w3"."""
        if v > self.n:
            return "w" + str(v - self.n)
        else:
            return "z" + str(v)

    def assert_basic(self, v: int, info: str) -> None:
        """Assert that variable v is basic."""
        if self.bas_cobas[v] >= self.n:
            raise RuntimeError(
                f"({info}) Cobasic variable {self.var_name(v)} should be basic"
            )

    def assert_cobasic(self, v: int, info: str) -> None:
        """Assert that variable v is cobasic."""
        if self.bas_cobas[v] < self.n:
            raise RuntimeError(
                f"({info}) Basic variable {self.var_name(v)} should be cobasic"
            )

    def test_table_vars(self) -> None:
        """Check that `bas_cobas` and `which_var` are consistent inverses."""
        n = self.n
        for i in range(2 * n + 1):
            if self.bas_cobas[self.which_var[i]] != i:
                message = ""
                # injective suffices
                for j in range(2 * n + 1):
                    if j == i:
                        message += f"First problem for j={j}:\n"
                    message += (
                        f"j={j} self.bas_cobas[j]={self.bas_cobas[j]} "
                        f"self.which_var[j]={self.which_var[j]}\n"
                    )
                raise RuntimeError(f"test_table_vars() failed:\n{message}")

    def complement(self, v: int) -> int:
        """Return the complementary variable of `v` (Z(i) <-> W(i)).

        Parameters
        ----------
        v : int
            A variable index other than ``z0``.

        Returns
        -------
        int
            The complementary variable index.

        Raises
        ------
        RuntimeError
            If `v` is ``z0`` (0), which has no complement.
        """
        n = self.n
        if v == 0:
            raise RuntimeError("Attempt to find complement of z0")
        if v > n:
            return v - n
        else:
            return v + n

    def lex_min_var(self, enter: int) -> tuple[int, bool]:
        """Find the leaving variable via the lexicographic minimum-ratio test.

        Parameters
        ----------
        enter : int
            The entering variable index (must currently be cobasic).

        Returns
        -------
        leave : int
            The leaving variable index.
        z0_leave : bool
            True if ``z0`` is among the (possibly tied) leaving candidates,
            meaning the algorithm may terminate after this pivot.

        Raises
        ------
        RayTermination
            If no row has a positive entry in the entering column,
            meaning the algorithm has found an unbounded ray instead of a solution.
        """
        n = self.n
        A = self.A
        self.assert_cobasic(enter, "Lexminvar")
        col = self.bas_cobas[enter] - n  # entering tableau column
        leave_candidates: list[int] = []  # candidates(=rows) for leaving var
        for i in range(n):  # start with positives in entering col
            if A[i][col] > 0:
                leave_candidates.append(i)
        if not leave_candidates:
            raise RayTermination(enter, self)
        if len(leave_candidates) == 1:  # single positive entering value
            z0_leave = self.bas_cobas[0] == leave_candidates[0]
        # omitted from statistics: only one possible row
        # means no min-ratio test needed for leaving variable
        #     self.lex_tested[0] += 1
        #     self.lex_comparisons[0] += 1

        # as long as there is more than one leaving candidate,
        # perform a minimum ratio test for the columns
        # j in RHS,W(1)..W(n) in the tableau.
        # That test has an easy known result if the test
        # column is basic, or equal to the entering variable.
        j = 0  # going through j = 0..n
        while len(leave_candidates) > 1:
            if j > n:  # impossible, perturbed RHS should have full rank
                raise RuntimeError("lex-minratio test failed")
            self.lex_tested[j] += 1
            self.lex_comparisons[j] += len(leave_candidates)
            test_col = n + 1 if j == 0 else self.bas_cobas[n + j] - n
            if test_col != col:  # otherwise nothing changed
                if test_col >= 0:
                    # not a basic test column: perform minimum ratio tests
                    new_candidates = [leave_candidates[0]]
                    # new_candidates contains the new candidates
                    for i in range(1, len(leave_candidates)):
                        # investigate remaining candidates
                        # compare ratios via products
                        tmp1 = (
                            A[new_candidates[0]][test_col]
                            * A[leave_candidates[i]][col]
                        )
                        tmp2 = (
                            A[leave_candidates[i]][test_col]
                            * A[new_candidates[0]][col]
                        )
                        if tmp1 == tmp2:  # new ratio is the same as before
                            new_candidates.append(leave_candidates[i])
                        elif tmp1 > tmp2:  # new smaller ratio detected: reset
                            new_candidates = [leave_candidates[i]]
                        # else : unchanged candidates
                    leave_candidates = new_candidates
                else:  # test_col < 0: W(j) basic, eliminate its row
                    # from leave_candidates if in there, since test_col is
                    # the  jth  unit column (ratio too big)
                    wj = self.bas_cobas[j + n]
                    if wj in leave_candidates:
                        leave_candidates.remove(wj)
            # end of  if test_col != col
            # check if  z0  among the first-col leaving candidates
            if j == 0:
                z0_leave = self.bas_cobas[0] in leave_candidates
            j += 1  # end while
        assert len(leave_candidates) == 1
        return self.which_var[leave_candidates[0]], z0_leave

    # end of lex_min_var(enter)

    def negate_col(self, col: int) -> None:
        """Negate every entry in the given column of the tableau."""
        for i in range(self.n):
            self.A[i][col] = -self.A[i][col]

    def negate_row(self, row: int) -> None:
        """Negate every entry in the given row of the tableau."""
        for j in range(self.n + 2):
            self.A[row][j] = -self.A[row][j]

    def pivot(self, leave: int, enter: int) -> None:
        """Pivot the tableau, exchanging `leave` (basic) and `enter` (cobasic).

        Performs an exact-arithmetic pivot on ``A[row][col]``
        where `row`/`col` correspond to `leave`/`enter`,
        then renormalizes the tableau to have positive determinant
        and updates the basic/cobasic variables.

        Parameters
        ----------
        leave : int
            Variable currently basic that will become cobasic.
        enter : int
            Variable currently cobasic that will become basic.
        """
        n = self.n
        A = self.A
        row = self.bas_cobas[leave]
        col = self.bas_cobas[enter] - n
        pivot_element = A[row][col]  # becomes new determinant
        neg_piv = pivot_element < 0
        if neg_piv:
            pivot_element = -pivot_element
        for i in range(n):
            if i != row:
                nonzero = A[i][col] != 0
                for j in range(n + 2):
                    if j != col:
                        tmp1 = A[i][j] * pivot_element
                        if nonzero:
                            tmp2 = A[i][col] * A[row][j]
                            if neg_piv:
                                tmp1 += tmp2
                            else:
                                tmp1 -= tmp2
                        A[i][j] = tmp1 // self.determinant
                # row  i  has been dealt with, update  A[i][col]  safely
                if nonzero and not neg_piv:
                    A[i][col] = -A[i][col]
        # end of  for i
        A[row][col] = self.determinant
        if neg_piv:
            self.negate_row(row)
        self.determinant = pivot_element  # by construction always positive
        # update tableau variables
        self.bas_cobas[leave] = col + n
        self.which_var[col + n] = leave
        self.bas_cobas[enter] = row
        self.which_var[row] = enter

    # end of  pivot (leave, enter)

    #  end of class Tableau


class RayTermination(Exception):
    """Raised when Lemke's algorithm can't find a solution
    and terminates on a secondary ray.

    Parameters
    ----------
    enter : int
        The variable that could not enter the basis
        (no positive pivot candidate).
    tableau : Tableau
        The tableau at the point of termination.

    Attributes
    ----------
    enter : str
        Name of the variable that could not enter the basis.
    tableau : Tableau
        The incomplete tableau at termination.
    """

    def __init__(self, enter: int, tableau: Tableau) -> None:
        self.tableau = tableau
        self.enter: str = tableau.var_name(enter)
        super().__init__(
            "Ray termination when trying to enter " + self.enter
        )


def _out_statistics(tableau: Tableau) -> columnprint.ColumnPrint:
    """Helper to output statistics of minimum ratio test."""
    n = tableau.n
    lex_tested = tableau.lex_tested
    stats = columnprint.ColumnPrint(n + 2)
    stats.make_left(0)
    stats.sprint("lex-column")
    for i in range(n + 1):
        stats.iprint(i)
    stats.sprint("times tested")
    for i in range(n + 1):
        stats.iprint(lex_tested[i])
    if lex_tested[0] > 0:  # otherwise never a degeneracy
        stats.sprint("% of pivots")
        for i in range(0, n + 1):
            stats.iprint(round(lex_tested[i] * 100 / tableau.pivot_count))
        stats.sprint("avg comparisons")
        for i in range(n + 1):
            if lex_tested[i] > 0:
                x = round(tableau.lex_comparisons[i] * 10 / lex_tested[0])
                stats.sprint(str(x / 10.0))
            else:
                stats.sprint("-")
    return stats


@dataclass(frozen=True)
class LcpResult:
    """Result of solving a linear complementarity
    problem (LCP) with Lemke's algorithm."""

    success: bool
    """``True`` if a solution was found (``z0`` left the basis),
    ``False`` if the algorithm terminated on a ray."""

    num_pivots: int
    """Number of pivots performed."""

    basis: frozenset[str]
    """Names of the variables in the final basis, e.g. ``{'w1', 'z2'}``."""

    z0: fractions.Fraction
    """Final value of the artificial variable. Equals zero on success."""

    z: tuple[fractions.Fraction, ...]
    """Final values of the variables ``(z1, ..., zn)``."""

    w: tuple[fractions.Fraction, ...]
    """Final values of the variables ``(w1, ..., wn)``."""

    ray_entering_variable: str | None
    """Name of the entering variable when ray termination occurred,
    or ``None`` if the algorithm terminated with a solution."""

    def __str__(self):
        pivot_word = "pivot" if self.num_pivots == 1 else "pivots"

        if self.success:
            status = (
                f"Process finished successfully after {self.num_pivots} {pivot_word}.\n"
                "Solution found:\n"
            )
        else:
            status = (
                f"Terminated on a secondary ray after {self.num_pivots} {pivot_word}, "
                f"when trying to enter {self.ray_entering_variable}.\n"
                "Current basis not an LCP solution:\n"
            )

        # printout in columns to check complementarity
        n = len(self.w)

        sol = columnprint.ColumnPrint(n + 2)

        sol.sprint("basis=")
        # align basis elements with corresponding columns
        basis_by_row = {int(b[1:]): b for b in self.basis}
        for i in range(n + 1):
            sol.sprint(basis_by_row.get(i, "  "))

        sol.sprint("z=")
        sol.sprint(str(self.z0))
        for el in self.z:
            sol.sprint(str(el))

        sol.sprint("w=")
        sol.sprint("")  # no W(0)
        for el in self.w:
            sol.sprint(str(el))

        return status + str(sol)


class LemkeCallback:
    """Callback interface for observing the progress of `run_lemke`.

    Subclass and override any of these methods to log, print, or
    otherwise react to the algorithm's progress (e.g. `PrintingCallback`).
    All methods are no-ops by default.

    Each pivot triggers `on_pivot_start`. Every pivot except the last of a
    successful run is followed by `on_pivot_end`; the final pivot, which
    makes ``z0`` leave the basis, is followed by `on_done` instead.
    No callbacks are invoked when ``q >= 0``, since no pivoting is needed.
    """

    def on_start(self, lcp: Lcp, tableau: Tableau) -> None:
        """Called once, after the initial tableau is built."""

    def on_neg_col(self, tableau: Tableau) -> None:
        """Called after the RHS column is negated to start pivoting."""

    def on_pivot_start(self, tableau: Tableau, leave: str, enter: str) -> None:
        """Called before each pivot, with the chosen leave/enter variables."""

    def on_pivot_end(self, tableau: Tableau) -> None:
        """Called after each pivot completes, except the final one
        of a successful run (see `on_done`).
        """

    def on_done(self, tableau: Tableau, result: LcpResult) -> None:
        """Called once a complementary solution is found,
        with the final `LcpResult`.
        """

    def on_ray_termination(
        self, tableau: Tableau, result: LcpResult, message: str
    ) -> None:
        """Called if the algorithm terminates on a secondary ray,
        with the (unsuccessful) `LcpResult` and the termination message.
        """


class PrintingCallback(LemkeCallback):
    """A `LemkeCallback` that prints tableaus and progress to a stream.

    Parameters
    ----------
    stream : file-like, optional
        Where to print output. Default is `sys.stdout`.
    verbose : bool, optional
        If True, print the full tableau after every pivot,
        not just at the start and end. Default is False.
    z0 : bool, optional
        If True, print the current value of ``z0`` before each pivot.
        Default is False.
    lex_stats : bool, optional
        If True, print lexicographic minimum-ratio test statistics
        when the algorithm finishes successfully. Default is False.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        verbose: bool = False,
        z0: bool = False,
        lex_stats: bool = False,
    ) -> None:
        if stream is not None:
            self.stream = stream
        else:
            self.stream = sys.stdout
        self.verbose = verbose
        self.z0 = z0
        self.lex_stats = lex_stats

    def printout(self, *args) -> None:
        """Print `args` to this callback's stream."""
        print(*args, file=self.stream)

    def on_start(self, lcp: Lcp, tableau: Tableau) -> None:
        """Print the LCP instance and the initial tableau."""
        self.printout(
            f"verbose={self.verbose} z0={self.z0} lexstats={self.lex_stats}"
        )
        self.printout(lcp)
        self.printout("==================================")

        # if (flags.binitabl)
        self.printout("After filltableau:")
        self.printout(tableau)

    def on_neg_col(self, tableau: Tableau) -> None:
        """Print the tableau after negating the RHS column, if `verbose`."""
        # if (flags.binitabl)
        if self.verbose:
            self.printout("After negcol:")
            self.printout(tableau)

    def on_pivot_start(
        self,
        tableau: Tableau,
        leave: str,
        enter: str,
    ) -> None:
        """Print the chosen leaving/entering variables,
        and `z0`'s value if `z0` is set."""

        if self.z0:  # printout progress of z0
            z0_value = 0.0
            if tableau.bas_cobas[0] < tableau.n:  # z0 is basic
                z0_value = (
                    tableau.A[tableau.bas_cobas[0]][tableau.n + 1]
                    / tableau.determinant
                )
            self.printout(f"pivot count = {tableau.pivot_count}, z0 = {z0_value}")

        # if (flags.bdocupivot)
        self.printout(f"leaving: {leave.ljust(5)} entering: {enter}")

    def on_pivot_end(self, tableau: Tableau) -> None:
        """Print the tableau after the pivot completes, if `verbose`."""
        if self.verbose:
            self.printout(tableau)

    def on_done(self, tableau: Tableau, result: LcpResult) -> None:
        """Print the final tableau, the `result`,
        and lex-stats if `lex_stats` is set."""
        if self.z0:
            self.printout(f"pivot count = {tableau.pivot_count + 1}, z0 = 0.0")

        # if (flags.binitabl)
        self.printout("Final tableau:")
        self.printout(tableau)

        # if (flags.boutsol)
        self.printout(result)

        if self.lex_stats:
            # output statistics of minimum ratio test
            self.printout(_out_statistics(tableau))

    def on_ray_termination(
        self,
        tableau: Tableau,
        result: LcpResult,
        message: str,
    ) -> None:
        """Print the ray-termination message, tableau,
        and the (unsuccessful) `result`."""
        self.printout(message)
        self.printout(tableau)
        self.printout(result)


def result_from_tableau(
    tableau: Tableau,
    success: bool,
    ray_entering_variable: str | None = None,
) -> LcpResult:
    """Build an `LcpResult` from the current state of `tableau`."""

    n = tableau.n
    basis: set[str] = set()

    # [z0, z1, ..., zn, w1, ..., wn]
    solution = [fractions.Fraction(0) for _ in range(2 * n + 1)]

    for i in range(2 * n + 1):
        row = tableau.bas_cobas[i]
        if row < n:  # i is a basic variable
            num = tableau.A[row][n + 1]
            # value of  Z(i):   scfa[Z(i)]*rhs[row] / (scfa[RHS]*det)
            # value of  W(i-n): rhs[row] / (scfa[RHS]*det)
            if i <= n:  # computing Z(i)
                num *= tableau.scale_factor[i]
            solution[i] = fractions.Fraction(
                num,
                tableau.determinant * tableau.scale_factor[n + 1]
            )
            basis.add(tableau.var_name(i))

    return LcpResult(
        success=success,
        num_pivots=tableau.pivot_count,
        basis=frozenset(basis),
        z0=solution[0],
        z=tuple(solution[1:n + 1]),
        w=tuple(solution[n + 1:]),
        ray_entering_variable=ray_entering_variable,
    )


def run_lemke(
    *,
    lcp: Lcp,
    callback: LemkeCallback | None = None
) -> LcpResult:
    """Solve an LCP using Lemke's complementary pivoting algorithm.

    Parameters
    ----------
    lcp : Lcp
        The LCP instance to solve.
    callback : LemkeCallback, optional
        Hook invoked at each step of the algorithm to observe or report progress.
        Pass `PrintingCallback` for a ready-made implementation. Default is None.

    Returns
    -------
    LcpResult
        The outcome of the algorithm. If a complementary solution was found,
        `success` is True and `z`, `w` hold the solution.
        If the algorithm terminated on a secondary ray, `success` is False,
        `ray_entering_variable` names the variable that could not enter,
        and `z0`, `z`, `w` describe the final (non-solution) basis.
        If ``q >= 0`` the trivial solution ``z = 0, w = q`` is returned
        without pivoting and without invoking `callback`.

    Examples
    --------
    Basic usage with no callbacks:

    >>> from lemke.lemke import Lcp, run_lemke
    >>> problem = Lcp.from_file("examples/lcp_2x2")
    >>> result = run_lemke(lcp=problem)
    >>> result.success
    True
    >>> result.z
    (Fraction(2, 3), Fraction(2, 3))
    >>> print(result)
    Process finished successfully after 3 pivots.
    Solution found:
    basis=     z1  z2
        z=  0 2/3 2/3
        w=      0   0

    Usage with a printing callback (prints the given lcp, z0 at each step,
    initial and final tableaus, and the final result):

    >>> from lemke.lemke import Lcp, run_lemke, PrintingCallback
    >>> problem = Lcp.from_file("examples/lcp_2x2")
    >>> cb = PrintingCallback(z0=True)
    >>> result = run_lemke(lcp=problem, callback=cb)
    verbose=False z0=True lexstats=False
    n= 2
    M=
    1/2   1
    -1  5/2
    q=
    -1   -1
    d=
    1     1
    ==================================
    After filltableau:
    Determinant: -1
    var  z0 z1 z2 RHS
    scfa  1  2  2   1
    <BLANKLINE>
    w1    1  1  2  -1
    w2    1 -2  5  -1
    -----------------end of tableau-----------------
    pivot count = 1, z0 = 0.0
    leaving: w2    entering: z0
    pivot count = 2, z0 = 1.0
    leaving: w1    entering: z2
    pivot count = 3, z0 = 1.0
    leaving: z0    entering: z1
    pivot count = 4, z0 = 0.0
    Final tableau:
    Determinant: 9
    var  w2 z0 w1 RHS
    scfa  1  1  1   1
    <BLANKLINE>
    z2   -1  3 -2   3
    z1    2  3 -5   3
    -----------------end of tableau-----------------
    Process finished successfully after 3 pivots.
    Solution found:
    basis=     z1  z2
        z=  0 2/3 2/3
        w=      0   0
    """
    callback = callback or LemkeCallback()

    # trivial case (q >= 0)
    if all(element >= 0 for element in lcp.q):
        return LcpResult(
            success=True,
            num_pivots=0,
            basis=frozenset(f"w{i + 1}" for i in range(lcp.n)),
            z0=fractions.Fraction(0),
            z=(fractions.Fraction(0),) * lcp.n,
            w=tuple(fractions.Fraction(x) for x in lcp.q),
            ray_entering_variable=None,
        )

    try:
        tableau = Tableau(lcp)

        n = tableau.n
        tableau.pivot_count = 1
        # check if d is ok - TBC
        # if (flags.binitabl)
        callback.on_start(lcp=lcp, tableau=tableau)

        # z0 enters the basis to obtain lex-feasible solution
        enter = 0
        leave, z0_leave = tableau.lex_min_var(enter)
        # negate RHS
        tableau.negate_col(n + 1)
        callback.on_neg_col(tableau=tableau)

        while True:  # main loop of complementary pivoting
            tableau.test_table_vars()
            tableau.assert_basic(leave, "docupivot")
            tableau.assert_cobasic(enter, "docupivot")

            callback.on_pivot_start(
                tableau=tableau,
                leave=tableau.var_name(leave),
                enter=tableau.var_name(enter),
            )
            tableau.pivot(leave, enter)
            if z0_leave:
                break

            callback.on_pivot_end(tableau=tableau)

            enter = tableau.complement(leave)
            leave, z0_leave = tableau.lex_min_var(enter)
            tableau.pivot_count += 1

        result = result_from_tableau(tableau, True)
        callback.on_done(tableau=tableau, result=result)

        return result
    except RayTermination as e:
        result = result_from_tableau(
            tableau=e.tableau,
            success=False,
            ray_entering_variable=e.enter,
        )
        callback.on_ray_termination(message=str(e), result=result, tableau=e.tableau)
        return result


@click.command(
    context_settings={"help_option_names": ["-?", "-h", "--help"]},
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Printout intermediate tableaus",
)
@click.option(
    "--z0",
    is_flag=True,
    help="Show value of z0 at each step",
)
@click.option(
    "--decimals",
    default=utils.DEFAULT_DECIMALS,
    show_default=True,
    type=click.IntRange(min=0, max=utils.MAX_DECIMALS),
    metavar="INTEGER",
    help="Allowed digits in input after decimal point",
)
@click.argument(
    "lcp_filename",
    type=click.Path(exists=True, readable=True, file_okay=True, dir_okay=False),
)
def main(
    verbose: bool,
    z0: bool,
    decimals: int,
    lcp_filename: str,
) -> None:
    """
    Tool for solving linear complementarity problems using Lemke's algorithm.

    LCP_FILENAME is the path to the input file.
    """

    lcp = Lcp.from_file(lcp_filename, decimals)

    result = run_lemke(
        lcp=lcp,
        callback=PrintingCallback(stream=sys.stdout, verbose=verbose, z0=z0),
    )

    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    # m = lcp(3)
    # m.M[0][1] = fractions.Fraction(2,3)
    # printout(m)
    # printout()
    # exit(0)
    main()
