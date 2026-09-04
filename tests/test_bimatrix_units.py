import textwrap
from fractions import Fraction

import pytest
from click.testing import CliRunner

from lemke.bimatrix import (
    bimatrix,
    lh,
    payoffmatrix,
    rangesplit,
    submatrix,
    supports,
    trace_random_cmd,
    trace_uniform_cmd,
    uniform,
)
from lemke.randomstart import MAX_ACCURACY
from lemke.utils import MAXDECIMALS


# ---   PAYOFF MATRIX   --------------------------------------------------
@pytest.fixture
def small_payoff_matrix():
    return payoffmatrix([
        [Fraction(1), Fraction(2)],
        [Fraction(3), Fraction(4)],
    ])


def test_payoff_matrix_init(small_payoff_matrix):
    pm = small_payoff_matrix
    assert pm.numrows == 2
    assert pm.numcolumns == 2

    assert all(
        isinstance(pm.matrix[i][j], Fraction)
        for i in range(2) for j in range(2)
    )
    assert pm.matrix[1][1] == Fraction(4)


def test_payoff_matrix_max_min(small_payoff_matrix):
    pm = small_payoff_matrix
    assert pm.max == Fraction(4)
    assert pm.min == Fraction(1)


def test_payoff_matrix_negshift_negmatrix(small_payoff_matrix):
    pm = small_payoff_matrix

    assert pm.negshift == 5  # int(max) + 1

    expected = [
        [pm.negshift - pm.matrix[0][0], pm.negshift - pm.matrix[0][1]],
        [pm.negshift - pm.matrix[1][0], pm.negshift - pm.matrix[1][1]],
    ]

    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert pm.negmatrix[i][j] == value


def test_addrow_updates_shape_max_min(small_payoff_matrix):
    pm = small_payoff_matrix
    pm.addrow([Fraction(10), Fraction(-10)])
    assert pm.numrows == 3
    assert pm.matrix[2][0] == Fraction(10)
    assert pm.max == Fraction(10)
    assert pm.min == Fraction(-10)


def test_addcolumn_updates_shape_max_min(small_payoff_matrix):
    pm = small_payoff_matrix
    pm.addcolumn([Fraction(-5), Fraction(20)])
    assert pm.numcolumns == 3
    assert pm.matrix[0][2] == Fraction(-5)
    assert pm.max == Fraction(20)
    assert pm.min == Fraction(-5)


# ---   BIMATRIX INIT   --------------------------------------------------
@pytest.fixture
def small_game_file(tmp_path):
    content = textwrap.dedent("""
        2 2

        # A=
        1     0.75
        -1/3  2/4

        # B=
        .4 3/1
        -2  1.0
    """)
    path = tmp_path / "small_game.txt"
    path.write_text(content)
    return str(path)


def test_bimatrix_dimensions(small_game_file):
    G = bimatrix.from_file(small_game_file)
    assert G.A.numrows == 2
    assert G.A.numcolumns == 2
    assert G.B.numrows == 2
    assert G.B.numcolumns == 2


def test_bimatrix_payoff_values(small_game_file):
    G = bimatrix.from_file(small_game_file)

    expected = [
        [Fraction(1), Fraction(3, 4)],
        [Fraction(-1, 3), Fraction(1, 2)]
    ]
    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert G.A.matrix[i][j] == value

    expected = [
        [Fraction(2, 5), Fraction(3)],
        [Fraction(-2), Fraction(1)]
    ]
    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert G.B.matrix[i][j] == value


def test_bimatrix_invalid_file_exits(tmp_path):
    bad_content = "2 2\n1 2 3\n"
    path = tmp_path / "bad_game.txt"
    path.write_text(bad_content)
    with pytest.raises(SystemExit):
        bimatrix.from_file(str(path))


# ---   BIMATRIX LCP  ----------------------------------------------------
def test_q_last_two_entries_are_minus_one(small_game_file):
    G = bimatrix.from_file(small_game_file)
    lcp = G.createLCP()
    assert lcp.q[-1] == -1
    assert lcp.q[-2] == -1


def test_d_defaults_to_all_ones(small_game_file):
    G = bimatrix.from_file(small_game_file)
    lcp = G.createLCP()
    assert all(d == 1 for d in lcp.d)


def test_player_block_signs(small_game_file):
    G = bimatrix.from_file(small_game_file)
    lcp = G.createLCP()
    m, n = G.A.numrows, G.A.numcolumns
    lcpdim = m + n + 2

    for i in range(m):
        assert lcp.M[i][lcpdim - 2] == -1
    for i in range(m):
        assert lcp.M[lcpdim - 2][i] == 1

    for j in range(m, m + n):
        assert lcp.M[j][lcpdim - 1] == -1
    for j in range(m, m + n):
        assert lcp.M[lcpdim - 1][j] == 1


def test_payoff_blocks_use_negmatrix(small_game_file):
    G = bimatrix.from_file(small_game_file)
    lcp = G.createLCP()
    m, n = G.A.numrows, G.A.numcolumns
    for i in range(m):
        for j in range(n):
            assert lcp.M[i][j + m] == G.A.negmatrix[i][j]
    for j in range(n):
        for i in range(m):
            assert lcp.M[j + m][i] == G.B.negmatrix[i][j]


# ---   TRACE WITH RANDOM PRIORS  -------------------------------------------------
@pytest.mark.parametrize("bad_priors", [0, -1, -100])
def test_rejects_non_positive_num_priors(small_game_file, bad_priors):
    G = bimatrix.from_file(small_game_file)
    with pytest.raises(ValueError):
        G.trace_random_priors(bad_priors)


# ---   HELPER FUNCTIONS   --------------------------------------------------------
@pytest.mark.parametrize(
    "input, expected",
    [
        ("1,3,5", [1, 3, 5]),                       # single numbers
        ("1, 3, 5", [1, 3, 5]),                     # single numbers with space
        ("1-3", [1, 2, 3]),                         # simple range
        ("1-3,10,4-7", [1, 2, 3, 10, 4, 5, 6, 7]),  # mixed
        ("8-", [8, 9, 10]),                         # open-ended range
        ("1,8-", [1, 8, 9, 10]),                    # mixed with open-ended range
        ("20-30", []),                              # range beyond "endrange"
        ("1,,3", [1, 3]),                           # empty parts
        ("", []),                                   # empty input string
    ]
)
def test_rangesplit(input, expected):
    assert rangesplit(input, endrange=10) == expected


@pytest.mark.parametrize("n", [1, 2, 3, 7])
def test_uniform(n):
    result = uniform(n)
    assert len(result) == n
    assert sum(result) == Fraction(1, 1)
    assert all(isinstance(x, Fraction) for x in result)


@pytest.mark.parametrize(
    "eq, row_expected, col_expected",
    [
        ((0, 0, 0, 0), [], []),
        ((1, 1, 1, 1), [0, 1], [0, 1]),
        ((1, 2, 0, 3), [0, 1], [1]),
    ]
)
def test_supports(eq, row_expected, col_expected):
    row_result, col_result = supports(eq, m=2, n=2)
    assert row_result == row_expected
    assert col_result == col_expected


def test_submatrix():
    result = submatrix(
        A=[
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ],
        rowset=[0, 2],
        colset=[1, 2],
    )
    expected = [
        [2, 3],
        [8, 9],
    ]

    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert result[i][j] == value


# ---   CLI   ------------------------------------------------------------
@pytest.mark.parametrize(
    "command, args",
    [
        (lh, []),
        (lh, [
            "--decimals", "10",
            "--labels", "1-2",
        ]),

        (trace_uniform_cmd, []),
        (trace_uniform_cmd, [
            "--decimals", "10",
        ]),

        (trace_random_cmd, []),
        (trace_random_cmd, [
            "--decimals", "10",
            "--priors", "10",
            "--seed", "42",
            "--accuracy", "100",
        ]),
    ]
)
def test_cli_runs_without_error(command, args, small_game_file):
    runner = CliRunner()
    result = runner.invoke(command, [str(small_game_file)] + args)

    assert result.exit_code == 0


@pytest.mark.parametrize("command", [
    lh,
    trace_uniform_cmd,
    trace_random_cmd,
])
def test_cli_rejects_missing_file(command, tmp_path):
    missing_path = tmp_path / "missing"

    runner = CliRunner()
    result = runner.invoke(command, [str(missing_path)])

    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()


@pytest.mark.parametrize("command", [
    lh,
    trace_uniform_cmd,
    trace_random_cmd,
])
def test_cli_rejects_directory(command, tmp_path):
    runner = CliRunner()
    result = runner.invoke(command, [str(tmp_path)])

    assert result.exit_code == 2
    assert "is a directory" in result.output.lower()


@pytest.mark.parametrize("command", [
    lh,
    trace_uniform_cmd,
    trace_random_cmd,
])
@pytest.mark.parametrize("decimals", ["-1", f"{MAXDECIMALS + 1}"])
def test_cli_invalid_decimals(command, decimals, tmp_path):
    runner = CliRunner()
    result = runner.invoke(command, [str(tmp_path), "--decimals", decimals])
    assert result.exit_code != 0
    assert "Invalid value" in result.output


@pytest.mark.parametrize("priors", ["-1", "0"])
def test_trace_random_invalid_priors(priors, tmp_path):
    runner = CliRunner()
    result = runner.invoke(trace_random_cmd, [str(tmp_path), "--priors", priors])
    assert result.exit_code != 0
    assert "Invalid value" in result.output


@pytest.mark.parametrize("accuracy", ["-1", "0", f"{MAX_ACCURACY + 1}"])
def test_trace_random_invalid_accuracy(accuracy, tmp_path):
    runner = CliRunner()
    result = runner.invoke(trace_random_cmd, ["--accuracy", accuracy])
    assert result.exit_code != 0
    assert "Invalid value" in result.output
