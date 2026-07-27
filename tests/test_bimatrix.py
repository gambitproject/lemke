"""
Test Lemke-Howson algorithm and tracing procedure on bimatrix games.
Tracing procedure is tested with a uniform prior, as well as random priors.
Seed is fixed, so that random priors are reproducible.

Conditions checked:
    For games with unique equilibrium:
    - Output matches precomputed solution.

    For all games:
    - Maximum regret is zero.
    - Output is a subset of the equilibria
      returned by pygambit.nash.enummixed_solve().
"""

import dataclasses
import random
import typing
from fractions import Fraction as Fr
from functools import partial
from pathlib import Path

import pygambit
import pytest

from lemke import randomstart
from lemke.bimatrix import bimatrix, uniform

FIXTURES_DIR = Path("tests/fixtures/bimatrix")


def lh_solver(G: bimatrix) -> list[list[Fr]]:
    """Run LH algorithm & return the list of equilibria found."""

    lh_eqs_dict = G.LH("1-" + str(G.A.numrows + G.A.numcolumns))
    return [list(eq_key) for eq_key in lh_eqs_dict]


def trace_uniform_prior(game: bimatrix) -> list[list[Fr]]:
    """Copied from bimatrix.py, but explicitly returns equilibria."""

    m = game.A.numrows
    n = game.A.numcolumns

    xprior = uniform(m)
    yprior = uniform(n)
    eq = game.runtrace(xprior, yprior)

    return [list(eq)]


# trace = 10, seed = 0
def trace_random_priors(
    game: bimatrix,
    trace,
    seed=None,
    accuracy=1000,
) -> list[list[Fr]]:
    """Copied from bimatrix.py, but explicitly returns equilibria."""

    if trace <= 0:
        raise ValueError("Number of priors must be a positive integer")
    m = game.A.numrows
    n = game.A.numcolumns
    trset = {}  # dict of equilibria, how often found

    for k in range(trace):
        if seed is not None:
            random.seed(10 * trace * seed + k)
        x = randomstart.randInSimplex(m)
        xprior = randomstart.roundArray(x, accuracy)
        y = randomstart.randInSimplex(n)
        yprior = randomstart.roundArray(y, accuracy)
        eq = game.runtrace(xprior, yprior)
        if eq in trset:
            trset[eq] += 1
        else:
            trset[eq] = 1

    return [list(eq) for eq in trset]


def build_pygambit_bimatrix_game(G: bimatrix) -> pygambit.Game:
    A = G.A.matrix
    B = G.B.matrix
    g = pygambit.Game.new_table([G.A.numrows, G.A.numcolumns])
    p1, p2 = g.players
    for i, row in enumerate(A):
        for j, val in enumerate(row):
            g[i, j][p1] = Fr(val)
            g[i, j][p2] = Fr(B[i][j])
    return g


@dataclasses.dataclass
class GameTestCase:
    factory: typing.Callable[[], bimatrix]
    expected: list[list[Fr]] | None = None
    regret_tol: Fr = Fr(0)
    prob_tol: Fr = Fr(0)


UNIQUE_PURE_NE_CASES = [
    pytest.param(
            GameTestCase(
                factory=lambda: bimatrix(FIXTURES_DIR / "unique_pure_single_strategy_1x1"),
                expected=[[Fr(1), Fr(1)]],
            ),
            id="unique_pure_single_strategy_1x1",
        ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "unique_pure_single_strategy_1x2"),
            expected=[[Fr(1), Fr(0), Fr(1)]],
        ),
        id="unique_pure_single_strategy_1x2",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "unique_pure_dominant_prisoners_dilemma"),
            expected=[[Fr(0), Fr(1), Fr(0), Fr(1)]]
        ),
        id="unique_pure_dominant_prisoners_dilemma",
    ),
]


UNIQUE_MIXED_NE_CASES = [
    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "unique_mixed_matching_pennies"),
            expected=[[Fr(1, 2), Fr(1, 2), Fr(1, 2), Fr(1, 2)]],
        ),
        id="unique_mixed_matching_pennies",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "unique_mixed_rock_paper_scissors"),
            expected=[[Fr(1, 3), Fr(1, 3), Fr(1, 3), Fr(1, 3), Fr(1, 3), Fr(1, 3)]],
        ),
        id="unique_mixed_rock_paper_scissors",
    ),
]


MULTIPLE_FINITE_NE_CASES = [
    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "multiple_finite_pure_coordination"),
        ),
        id="multiple_finite_pure_coordination",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "multiple_finite_battle_of_the_sexes"),
        ),
        id="multiple_finite_battle_of_the_sexes",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "multiple_finite_4x2"),
        ),
        id="multiple_finite_4x2",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "multiple_finite_3x2"),
        ),
        id="multiple_finite_3x2",
    ),
]


INFINITE_NE_CASES = [
    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "infinite_equilibria_degenerate_1"),
        ),
        id="infinite_equilibria_degenerate_1",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: bimatrix(FIXTURES_DIR / "infinite_equilibria_degenerate_2"),
        ),
        id="infinite_equilibria_degenerate_2",
    ),
]


SOLVERS = [
    pytest.param(lh_solver, id="LH"),
    pytest.param(trace_uniform_prior, id="trace_uniform"),
    pytest.param(partial(trace_random_priors, trace=10, seed=0), id="trace_random"),
]


UNIQUE_NE_CASES = UNIQUE_PURE_NE_CASES + UNIQUE_MIXED_NE_CASES


CASES = []
CASES += UNIQUE_NE_CASES
CASES += MULTIPLE_FINITE_NE_CASES
CASES += INFINITE_NE_CASES


@pytest.mark.parametrize("test_case", CASES)
@pytest.mark.parametrize("solver", SOLVERS)
def test_with_max_regret(test_case: GameTestCase, solver, subtests):
    G = test_case.factory()
    eqs = solver(G)

    m = G.A.numrows

    pygambit_game = build_pygambit_bimatrix_game(G)

    for eq_idx, eq in enumerate(eqs):
        x = eq[:m]
        y = eq[m:]

        profile = pygambit_game.mixed_strategy_profile([list(x), list(y)], rational=True)

        with subtests.test(f"Max regret for equilibrium {eq_idx}"):
            max_regret = profile.max_regret()
            assert max_regret <= test_case.regret_tol


@pytest.mark.parametrize("test_case", UNIQUE_NE_CASES)
@pytest.mark.parametrize("solver", SOLVERS)
def test_with_expected_results(test_case: GameTestCase, solver, subtests):
    """Tests both algorithms by comparing the output to the pre-computed unique solution."""

    G = test_case.factory()
    eqs = solver(G)

    with subtests.test("Only one equilibrium"):
        assert len(eqs) == 1

    equilibrium = eqs[0]
    expected = test_case.expected[0]

    with subtests.test("Length of equilibrium"):
        assert len(equilibrium) == len(expected)

    for i, (a, b) in enumerate(zip(equilibrium, expected)):
        with subtests.test(f"component {i}"):
            assert abs(a - b) <= test_case.prob_tol, (
                f"component {i}: actual {a}, expected {b}"
            )


@pytest.mark.parametrize("test_case", CASES)
@pytest.mark.parametrize("solver", SOLVERS)
def test_with_pygambit_enummixed(test_case: GameTestCase, solver, subtests):
    """Tests both algorithms against pygambit solutions."""

    G = test_case.factory()
    eqs = solver(G)

    g = build_pygambit_bimatrix_game(G)
    p1, p2 = g.players

    # enummixed_solve() is used to get all equilibria
    pygambit_eqs = []
    for eq in pygambit.nash.enummixed_solve(g, rational=True).equilibria:
        flat_eq = [s[1] for s in eq[p1]] + [s[1] for s in eq[p2]]
        pygambit_eqs.append([Fr(x) for x in flat_eq])  # convert to Fraction (it's Rational)

    # each equilibrium found by LH or tracing should appear in equilibria that pygambit found
    for idx, eq in enumerate(eqs):
        with subtests.test(f"Equilibrium {idx} pygambit check"):
            matched = any(
                all(abs(a - b) <= test_case.prob_tol for a, b in zip(eq, ne))
                for ne in pygambit_eqs
            )
            assert matched, f"Equilibrium not in pygambit set: {eq}"
