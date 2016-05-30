Versioning
**********

Inmanta has the moduletool subcommand to hanlde installing and checking of modules. The requirement are the following


Creating a project
==================

to create a project,
 
1. make a project directory
2. create a project.yml file::

	name: Testproject
	description: A project to demonstrate project creation
	modulepath: libs
	downloadpath: libs
	repo: ['git@git.inmanta.com:modules/', 'git@git.inmanta.com:config/']
	requires:
  		- std
  		- ip

* The modulepath is a list of paths where the compiler will search for modules
* the downloadpath is the path where the moduletool will install new modules
* the repo is a list of paths where the moduletool will search for new modules

Installing modules
==================
Once you have a project.yml file, you can automatically install the required modules::

	inmnata modules install 

This will clone the module and check out the last version.

Changing a module
==================

To make changes to a module, first create a new git branch::

	git checkout -b mywork
	
When done, first use git to add files::

	git add *
	
To commit, use the module tool. It will autmatically set the right tags on the module::

	inmanta moduletool commit -m "First commit" 

This will create a new dev release. To make an actual release::

	inmanta moduletool commit -r -m "First Release" 
	
To set a specific version:::

	inmanta moduletool commit -r -m "First Release" -v 1.0.1

Requires format
===============

To specify specific version are required, constraints can be added to the requires list::

	license: Apache 2.0
	name: ip
	source: git@git.inmanta.com:modules/ip
	version: 0.1.15
	requires:
    	net: net ~= 0.2.4
    	std: std >1.0 <2.5