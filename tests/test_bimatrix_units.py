import re
import textwrap
from fractions import Fraction

import pytest
from click.testing import CliRunner

from lemke.bimatrix import (
    Bimatrix,
    PayoffMatrix,
    _range_split,
    _submatrix,
    _supports,
    _uniform,
    lh_cmd,
    trace_random_cmd,
    trace_uniform_cmd,
)
from lemke.lemke import LcpResult
from lemke.randomstart import MAX_ACCURACY
from lemke.utils import MAX_DECIMALS


# ---   PAYOFF MATRIX   --------------------------------------------------
@pytest.fixture
def small_payoff_matrix():
    return PayoffMatrix([
        [Fraction(1), Fraction(2)],
        [Fraction(3), Fraction(4)],
    ])


def test_payoff_matrix_init(small_payoff_matrix):
    pm = small_payoff_matrix
    assert pm.num_rows == 2
    assert pm.num_columns == 2

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

    assert pm.neg_shift == 5  # int(max) + 1

    expected = [
        [pm.neg_shift - pm.matrix[0][0], pm.neg_shift - pm.matrix[0][1]],
        [pm.neg_shift - pm.matrix[1][0], pm.neg_shift - pm.matrix[1][1]],
    ]

    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert pm.neg_matrix[i][j] == value


def test_add_row_updates_shape_max_min(small_payoff_matrix):
    pm = small_payoff_matrix
    pm.add_row([Fraction(10), Fraction(-10)])
    assert pm.num_rows == 3
    assert pm.matrix[2][0] == Fraction(10)
    assert pm.max == Fraction(10)
    assert pm.min == Fraction(-10)


def test_add_column_updates_shape_max_min(small_payoff_matrix):
    pm = small_payoff_matrix
    pm.add_column([Fraction(-5), Fraction(20)])
    assert pm.num_columns == 3
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
    game = Bimatrix.from_file(small_game_file)
    assert game.A.num_rows == 2
    assert game.A.num_columns == 2
    assert game.B.num_rows == 2
    assert game.B.num_columns == 2


def test_bimatrix_payoff_values(small_game_file):
    game = Bimatrix.from_file(small_game_file)

    expected = [
        [Fraction(1), Fraction(3, 4)],
        [Fraction(-1, 3), Fraction(1, 2)]
    ]
    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert game.A.matrix[i][j] == value

    expected = [
        [Fraction(2, 5), Fraction(3)],
        [Fraction(-2), Fraction(1)]
    ]
    for i, row in enumerate(expected):
        for j, value in enumerate(row):
            assert game.B.matrix[i][j] == value


def test_bimatrix_invalid_file(tmp_path):
    bad_content = "2 2\n1 2 3\n"
    path = tmp_path / "bad_game.txt"
    path.write_text(bad_content)

    with pytest.raises(ValueError):
        Bimatrix.from_file(str(path))


# ---   BIMATRIX LCP  ----------------------------------------------------
def test_q_last_two_entries_are_minus_one(small_game_file):
    game = Bimatrix.from_file(small_game_file)
    lcp = game.create_lcp()
    assert lcp.q[-1] == -1
    assert lcp.q[-2] == -1


def test_d_defaults_to_all_ones(small_game_file):
    game = Bimatrix.from_file(small_game_file)
    lcp = game.create_lcp()
    assert all(d == 1 for d in lcp.d)


def test_player_block_signs(small_game_file):
    game = Bimatrix.from_file(small_game_file)
    lcp = game.create_lcp()
    m, n = game.A.num_rows, game.A.num_columns
    lcp_dim = m + n + 2

    for i in range(m):
        assert lcp.M[i][lcp_dim - 2] == -1
    for i in range(m):
        assert lcp.M[lcp_dim - 2][i] == 1

    for j in range(m, m + n):
        assert lcp.M[j][lcp_dim - 1] == -1
    for j in range(m, m + n):
        assert lcp.M[lcp_dim - 1][j] == 1


def test_payoff_blocks_use_negmatrix(small_game_file):
    game = Bimatrix.from_file(small_game_file)
    lcp = game.create_lcp()
    m, n = game.A.num_rows, game.A.num_columns
    for i in range(m):
        for j in range(n):
            assert lcp.M[i][j + m] == game.A.neg_matrix[i][j]
    for j in range(n):
        for i in range(m):
            assert lcp.M[j + m][i] == game.B.neg_matrix[i][j]


# ---   TRACE WITH RANDOM PRIORS  -------------------------------------------------
@pytest.mark.parametrize("bad_priors", [0, -1, -100])
def test_rejects_non_positive_num_priors(small_game_file, bad_priors):
    game = Bimatrix.from_file(small_game_file)
    with pytest.raises(ValueError):
        game.trace_random_priors(bad_priors)


# ---   RUN_LEMKE FAILURE  -------------------------------------------------
@pytest.fixture
def lemke_failure(monkeypatch):
    failed_result = LcpResult(
        success=False,
        num_pivots=0,
        basis=frozenset(),
        z0=Fraction(-1),
        z=(),
        w=(),
        ray_entering_variable=None,
    )
    monkeypatch.setattr(
        "lemke.lemke.run_lemke",
        lambda **kwargs: failed_result,
    )


def test_run_lh_throws_on_lemke_failure(lemke_failure, small_game_file):
    game = Bimatrix.from_file(small_game_file)

    with pytest.raises(RuntimeError, match=re.escape("run_lemke() failed")):
        game._run_lh(1)


def test_run_trace_throws_on_lemke_failure(lemke_failure, small_game_file):
    game = Bimatrix.from_file(small_game_file)

    with pytest.raises(RuntimeError, match=re.escape("run_lemke() failed")):
        game._run_trace([0.5, 0.5], [0.4, 0.6])


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
def test_range_split(input, expected):
    assert _range_split(input, end_range=10) == expected


@pytest.mark.parametrize("n", [1, 2, 3, 7])
def test_uniform(n):
    result = _uniform(n)
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
    row_result, col_result = _supports(eq, m=2, n=2)
    assert row_result == row_expected
    assert col_result == col_expected


def test_submatrix():
    result = _submatrix(
        matrix=[
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ],
        row_set=[0, 2],
        col_set=[1, 2],
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
        (lh_cmd, []),
        (lh_cmd, [
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
    lh_cmd,
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
    lh_cmd,
    trace_uniform_cmd,
    trace_random_cmd,
])
def test_cli_rejects_directory(command, tmp_path):
    runner = CliRunner()
    result = runner.invoke(command, [str(tmp_path)])

    assert result.exit_code == 2
    assert "is a directory" in result.output.lower()


@pytest.mark.parametrize("command", [
    lh_cmd,
    trace_uniform_cmd,
    trace_random_cmd,
])
@pytest.mark.parametrize("decimals", ["-1", f"{MAX_DECIMALS + 1}"])
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
