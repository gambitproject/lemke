"""Random priors generation and visualization on the simplex."""

import fractions
import numbers
import random

import click
import matplotlib.pyplot as plt

MAX_ACCURACY = 10_000_000


def _rand_in_simplex(n: int, naive: bool = False) -> list[float]:
    """Generate a random n-tuple uniformly distributed on the unit simplex."""
    x = [0.0] * n
    if naive:  # random numbers re-normalized
        total = 0.0
        for i in range(n):
            x[i] = random.uniform(0, 1)
            total += x[i]
        return [k / total for k in x]

    else:  # properly uniformly in simplex
        factor = 1.0
        i = n - 1
        while i > 0:
            b = random.uniform(0, 1)
            f = b ** (1 / i)
            x[i] = factor * (1 - f)
            factor *= f
            i -= 1
        x[0] = factor
        return x


def _validate_accuracy(accuracy: int) -> None:
    """Check that `accuracy` is an integer between 1 and `MAX_ACCURACY`."""
    if not isinstance(accuracy, numbers.Integral):
        raise TypeError(f"accuracy must be an integer, got {type(accuracy).__name__}")
    if not 1 <= accuracy <= MAX_ACCURACY:
        raise ValueError(f"accuracy must be between 1 and {MAX_ACCURACY}, got {accuracy}")


def _round_array(x: list[float], accuracy: int = 10000) -> list[fractions.Fraction]:
    """
    Round an array of probabilities `x` to multiples of 1 / `accuracy`
    that still sum to 1.

    Entries are not necessarily rounded to the nearest multiple,
    since the rounded values must sum to 1.
    The probabilities are multiplied by `accuracy`, then rounded down to their integer parts,
    which will be the numerators, augmented by 1 in order of decreasing size of the remainders
    (which are less than 1) until they sum to `accuracy`.

    Example: accuracy=10, x=[0.18, .35, .47] becomes [2/10, 3/10, 5/10].
    """
    _validate_accuracy(accuracy)

    n = len(x)
    total = 0
    numerator = [0] * n
    past_decimals = [0.0] * n
    for i in range(n):
        a_big = x[i] * accuracy
        num = numerator[i] = int(a_big)
        past_decimals[i] = a_big - num
        total += num
    to_be_added = accuracy - total
    if not (0 <= to_be_added < n):
        raise ValueError("need probabilities")
    for _ in range(to_be_added):
        max_val = max(past_decimals)
        position = past_decimals.index(max_val)
        past_decimals[position] = 0.0
        numerator[position] += 1
    return [fractions.Fraction(k, accuracy) for k in numerator]


def _renormalize(x: list[float]) -> list[float]:
    """Rescale a list of numbers so that it sums to one."""
    s = sum(x)
    if s == 0:
        return x
    return [k / s for k in x]


def _map_to_triangle(vec: list[float] | list[fractions.Fraction]) -> tuple[float, float]:
    """Map a point on the unit triangle (3D) to 2D coordinates
    in a triangle with corners at (0, 0), (1, 0), (0.5, sqrt(3)/2).
    """
    x = vec[1] + 0.5 * vec[2]
    y = 3 ** .5 / 2 * vec[2]
    return x, y


def plot_simplex(
    num_points: int = 200,
    accuracy: int = 20,
    higher_dim: int = 3,
    naive_plot: bool = False,
) -> None:
    """Generate a simplex sampling plot.

    Samples `num_points` random points from the simplex of dimension `higher_dim`
    and projects them onto a 2D triangle (if `higher_dim` is greater than 3,
    only the middle 3 components of each point are used, renormalized to sum to 1).
    Plots the raw sampled points in green and their rounded approximations in red.

    Parameters
    ----------
    num_points : int
        Number of points to plot. Default is 200.
    accuracy : int
        Denominator for rounding: each point's coordinates are rounded to
        multiples of 1/`accuracy` that sum to 1 (see `_round_array`).
        Default is 20. Must be between 1 and `MAX_ACCURACY` (10,000,000).
    higher_dim : int
        Dimension from which the middle 3 components will be sampled.
        Default is 3. Must be between 3 and 10.
    naive_plot : bool
        Sample naively by normalizing random uniforms (biased toward center).
        Default is False.

    Raises
    ------
    TypeError
        If `accuracy` or `higher_dim` is not an integer.
    ValueError
        If `accuracy` or `higher_dim` is out of range.
    """
    if not isinstance(higher_dim, numbers.Integral):
        raise TypeError(f"higher_dim must be an integer, got {type(higher_dim).__name__}")
    if not 3 <= higher_dim <= 10:
        raise ValueError(f"higher_dim must be between 3 and 10, got {higher_dim}")
    _validate_accuracy(accuracy)
    print(
        f"num_points={num_points} accuracy={accuracy} "
        f"higher_dim={higher_dim} naive_plot={naive_plot}"
    )
    segment_start = (higher_dim - 2) // 2
    if higher_dim > 3:
        print("show positions", segment_start, "..",
              segment_start + 2, "of 0 ..", higher_dim - 1)
    fig1, ax = plt.subplots()
    ax.set_box_aspect(.866)
    # plt.axis('square')
    x1, y1 = _map_to_triangle([1, 0, 0])
    x2, y2 = _map_to_triangle([0, 1, 0])
    x3, y3 = _map_to_triangle([0, 0, 1])
    plt.plot([x1, x2, x3, x1], [y1, y2, y3, y1], "black")

    rounded_points = []
    for _ in range(num_points):
        point = _rand_in_simplex(higher_dim, naive_plot)
        if higher_dim > 3:
            point = _renormalize(point[segment_start:segment_start + 3])
        rounded_points.append(_round_array(point, accuracy))
        x, y = _map_to_triangle(point)
        plt.plot([x], [y], "g.")
    for circ in rounded_points:
        x, y = _map_to_triangle(circ)
        plt.scatter([x], [y], s=10000 // accuracy, facecolors="none",
                    edgecolors="r")
    plt.show()


@click.command(
    context_settings={"help_option_names": ["-?", "-h", "--help"]},
)
@click.option(
    "--numpoints",
    "num_points",
    default=200,
    show_default=True,
    help="Number of points plotted",
)
@click.option(
    "--accuracy",
    default=20,
    show_default=True,
    help="Denominator x: coordinates are rounded to multiples of 1/x that sum to 1",
    type=click.IntRange(1, MAX_ACCURACY),
    metavar="INTEGER",
)
@click.option(
    "--higherdim",
    "higher_dim",
    default=3,
    show_default=True,
    help="Dimension from which the middle 3 components will be sampled",
    type=click.IntRange(3, 10),
    metavar="INTEGER",
)
@click.option(
    "--naiveplot",
    "naive_plot",
    is_flag=True,
    help="Sample naively by normalizing random uniforms (biased toward center)",
)
def main(num_points: int, accuracy: int, higher_dim: int, naive_plot: bool) -> None:
    """Plot random points on the 2-simplex, rounded to rational coordinates.

    Green dots are the raw sampled points;
    red circles are their rounded rational approximations.
    """
    plot_simplex(num_points, accuracy, higher_dim, naive_plot)


if __name__ == "__main__":
    main()
