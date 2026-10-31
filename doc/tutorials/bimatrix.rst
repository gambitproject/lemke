Finding equilibria of a bimatrix game
=====================================

This tutorial shows how to define a two-player game in strategic form and
compute its Nash equilibria with the Lemke-Howson algorithm and with the
tracing procedure.

In a *bimatrix game*, the row player has :math:`m` pure strategies, the
column player has :math:`n` pure strategies, and the payoffs are given by two
:math:`m \times n` matrices :math:`A` (row player) and :math:`B` (column
player). All payoffs are stored as exact fractions.

Throughout we use this coordination game:

.. math::

   A = \begin{pmatrix} 3 & 0 \\ 0 & 2 \end{pmatrix}, \qquad
   B = \begin{pmatrix} 2 & 0 \\ 0 & 7 \end{pmatrix}.


Creating a game
---------------

A game is represented by the :class:`~lemke.bimatrix.Bimatrix` class,
which contains two :class:`~lemke.bimatrix.PayoffMatrix` objects, one per player.
A game instance can be created in two ways.

1) From Python
~~~~~~~~~~~~~~

First wrap each payoff matrix in a :class:`~lemke.bimatrix.PayoffMatrix`,
then combine them:

.. doctest::

   >>> from fractions import Fraction as F
   >>> from lemke.bimatrix import Bimatrix, PayoffMatrix
   >>> game = Bimatrix(
   ...    A=PayoffMatrix([
   ...       [F(3), F(0)],
   ...       [F(0), F(2)],
   ...    ]),
   ...    B=PayoffMatrix([
   ...       [F(2), F(0)],
   ...       [F(0), F(7)],
   ...    ]),
   ... )
   >>> print(game.A.num_rows)
   2

A :class:`~lemke.bimatrix.PayoffMatrix` also records useful facts about its entries,
for example its largest entry:

.. doctest::

   >>> print(game.A.max)
   3

.. note::

   Every entry must be an exact rational (:class:`fractions.Fraction`).
   Other types cannot be passed directly.

2) From a file
~~~~~~~~~~~~~~

Alternatively, describe the game in a text file and load it with
:meth:`~lemke.bimatrix.Bimatrix.from_file`.

First, create a file such as ``examples/game``::

   # m,n=
   2 2

   # A=
   3 0
   0 2

   # B=
   2 0
   0 7

then load it:

.. doctest::

   >>> game = Bimatrix.from_file("examples/game")
   >>> print(game.A.num_rows)
   2

See details about how the input file should be formatted on
the :doc:`file formats<../file_formats>` page.


Lemke-Howson
------------

The Lemke-Howson algorithm finds one equilibrium for each starting *label*.
There are :math:`m + n` labels, one for each pure strategy of either player.
:meth:`~lemke.bimatrix.Bimatrix.lh` takes a string saying which labels to
try, for example ``"1-3,7"``. You can also pass ``"1-"`` for all labels:

.. doctest::

   >>> result = game.lh("1-")
   label 1 found eq (1,0),(1,0)
       supports: [0][0]
   label 2 found eq (0,1),(0,1)
       supports: [1][1]
   -------- equilibria found: --------
   (1,0),(1,0)
       supports: [0][0] found by labels [1, 3]
   (0,1),(0,1)
       supports: [1][1] found by labels [2, 4]

This prints a line each time a *new* equilibrium is found, followed by a
summary of all distinct equilibria and the labels that found them.

The same information is returned as a dictionary, which maps each
equilibrium (a tuple) to the list of labels that produced it:

.. doctest::

   >>> for eq, labels in result.items():
   ...    print(labels)
   ...    print(eq)
   [1, 3]
   (Fraction(1, 1), Fraction(0, 1), Fraction(1, 1), Fraction(0, 1))
   [2, 4]
   (Fraction(0, 1), Fraction(1, 1), Fraction(0, 1), Fraction(1, 1))

.. note::

   Different labels can lead to the same equilibrium,
   and Lemke-Howson may not find *all* equilibria of a game.
   For this game, it found two pure strategy equilibria, but
   not the mixed strategy one: :math:`(\frac{7}{9}, \frac{2}{9}), (\frac{2}{5}, \frac{3}{5})`.


.. _tracing:

The tracing procedure
---------------------

The tracing procedure is another way to find an equilibrium. It starts from
a *prior:* a pair of mixed strategies, one per player, that represents
initial beliefs. The equilibrium found depends on the prior.

Uniform prior
~~~~~~~~~~~~~

:meth:`~lemke.bimatrix.Bimatrix.trace_uniform_prior` runs the procedure once
from the uniform prior, where each player mixes equally over all their
pure strategies, and prints the equilibrium found:

.. doctest::

   >>> game.trace_uniform_prior()
   -------- statistics of equilibria found: --------
   1 times found (0,1),(0,1)
       supports: [1][1]
   1 total priors, 1 equilibria found

Random priors
~~~~~~~~~~~~~

:meth:`~lemke.bimatrix.Bimatrix.trace_random_priors` runs the procedure from
several random priors, to see which equilibria they lead to and how often.
To make a run reproducible, pass a ``seed``:

.. doctest::

   >>> game.trace_random_priors(100, seed=1, accuracy=100)
   found eq (1,0),(1,0)
       supports: [0][0] index 1
   found eq (0,1),(0,1)
       supports: [1][1] index 1
   -------- statistics of equilibria found: --------
   24 times found (1,0),(1,0)
       supports: [0][0]
   76 times found (0,1),(0,1)
       supports: [1][1]
   100 total priors, 2 equilibria found

The priors are sampled uniformly from the simplex and
rounded to fractions with denominator ``accuracy`` (default 1000).

Check :doc:`this tutorial<randomstart>` to see how the sampling and rounding work.
