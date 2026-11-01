Solving a linear complementarity problem
========================================

This tutorial walks through solving a *linear complementarity problem* (LCP)
with Lemke's algorithm, from creating the problem to interpreting the result
and watching the algorithm run.

Given a vector :math:`q` and a matrix :math:`M`,
an LCP asks to find a vector :math:`z \ge 0` such that

.. math::

   w = q + Mz \ge 0, \qquad z^T w = 0.

To get started, Lemke's algorithm also needs a *covering vector* :math:`d`,
which multiplies the extra variable :math:`z_0`.
So, a problem is described by the triple :math:`(M, q, d)`.
All arithmetic is exact, using rational numbers.


Creating an LCP
---------------

An LCP is represented by the :class:`~lemke.lemke.Lcp` class.
It can be created in two ways.

Let's consider an LCP, where

.. math::

   M = \begin{pmatrix} \frac{1}{2} & 1 \\ -1 & \frac{5}{2} \end{pmatrix},
   \qquad
   q = \begin{pmatrix} -1 \\ -1 \end{pmatrix},
   \qquad
   d = \begin{pmatrix} 1 \\ 1 \end{pmatrix}.


1) From Python
~~~~~~~~~~~~~~

Pass the matrix ``M`` (as a list of its rows) and the vectors ``q`` and ``d``:

.. doctest::

   >>> from fractions import Fraction as F
   >>> from lemke.lemke import Lcp
   >>> problem = Lcp(
   ...    M=[
   ...       [F(1, 2), F(1)],
   ...       [F(-1), F(5, 2)],
   ...    ],
   ...    q=[F(-1), F(-1)],
   ...    d=[F(1), F(1)],
   ... )
   >>> print(problem.n)
   2

.. note::

   Entries must be exact rationals, such as Python integers or
   :class:`fractions.Fraction` instances. Floats are not supported.

2) From a file
~~~~~~~~~~~~~~

Alternatively, describe the problem in a text file and load it with
:meth:`~lemke.lemke.Lcp.from_file`.

First, create a file such as ``examples/lcp_2x2``::

   n= 2
   M= 1/2 1
     -1 2.5
   q= -1 -1
   d= 1 1

then load it:

.. doctest::

   >>> problem = Lcp.from_file("examples/lcp_2x2")
   >>> print(problem.n)
   2

See details about how the input file should be formatted on
the :doc:`file formats<../file_formats>` page.


Solving the problem
-------------------

Pass the problem to :func:`~lemke.lemke.run_lemke`:

.. doctest::

   >>> from lemke.lemke import run_lemke
   >>> result = run_lemke(lcp=problem)
   >>> print(result.success)
   True

:func:`~lemke.lemke.run_lemke` always returns an :class:`~lemke.lemke.LcpResult`,
whether or not a solution was found. Its fields are the same in both cases,
so you must check :attr:`~lemke.lemke.LcpResult.success` field first.

.. note::

   If every entry of ``q`` is non-negative, the trivial solution
   :math:`z = 0,\ w = q` is returned immediately without any pivoting.


Reading the result
------------------

The solution values are available as tuples of :class:`fractions.Fraction`:

.. doctest::

   >>> print(result.z)
   (Fraction(2, 3), Fraction(2, 3))
   >>> print(result.w)
   (Fraction(0, 1), Fraction(0, 1))

Printing the result shows the basis and the values in aligned columns,
so that the complementarity condition (:math:`z_i w_i = 0`) can be checked by eye:

.. doctest::

   >>> print(result)
   Process finished successfully after 3 pivots.
   Solution found:
   basis=     z1  z2
       z=  0 2/3 2/3
       w=      0   0

The first column of ``z=`` is the artificial variable :math:`z_0`, which is
always 0 for a successful run. See :class:`~lemke.lemke.LcpResult` for all
fields, such as :attr:`~lemke.lemke.LcpResult.basis` and :attr:`~lemke.lemke.LcpResult.num_pivots`.

Degenerate solutions
~~~~~~~~~~~~~~~~~~~~

The solution above is *non-degenerate*: for every :math:`i`, exactly one of
:math:`z_i` and :math:`w_i` is positive.

A solution is *degenerate* if some basic variable has value zero, meaning
both :math:`z_i` and :math:`w_i` are zero for some :math:`i`.
It is still a valid solution. For example:

.. doctest::

   >>> problem = Lcp(
   ...    M=[
   ...       [F(1), F(0)],
   ...       [F(0), F(1)],
   ...    ],
   ...    q=[F(-1), F(0)],
   ...    d=[F(1), F(1)],
   ... )
   >>> result = run_lemke(lcp=problem)
   >>> print(result.z)
   (Fraction(1, 1), Fraction(0, 1))
   >>> print(result.w)
   (Fraction(0, 1), Fraction(0, 1))

Here :math:`z_2 = w_2 = 0`, so the second complementary pair is degenerate.
Degeneracy is handled by the lexicographic minimum ratio test, which
prevents the algorithm from cycling. You can inspect how often that test
was needed with the ``lex_stats`` option of the printing callback (see below).

Since in this case it is not clear which variables are basic,
you can explicitly check the :attr:`~lemke.lemke.LcpResult.basis` field:

.. doctest::

   >>> print(sorted(result.basis))
   ['w2', 'z1']


.. _ray-termination:

Ray termination
---------------

Lemke's algorithm can also end on a *secondary ray*, when the variable
that should enter the basis has no positive pivot candidate.
In that case no valid solution is found.

Consider the following example, where :math:`w = -1 + 0 * z` can
never be non-negative:

.. doctest::

   >>> problem = Lcp(
   ...   M=[[F(0)]],
   ...   q=[F(-1)],
   ...   d=[F(1)],
   ... )
   >>> result = run_lemke(lcp=problem)
   >>> print(result.success)
   False
   >>> print(result.ray_entering_variable)
   z1

When ``success`` is ``False``:

* ``ray_entering_variable`` names the entering variable that led to the secondary ray,
* ``z0``, ``z`` and ``w`` describe the final values reached,
  which is **not** a solution of the LCP.

.. doctest::

   >>> print(result)
   Terminated on a secondary ray after 1 pivot, when trying to enter z1.
   Current basis not an LCP solution:
   basis= z0
       z=  1  0
       w=     0

.. note::

   Ray termination does not, by itself, prove that the LCP has no solution.
   It only means the algorithm could not find one from this covering vector.


Watching the algorithm
----------------------

To see what happens at each pivot, pass a callback to :func:`~lemke.lemke.run_lemke`.
The ready-made :class:`~lemke.lemke.PrintingCallback` prints the LCP, the
tableaus and the chosen leaving and entering variables:

.. doctest::

   >>> from lemke.lemke import PrintingCallback
   >>> problem = Lcp.from_file("examples/lcp_2x2")
   >>> result = run_lemke(lcp=problem, callback=PrintingCallback())
   verbose=False z0=False lexstats=False
   n= 2
   M=
   1/2   1
   -1  5/2
   q=
   -1   -1
   d=
   1     1
   ==================================
   After filltableau:
   Determinant: -1
   var  z0 z1 z2 RHS
   scfa  1  2  2   1
   <BLANKLINE>
   w1    1  1  2  -1
   w2    1 -2  5  -1
   -----------------end of tableau-----------------
   leaving: w2    entering: z0
   leaving: w1    entering: z2
   leaving: z0    entering: z1
   Final tableau:
   Determinant: 9
   var  w2 z0 w1 RHS
   scfa  1  1  1   1
   <BLANKLINE>
   z2   -1  3 -2   3
   z1    2  3 -5   3
   -----------------end of tableau-----------------
   Process finished successfully after 3 pivots.
   Solution found:
   basis=     z1  z2
       z=  0 2/3 2/3
       w=      0   0

The options are:

* ``verbose``: print the full tableau after every pivot,
* ``z0``: print the current value of :math:`z_0` before each pivot,
* ``lex_stats``: print minimum-ratio test statistics at the end,
* ``stream``: write to a file-like object instead of ``sys.stdout``.

Writing your own callback
~~~~~~~~~~~~~~~~~~~~~~~~~

To react to the algorithm in your own way, subclass
:class:`~lemke.lemke.LemkeCallback` and override only the methods you need.
All of them do nothing by default.

For example, to log entering variables during each pivot,
you can override :func:`~lemke.lemke.LemkeCallback.on_pivot_start`:

.. doctest::

   >>> from lemke.lemke import LemkeCallback
   >>> class LogEnteringVariables(LemkeCallback):
   ...    def on_pivot_start(self, tableau, leave, enter):
   ...        print(enter)
   >>> result = run_lemke(lcp=problem, callback=LogEnteringVariables())
   z0
   z2
   z1

.. note::

   No callbacks are invoked in the trivial case :math:`q \ge 0`.
