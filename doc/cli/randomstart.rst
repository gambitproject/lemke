The ``randomstart`` command
=============================

.. note::

   This is a CLI reference, you can view Python API reference
   :doc:`here <../api/lemke.randomstart>`.
   For an in-depth tutorial using Python API, see :doc:`/tutorials/randomstart`.


.. click:: lemke.randomstart:main
   :prog: randomstart
   :nested: full


Examples
--------

Plot 300 points, rounded to multiples of 1/30 that sum to 1:

.. code-block:: console

   $ randomstart --numpoints 300 --accuracy 30

   num_points=300 accuracy=30 higher_dim=3 naive_plot=False

.. plot::
   :include-source: false

   import random
   from lemke.randomstart import plot_simplex

   random.seed(1)
   plot_simplex(num_points=300, accuracy=30)

.. note::

   Your plot will differ, since new random points are generated
   each time you run the command.

A finer rounding grid:

.. code-block:: console

   $ randomstart --numpoints 300 --accuracy 100

Sample naively, by normalizing independent uniform numbers (this is biased
towards the centre of the triangle):

.. code-block:: console

   $ randomstart --numpoints 300 --accuracy 30 --naiveplot

Sample from a higher-dimensional simplex, showing only the middle three
components:

.. code-block:: console

   $ randomstart --numpoints 300 --accuracy 30 --higherdim 6

   num_points=300 accuracy=30 higher_dim=6 naive_plot=False
   show positions 2 .. 4 of 0 .. 5
