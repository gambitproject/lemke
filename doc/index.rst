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
  with a covering vector :math:`d`;
- Lexicographic minimum ratio test to handle degenerate problems;
- Arbitrary precision with integer pivoting;
- Lemke–Howson and the tracing procedure for bimatrix games;
- Verbose tableau output that shows every pivot;
- Command-line tools: ``lemke``, ``bimatrix`` and ``randomstart``.


Usage examples
--------------

Here are two quick examples of using lemke.
You can view more detailed explanations in the :doc:`tutorials/index`.

1) Solve a 2×2 LCP in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consider LCP given in ``examples/lcp_2x2``: find :math:`z \ge 0`
with :math:`w = q + Mz \ge 0` and :math:`z^\top w = 0`, where

.. math::

   M = \begin{pmatrix} \frac{1}{2} & 1 \\ -1 & \frac{5}{2} \end{pmatrix},
   \qquad
   q = \begin{pmatrix} -1 \\ -1 \end{pmatrix}.

.. doctest::

   >>> from fractions import Fraction as F
   >>> from lemke.lemke import Lcp, run_lemke
   >>> problem = Lcp(
   ...    M=[
   ...       [F(1, 2), F(1)],
   ...       [F(-1), F(5, 2)],
   ...    ],
   ...    q=[F(-1), F(-1)],
   ...    d=[F(1), F(1)],
   ... )
   >>> result = run_lemke(lcp=problem)
   >>> result.success
   True
   >>> result.z
   (Fraction(2, 3), Fraction(2, 3))

The solution is exact: :math:`z = (\frac{2}{3}, \frac{2}{3})`, with :math:`w = 0`.


2) Find a Nash equilibrium from the CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find Nash equilibria with the Lemke–Howson method for the bimatrix game
in ``examples/game``, where the payoff matrices are

.. math::

   A = \begin{pmatrix} 3 & 0 \\ 0 & 2 \end{pmatrix},
   \qquad
   B = \begin{pmatrix} 2 & 0 \\ 0 & 7 \end{pmatrix}.

Save the following as ``game_file``::

   # m,n=
   2 2

   # A=
   3 0
   0 2

   # B=
   2 0
   0 7

Then run:

.. code-block:: console

   $ bimatrix lh game_file

The algorithm runs for all labels by default and finds 2 equilibria:

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


Installation
------------

lemke needs Python 3.10 or later.

It is **not** yet available on PyPI, but can be installed directly from GitHub:

.. code-block:: console

   pip install git+https://github.com/gambitproject/lemke.git


.. _licence-citing:

Citing lemke
------------

lemke is Free/Open Source software, released under the terms of
the GNU General Public Licence, version 3 (GPL-3.0).

If you use lemke in a scientific publication, you can use the following citation:

   Von Stengel, B. (2026). *lemke: Lemke's algorithm for linear complementarity
   problems and bimatrix games*.
   https://github.com/gambitproject/lemke.


Useful links
------------

.. toctree::
   :maxdepth: 2

   api
   file_formats
   tutorials/index
   cli/index
   contributing
