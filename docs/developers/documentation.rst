Documentation writing
=====================

Inmanta uses Sphinx to generate documentation.

Inmanta code documentation
--------------------------

Modules
*******

Python core
***********

Sphinx tooling
--------------
The inmanta-sphinx package provides additional sphinx directives. The directives can render inmanta module documentation
and configuration documentation.

Install inmanta sphinx extension
********************************
Install the inmanta sphinx extension by installing the inmanta-sphinx package from pypi. Adding the extensions to the extension
list in conf.py enables the extensions. The names are ```sphinxcontrib.inmanta.config``` and ```sphinxcontrib.inmanta.dsl```.

This module also install the sphinx-inmanta-api script. This script can be used to generate an RST file with the full
API documentation from a module. This script is used to generate for example the API docs included in the 
documentation on https://docs.inmanta.com

sphinxcontrib.inmanta.config
****************************

This extension loads all the defined configuration options in the Inmanta core and uses
the embedded documentation to generate a config reference.

It adds the show-options directive and a number of config objects to sphinx. Use it like this to
generate documentation:

.. code-block:: rst

    .. show-options::

        inmanta.server.config
        inmanta.agent.config


sphinxcontrib.inmanta.dsl
*************************

This exention adds objects and directives to add documentation for Inmanta dsl objects such as
entities, relations, ...

RST files can reference to inmanta configuration code with ```:inmanta:entity:`std::File````. This renders to
:inmanta:entity:`std::File`

sphinx-inmanta-api
******************

This scripts generates an RST file that provides the API documentation of a module. The documentation is generated
by compiling an empty project with this module included. The generator then uses the compiler representation to emit 
RST code, using the directives from the inmanta.dsl domain extension. This script has the following options:

 * ```--module_repo``` A local directory that function as the repo where all modules are stored that are required to generate the API documentation.
 * ```--module``` The name of the module to generate api docs for.
 * ```-m``` or ```--extra-modules```  An optional argument that can be provided multiple times. This is a list of modules that should be loaded 
   as well when the API docs are generated. This might be required when other modules also provided implementations that have to be listed.
 * ```--source-repo``` The repo where the upstream source is located. This is used to include a url in the documentation.
 * ```-f``` or ```--file``` The file to save the generated documentation in.