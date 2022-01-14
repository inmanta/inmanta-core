Test plugins
************

Testing the behavior of an Inmanta plugin can be done by using the ``project`` fixture, which is part of the ``pytest-inmanta``
package. This fixture provides functionality to call a plugin directly from a pytest test case.


Install the pytest-inmanta package
==================================

The ``pytest-inmanta`` package can be installed via pip:

.. code-block:: sh

    pip install pytest-inmanta


Writing a test case
===================

Take the following plugin as an example:

.. code-block:: python
    :linenos:

    # example_module/plugins/__init__.py

    from inmanta.plugins import plugin

    @plugin
    def hostname(fqdn: "string") -> "string":
        """
            Return the hostname part of the fqdn
        """
        return fqdn.split(".")[0]


A test case, to test this plugin looks like this:

.. code-block:: python
    :linenos:

    # example_module/tests/test_hostname.py

    def test_hostname(project, inmanta_plugins):
        host = "test"
        fqdn = f"{host}.something.com"
        assert inmanta_plugins.example_module.hostname(fqdn) == host


* **Line 3:** Creates a pytest test case, which requires the ``project`` fixture.
* **Line 6:** Uses the ``inmanta_plugins`` fixture to access the ``hostname`` function from the ``example_module``
    module's Python namespace. As such, this line tests whether ``host`` is returned when the plugin function
  ``hostname`` is called with the parameter ``fqdn``.

.. note::
    V2 modules do not need to use the ``inmanta_plugins`` fixture. They can just import from the ``inmanta_plugins`` namespace
    directly at the top of the test file.


For more information see: `pytest-inmanta <https://github.com/inmanta/pytest-inmanta>`_
