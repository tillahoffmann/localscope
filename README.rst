🔐 localscope
=============

.. image:: https://img.shields.io/static/v1?label=&message=GitHub&color=gray&logo=github
    :target: https://github.com/tillahoffmann/localscope

.. image:: https://github.com/tillahoffmann/localscope/actions/workflows/build.yml/badge.svg
  :target: https://github.com/tillahoffmann/localscope/actions/workflows/build.yml

.. image:: https://readthedocs.org/projects/localscope/badge/?version=latest
  :target: https://localscope.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/pypi/v/localscope.svg
   :target: https://pypi.python.org/pypi/localscope

Have you ever hunted bugs caused by accidentally using a global variable in a function in a `Jupyter notebook <https://jupyter.org/>`__? Have you ever scratched your head because your code broke after restarting the Python kernel? localscope can help by restricting the variables a function can access.

.. doctest::

   >>> from localscope import localscope
   >>>
   >>> a = 'hello world'
   >>>
   >>> @localscope
   ... def print_a():
   ...     print(a)
   Traceback (most recent call last):
     ...
   localscope.LocalscopeException: `a` is not a permitted global (file "...",
      line 1, in print_a)

See the :ref:`interface` section for an exhaustive list of options and the :ref:`motivation` for a more detailed example.

Installation
------------

.. code-block:: bash

   $ pip install localscope

.. _interface:

Interface
---------

.. autofunction:: localscope.localscope

.. _motivation:

Motivation and Example
----------------------

Interactive python sessions are outstanding tools for analysing data, generating visualisations, and training machine learning models. However, the interactive nature allows global variables to leak into the scope of functions accidentally, leading to unexpected behaviour. For example, suppose you are evaluating the mean squared error between two lists of numbers, including a scale factor ``sigma``.

.. doctest::

   >>> sigma = 7
   >>> # [other notebook cells and bits of code]
   >>> xs = [1, 2, 3]
   >>> ys = [4, 5, 6]
   >>> mse = sum(((x - y) / sigma) ** 2 for x, y in zip(xs, ys))
   >>> mse
   0.55102...

Everything works nicely, and you package the code in a function for later use but forget about the scale factor introduced earlier in the notebook.

.. doctest::

   >>> def evaluate_mse(xs, ys):  # missing argument sigma
   ...     return sum(((x - y) / sigma) ** 2 for x, y in zip(xs, ys))
   >>>
   >>> mse = evaluate_mse(xs, ys)
   >>> mse
   0.55102...

The variable ``sigma`` is obtained from the global scope, and the code executes without any issue. But the output is affected by changing the value of sigma.

.. doctest::

   >>> sigma = 13
   >>> evaluate_mse(xs, ys)
   0.15976...

This example may seem contrived. But unintended information leakage from the global scope to the local function scope often leads to unreproducible results, hours spent debugging, and many kernel restarts to identify the source of the problem. Localscope fixes this problem by restricting the allowed scope.

.. doctest::

   >>> @localscope
   ... def evaluate_mse(xs, ys):  # missing argument sigma
   ...     return sum(((x - y) / sigma) ** 2 for x, y in zip(xs, ys))
   Traceback (most recent call last):
     ...
   localscope.LocalscopeException: `sigma` is not a permitted global (file "...",
      line 3, in <genexpr>)
