v 2018.4 (2018-12-xx)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- Removal of snapshot and restore functionality from the server (#789)
- Replace virtualenv by python standard venv (#783)
- Updated to Tornado 5, moving from tornado ioloop to the standard python async framework (#765)
- Extend mypy type annotations
- Use files for all logs and split out logs, stdout and stderr in autostarted agents (#824, #234)
- Introduce request_timeout option for transport settings
- Port unit tests to pytest-asyncio and fix deprecation warnings (#743)
- Remove all io_loop references and only use current ioloop (#847)

v 2018.3 (2018-12-07)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- Added improved error reporting to CLI (#814)
- Fixed missing re-raise on pip install  (#810)
- Add pytest plugins (#786)
- Extra test cases for the data module + two bugfixes (#805)
- Fix deprecation warnings (#785)
- Reorganized test case in more modules to reduce the number of merge conflicts (#764)
- Prevent purge_on_delete due to failed compile (#780)
- Add mypy to tox and improve typing annotations (no enforcement yet) (#763)
- Removed incorrect uninitialize of subprocess signal handler (#778, #777)
- Fix modules do command (#760)
- Changed process_events so that it is called even when processing a skip. (#761)
- Track all locations where an instance has been created. (fixes #747)
- Add start to the index for the get_log query (#758)
- Improved reporting of nested exceptions (#746)
- Added compiler check on index attributes so an index on a nullable attribute now raises a compiler error. (#745)
- Added support for lazy attribute execution in constructors (#729)
- Big update to module and project version freeze. See documentation for more details (#106)
- Added argument to @plugin to allow unknown objects as arguments (#754)
- Fix for deploy of undefined resource (#627)
- Improved handling ofr dryrun failures (#631)
- Correctly store and report empty facts (#731)
- Allow get facts from undeployed or undefined resources  (#726)
- Minor changes for ide alpha release (#607)
- Added uniqueness check to indices (#715)
- Bugfixes in handling of optional attributes (#724)
- Transport cleanup (added bootloader, split off session management) (#564)
- Reserved keywords in resources (#645)
- Fix a bug in option definition
- Use own mongobox implementation that works with mongo >= 4
- Fixed reporting on undefined list attributes (#657)
- Improved list freeze for gradual execution (#643)
- Fixed bug in bounds check (#671)
- Improved error reporting on bad assignment (#670)
- Improved error reporting on missing type (#672)
- Added in operator for dicts (#673)

v 2018.2 (2018-07-30)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- The internal storage format for code is optimized. This introduces API and schema changes.
  This release supports both storage versions. The old version will be removed in the next release.
- Support formatter in repo url
- Make export of complete model configurable
- Use id of loopvar instead of hash to support iteration over list returned by plugins
- Fix error in default args for list attribute (#633)
- Add multi level map lookup (#622 and #632)
- Improved deploy, make deploy sync
- Added improved error message for lower bound violations on relations (#610)
- Fixes for empty optionals  (#609)
- Added improved logging to context handler (#602)
- Added fix for string representation (#552)
- Added support for single quotes (#589)
- Fix in operator in typedefs (#596)
- Fixed line numbers on MLS (#601)
- Added += operator for assignment to lists (#587)
- Add a synchronous protocol client
- Fix error message for wrong type in ctor
- Improve index error reporting
- Fix validate on modules with no commited version
- Set purged=false on clone in CRUDHandler (#582)
- Add gzip encoding support to protocol (#576)
- added anchormap functions to compiler
- Improved error reporting on for loops (#553)

v 2018.1 (2018-02-09)
Changes in this release:
- Various bugfixes and performance enhancements
- Dependency updates
- Ubuntu 14.04 mongo (2.4) is no longer supported. Version 2.6 or higher is required.
- The inmanta API endpoint is now versioned and available under /api/v1. The old API methods
  still work, but are deprecated and will be removed in the next release.
- Added support for escapes in regex (#540)
- Added per env config for agent_interval (#542): This adds an per environment setting that controls
  the agent interval for the agents started by the server.
- Removed implicit string to number conversion (#539)
- Fix dockerfile (#538)
- Fixed execnet resource leak (#534)
- Solution for resource leak issue in agent (#518): Numerous stability fixes for the agent related
  to resource leaks and races
- Remove compile reports on env clean
- Refactor report API: The report list no longer contains the output of the processes. This
  reduces the size of the response.
- Fix recompile triggered from a form change
- Add missing mongo indexes to improve performance
- Remove catchlog from tox run
- Create a post method for notify: only the post method allows to pass metadata
- Fix trigger metadata (#520): Add compile metadata to each version. Fixes #519 and add delete with
  resource_id for parameters
- Add representation for null value

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
