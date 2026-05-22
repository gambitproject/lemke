"""Tests for Lemke's algorithm on LCPs."""

from dataclasses import dataclass
from fractions import Fraction as Fr
from pathlib import Path
from typing import Callable

import pytest

from src.lemke.lemke import lcp, tableau

FIXTURES_DIR = Path("tests/fixtures/lcp")


def lemke_solver(lcp_instance: lcp) -> list[Fr]:
    """Runs Lemke's algorithm on the given LCP and returns the solution."""

    tabl = tableau(lcp_instance)
    tabl.runlemke(verbose=False, z0=False, silent=False)
    return tabl.solution


@dataclass
class LCPTestCase:
    """Defines data for one LCP test case for Lemke's algorithm."""
    factory: Callable[[], lcp]
    expected: list[Fr] | None = None
    tol: Fr = Fr(0)


# ---   NO PIVOTING   --------------------------------------------------------------------
# Trivial cases where q >= 0
# z = 0 is immediately a valid solution and the algorithm should return without pivoting
TRIVIAL_CASES = [
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "trivial_q_pos_M_arbitrary"),
            expected=[Fr(0), Fr(0), Fr(0), Fr(3), Fr(1)],
        ),
        id="trivial_q_pos_M_arbitrary",
    ),

    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "trivial_q_zero_M_identity"),
            expected=[Fr(0), Fr(0), Fr(0), Fr(0), Fr(0)],
        ),
        id="trivial_q_zero_M_identity",
    ),

    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "trivial_q_zero_M_zero"),
            expected=[Fr(0), Fr(0), Fr(0), Fr(0), Fr(0)],
        ),
        id="trivial_q_zero_M_zero",
    ),
]


# ---   PIVOTING (LEAVING VARIABLE UNIQUE)   ----------------------------
# Cases where the ratio test always produces a unique leaving variable
NON_DEGENERATE_CASES = [
    # example 4.3.3 (Cottle, Pang, Stone)
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "non_degenerate_book_ex_3x3"),
            expected=[Fr(0), Fr(0), Fr(1), Fr(3), Fr(2), Fr(0), Fr(0)],
        ),
        id="non_degenerate_book_ex_3x3",
    ),

    # example 4.4.17 (Cottle, Pang, Stone)
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "non_degenerate_book_ex_4x4"),
            expected=[Fr(0), Fr(0), Fr(1, 2), Fr(0), Fr(0), Fr(1, 2), Fr(0), Fr(11, 2), Fr(4)],
        ),
        id="non_degenerate_book_ex_4x4",
    ),

    # M > 0, q < 0
    # There is a unique solution: z = -q/M
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "non_degenerate_1x1"),
            expected=[Fr(0), Fr(329, 20), Fr(0)],
        ),
        id="non_degenerate_1x1",
    ),

    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "non_degenerate_2x2"),
            expected=[Fr(0), Fr(2), Fr(1), Fr(0), Fr(0)],
        ),
        id="non_degenerate_2x2",
    ),

    # M = I, q has no 0 entries
    # There is a unique solution: z[i] = max(0, -q[i]), w[i] = max(0, q[i])
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "non_degenerate_M_identity"),
            expected=[Fr(0), Fr(51, 10), Fr(0), Fr(0), Fr(8), Fr(0), Fr(2, 7), Fr(10), Fr(0)],
        ),
        id="non_degenerate_M_identity",
    ),
]


# ---   PIVOTING (LEAVING VARIABLE NOT UNIQUE)   -------------------------------
# Cases for which multiple candidates can be chosen as the leaving variable.
# The lexicographic minimum ratio test should be used for tie-breaking.
DEGENERATE_CASES = [
    # page 141 in Cottle, Pang, Stone (1992)
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "degenerate_tie_in_initial_lexmin"),
            expected=[Fr(0), Fr(0), Fr(1), Fr(0), Fr(0)],
        ),
        id="degenerate_tie_in_initial_lexmin",
    ),

    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "degenerate_tie_in_noninitial_lexmin"),
            expected=[Fr(0), Fr(0), Fr(1), Fr(0), Fr(0)],
        ),
        id="degenerate_tie_in_noninitial_lexmin",
    ),

    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "degenerate_tie_in_several_lexmins"),
            expected=[Fr(0), Fr(0), Fr(1), Fr(0), Fr(1), Fr(0), Fr(0)],
        ),
        id="degenerate_tie_in_several_lexmins",
    ),
]


SUCCESS_CASES = []
# SUCCESS_CASES += TRIVIAL_CASES
SUCCESS_CASES += NON_DEGENERATE_CASES
SUCCESS_CASES += DEGENERATE_CASES


@pytest.mark.parametrize("test_case", SUCCESS_CASES)
def test_with_expected_results(test_case: LCPTestCase, subtests):
    """
    Test the Lemke solver on LCPs with a known solution
    by comparing the solution size and values to the expected results.
    """

    lcp_instance = test_case.factory()
    sol = lemke_solver(lcp_instance)
    n = lcp_instance.n

    with subtests.test("Solution length"):
        assert len(sol) == 2 * n + 1

    for i, val in enumerate(sol):
        label = f"z{i}" if i <= n else f"w{i - n}"
        expected_val = test_case.expected[i]

        with subtests.test(f"{label} value"):
            assert abs(val - expected_val) <= test_case.tol


@pytest.mark.parametrize("test_case", SUCCESS_CASES)
def test_with_lcp_conditions(test_case: LCPTestCase, subtests):
    """
    Test the Lemke solver output by verifying LCP conditions:

    - Artificial variable z0 = 0
    - Nonnegativity: z >= 0, w >= 0
    - Complementarity: z[i] * w[i] = 0 (for each i)
    - Equation is satisfied: w = M * z + q
    """

    lcp_instance = test_case.factory()
    sol = lemke_solver(lcp_instance)

    # solution format: [z0, z1..zn, w1..wn]
    n = lcp_instance.n
    z0 = sol[0]
    z = sol[1:n + 1]
    w = sol[n + 1:]

    with subtests.test("z0 = 0"):
        assert z0 == Fr(0)

    for i, val in enumerate(z):
        with subtests.test(f"z{i + 1} nonnegativity"):
            assert val >= 0
    for i, val in enumerate(w):
        with subtests.test(f"w{i + 1} nonnegativity"):
            assert val >= 0

    for i in range(n):
        with subtests.test(f"z{i + 1} * w{i + 1} = 0"):
            assert abs(z[i] * w[i]) <= test_case.tol

    for i in range(n):
        expected_w = sum(lcp_instance.M[i][j] * z[j] for j in range(n)) + lcp_instance.q[i]
        with subtests.test(f"w{i + 1} = M * z + q"):
            assert abs(w[i] - expected_w) <= test_case.tol


# ---   NO SOLUTION   --------------------------------------------------------------------
# Cases where no solution exists
# Lemke's algorithm should terminate by reporting a secondary ray rather than a solution
FAILURE_CASES = [
    # M = 0, q < 0
    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "failure_after_first_pivot"),
        ),
        id="failure_after_first_pivot",
    ),

    pytest.param(
        LCPTestCase(
            factory=lambda: lcp(FIXTURES_DIR / "failure_after_several_pivots"),
        ),
        id="failure_after_several_pivots",
    ),
]


@pytest.mark.parametrize("test_case", FAILURE_CASES)
def test_failure(test_case: LCPTestCase):
    """
    Test the Lemke solver on LCPs that terminate on a secondary ray 
    by verifying that it raises SystemExit with code 1.
    """
    lcp_instance = test_case.factory()

    with pytest.raises(SystemExit) as exc_info:
        lemke_solver(lcp_instance)

    assert exc_info.value.code == 1
