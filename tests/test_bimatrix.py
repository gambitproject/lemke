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
from lemke.bimatrix import Bimatrix, _uniform

FIXTURES_DIR = Path("tests/fixtures/bimatrix")


def lh_solver(game: Bimatrix) -> list[list[Fr]]:
    """Run LH algorithm & return the list of equilibria found."""

    lh_eqs_dict = game.lh("1-" + str(game.A.num_rows + game.A.num_columns))
    return [list(eq_key) for eq_key in lh_eqs_dict]


def trace_uniform_prior(game: Bimatrix) -> list[list[Fr]]:
    """Copied from bimatrix.py, but explicitly returns equilibria."""

    m = game.A.num_rows
    n = game.A.num_columns

    xprior = _uniform(m)
    yprior = _uniform(n)
    eq = game._run_trace(xprior, yprior)

    return [list(eq)]


# trace = 10, seed = 0
def trace_random_priors(
    game: Bimatrix,
    trace,
    seed=None,
    accuracy=1000,
) -> list[list[Fr]]:
    """Copied from bimatrix.py, but explicitly returns equilibria."""

    if trace <= 0:
        raise ValueError("Number of priors must be a positive integer")
    m = game.A.num_rows
    n = game.A.num_columns
    trset = {}  # dict of equilibria, how often found

    for k in range(trace):
        if seed is not None:
            random.seed(10 * trace * seed + k)
        x = randomstart._rand_in_simplex(m)
        xprior = randomstart._round_array(x, accuracy)
        y = randomstart._rand_in_simplex(n)
        yprior = randomstart._round_array(y, accuracy)
        eq = game._run_trace(xprior, yprior)
        if eq in trset:
            trset[eq] += 1
        else:
            trset[eq] = 1

    return [list(eq) for eq in trset]


def build_pygambit_bimatrix_game(game: Bimatrix) -> pygambit.Game:
    A = game.A.matrix
    B = game.B.matrix
    g = pygambit.Game.new_table([game.A.num_rows, game.A.num_columns])
    p1, p2 = g.players
    for i, row in enumerate(A):
        for j, val in enumerate(row):
            g[i, j][p1] = Fr(val)
            g[i, j][p2] = Fr(B[i][j])
    return g


@dataclasses.dataclass
class GameTestCase:
    factory: typing.Callable[[], Bimatrix]
    expected: list[list[Fr]] | None = None
    regret_tol: Fr = Fr(0)
    prob_tol: Fr = Fr(0)


UNIQUE_PURE_NE_CASES = [
    pytest.param(
            GameTestCase(
                factory=lambda: Bimatrix.from_file(
                    FIXTURES_DIR / "unique_pure_single_strategy_1x1"
                ),
                expected=[[Fr(1), Fr(1)]],
            ),
            id="unique_pure_single_strategy_1x1",
        ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "unique_pure_single_strategy_1x2"),
            expected=[[Fr(1), Fr(0), Fr(1)]],
        ),
        id="unique_pure_single_strategy_1x2",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(
                FIXTURES_DIR / "unique_pure_dominant_prisoners_dilemma"
            ),
            expected=[[Fr(0), Fr(1), Fr(0), Fr(1)]]
        ),
        id="unique_pure_dominant_prisoners_dilemma",
    ),
]


UNIQUE_MIXED_NE_CASES = [
    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "unique_mixed_matching_pennies"),
            expected=[[Fr(1, 2), Fr(1, 2), Fr(1, 2), Fr(1, 2)]],
        ),
        id="unique_mixed_matching_pennies",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "unique_mixed_rock_paper_scissors"),
            expected=[[Fr(1, 3), Fr(1, 3), Fr(1, 3), Fr(1, 3), Fr(1, 3), Fr(1, 3)]],
        ),
        id="unique_mixed_rock_paper_scissors",
    ),
]


MULTIPLE_FINITE_NE_CASES = [
    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "multiple_finite_pure_coordination"),
        ),
        id="multiple_finite_pure_coordination",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(
                FIXTURES_DIR / "multiple_finite_battle_of_the_sexes"
            ),
        ),
        id="multiple_finite_battle_of_the_sexes",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "multiple_finite_4x2"),
        ),
        id="multiple_finite_4x2",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "multiple_finite_3x2"),
        ),
        id="multiple_finite_3x2",
    ),
]


INFINITE_NE_CASES = [
    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "infinite_equilibria_degenerate_1"),
        ),
        id="infinite_equilibria_degenerate_1",
    ),

    pytest.param(
        GameTestCase(
            factory=lambda: Bimatrix.from_file(FIXTURES_DIR / "infinite_equilibria_degenerate_2"),
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
    game = test_case.factory()
    eqs = solver(game)

    m = game.A.num_rows

    pygambit_game = build_pygambit_bimatrix_game(game)

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

    game = test_case.factory()
    eqs = solver(game)

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

    game = test_case.factory()
    eqs = solver(game)

    pygambit_game = build_pygambit_bimatrix_game(game)
    p1, p2 = pygambit_game.players

    # enummixed_solve() is used to get all equilibria
    pygambit_eqs = []
    for eq in pygambit.nash.enummixed_solve(pygambit_game, rational=True).equilibria:
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
