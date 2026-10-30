The ``bimatrix`` command
========================

.. note::

   This is a CLI reference, you can view Python API reference
   :doc:`here <../api/lemke.bimatrix>`.
   For an in-depth tutorial using Python API, see :doc:`/tutorials/bimatrix`.

.. click:: lemke.bimatrix:main
   :prog: bimatrix
   :nested: full


Examples
--------

CLI commands work on a file specifying the bimatrix game,
such as ``examples/game``:

.. literalinclude:: ../../examples/game
   :language: text

See details about how the input file should be formatted
on the :doc:`file formats <../file_formats>` page.

Lemke-Howson
~~~~~~~~~~~~

Start from all labels (the default):

.. code-block:: console

   $ bimatrix lh examples/game

   label 1 found eq (1,0),(1,0)
       supports: [0][0]
   label 2 found eq (0,1),(0,1)
       supports: [1][1]
   -------- equilibria found: --------
   (1,0),(1,0)
       supports: [0][0] found by labels [1, 3]
   (0,1),(0,1)
       supports: [1][1] found by labels [2, 4]

Start only from some labels, given as single labels and ranges:

.. code-block:: console

   $ bimatrix lh --labels 1,3-4 examples/game

   label 1 found eq (1,0),(1,0)
       supports: [0][0]
   label 4 found eq (0,1),(0,1)
       supports: [1][1]
   -------- equilibria found: --------
   (1,0),(1,0)
       supports: [0][0] found by labels [1, 3]
   (0,1),(0,1)
       supports: [1][1] found by labels [4]

Tracing procedure
~~~~~~~~~~~~~~~~~

From the uniform prior:

.. code-block:: console

   $ bimatrix trace uniform examples/game

   -------- statistics of equilibria found: --------
   1 times found (0,1),(0,1)
       supports: [1][1]
   1 total priors, 1 equilibria found

From 100 random priors, with a fixed seed:

.. code-block:: console

   $ bimatrix trace random --priors 100 --seed 1 --accuracy 100 examples/game

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

Allow more digits after the decimal point in the game file
(all subcommands accept this):

.. code-block:: console

   $ bimatrix trace uniform --decimals 6 examples/game
