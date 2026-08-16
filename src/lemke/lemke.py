"""Lemke's algorithm for solving linear complementarity problems (LCPs)."""

import fractions
import math  # gcd
import sys

import click

from . import columnprint, utils


class lcp:
    r"""A linear complementarity problem instance `(M, q, d)`.

    Represents the LCP :math:`w = q + Mz,\ w, z \ge 0,\ z^T w = 0`,
    together with a covering vector `d` used to start Lemke's algorithm.

    Can be constructed directly from `M`, `q`, `d`,
    or via `from_file` for problems stored in the LCP file format.

    Parameters
    ----------
    M : list of list of fractions.Fraction
        Square matrix of shape `(n, n)`.
    q : list of fractions.Fraction
        Vector of length `n`.
    d : list of fractions.Fraction
        Covering vector of length `n`.

    Attributes
    ----------
    M : list of list of fractions.Fraction
        As passed in.
    q, d : list of fractions.Fraction
        As passed in.
    n : int
        Dimension of the problem.

    Examples
    --------
    >>> from fractions import Fraction as F
    >>> from lemke.lemke import lcp
    >>> problem = lcp(
    ...     M=[[F(2), F(1)], [F(1), F(2)]],
    ...     q=[F(-1), F(-1)],
    ...     d=[F(1), F(1)],
    ... )
    >>> problem.n
    2
    """

    def __init__(self, M, q, d):
        self.M = M
        self.q = q
        self.d = d
        self.n = len(d)

    @classmethod
    def from_file(cls, filename):
        """Create an LCP instance from a text file.

        Expects a file starting with ``n= <dim>``,
        followed by keyword-labeled blocks ``M=``, ``q=``, ``d=``
        giving the matrix and vectors as whitespace-separated numbers.
        Numbers may be given as integers, fractions (e.g. ``1/3``),
        or decimals (e.g. ``0.3``).
        ``#`` starts a comment that runs to the end of the line.

        Parameters
        ----------
        filename : str or pathlib.Path
            Path to the LCP file.

        Returns
        -------
        lcp
            The LCP described by the file.

        Raises
        ------
        ValueError
            If the file does not start with ``n=``, doesn't contain
            the expected number of values, or has an unrecognized keyword.

        Examples
        --------
        Given a file ``lcp.txt`` containing::

            n= 2
            M= 2 1
               1 2
            q= -1 -1
            d= 1 1

        >>> from lemke.lemke import lcp
        >>> problem = lcp.from_file("lcp.txt")
        >>> print(problem.n)
        2
        """
        lines = utils.stripcomments(filename)
        # flatten into words
        words = utils.towords(lines)
        if words[0] != "n=":
            raise ValueError(
                f"lcp file {filename!r} must start with 'n=' lcpdim, e.g. 'n= 5', "
                f"not {words[0]!r}"
            )
        n = int(words[1])
        needfracs = n * n + 2 * n
        if len(words) != needfracs + 5:
            # printout("in lcp file '",filename,"':")
            raise ValueError(
                f"in lcp file {filename!r}: "
                f"n={n}, need keywords 'M=' 'q=' 'd=' and "
                f"n*n + n + n = {needfracs} fractions, got {len(words) - 5}"
            )
        M, q, d = None, None, None
        k = 2  # index in words
        while k < len(words):
            if words[k] == "M=":
                k += 1
                M = utils.tomatrix(n, n, words, k)
                k += n * n
            elif words[k] == "q=":
                k += 1
                q = utils.tovector(n, words, k)
                k += n
            elif words[k] == "d=":
                k += 1
                d = utils.tovector(n, words, k)
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
        m = columnprint.columnprint(n)
        m.makeLeft(0)
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
    #  end of class lcp


class tableau:
    """The tableau used to run Lemke's pivoting algorithm.

    Stores the LCP data as a scaled integer tableau
    (to allow exact arithmetic during pivoting)
    and keeps track of which variables are currently basic/cobasic.

    Parameters
    ----------
    Mqd : lcp
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
    scalefactor : list of int
        Per-column scale factors (LCM of denominators) used to keep
        the tableau in exact integer arithmetic.
    bascobas : list of int
        Location for each variable index: its tableau row (if basic) or
        ``n + column`` (if cobasic).
    whichvar : list of int
        Inverse of `bascobas`: which variable occupies each row or column.
    solution : list of fractions.Fraction
        Current solution vector, filled in by `createsol`.
    pivotcount : int
        Number of pivots performed so far.
    lextested, lexcomparisons : list of int
        Per-column statistics from the lexicographic minimum-ratio test.
    """

    def __init__(self, Mqd):
        self.n = Mqd.n
        n = self.n
        self.scalefactor = [0] * (n + 2)  # 0 for z0, n+1 for RHS
        # A = tableau, long integer entries
        # self.A = np.zeros( (n,n+2), dtype=object)
        self.A = [[]] * n
        for i in range(n):
            self.A[i] = [0] * (n + 2)
        self.determinant = 1
        self.lextested = [0] * (n + 1)
        self.lexcomparisons = [0] * (n + 1)
        self.pivotcount = 0
        self.solution = [fractions.Fraction(0)] * (2 * n + 1)  # all vars
        # variable encodings: VARS = 0..2n = Z(0) .. Z(n) W(1) .. W(n)
        # tableau columns: RHS n+1
        # bascobas[v] in 0..n-1: basic,   bascobas[v]   = tableau row
        # bascobas[v] in n..2n:  cobasic, bascobas[v]-n = tableau col
        self.bascobas = [0] * (2 * n + 1)
        # whichvar inverse of bascobas, shows which basic/cobasic vars
        self.whichvar = [0] * (2 * n + 1)
        for i in range(n + 1):  # variables Z(i) all cobasic
            self.bascobas[i] = n + i
            self.whichvar[n + i] = i
        for i in range(n):  # variables W(i+1) all basic
            self.bascobas[n + 1 + i] = i
            self.whichvar[i] = n + 1 + i
        # determine scale factors, lcm of denominators
        for j in range(n + 2):
            factor = 1
            for i in range(n):
                if j == 0:
                    den = Mqd.d[i].denominator
                elif j == n + 1:  # RHS
                    den = Mqd.q[i].denominator
                else:
                    den = Mqd.M[i][j - 1].denominator
                # least common multiple
                factor *= den // math.gcd(factor, den)
            self.scalefactor[j] = factor
            # fill in column j of A
            for i in range(n):
                if j == 0:
                    den = Mqd.d[i].denominator
                    num = Mqd.d[i].numerator
                elif j == n + 1:  # RHS
                    den = Mqd.q[i].denominator
                    num = Mqd.q[i].numerator
                else:
                    den = Mqd.M[i][j - 1].denominator
                    num = Mqd.M[i][j - 1].numerator
                self.A[i][j] = (factor // den) * num
            self.determinant = -1
        return

    def __str__(self):
        out = "Determinant: " + str(self.determinant)
        n = self.n
        tabl = columnprint.columnprint(n + 3)
        tabl.makeLeft(0)
        tabl.sprint("var")  # headers
        for j in range(n + 1):
            tabl.sprint(self.vartoa(self.whichvar[j + n]))
        tabl.sprint("RHS")
        tabl.sprint("scfa")  # scale factors
        for j in range(n + 2):
            if j == n + 1:  # RHS
                tabl.sprint(str(self.scalefactor[n + 1]))
            elif self.whichvar[j + n] > n:  # col  j  is some  W
                tabl.sprint("1")
            else:
                tabl.sprint(str(self.scalefactor[self.whichvar[j + n]]))
        tabl.newline()  # blank line
        for i in range(n):
            tabl.sprint(self.vartoa(self.whichvar[i]))
            for j in range(n + 2):
                s = str(self.A[i][j])
                if s == "0":
                    s = "."  # replace 0 by dot
                tabl.sprint(s)
        out += "\n" + str(tabl)
        out += "\n" + "-----------------end of tableau-----------------"
        return out

    def vartoa(self, v):
        """Return the display name of variable index `v`, e.g. "z0" or "w3"."""
        if v > self.n:
            return "w" + str(v - self.n)
        else:
            return "z" + str(v)

    def createsol(self):
        """Get solution from current tableau."""
        n = self.n
        for i in range(2 * n + 1):
            row = self.bascobas[i]
            if row < n:  # i is a basic variable
                num = self.A[row][n + 1]
                # value of  Z(i):   scfa[Z(i)]*rhs[row] / (scfa[RHS]*det)
                # value of  W(i-n): rhs[row] / (scfa[RHS]*det)
                if i <= n:  # computing Z(i)
                    num *= self.scalefactor[i]
                self.solution[i] = fractions.Fraction(num,
                                                      self.determinant * self.scalefactor[n + 1])
            else:  # i is nonbasic
                self.solution[i] = fractions.Fraction(0)

    def assertbasic(self, v, info):
        """Assert that variable v is basic."""
        if self.bascobas[v] >= self.n:
            raise RuntimeError(
                f"({info}) Cobasic variable {self.vartoa(v)} should be basic"
            )

    def assertcobasic(self, v, info):
        """Assert that variable v is cobasic."""
        if self.bascobas[v] < self.n:
            raise RuntimeError(
                f"({info}) Basic variable {self.vartoa(v)} should be cobasic"
            )

    def testtablvars(self):
        """Check that `bascobas` and `whichvar` are consistent inverses."""
        n = self.n
        for i in range(2 * n + 1):
            if self.bascobas[self.whichvar[i]] != i:
                message = ""
                # injective suffices
                for j in range(2 * n + 1):
                    if j == i:
                        message += f"First problem for j={j}:\n"
                    message += (
                        f"j={j} self.bascobas[j]={self.bascobas[j]} "
                        f"self.whichvar[j]={self.whichvar[j]}\n"
                    )
                raise RuntimeError(f"testtablvars() failed:\n{message}")

    def complement(self, v):
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

    def lexminvar(self, enter):
        """Find the leaving variable via the lexicographic minimum-ratio test.

        Parameters
        ----------
        enter : int
            The entering variable index (must currently be cobasic).

        Returns
        -------
        leave : int
            The leaving variable index.
        z0leave : bool
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
        self.assertcobasic(enter, "Lexminvar")
        col = self.bascobas[enter] - n  # entering tableau column
        leavecand = []  # candidates(=rows) for leaving var
        for i in range(n):  # start with positives in entering col
            if A[i][col] > 0:
                leavecand.append(i)
        if not leavecand:
            raise RayTermination(enter, self)
        if len(leavecand) == 1:  # single positive entering value
            z0leave = self.bascobas[0] == leavecand[0]
        # omitted from statistics: only one possible row
        # means no min-ratio test needed for leaving variable
        #     self.lextested[0] += 1
        #     self.lexcomparisons[0] += 1

        # as long as there is more than one leaving candidate,
        # perform a minimum ratio test for the columns
        # j in RHS,W(1)..W(n) in the tableau.
        # That test has an easy known result if the test
        # column is basic, or equal to the entering variable.
        j = 0  # going through j = 0..n
        while len(leavecand) > 1:
            if j > n:  # impossible, perturbed RHS should have full rank
                raise RuntimeError("lex-minratio test failed")
            self.lextested[j] += 1
            self.lexcomparisons[j] += len(leavecand)
            testcol = n + 1 if j == 0 else self.bascobas[n + j] - n
            if testcol != col:  # otherwise nothing changed
                if testcol >= 0:
                    # not a basic testcolumn: perform minimum ratio tests
                    newcand = [leavecand[0]]
                    # newcand  contains the new candidates
                    for i in range(1, len(leavecand)):
                        # investigate remaining candidates
                        # compare ratios via products
                        tmp1 = A[newcand[0]][testcol] * A[leavecand[i]][col]
                        tmp2 = A[leavecand[i]][testcol] * A[newcand[0]][col]
                        # sgn = np.sign(tmp1 - tmp2)
                        # if sgn==0:
                        if tmp1 == tmp2:  # new ratio is the same as before
                            newcand.append(leavecand[i])
                        elif tmp1 > tmp2:  # new smaller ratio detected: reset
                            newcand = [leavecand[i]]
                        # else : unchanged candidates
                    leavecand = newcand
                else:  # testcol < 0: W(j) basic, eliminate its row
                    # from  leavecand  if in there, since testcol is
                    # the  jth  unit column (ratio too big)
                    wj = self.bascobas[j + n]
                    if wj in leavecand:
                        leavecand.remove(wj)
            # end of  if testcol != col
            # check if  z0  among the first-col leaving candidates
            if j == 0:
                z0leave = self.bascobas[0] in leavecand
            j += 1  # end while
        assert (len(leavecand) == 1)
        return self.whichvar[leavecand[0]], z0leave

    # end of lexminvar(enter)

    def negcol(self, col):
        """Negate every entry in the given column of the tableau."""
        for i in range(self.n):
            self.A[i][col] = -self.A[i][col]

    def negrow(self, row):
        """Negate every entry in the given row of the tableau."""
        for j in range(self.n + 2):
            self.A[row][j] = -self.A[row][j]

    def pivot(self, leave, enter):
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
        row = self.bascobas[leave]
        col = self.bascobas[enter] - n
        pivelt = A[row][col]  # becomes new determinant
        negpiv = pivelt < 0
        if negpiv:
            pivelt = -pivelt
        for i in range(n):
            if i != row:
                nonzero = A[i][col] != 0
                for j in range(n + 2):
                    if j != col:
                        tmp1 = A[i][j] * pivelt
                        if nonzero:
                            tmp2 = A[i][col] * A[row][j]
                            if negpiv:
                                tmp1 += tmp2
                            else:
                                tmp1 -= tmp2
                        A[i][j] = tmp1 // self.determinant
                # row  i  has been dealt with, update  A[i][col]  safely
                if nonzero and not negpiv:
                    A[i][col] = -A[i][col]
        # end of  for i
        A[row][col] = self.determinant
        if negpiv:
            self.negrow(row)
        self.determinant = pivelt  # by construction always positive
        # update tableau variables
        self.bascobas[leave] = col + n
        self.whichvar[col + n] = leave
        self.bascobas[enter] = row
        self.whichvar[row] = enter

    # end of  pivot (leave, enter)

    #  end of class tableau


class RayTermination(Exception):
    """Raised when Lemke's algorithm can't find a solution
    and terminates on a secondary ray.

    Parameters
    ----------
    enter : int
        The variable that could not enter the basis
        (no positive pivot candidate).
    tableau : tableau
        The tableau at the point of termination.
        Its `solution` is populated before the exception is raised.

    Attributes
    ----------
    tableau : tableau
        The incomplete tableau at termination.
    """

    def __init__(self, enter, tableau):
        tableau.createsol()
        self.tableau = tableau
        super().__init__(
            "Ray termination when trying to enter " + tableau.vartoa(enter)
        )


def outsol(tableau):
    """Format the solution vector [z0, z1, ..., zn, w1, ..., wn] into columns."""
    # printout in columns to check complementarity
    n = tableau.n
    sol = columnprint.columnprint(n + 2)
    sol.sprint("basis=")
    for i in range(n + 1):
        if tableau.bascobas[i] < n:  # Z(i) is a basic variable
            s = tableau.vartoa(i)
        elif i > 0 and tableau.bascobas[n + i] < n:  # W(i) is a basic variable
            s = tableau.vartoa(n + i)
        else:
            s = "  "
        sol.sprint(s)
    sol.sprint("z=")
    for i in range(2 * n + 1):
        sol.sprint(str(tableau.solution[i]))
        if i == n:  # new line since printouting slack vars  w  next
            sol.sprint("w=")
            sol.sprint("")  # no W(0)
    return str(sol)


def outstatistics(tableau):
    """Helper to output statistics of minimum ratio test."""
    n = tableau.n
    lext = tableau.lextested
    stats = columnprint.columnprint(n + 2)
    stats.makeLeft(0)
    stats.sprint("lex-column")
    for i in range(n + 1):
        stats.iprint(i)
    stats.sprint("times tested")
    for i in range(n + 1):
        stats.iprint(lext[i])
    if lext[0] > 0:  # otherwise never a degeneracy
        stats.sprint("% of pivots")
        for i in range(0, n + 1):
            stats.iprint(round(lext[i] * 100 / tableau.pivotcount))
        stats.sprint("avg comparisons")
        for i in range(n + 1):
            if lext[i] > 0:
                x = round(tableau.lexcomparisons[i] * 10 / lext[0])
                stats.sprint(str(x / 10.0))
            else:
                stats.sprint("-")
    return stats


class LemkeCallback:
    """Callback interface for observing the progress of `runlemke`.

    Subclass and override any of these methods to log, print, or
    otherwise react to the algorithm's progress (e.g. `PrintingCallback`).
    All methods are no-ops by default.
    """

    def on_start(self, lcp, tableau):
        """Called once, after the initial tableau is built."""

    def on_negcol(self, tableau):
        """Called after the RHS column is negated to start pivoting."""

    def on_pivot_start(self, tableau, leave, enter):
        """Called before each pivot, with the chosen leave/enter variables."""

    def on_pivot_end(self, tableau):
        """Called after each pivot completes."""

    def on_done(self, tableau):
        """Called once a complementary solution is found."""

    def on_ray_termination(self, tableau, message):
        """Called if the algorithm terminates on a secondary ray."""


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
    lexstats : bool, optional
        If True, print lexicographic minimum-ratio test statistics
        when the algorithm finishes successfully. Default is False.
    """

    def __init__(
        self,
        stream=sys.stdout,
        verbose=False,
        z0=False,
        lexstats=False,
    ):
        self.stream = stream
        self.verbose = verbose
        self.z0 = z0
        self.lexstats = lexstats

    def printout(self, *args):
        """Print `args` to this callback's stream."""
        print(*args, file=self.stream)

    def on_start(self, lcp, tableau):
        """Print the LCP instance and the initial tableau."""
        self.printout(f"verbose={self.verbose} z0={self.z0} lexstats={self.lexstats}")
        self.printout(lcp)
        self.printout("==================================")

        # if (flags.binitabl)
        self.printout("After filltableau:")
        self.printout(tableau)

    def on_negcol(self, tableau):
        """Print the tableau after negating the RHS column, if `verbose`."""
        # if (flags.binitabl)
        if self.verbose:
            self.printout("After negcol:")
            self.printout(tableau)

    def on_pivot_start(self, tableau, leave, enter):
        """Print the chosen leaving/entering variables,
        and `z0`'s value if `z0` is set.
        """
        if self.z0:  # printout progress of z0
            z0_value = 0.0
            if tableau.bascobas[0] < tableau.n:  # z0 is basic
                z0_value = tableau.A[tableau.bascobas[0]][tableau.n + 1] / tableau.determinant
            self.printout(f"pivot count = {tableau.pivotcount}, z0 = {z0_value}")

        # if (flags.bdocupivot)
        self.printout(f"leaving: {leave.ljust(5)} entering: {enter}")

    def on_pivot_end(self, tableau):
        """Print the tableau after the pivot completes, if `verbose`."""
        if self.verbose:
            self.printout(tableau)

    def on_done(self, tableau):
        """Print the final tableau, solution,
        and lex-stats if `lexstats` is set.
        """
        if self.z0:
            self.printout(f"pivot count = {tableau.pivotcount + 1}, z0 = 0.0")

        # if (flags.binitabl)
        self.printout("Final tableau:")
        self.printout(tableau)

        # if (flags.boutsol)
        self.printout(outsol(tableau))

        if self.lexstats:
            # output statistics of minimum ratio test
            self.printout(outstatistics(tableau))

    def on_ray_termination(self, tableau, message):
        """Print the ray-termination message, tableau,
        and current (incomplete) solution.
        """
        self.printout(message)
        self.printout(tableau)
        self.printout("Current basis not an LCP solution:")
        self.printout(outsol(tableau))


def runlemke(*, lcp, callback=None):
    """Solve an LCP using Lemke's complementary pivoting algorithm.

    Parameters
    ----------
    lcp : lcp
        The LCP instance to solve.
    callback : LemkeCallback, optional
        Hook invoked at each step of the algorithm to observe or report progress.
        Pass `PrintingCallback` for a ready-made implementation. Default is None.

    Returns
    -------
    list of fractions.Fraction or None
        The full solution vector (length ``2n + 1``,
        indices ``z0, z1, ..., zn, w1, ..., wn``)
        if a complementary solution was found,
        or None if the algorithm couldn't find a solution
        and terminated on a secondary ray.

    Examples
    --------
    Basic usage with no callbacks:

    >>> from lemke.lemke import lcp, runlemke
    >>> problem = lcp.from_file("lcp.txt")
    >>> solution = runlemke(lcp=problem)
    >>> print(solution)
    [Fraction(0, 1), Fraction(2, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1)]

    Usage with a printing callback:

    >>> from lemke.lemke import lcp, runlemke, PrintingCallback
    >>> problem = lcp.from_file("lcp.txt")
    >>> cb = PrintingCallback(verbose=True, z0=True)
    >>> solution = runlemke(lcp=problem, callback=cb)
    # prints the given lcp, tableau and z0 at each step, and the final solution
    >>> print(solution)
    [Fraction(0, 1), Fraction(2, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1)]
    """
    callback = callback or LemkeCallback()

    try:
        tabl = tableau(lcp)

        n = tabl.n
        tabl.pivotcount = 1
        # check if d is ok - TBC
        # if (flags.binitabl)
        callback.on_start(lcp=lcp, tableau=tabl)

        # z0 enters the basis to obtain lex-feasible solution
        enter = 0
        leave, z0leave = tabl.lexminvar(enter)
        # negate RHS
        tabl.negcol(n + 1)
        callback.on_negcol(tableau=tabl)

        while True:  # main loop of complementary pivoting
            tabl.testtablvars()
            tabl.assertbasic(leave, "docupivot")
            tabl.assertcobasic(enter, "docupivot")

            callback.on_pivot_start(
                tableau=tabl,
                leave=tabl.vartoa(leave),
                enter=tabl.vartoa(enter),
            )
            tabl.pivot(leave, enter)
            if z0leave:
                break

            callback.on_pivot_end(tableau=tabl)

            enter = tabl.complement(leave)
            leave, z0leave = tabl.lexminvar(enter)
            tabl.pivotcount += 1

        tabl.createsol()
        callback.on_done(tableau=tabl)

        return tabl.solution
    except RayTermination as e:
        callback.on_ray_termination(message=str(e), tableau=e.tableau)
        return None


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
@click.argument(
    "lcpfilename",
    type=click.Path(exists=True, readable=True, file_okay=True, dir_okay=False),
)
def main(verbose, z0, lcpfilename):
    """
    Tool for solving linear complementarity problems using Lemke's algorithm.

    LCPFILENAME is the path to the input file.
    """

    m = lcp.from_file(lcpfilename)

    result = runlemke(
        lcp=m,
        callback=PrintingCallback(stream=sys.stdout, verbose=verbose, z0=z0),
    )

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    # m = lcp(3)
    # m.M[0][1] = fractions.Fraction(2,3)
    # printout(m)
    # printout()
    # exit(0)
    main()
