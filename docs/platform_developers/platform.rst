Platform Developers Guide
=========================

Dependencies
------------

All dependencies in this project need to be pinned to specific version. These versions are pinned in requirements.txt. This
file can be used to install all dependencies at once or use it as a constraint file for tox or pip install. requirements.txt
contains all dependencies for the core platform, for running tests and for generating documentation.

.. code-block:: sh

    # Install inmanta from current checkout
    pip install -c requirements.txt .


https://pyup.io monitors each dependency for updates and security issues. The inmanta development policy is to track the latest
version of all dependencies.

Versioning
----------

A release gets its version based on the current year and an index for the release. The release schedule targets a release every
two months but this tends to slip. The latest stable release (e.g. 2017.1) gets backported bugfixes, these release get a micro
version number (e.g. 2017.1.4). All versions get a tag in the git repo prefixed with v (e.g. v2017.1.
Supported versions are available in a branch under stable/ for backports and bugfixes (e.g. stable/v2017.1).

Development is done in the master branch. The version of the master branch is set to the next release version, but tagged with 
dev. This is configured in setup.cfg with the tag_build setting. The CI/build server can generate snapshots. Snapshots also need
to have the dev tag (for correct version comparison) appended with the current date in +%Y%m%d%H%M format.

.. code-block:: sh

    # Tag the code and build a source dist
    python setup.py egg_info -b "dev$(date +%Y%m%d%H%M)" sdist
    

Running tests
-------------

Inmanta unit tests are executed with pytest. In tests/conftest.py provides numerous fixtures for tests. Use python functions 
for new tests. If setup and teardown is required, use fixtures instead of class based tests. Currently a number of tests are
still class based and are in progress of being ported to function based tests.

To make sure the tests run with correct dependencies installed, use tox as a testrunner. This is as simple as installing tox and
executing tox in the inmanta repo. This will first run unit tests and validate code guideliness as well.  
