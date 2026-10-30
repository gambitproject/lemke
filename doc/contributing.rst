Contributing
============

Thank you for your interest in contributing to lemke.
Contributions of all kinds are welcome, including bug reports,
documentation improvements, feature requests, and code.

This guide explains how to get set up and how to submit your changes.


Ways to contribute
------------------

Reporting bugs
~~~~~~~~~~~~~~

Before opening a new issue, please search the
`issue tracker <https://github.com/gambitproject/lemke/issues>`_
to see whether the problem has already been reported.

When creating a new issue, include:

- A clear and descriptive title
- Steps to reproduce the problem
- The expected behavior and the actual behavior
- Your environment (OS, Python version, lemke version)
- Relevant logs, tracebacks, or screenshots

Suggesting features
~~~~~~~~~~~~~~~~~~~

You can use `discussions <https://github.com/gambitproject/lemke/discussions>`_
to suggest new features.

Open a discussion describing:

- Feature you want to add
- Use cases
- Any alternatives you have considered

Improving documentation
~~~~~~~~~~~~~~~~~~~~~~~

Other than bug fixes and new features, you can also update documentation.
The docs live in the ``doc/`` directory and are written in reStructuredText.


Development Setup
-----------------

1. Fork the repository on GitHub and clone your fork:

   .. code-block:: bash

      git clone https://github.com/<your-username>/lemke.git
      cd lemke

2. Add the upstream repository as a remote:

   .. code-block:: bash

      git remote add upstream https://github.com/gambitproject/lemke.git

3. Create and activate a virtual environment, then install the project in
   editable mode with development, testing, and documentation dependencies:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate
      pip install -e ".[dev,test,doc]"

4. Verify that the test suite passes:

   .. code-block:: bash

      pytest


Contribution workflow
---------------------

1. Sync your fork with the latest upstream changes:

   .. code-block:: bash

      git fetch upstream
      git checkout main
      git merge upstream/main

2. Create a branch with a descriptive name:

   .. code-block:: bash

      git checkout -b fix/short-description

3. Make your changes, adding or updating tests and documentation as needed.

4. Run the checks locally (see :ref:`contributing-testing`,
   :ref:`contributing-style`, and :ref:`contributing-docs`).

5. Commit your changes with a clear message.

6. Push your branch and open a pull request against ``main``.
   Before requesting a review, make sure that:

   - The code follows the project style and passes linting
   - Tests have been added or updated and pass locally
   - Documentation has been updated where relevant
   - The pull request description explains the change and links related issues


.. _contributing-style:

Code style
----------

We use automated tools like ``ruff`` to keep the codebase consistent.
Before submitting changes, you can run:

.. code-block:: bash

   ruff check .

.. tip::

   Install the pre-commit hooks with ``pre-commit install`` to run
   code style checks automatically on every commit.


.. _contributing-testing:

Testing
-------

All new features and bug fixes should include tests. Tests live in the
``tests/`` directory and are run with ``pytest``:

.. code-block:: bash

   # Run the full test suite
   pytest

   # Run a single file or test
   pytest tests/test_lcp.py::test_with_expected_results


.. _contributing-docs:

Building the documentation
--------------------------

The documentation is built with `Sphinx <https://www.sphinx-doc.org/>`_.
You can build it locally before pushing your changes.

To build the docs once:

.. code-block:: bash

   sphinx-build -b html doc doc/_build/html

To preview your changes with live reload, run the following from the
repository root and open http://127.0.0.1:8000 in your browser:

.. code-block:: bash

   sphinx-autobuild doc doc/_build/html

.. note::

   These commands work on Linux, macOS, and Windows.
   Stop the server with ``Ctrl+C``.


Running Doctests
~~~~~~~~~~~~~~~~

Code examples in the documentation and in docstrings are tested, so they must
stay correct. Run the doctests before submitting changes that touch either:

.. code-block:: bash

   sphinx-build -b doctest doc doc/_build/doctest


Licence
-------

By contributing, you agree that your contributions will be licenced under the
same licence as the project. See the :ref:`licence info <licence-citing>` for details.
