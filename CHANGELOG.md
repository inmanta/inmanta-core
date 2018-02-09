v 2018.1 (201x-xx-xx)
Changes in this release:
- Ubuntu 14.04 mongo (2.4) is no longer supported. Version 2.6 or higher is required.
- The inmanta API endpoint is now versioned and available under /api/v1. The old API methods
  still work, but are deprecated and will be removed in the next release.

v 2017.4 (2017-11-27)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- added keyword parents, and implemented implementation inheritance (#504)
- set_param recompile parameter
- Raise an exception when duplicate resources are exported (#513)
- Added fix for index issue (#512)
- Allow to configure server compile per environment
- Add remove parameter API call
- Attributes and lists now accept trailing comma (#502)
- Added check for attribute redefinition within one entity (#503)
- Parse bool values in the rest api
- Fix bug in dryrun reporting with auth enabled

v 2017.3 (2017-10-27)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- Add relation annotations to the relation attribute and resolve it for exporters to use
- Documentation improvements
- Add an undefined resource state to the server (#489)
  Previously all unknown handling was done in the server. This resulted in strange reporting as the number of managed resource
  could go up and down. Now, an additional resource state "undefined" is introduced. This  state is handled similar to skipped
  during deploys. Undefined resources are undeployable.
- Undeployable resources are now already marked as finished at the moment a version is released or a dryrun is requested.
  Resources that depend on resources in an undeployable state will be skipped on the server as well.
- Sort index attributes: This patch ensure that std::File(host, path) and std::File(path, host) are the same indexes.
- Improved modules list ouput: rename columns and added a column to indicate matching rows
- Improve attribute check. fixes (#487)
- Fix index issues related with inheritance (#488)
- When a resource is purged, its facts will be removed. (#3)
- Add location to type not found exception in relation (#475. #294)
- Add JWT authz and limitation to env and client type (#473)
- Added fix for function execution in constraints (#470)
- Each agent instance now has its own threadpool to execute handlers. (#461)
- Allow agent instances to operate independently (#483)
- Improved error reporting on parser errors (#468, #466)
- Fixed selection of lazy arguments (#465)

v 2017.2 (2017-08-28)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- Preserve env variables when using sudo in the agent
- Prune all versions instead of only the ones that have not been released.
- Use python 2.6 compatible syntax for the remote io in the agent
- Gradual execution for for-loops and constructors
- Stop agents and expire session on clear environment
- Improve purge_on_delete semantics
- New autostart mechanism  (#437)
- Add settings mechanism to environment. More settings will become environment specific in later
  releases.
- Do not create index in background to prevent race conditions
- Add support for exception to the json serializer
- Invert requires for purged resources (purge_on_delete)
- Add autodeploy_splay option
- Remove ruaml yaml dependency (#292)
- Handle modified_count is None for mongodb < 2.6
- Add python3.6 support
- Add nulable types
- Various documentation updates
- Added monitor command to inmanta-cli (#418)
- Generate inmanta entrypoint with setuptools
- Update quickstart to use centos
- Improve event mechanism (#416)
- Added auto newline at end of file (#413)
- Improved type annotations for plugins and improved object unwrapping (#412)
- Inline index lookup syntax (#411)
- Added cycle detection (#401)
- Fixed handling of newlines in MLS lexer mode (#392)
- Added docstring to relations, typedef, implementation and implement (#386)
- Fix agent-map propagation from deploy

v 2017.1 (2017-03-29)
New release with many improvements and bug fixes. Most noteable features include:
- Port CLI tool to click and improve it. This removes cliff and other openstack deps from core
- Complete rewrite of the database layer removing the dependency on motorengine and improve
  scalability.
- Cleanup of many API calls and made them more consistent
- Improved handler protocol and logging to the server.

v 2016.6 (2017-01-08)
Mainly a bugfix and stabilisation release. No new features.

v 2016.5 (2016-11-28)
New release with upgraded server-agent protocol
- Upgraded server agent protocol
- New relation syntax

v 2016.4 (2016-09-05)
New relase of the core platform
- Various compiler improvements
- Add list types
- Cleanup of is defined syntax in the DSL and templates
- Many additional test cases
- Various bugfixes

v 2016.3 (2016-08-18)
New release. Way to late due to kids and vacation.
- Added SSL support
- Added auth to server
- Add JIT loading of modules
- Various bug fixes

v 2016.2.3 (2016-05-30)
- Fix memory leak in server

v 2016.2.2 (2016-05-25)
- Remove urllib3 dependency to ease packaging on el7

v 2016.2.1 (2016-05-04)
- Various bugfixes related to new ODM and async IO

v 2016.2 (2016-05-02)
- First bi-monthly release of Inmanta
- New compiler that speeds up compilation an order of magnitude
- All RPC is now async on the tornado IOLoop
- New async ODM for MongoDB
- Increased test coverage
