Compatibility check
###################

The Docker container for the Inmanta server contains a compatibility file at ``/usr/share/inmanta/compatibility/compatibility.json``. This file indicates with which versions of dependent components this orchestrator version is guaranteed to be compatible (See: :ref:`the compatibility page<compatibility-file>` for more information). The :inmanta.config:option:`server.compatibility-file` config option is unset by default.
