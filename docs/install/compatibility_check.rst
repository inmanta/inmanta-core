Compatibility check
###################

The Docker container for the Inmanta server contains a compatibility file at ``/usr/share/inmanta/compatibility/compatibility.json``. This file indicates with which versions of dependent components this orchestrator version is guaranteed to be compatible (See: :ref:`the compatibility page<compatibility-file>` for more information).

The container sets the :inmanta.config:option:`server.compatibility-file` config option via the ``INMANTA_SERVER_COMPATIBILITY_FILE`` environment variable to the above-mentioned file by default. As such:

* The Inmanta orchestrator will fail to start if it would run against an incompatible PostgreSQL version.
* The constraints defined in the `python_package_constraints` field of the compatibility file will be enforced both
  during project install and during agent install.
