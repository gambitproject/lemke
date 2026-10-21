File formats
============

lemke reads two kinds of plain-text input files: **LCP files** and **bimatrix files**.


Common rules
------------

Comments
   Lines starting with ``#``, ``%`` or ``*`` are ignored. Use them for
   notes, titles or the source of a game.

   Keep in mind that only whole lines starting with these characters are ignored,
   i.e. a ``#`` in the middle of a line does not start a comment.

Spaces
   Every item, including keywords such as ``n=`` and ``M=``,
   must be separated from its neighbours by white space.

   Extra line breaks and white spaces are ignored.

Numbers
   Entries are read as exact rational numbers. You can use integers,
   fractions such as ``1/3``, and decimals such as ``0.33``.

   Each parsed decimal is rounded (half away from zero) to a specified
   number of decimal places, which is 4 by default.
   This number can be set by the ``decimals`` argument
   in the library, and the ``--decimals`` flag via the CLI.

Errors
    In case of a malformed file, an error is thrown.

Examples
    You can view the ``examples/`` directory for additional example files.


LCP files
---------

An LCP file describes the problem

.. math::

   w = q + Mz, \qquad w \ge 0, \quad z \ge 0, \quad z^\top w = 0,

together with a covering vector :math:`d` for Lemke's algorithm, where
:math:`M` is an :math:`n \times n` matrix and :math:`q` and :math:`d` are
vectors of length :math:`n`.

Structure
~~~~~~~~~

1. The file starts with the keyword ``n=`` followed by the dimension
   :math:`n`, for example ``n= 5``. The keyword and the number are separate
   words, so write a space between them.
2. The keywords ``M=``, ``q=`` and ``d=`` follow, each introducing its data.
   They may appear in any order, but each of them must appear.

   - ``M=`` is followed by :math:`n \cdot n` numbers, the entries of
     :math:`M` row by row.
   - ``q=`` and ``d=`` are each followed by :math:`n` numbers.

Example
~~~~~~~

A simple 2x2 LCP:

.. code-block:: text

   # a 2x2 LCP

   n= 2
   M= 2/3 1.2
      1 2
   q= -1 -1
   d= 1 1


Bimatrix files
--------------

A bimatrix file describes a two-player game in strategic form. The row
player has :math:`m` pure strategies, the column player has :math:`n`, and
the game is given by two payoff matrices :math:`A` and :math:`B`, each of
size :math:`m \times n`.

Structure
~~~~~~~~~

1. The file starts with the two integers :math:`m` and :math:`n`, with no
   keywords.
2. Next come the :math:`m \cdot n` payoffs of the row player (matrix
   :math:`A`), row by row.
3. Last come the :math:`m \cdot n` payoffs of the column player (matrix
   :math:`B`), row by row.

Entry :math:`(i, j)` of each matrix is the payoff to that player when the row
player chooses strategy :math:`i` and the column player chooses strategy
:math:`j`.

Example
~~~~~~~

A 2×2 coordination game, "Battle of the Sexes":

.. code-block:: text

   # Battle of the Sexes

   # m n
   2 2

   # row player's payoffs A
   3 0
   0 2

   # column player's payoffs B
   2 0
   0 3
