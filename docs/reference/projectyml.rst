Compiler Configuration Reference
===================================


project.yml
------------
Inside any project the compiler expects a project.yml file that defines metadata about the project,
the location to store modules, repositories where to find modules and possibly specific versions of
modules. 

For basic usage information, see 'Create a configuration model'_.

Project.yml defines the following settings:

    * ``name`` An optional name of the project.
    * ``description`` An optional description of the project
    * ``modulepath`` This value is a list of paths where Inmanta should search for modules. Paths
      are separated with ``:``
    * ``downloadpath`` This value determines the path where Inmanta should download modules from
      repositories. This path is not automatically included in in modulepath!
    * ``install_mode`` This key determines what version of a module should be selected when a module
      is downloaded. This is used when the module version is not "pinned" in the ``requires`` list.
      The available values are:

        * release (default): Only use a released version, that is compatible with the current
          compiler. A version is released when there is a tag on a commit. This tag should be a
          valid version identifier (PEP440) and should not be a prerelease version. Inmanta selects
          the latest available version (version sort based on PEP440).
        * prerelease: Similar to release, but also prerelease versions are allowed.
        * master: Use the master branch.

    * ``repo`` This key requires a list (a yaml list) of repositories where Inmanta can find
      modules. Inmanta creates the git repo url by formatting {} or {0} with the name of the repo. If no formatter is present it
      appends the name of the module. Inmanta tries to clone a module in the order in which it is defined in this value.
    * ``requires`` Model files import other modules. These imports do not determine a version, this
      is based on the install_model setting. Modules and projects can constrain a version in the
      requires setting. Similar to the module, version constraints are defined using `PEP440 syntax
      <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.
    * ``freeze_recursive`` This key determined if the freeze command will behave recursively or not. If freeze_recursive is set to false or not set, 
      the current version of all modules imported directly in the main.cf file will be set in project.yml. If it is set to true, 
      the versions of all modules used in this project will set in project.yml.
    * ``freeze_operator`` This key determines the comparison operator used by the freeze command. *Default is '~='*  
 
 
 module.yml
 ----------
 Inside any module the compiler expects a module.yml file that defines metadata about the module.
 
 
 module.yml defines the following settings:

    * ``name`` An optional name of the project.
    * ``description`` An optional description of the project
    * ``license`` The license for this module
    * ``requires`` Model files import other modules. These imports do not determine a version, this
      is based on the install_model setting of the project. Modules and projects can constrain a version in the
      requires setting. Similar to the module, version constraints are defined using `PEP440 syntax
      <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.
    * ``freeze_recursive`` This key determined if the freeze command will behave recursively or not. If freeze_recursive is set to false or not set, 
      the current version of all modules imported directly in any submodule of this module will be set in module.yml. If it is set to true, 
      all modules imported in any of those modules will also be set.
    * ``freeze_operator`` This key determines the comparison operator used by the freeze command. *Default is '~='*  
 
 
    