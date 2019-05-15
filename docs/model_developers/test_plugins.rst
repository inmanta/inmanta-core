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

    # <module-name>/plugins/__init__.py

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

    # <module-name>/tests/test_hostname.py

    def test_hostname(project):
        host = "test"
        fqdn = f"{host}.something.com"
        assert project.get_plugin_function("hostname")(fqdn) == host


* **Line 3:** Creates a pytest test case, which requires the ``project`` fixture.
* **Line 6:** Calls the function ``project.get_plugin_function(plugin_name: str): FunctionType``, which returns the plugin
  function named ``plugin_name``. As such, this line tests whether ``host`` is returned when the plugin function
  ``hostname`` is called with the parameter ``fqdn``.
