The ``lemke`` command
=====================

.. note::

   This is a CLI reference, you can view Python API reference
   :doc:`here <../api/lemke.lemke>`.
   For an in-depth tutorial using the Python API, see :doc:`/tutorials/lcp`.

.. click:: lemke.lemke:main
   :prog: lemke
   :nested: full


Examples
--------

CLI commands work on a file specifying the LCP you want to solve,
such as ``examples/lcp_2x2``:

.. literalinclude:: ../../examples/lcp_2x2
   :language: text

See details about how the input file should be formatted
on the :doc:`file formats <../file_formats>` page.

To solve the LCP, run the ``lemke`` command:

.. code-block:: console

   $ lemke examples/lcp_2x2

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

   z2   -1  3 -2   3
   z1    2  3 -5   3
   -----------------end of tableau-----------------
   Process finished successfully after 3 pivots.
   Solution found:
   basis=     z1  z2
       z=  0 2/3 2/3
       w=      0   0

If the algorithm ends on a secondary ray (see :ref:`ray-termination`), the
output says so and the last computed values are shown, **not** a solution.
For example, for a file such as ``examples/lcp_ray``:

.. literalinclude:: ../../examples/lcp_ray
   :language: text

.. code-block:: console

   $ lemke examples/lcp_ray

   verbose=False z0=False lexstats=False
   n= 1
   M=

   0
   q=

   -1
   d=

   1
   ==================================
   After filltableau:
   Determinant: -1
   var  z0 z1 RHS
   scfa  1  1   1

   w1    1  .  -1
   -----------------end of tableau-----------------
   leaving: w1    entering: z0
   Ray termination when trying to enter z1
   Determinant: 1
   var  w1 z1 RHS
   scfa  1  1   1

   z0   -1  .   1
   -----------------end of tableau-----------------
   Terminated on a secondary ray after 1 pivot, when trying to enter z1.
   Current basis not an LCP solution:
   basis= z0
       z=  1  0
       w=     0

To print the tableau after every pivot,
and the value of :math:`z_0` at each step:

.. code-block:: console

   $ lemke -v --z0 examples/lcp_2x2

To allow more digits after the decimal point in the input file:

.. code-block:: console

   $ lemke --decimals 6 examples/lcp_2x2
