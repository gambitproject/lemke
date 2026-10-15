lemke
=====

**lemke** is a pure Python implementation of Lemke's algorithm for linear
complementarity problems (LCPs), including its application to computing a
Nash equilibrium of a bimatrix game. It uses exact rational arithmetic
and is built for teaching and research, where you want to see each pivot.
It can be used as both a callable library and a CLI tool.

lemke is part of the `Gambit project <https://www.gambit-project.org>`_ for
computation in game theory, and it builds on the work of
`Bernhard von Stengel <http://www.maths.lse.ac.uk/personal/stengel/>`_.


Features
--------
- Lemke's algorithm for linear complementarity problems,
  with a covering vector ``d``;
- Lexicographic minimum ratio test to handle degenerate problems;
- Arbitrary precision with integer pivoting;
- Lemke–Howson and the tracing procedure for bimatrix games;
- Verbose tableau output that shows every pivot;
- Command-line tools: ``lemke``, ``bimatrix`` and ``randomstart``.


Examples
--------

**1. Solving a 2×2 LCP in Python.**

Find :math:`z \ge 0` with :math:`w = q + Mz \ge 0` and
:math:`z^\top w = 0`, where

.. math::

   M = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix},
   \qquad
   q = \begin{pmatrix} -1 \\ -1 \end{pmatrix}.

.. doctest::

   >>> from fractions import Fraction
   >>> from lemke.lemke import lcp, runlemke
   >>> m = [
   ...   [Fraction(2), Fraction(1)],
   ...   [Fraction(1), Fraction(2)],
   ... ]
   >>> q = [Fraction(-1), Fraction(-1)]
   >>> d = [Fraction(1), Fraction(1)]  # covering vector
   >>> problem = lcp(m, q, d)
   >>> result = runlemke(lcp=problem)
   >>> result.success
   True
   >>> result.z
   (Fraction(1, 3), Fraction(1, 3))

The solution is exact: :math:`z = (1/3,\, 1/3)`, with :math:`w = 0`.


**2. Computing a Nash equilibrium from the command line.**

Find Nash equilibria using the Lemke–Howson method for the bimatrix game
in ``examples/game``, where the payoff matrices are

.. math::

   A = \begin{pmatrix} 3 & 0 \\ 0 & 2 \end{pmatrix},
   \qquad
   B = \begin{pmatrix} 2 & 0 \\ 0 & 7 \end{pmatrix}.


.. code-block:: console

   $ bimatrix lh examples/game


.. code-block:: text

    label 1 found eq (1,0),(1,0)
        supports: [0][0]
    label 2 found eq (0,1),(0,1)
        supports: [1][1]
    -------- equilibria found: --------
    (1,0),(1,0)
        supports: [0][0] found by labels [1, 3]
    (0,1),(0,1)
        supports: [1][1] found by labels [2, 4]

The algorithm runs for all labels by default and finds 2 equilibria.


Installation
------------

lemke needs Python 3.10 or later.

It is **not** yet available on PyPI, but can be installed directly from GitHub:

.. code-block:: console

   pip install git+https://github.com/gambitproject/lemke.git


Citing lemke
------------

lemke is Free/Open Source software, released under the terms of
the GNU General Public Licence, version 3 (GPL-3.0).

If you use lemke in a scientific publication, you can use the following citation:

   Von Stengel, B. (2026). *lemke: Lemke's algorithm for linear complementarity
   problems and bimatrix games*.
   https://github.com/gambitproject/lemke


API documentation
-----------------

.. toctree::
   :maxdepth: 2

   api
