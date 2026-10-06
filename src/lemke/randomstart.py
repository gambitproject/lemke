import fractions
import numbers
import random

import click
import matplotlib.pyplot as plt

MAX_ACCURACY = 10_000_000


def randInSimplex(n, naive=False):
    """Generate a random n-tuple uniformly distributed on the unit simplex."""
    x = [0.0] * n
    if naive:  # random numbers re-normalized
        sum = 0
        for i in range(n):
            x[i] = random.uniform(0, 1)
            sum += x[i]
        return [k / sum for k in x]

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


def validate_accuracy(accuracy):
    """Check that `accuracy` is an integer between 1 and `MAX_ACCURACY`."""
    if not isinstance(accuracy, numbers.Integral):
        raise TypeError(f"accuracy must be an integer, got {type(accuracy).__name__}")
    if not 1 <= accuracy <= MAX_ACCURACY:
        raise ValueError(f"accuracy must be between 1 and {MAX_ACCURACY}, got {accuracy}")


def roundArray(x, accuracy=10000):
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
    validate_accuracy(accuracy)

    n = len(x)
    sum = 0
    numerator = [0] * n
    pastdecimals = [0.0] * n
    for i in range(n):
        abig = x[i] * accuracy
        num = numerator[i] = int(abig)
        pastdecimals[i] = abig - num
        sum += num
    tobeadded = accuracy - sum
    # print(tobeadded)
    if not (0 <= tobeadded < n):
        raise ValueError("need probabilities")
    for _ in range(tobeadded):
        maxval = max(pastdecimals)
        position = pastdecimals.index(maxval)
        pastdecimals[position] = 0.0
        numerator[position] += 1
    return [fractions.Fraction(k, accuracy) for k in numerator]


def renormalize(x):
    """Rescale a list of numbers so that it sums to one."""
    s = sum(x)
    if s == 0:
        return x
    return [k / s for k in x]


def maptotriangle(vec):
    """Map a point on the unit triangle (3D) to 2D coordinates
    in a triangle with corners at (0, 0), (1, 0), (0.5, sqrt(3)/2).
    """
    x = vec[1] + 0.5 * vec[2]
    y = 3 ** .5 / 2 * vec[2]
    return x, y


def plot_simplex(numpoints=200, accuracy=20, higherdim=3, naiveplot=False):
    """Generate a simplex sampling plot.

    Samples `numpoints` random points from the simplex of dimension `higherdim`
    and projects them onto a 2D triangle (if `higherdim` is greater than 3,
    only the middle 3 components of each point are used, renormalized to sum to 1).
    Plots the raw sampled points in green and their rounded approximations in red.

    Parameters
    ----------
    numpoints : int
        Number of points to plot. Default is 200.
    accuracy : int
        Denominator for rounding: each point's coordinates are rounded to
        multiples of 1/`accuracy` that sum to 1 (see `roundArray`).
        Default is 20. Must be between 1 and `MAX_ACCURACY` (10,000,000).
    higherdim : int
        Dimension from which the middle 3 components will be sampled.
        Default is 3. Must be between 3 and 10.
    naiveplot : bool
        Sample naively by normalizing random uniforms (biased toward center).
        Default is False.

    Raises
    ------
    TypeError
        If `accuracy` or `higherdim` is not an integer.
    ValueError
        If `accuracy` or `higherdim` is out of range.
    """
    if not isinstance(higherdim, numbers.Integral):
        raise TypeError(f"higherdim must be an integer, got {type(higherdim).__name__}")
    if not 3 <= higherdim <= 10:
        raise ValueError(f"higherdim must be between 3 and 10, got {higherdim}")
    validate_accuracy(accuracy)
    print(
        f"numpoints={numpoints} accuracy={accuracy} higherdim={higherdim} naiveplot={naiveplot}"
    )
    segmentstart = (higherdim - 2) // 2
    if higherdim > 3:
        print("show positions", segmentstart, "..",
              segmentstart + 2, "of 0 ..", higherdim - 1)
    fig1, ax = plt.subplots()
    ax.set_box_aspect(.866)
    # plt.axis('square')
    x1, y1 = maptotriangle([1, 0, 0])
    x2, y2 = maptotriangle([0, 1, 0])
    x3, y3 = maptotriangle([0, 0, 1])
    plt.plot([x1, x2, x3, x1], [y1, y2, y3, y1], "black")

    roundedpoints = []
    for _ in range(numpoints):
        point = randInSimplex(higherdim, naiveplot)
        if higherdim > 3:
            point = renormalize(point[segmentstart:segmentstart + 3])
        roundedpoints.append(roundArray(point, accuracy))
        x, y = maptotriangle(point)
        plt.plot([x], [y], "g.")
    for circ in roundedpoints:
        x, y = maptotriangle(circ)
        plt.scatter([x], [y], s=10000 // accuracy, facecolors="none",
                    edgecolors="r")
    plt.show()


@click.command(
    context_settings={"help_option_names": ["-?", "-h", "--help"]},
)
@click.option(
    "--numpoints",
    default=200,
    show_default=True,
    help="Number of points plotted",
)
@click.option(
    "--accuracy",
    default=20,
    show_default=True,
    help="Denominator x: each coordinate is rounded to the nearest multiple of 1/x",
    type=click.IntRange(1, MAX_ACCURACY),
    metavar="INTEGER",
)
@click.option(
    "--higherdim",
    default=3,
    show_default=True,
    help="Dimension from which the middle 3 components will be sampled",
    type=click.IntRange(3, 10),
    metavar="INTEGER",
)
@click.option(
    "--naiveplot",
    is_flag=True,
    help="Sample naively by normalizing random uniforms (biased toward center)",
)
def main(numpoints, accuracy, higherdim, naiveplot):
    """Plot random points on the 2-simplex, rounded to rational coordinates.

    Green dots are the raw sampled points;
    red circles are their rounded rational approximations.
    """
    plot_simplex(numpoints, accuracy, higherdim, naiveplot)


if __name__ == "__main__":
    main()
