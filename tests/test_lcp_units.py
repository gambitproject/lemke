from fractions import Fraction

import pytest
from click.testing import CliRunner

from lemke.lemke import (
    RayTermination,
    lcp,
    main,
    tableau,
)


def get_empty_lcp(n):
    return lcp(
        M=[[0] * n for _ in range(n)],
        q=[0] * n,
        d=[0] * n,
    )


# ---   LCP   -------------------------------------------------------
@pytest.mark.parametrize("raw, expected", [
    ("1",    Fraction(1)),
    ("0.75", Fraction(3, 4)),
    ("-1/3", Fraction(-1, 3)),
    ("2/4",  Fraction(1, 2)),
])
def test_lcp_valid_file(tmp_path, raw, expected):
    content = f"n= 1\nM= {raw}\nq= 1\nd= 1\n"
    file_path = tmp_path / "lcp"
    file_path.write_text(content)

    m = lcp.from_file(str(file_path))
    assert m.M[0][0] == expected


@pytest.mark.parametrize(
    "raw, expected, decimals",
    [
        ("0.00015", Fraction(2, 10000), 4),
        ("0.145", Fraction(3, 20), 2),
        ("9999999999999991.1", Fraction(9999999999999991, 1), 0),
        ("9999999999999999.1", Fraction(99999999999999991, 10), 4),
    ]
)
def test_lcp_file_parsing_in_fractions(tmp_path, raw, expected, decimals):
    content = f"n= 1\nM= {raw}\nq= 1\nd= 1\n"
    file_path = tmp_path / "lcp"
    file_path.write_text(content)

    m = lcp.from_file(str(file_path), decimals)
    assert m.M[0][0] == expected


@pytest.mark.parametrize("content", [
    "M= 1 0 0 1 q= 1 1 d= 1 1\n",           # missing n=
    "n= 2\nM= 1 0 0 1\nq= 1 1\nd= 1\n",     # wrong number of values
    "n= 2\nM= 1 0 0 1\nq= 1 1\nx= 1 1\n",   # X= instead of d=
    "invalid content",
])
def test_lcp_invalid_file(tmp_path, content):
    file_path = tmp_path / "lcp"
    file_path.write_text(content)

    with pytest.raises(ValueError):
        lcp.from_file(str(file_path))


# ---   TABLEAU INIT   ----------------------------------------------
def test_tableau_dimensions():
    n = 3
    t = tableau(get_empty_lcp(n))
    assert t.n == n
    assert len(t.A) == n
    assert len(t.A[0]) == n + 2


def test_tableau_initial_basis():
    n = 3
    t = tableau(get_empty_lcp(n))
    for i in range(2 * n + 1):
        if i <= n:
            assert t.bascobas[i] >= n, f"Z({i}) should be cobasic"
        else:
            assert t.bascobas[i] < n, f"W({i}) should be basic"


def test_tableau_bascobas_whichvar_are_inverses():
    n = 3
    t = tableau(get_empty_lcp(n))
    for i in range(2 * n + 1):
        assert t.bascobas[t.whichvar[i]] == i
        assert t.whichvar[t.bascobas[i]] == i


# ---   VARTOA   ----------------------------------------------------
def test_vartoa():
    n = 3
    t = tableau(get_empty_lcp(n))
    assert t.vartoa(0) == "z0"
    assert t.vartoa(n + 1) == "w1"
    assert t.vartoa(n) == f"z{n}"
    assert t.vartoa(n + n) == f"w{n}"


# ---   COMPLEMENT   ------------------------------------------------
@pytest.mark.parametrize("i", [1, 2, 3])
def test_complement_pairs(i):
    n = 3
    t = tableau(get_empty_lcp(n))
    assert t.complement(i) == n + i
    assert t.complement(n + i) == i


def test_complement_z0_fails():
    t = tableau(get_empty_lcp(2))
    with pytest.raises(RuntimeError):
        t.complement(0)


# ---   PIVOT   -----------------------------------------------------
def test_pivot_correctly_swaps_basis_variables():
    m = lcp(
        M=[
            [Fraction(1), Fraction(0)],
            [Fraction(0), Fraction(1)],
        ],
        q=[Fraction(-1), Fraction(-2)],
        d=[Fraction(1), Fraction(1)],
    )

    t = tableau(m)

    enter = 0              # z0 (cobasic in col 0)
    leave = t.whichvar[0]  # w1 (basic in row 0)

    t.pivot(leave, enter)

    assert t.bascobas[enter] < t.n   # entering variable is basic
    assert t.bascobas[leave] >= t.n  # leaving variable is cobasic


# ---   LEXMINVAR   -------------------------------------------------
def test_lexminvar_without_positive_entry():
    t = tableau(get_empty_lcp(2))

    t.A[0][0] = -1
    t.A[1][0] = -3

    enter = 0  # z0, cobasic in col 0

    with pytest.raises(RayTermination):
        t.lexminvar(enter)


@pytest.mark.parametrize(
    "row0, row1",
    [
        pytest.param([-1, 0, 0, 0], [3, 0, 0, 0], id="single_candidate"),
        pytest.param([2, 0, 0, 6], [2, 0, 0, 4], id="multiple_candidates"),
    ],
)
def test_lexminvar_with_positive_entry(row0, row1):
    t = tableau(get_empty_lcp(2))
    t.A[0] = row0
    t.A[1] = row1

    enter = 0  # z0, cobasic in col 0
    leave, z0leave = t.lexminvar(enter)

    assert leave == t.whichvar[1]  # w2 leaves
    assert z0leave is False


# ---   CLI   -------------------------------------------------------
@pytest.mark.parametrize("extra_args", [
    [],
    ["--verbose", "--z0"],
])
def test_exit_code_0_on_success(tmp_path, extra_args):
    file_path = tmp_path / "test.lcp"
    file_path.write_text("n= 2\nM= 1 0 0 1\nq= 1 1\nd= 1 1\n")

    runner = CliRunner()
    result = runner.invoke(main, [str(file_path)] + extra_args)

    assert result.exit_code == 0


def test_exit_code_1_on_ray_termination(tmp_path):
    file_path = tmp_path / "test.lcp"
    file_path.write_text("n= 2\nM= -1 0 0 -1\nq= -1 -1\nd= 1 1\n")

    runner = CliRunner()
    result = runner.invoke(main, [str(file_path)])

    assert result.exit_code == 1


def test_cli_rejects_missing_file(tmp_path):
    missing_path = tmp_path / "missing"

    runner = CliRunner()
    result = runner.invoke(main, [str(missing_path)])

    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()


def test_cli_rejects_directory(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, [str(tmp_path)])

    assert result.exit_code == 2
    assert "is a directory" in result.output.lower()
