import fractions
import math
from unittest.mock import patch

import matplotlib
import pytest
from click.testing import CliRunner

from lemke.randomstart import (
    MAX_ACCURACY,
    main,
    maptotriangle,
    plot_simplex,
    randInSimplex,
    renormalize,
    roundArray,
)

matplotlib.use("Agg")


@pytest.mark.parametrize("n", [2, 3, 5, 20])
@pytest.mark.parametrize("naive", [True, False])
class TestRandInSimplex:
    def test_output_length(self, n, naive):
        result = randInSimplex(n, naive)
        assert len(result) == n

    def test_sum_is_approx_one(self, n, naive):
        result = randInSimplex(n, naive)
        assert sum(result) == pytest.approx(1.0)

    def test_components_in_range(self, n, naive):
        result = randInSimplex(n, naive)
        assert all(0.0 <= x <= 1.0 for x in result)


@pytest.mark.parametrize(
    "array",
    [
        [1.0, 0.0],
        [0.3333, 0.3333, 0.3334],
        [0.1, 0.2, 0.3, 0.4],
        [0.0, 0.5, 0.5],
        [0.111111111111111] * 9,
    ],
)
@pytest.mark.parametrize(
    "accuracy",
    [
        10,
        100,
        10000,
        MAX_ACCURACY,
    ],
)
class TestRoundArraySuccess:
    def test_output_length(self, array, accuracy):
        result = roundArray(array, accuracy)
        assert len(result) == len(array)

    def test_sum_is_exactly_one(self, array, accuracy):
        result = roundArray(array, accuracy)
        assert sum(result) == fractions.Fraction(1, 1)

    def test_returns_fractions(self, array, accuracy):
        result = roundArray(array, accuracy)
        assert all(isinstance(x, fractions.Fraction) for x in result)

    def test_denominators_match_accuracy(self, array, accuracy):
        result = roundArray(array, accuracy)

        # Check if requested accuracy is a multiple of the (possibly reduced) denominator
        assert all(accuracy % x.denominator == 0 for x in result)


class TestRoundArrayFailure:
    @pytest.mark.parametrize("bad_accuracy", [0, -1, MAX_ACCURACY + 1])
    def test_accuracy_out_of_bounds(self, bad_accuracy):
        with pytest.raises(ValueError, match="accuracy must be between"):
            roundArray([0.5, 0.5], accuracy=bad_accuracy)

    def test_accuracy_not_integer(self):
        with pytest.raises(TypeError, match="accuracy must be an integer"):
            roundArray([0.5, 0.5], accuracy=2.5)

    def test_invalid_probabilities(self):
        with pytest.raises(ValueError, match="need probabilities"):
            roundArray([1.0, 1.0])


class TestRenormalize:
    def test_all_zeros(self):
        assert renormalize([0, 0, 0]) == [0, 0, 0]

    def test_single_element(self):
        assert renormalize([42.0]) == [1.0]

    def test_already_normalized(self):
        assert renormalize([0.2, 0.5, 0.3]) == pytest.approx([0.2, 0.5, 0.3])

    def test_standard(self):
        assert renormalize([1, 2, 3, 4]) == pytest.approx([0.1, 0.2, 0.3, 0.4])


class TestMapToTriangle:
    def test_vertices(self):
        assert maptotriangle([1, 0, 0]) == pytest.approx((0.0, 0.0))
        assert maptotriangle([0, 1, 0]) == pytest.approx((1.0, 0.0))
        assert maptotriangle([0, 0, 1]) == pytest.approx((0.5, math.sqrt(3) / 2))

    @pytest.mark.parametrize(
        "vec, expected",
        [
            ([1/3, 1/3, 1/3], (0.5, math.sqrt(3) / 6)),
            ([0.5, 0.5, 0.0], (0.5, 0.0)),
            ([0.0, 0.5, 0.5], (0.75, math.sqrt(3) / 4)),
        ],
    )
    def test_known_points(self, vec, expected):
        assert maptotriangle(vec) == pytest.approx(expected)


class TestPlotSimplex:
    @pytest.mark.parametrize("bad_higherdim", [-1, 2, 11])
    def test_higherdim_out_of_bounds(self, bad_higherdim):
        with pytest.raises(ValueError, match="higherdim must be between"):
            plot_simplex(higherdim=bad_higherdim)

    def test_higherdim_not_integer(self):
        with pytest.raises(TypeError, match="higherdim must be an integer"):
            plot_simplex(higherdim=3.5)


class TestCLI:
    @pytest.mark.parametrize(
        "arguments",
        [
            [],
            ["--numpoints", "10", "--accuracy", "100", "--higherdim", "7", "--naiveplot"],
        ]
    )
    def test_cli_runs_without_error(self, arguments):
        runner = CliRunner()
        with patch("matplotlib.pyplot.show"):
            result = runner.invoke(main, arguments)
        assert result.exit_code == 0

    @pytest.mark.parametrize("higherdim", ["-1", "0", "2", "20"])
    def test_cli_invalid_higherdim(self, higherdim):
        runner = CliRunner()
        result = runner.invoke(main, ["--higherdim", higherdim])
        assert result.exit_code != 0
        assert "Invalid value" in result.output

    @pytest.mark.parametrize("accuracy", ["-1", "0", f"{MAX_ACCURACY + 1}"])
    def test_cli_invalid_accuracy(self, accuracy):
        runner = CliRunner()
        result = runner.invoke(main, ["--accuracy", accuracy])
        assert result.exit_code != 0
        assert "Invalid value" in result.output
