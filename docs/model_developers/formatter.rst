.. _model-developers-formatter:

Formatting ``.cf`` files
========================

Inmanta ships with an opinionated, AST-safe formatter for the Inmanta DSL.
It normalizes whitespace, indentation, quote style, blank lines and line wrapping
across a code base so that diffs stay focused on real changes.

The formatter is inspired by `Black <https://black.readthedocs.io/>`_: it has
a small number of options and verifies that formatting never changes the parsed
AST of the file.

Quick start
-----------

Format every ``.cf`` file in the current directory tree in place:

.. code-block:: sh

    inmanta format

Format specific files or directories:

.. code-block:: sh

    inmanta format model/_init.cf model/services/

Show what would change without writing anything (CI mode):

.. code-block:: sh

    inmanta format --check

Print a unified diff of the changes that would be applied:

.. code-block:: sh

    inmanta format --diff

Override the maximum line length on the command line:

.. code-block:: sh

    inmanta format --line-length 100

Exit codes
~~~~~~~~~~

* ``0`` — nothing to do, or all files reformatted successfully.
* ``1`` — used together with ``--check``: at least one file would be reformatted.
* ``2`` — one or more files failed to format (parse errors, AST-equivalence
  failures, ...).  These errors are printed to stderr.

Configuration
-------------

The formatter reads its configuration from ``pyproject.toml`` in the current
directory or any parent directory.  All options live under the
``[tool.inmanta-format]`` table and use kebab-case keys:

.. code-block:: toml

    [tool.inmanta-format]
    line-length = 120
    indent-width = 4
    blank-lines-between-top-level = 2
    blank-lines-after-imports = 2
    normalize-quotes = true
    magic-trailing-comma = true
    group-annotations = true

If no configuration file is present, the defaults shown above apply.  CLI flags
take precedence over the configuration file.

Available options:

+--------------------------------------+----------+------------------------------------------------------------------+
| Key                                  | Default  | Description                                                      |
+======================================+==========+==================================================================+
| ``line-length``                      | ``120``  | Maximum line length before expressions are wrapped.              |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``indent-width``                     | ``4``    | Number of spaces per indentation level.                          |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``blank-lines-between-top-level``    | ``2``    | Blank lines around ``entity``, ``implementation``, ``typedef``.  |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``blank-lines-after-imports``        | ``2``    | Blank lines between the ``import`` block and the first           |
|                                      |          | non-import statement.                                            |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``normalize-quotes``                 | ``true`` | Rewrite single-quoted strings to double quotes when safe.        |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``magic-trailing-comma``             | ``true`` | Force multi-line layout when the user wrote a trailing comma in  |
|                                      |          | a list, dict, constructor or function call.                      |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``group-annotations``                | ``true`` | Insert blank lines between attribute groups inside an entity     |
|                                      |          | when ``__modifier`` / ``__annotation`` attributes are present.   |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``spaces-around-assignment``         | ``true`` | Use ``x = 1`` instead of ``x=1`` for statement-level assignment. |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``no-spaces-in-kwarg``               | ``true`` | Use ``Foo(name="x")`` instead of ``Foo(name = "x")``.            |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``no-spaces-in-default``             | ``true`` | Use ``string name="x"`` instead of ``string name = "x"`` for     |
|                                      |          | entity attribute defaults.                                       |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``spaces-around-binary-op``          | ``true`` | Insert spaces around binary operators (``a + b``, ``a == b``).   |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``space-after-comma``                | ``true`` | Insert a space after every comma in argument and element lists.  |
+--------------------------------------+----------+------------------------------------------------------------------+
| ``trailing-comma-in-expansion``      | ``true`` | Add a trailing comma when a list/dict/call is expanded over      |
|                                      |          | multiple lines.                                                  |
+--------------------------------------+----------+------------------------------------------------------------------+

Formatting rules
----------------

The formatter applies the following rules.  Unless explicitly noted, each rule
can be turned off through the corresponding ``[tool.inmanta-format]`` setting.

Layout
~~~~~~

* Indentation is 4 spaces; tabs are never produced.
* The output always ends with exactly one trailing newline.
* Trailing whitespace at the end of a line is removed.

Blank lines
~~~~~~~~~~~

* Two blank lines surround top-level ``entity``, ``implementation`` and
  ``typedef`` definitions.
* Two blank lines separate the import block from the rest of the file.
* Consecutive ``import``, ``implement``, ``index`` and relation statements are
  grouped together with no blank lines between them.
* Blank lines that the author wrote between regular statements are preserved,
  but multiple blank lines collapse to a single one.

Strings and quotes
~~~~~~~~~~~~~~~~~~

* Single-quoted strings are rewritten to double-quoted strings when this does
  not require introducing escapes (``'hello'`` → ``"hello"``, but
  ``'say "hi"'`` is left untouched).
* Triple-quoted docstrings (``"""..."""``) and raw / f-strings are preserved
  verbatim.

Spaces around operators and ``=``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Binary operators get a single space on both sides: ``a + b``, ``a == b``,
  ``a and b``.
* Statement-level assignments use spaces around ``=`` and ``+=``:
  ``x = 1``, ``self.items += [item]``.
* Constructor keyword arguments and entity attribute defaults use **no**
  spaces around ``=`` (matching Black's convention for keyword arguments):

  .. code-block:: text

      # before
      x = Foo(name = "bar", age = 5)
      entity Server:
          string hostname = "localhost"
      end

      # after
      x = Foo(name="bar", age=5)
      entity Server:
          string hostname="localhost"
      end

* A space is inserted after every comma in argument lists, lists and dicts.

Line wrapping and the magic trailing comma
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a list, dict, constructor or function call fits within ``line-length``,
it is kept on one line.  Otherwise, the formatter expands it across multiple
lines, with one element per line and a trailing comma:

.. code-block:: text

    # short — kept compact
    x = [1, 2, 3]

    # too long — expanded
    x = [
        a_long_identifier,
        another_long_identifier,
        yet_another_long_identifier,
    ]

A *magic trailing comma* — a comma after the last element written by the
author — forces the multi-line form even if the expression would fit on one
line.  This lets you opt in to a stable, multi-line layout:

.. code-block:: text

    # input
    Foo(name="bar", age=5,)

    # output
    Foo(
        name="bar",
        age=5,
    )

Removing the trailing comma collapses the construct back to a single line.
The behaviour can be disabled with ``magic-trailing-comma = false``.

Entities, relations and implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Entity bodies are indented one level under the ``entity ... :`` header and
  closed with ``end`` at the same indentation as the header.
* Relations are formatted with a single space around the relation operator
  (``--``) and before each multiplicity bracket: ``A.b [0:] -- B.a [1]``.
* When ``group-annotations`` is enabled, attributes whose name contains
  ``__`` (for example ``name__modifier``, ``name__annotations``) are grouped
  with the matching base attribute, and a blank line is inserted between
  groups inside the entity body.

AST-equivalence safety check
----------------------------

After formatting a file, the formatter parses both the original and the
formatted source and compares the resulting ASTs structurally.  If the two
ASTs differ in anything other than source positions, the formatter aborts and
raises an error rather than write a corrupted file.  This guarantees that
formatting can never change the meaning of your model.

If you ever encounter an ``AST equivalence`` error, please report it as a
bug — it indicates a defect in the formatter, not in your code.

Disabling the formatter locally
-------------------------------

Like Black, the Inmanta formatter understands three special comment
directives that suppress formatting for parts of a file.  They are useful to
preserve hand-aligned tables, annotated examples or generated blocks.

``# fmt: off`` / ``# fmt: on``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Everything between a ``# fmt: off`` and the next ``# fmt: on`` is emitted
verbatim:

.. code-block:: text

    x = Foo(a=1, b=2)
    # fmt: off
    y = Foo(  a =  1 , b   =2  )
    # fmt: on
    z = Bar(c=3)

If a ``# fmt: off`` is never closed, formatting is suppressed until the end
of the file.

``# fmt: skip``
~~~~~~~~~~~~~~~

A trailing ``# fmt: skip`` on a single line preserves that line as-is:

.. code-block:: text

    x = Foo(  a =  1  )  # fmt: skip
    y = Bar(b=2)

Continuous integration
----------------------

Add a CI step that fails the build if any file is not properly formatted:

.. code-block:: sh

    inmanta format --check

In ``--check`` mode the formatter never writes to disk; it lists the files
that would change and exits with status code ``1`` when there is at least
one.

Programmatic API
----------------

The formatter is also available as a Python module:

.. code-block:: python

    from inmanta.formatter import (
        FormatterError,
        check_file,
        diff_file,
        format_file,
        format_string,
    )
    from inmanta.formatter.config import FormatConfig

    config = FormatConfig.from_pyproject()  # or FormatConfig(line_length=100)

    formatted = format_string(source, config=config)
    formatted, changed = format_file("model/_init.cf", config=config, write=True)
    is_clean = check_file("model/_init.cf", config=config)
    patch = diff_file("model/_init.cf", config=config)

``format_string`` and ``format_file`` raise ``FormatterError`` if the input
fails to parse or if the AST-equivalence check would fail.
