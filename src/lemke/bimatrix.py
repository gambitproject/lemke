# bimatrix class

import fractions
import random  # random.seed
from functools import wraps

import click
import numpy as np

from . import columnprint, lemke, randomstart, utils
from .randomstart import MAX_ACCURACY

# file format:
# <m> <n>
# m*n entries of A, separated by blanks / newlines
# m*n entries of B, separated by blanks / newlines
#
# blank lines or lines starting with "#" are ignored

# defaults
# MAXDIM = 2000 # largest allowed value for m and n; not used yet


# list generated from string s such as "1-3,10,4-7", all not
# larger than endrange (50 is arbitrary default) and at least 1
def rangesplit(s, endrange=50):
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


# used for both A and B
class payoffmatrix:
    # create matrix from any numerical matrix
    def __init__(self, A):
        AA = np.array(A, dtype=object)
        if not all(isinstance(x, fractions.Fraction) for x in AA.flat):
            raise TypeError("matrix must contain only Fraction values")
        m, n = AA.shape
        self.numrows = m
        self.numcolumns = n
        self.matrix = AA
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
        self.max = self.matrix[0][0]
        self.min = self.matrix[0][0]
        self.updatemaxmin(0, 0)

    # add full row, row must be of size n
    def addrow(self, row):
        if not all(isinstance(x, fractions.Fraction) for x in row):
            raise TypeError("New row must contain only Fraction values")
        self.matrix = np.vstack([self.matrix, row])
        self.numrows += 1
        self.updatemaxmin(self.numrows - 1, 0)

    # add full column, col must be of size m
    def addcolumn(self, col):
        if not all(isinstance(x, fractions.Fraction) for x in col):
            raise TypeError("New column must contain only Fraction values")
        self.matrix = np.column_stack([self.matrix, col])
        self.numcolumns += 1
        self.updatemaxmin(0, self.numcolumns - 1)


class bimatrix:
    def __init__(self, A, B):
        self.A = A
        self.B = B

    # create A,B from file
    @classmethod
    def from_file(cls, filename, decimals=utils.DEFAULT_DECIMALS):
        utils.validate_decimals(decimals)
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
        C = utils.tomatrix(m, n, words, k, decimals)
        A = payoffmatrix(C)
        k += m * n
        C = utils.tomatrix(m, n, words, k, decimals)
        B = payoffmatrix(C)
        return cls(A, B)

    def __str__(self):
        out = "# m,n= \n" + str(self.A.numrows)
        out += " " + str(self.A.numcolumns)
        out += "\n# A= \n" + str(self.A)
        out += "\n# B= \n" + str(self.B)
        return out

    def createLCP(self):
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
        lcp = self.createLCP()
        lcp.d[droppedlabel - 1] = 0  # subsidize this label
        # tabl.runlemke(verbose=True, lexstats=True, z0=gz0)

        result = lemke.runlemke(lcp=lcp)
        if result is None:
            raise RuntimeError("runlemke() failed to find a solution unexpectedly.")

        equilibrium = result[1: lcp.n - 1]
        return tuple(equilibrium)

    def LH(self, LHstring):
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
        m = self.A.numrows
        n = self.A.numcolumns

        print("-------- statistics of equilibria found: --------")
        for eq, count in equilibria.items():
            print(count, "times found", str_eq(eq, m, n))
        print(total_priors, "total priors,", len(equilibria), "equilibria found")

    def eqindex(self, eq, m, n):
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
    return np.array([fractions.Fraction(1, n) for _ in range(n)])


def str_eq(eq, m, n):
    x = "(" + ",".join([str(x) for x in eq[0:m]]) + ")"
    y = "(" + ",".join([str(x) for x in eq[m: m + n]]) + ")"
    rowset, colset = supports(eq, m, n)
    return x + "," + y + "\n    supports: " + str(rowset) + str(colset)


def supports(eq, m, n):
    rowset = [i for i in range(m) if eq[i] != 0]
    colset = [j for j in range(n) if eq[m + j] != 0]
    return rowset, colset


def submatrix(A, rowset, colset):
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
        default=utils.DEFAULT_DECIMALS,
        show_default=True,
        type=click.IntRange(min=0, max=utils.MAXDECIMALS),
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


@main.command()
@common_options
@click.option(
    "--labels",
    default="1-",
    help="Missing labels, e.g. 1,3-5,7-  "
         "[default: all labels]",
)
def lh(filename, decimals, labels):
    """Find equilibria using the Lemke-Howson algorithm."""

    G = bimatrix.from_file(filename, decimals)
    G.LH(labels)


@main.group()
def trace():
    """Find equilibria using the tracing procedure."""
    pass


@trace.command(name="uniform")
@common_options
def trace_uniform_cmd(filename, decimals):
    """Trace using a uniform prior."""

    G = bimatrix.from_file(filename, decimals)
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
def trace_random_cmd(filename, decimals, priors, seed, accuracy):
    """Trace using random prior(s)."""

    G = bimatrix.from_file(filename, decimals)
    G.trace_random_priors(priors, seed, accuracy)
