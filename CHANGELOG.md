# Release 2020.4 (?)

## New features
- Added merging of similar compile requests to the compile queue (#2137)
- Export all handler's / resource's module's plugin source files so helper functions can be used from sibling modules (#2162)
- Added documentation on how a string is matched against a regex defined in a regex-based typedef (#2214)
- Added support to query the resource action log of a resource via the CLI (#2253)
- Added conditional expression to the language with syntax condition ? x: y (#1987)
- Add support for inmanta-cli click plugins
- Added link to the PDF version of the documentation

## Bug fixes
- Restore support to pass mocking information to the compiler
- Disallow parameters mapped to a header to be passed via the body instead (#2151)
- Handle skipped and unavailable as failures when calculating increments (#2184)
- Constrain agent name to string values (#2172)
- Fix for allowing comments in the requirements.txt file of modules (#2206)
- Allow equality checks between types to support optional value overrides (#2243)

# Release 2020.3 (2020-07-02)

## New features
- Added cleanup mechanism of old compile reports (#2054)
- Added `compiler.json` option and `--json` compile flag to export structured compile data such as occurred errors (#1206)
- Added troubleshooting documentation (#1211)
- Documentation on compiler API and JSON (#2060)
- Documentation on valid client types (#2015)
- Improved documentation on handler development (#1278)
- Added further documentation to inmanta-cli command (#2057)
- Documentation of config option types (#2072)
- Added method names as Operation Id to OpenApi definition (#2053)
- Added documentation of exceptions to the platform developers guide (#1210)
- Extended documentation of autostarted agent settings (#2040)
- Typing Improvements
- Redirect stdout and stderr to /var/log/inmanta/agent.{out,err} for agent service (#2091)
- Added resource name to log lines in agent log.
- Better reporting of json decoding errors on requests (#2107)
- Faster recovery of agent sessions
- Add compiler entrypoint to get types and scopes (#2114)
- Add support to push facts via the handler context (#593)

## Upgrade notes
- Ensure the database is backed up before executing an upgrade.
- Updated Attribute.get_type() to return the full type instead of just the base type (inmanta/inmanta-sphinx#29)
- Overriding parent attribute type with the same base type but different modifiers (e.g. override `number` with `number[]`)
    is no longer allowed. This was previously possible due to bug (#2132)

## Bug fixes
- Various small issues (#2134)
- Fixed issue of autostarted agents not being restarted on environment setting change (#2049)
- Log primary for agent correctly in the database when pausing/unpausing agents (#2079)
- Cancel scheduled deploy operations of an agent when that agent is paused (#2077)
- Fix agent-names config type (#2071)
- Ensure the internal agent is always present in the autostart_agent_map of auto-started agents (#2101)
- Cancel scheduled ResourceActions when AgentInstance is stopped (#2106)
- Decoding of REST return value for content type html with utf-8 charset (#2074)
- Empty list option in config no longer interpreted as list of empty string (#2097)
- Correct closing of agentcache
- Agent cross environment communication bug (#2163)
- Fixed an issue where an argument missing from a request would result in a http-500 error instead of 400 (#2152)
- Ensure agent is in proper state after URI change (#2138)
- Removed warning about collecting requirements for project that has not been loaded completely on initial compile (#2125)

# v 2020.2 (2020-04-24) Changes in this release:

## Breaking changes
- Non-boolean arguments to boolean operators are no longer allowed, this was previously possible due to bug (#1808)
- Server will no longer start if the database schema is for a newer version (#1878)
- The environment setting autostart_agent_map should always contain an entry for the agent "internal" (#1839)

## Deprecated
 - Leaving a nullable attribute unassigned now produces a deprecation warning. Explicitly assign null instead. (#1775)
 - Default constructors (typedef MyType as SomeEntityType(some_field = "some_value")). Use inheritance instead. (#402)
 - Old relation syntax (A aa [0:] -- [0:] B bb) (#2000)

## Fixed
 - Various compiler error reporting improvements (#1810, #1920)
 - Fixed cache leak in agent when deployments are canceled (#1883)
 - Improved robustness of modules update (#1885)
 - Removed environmental variables from agent report (#1891)
 - Use asyncio subprocess instead of tornado subprocess (#1792)
 - Added warning for incorrect database migration script names (#1912)
 - Agent manager remains consistent when the database connection is lost (#1893)
 - Ensure correct version is used in api docs (#1994)
 - Fixed double assignment error resulting from combining constructor kwargs with default values (#2003)
 - Fixed recursive unwrapping of dict return values from plugins (#2004)
 - Resource action update is now performed in a single transaction, eliminating the possibility of inconsistent state (#1944)
 - Type.type_string is now defined as returning the representation of the type in the inmanta DSL (inmanta/lsm#75)

## Added
 - Experimental data trace, root cause and graphic data flow visualization applications (#1820, #1831, #1821, #1822)
 - Warning when shadowing variable (#1366, #1918)
 - Added support for compiler warnings (#1779, #1905, #1906)
 - Added support for DISABLED flag for database migration scripts (#1913)
 - Added v5 database migration script (#1914)
 - Added support for declaring implement using parents together with normal implement declaration list (#1971)
 - Resource Action Log now includes timestamps (#1496)
 - Added support to pause an agent (#1128)
 - Added --no-tag option to module tool (#1939)
 - Added base exception for plugins and corresponding documentation (#1205)
 - Added tags to openapi definition (#1751)
 - Added support to pause an agent (#1128, #1982)
 - Plugins are now imported in the inmanta_plugins package to allow importing submodules (#507)
 - Added event listener to Environment Service (#1996)
 - Autostarted agents can load a new value for the autostart_agent_map setting without agent restart (#1839)
 - Added protected environment option (#1997)
 - Added warning when trying to override a built-in type with a typedef (#81)
 - Added inmanta-cli documentation to the docs (#1992)

# v 2020.1 (2020-02-19) Changes in this release:

## Fixed
 - Added support for conditions as expressions and vice versa (#1815)

## Breaking changes
- Entity instances are no longer allowed in list and dict attributes, this was previously possible due to bug (#1435)

## Fixed
 - Fixed incorrect parsing of booleans as conditions (#1804)
 - Added support for nullable types in plugins (#674)
 - Inmanta type module cleanup and type coverage
 - Various compiler error reporting improvements (#1584, #1341, #1600, #1292, #1652, #1221, #1707, #1480, #1767, #1766, #1762, #1575)
 - CRUDHandler bugfix, ensure update is not called on purged resources
 - Changes in default values: AUTO_DEPLOY, PUSH_ON_AUTO_DEPLOY are enabled by default,
 AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY is set to incremental deployment
 - Fixed deadlock triggered by std::AgenConfigHandler (#1662)
 - Removed the resourceversionid table from the database (#1627)
 - Remote machines not being available or not having a python interpreter now results in a clearer error.
 - Parse comments and urls correctly from the requirements.txt file of an Inmanta module (#1764)

## Added
 - Added support for dict lookup in conditions (#1573)
 - Added support for type casts for primitive types (#1798)
 - Added support for multiline string interpolations (#1568)
 - Added int type to the language (#1568)
 - Add get_environment_id to exporter (#1683)
 - Added inmanta-cli environment save command (#1666)
 - Added finalizer support to @cache annotation
 - Added support to parse the docstring of an entity
 - Added support for \*\*dict as kwargs for constructor calls and index lookups (#620, #1702)
 - Added support for kwargs in plugin calls, as named arguments as well as using \*\*dict (#1143)

## Removed
 - Removed the inmanta module validate command. Use pytest-inmanta fixtures to test your modules instead.
 - Removed Forms functionality (#1667)

# v 2019.5 (2019-12-05) Changes in this release:

## Fixed
 - Compiler bugfix, ensure done nodes are correctly removed from zerowaiters
 - Fixed memory leak in database layer
 - Fixed lexing of strings ending in an escaped backslash (#1601)
 - Fixed bug where `module freeze` results in empty module.yml (#1598)
 - Fixed inconsistent behavior of `export` and `export -j` (#1595)

IMPORTANT CHANGES:
 - Added environment variables for config, env variables overwrite all other forms of config (#1507)

v 2019.4 (2019-10-30) Changes in this release:
- Various bugfixes (#1367,#1398,#736, #1454)
- Added if statement (#1325)
- Added CORS Access-Control-Allow-Origin header configuration (#1306)
- Added --version option (#1291)
- Added retry to moduletool update, to allow updating of corrupt projects (#177)
- RPM-based installations on Fedora are not supported anymore
- Added option to configure asyncpg pool (#1304)
- Split out the main service into many smaller services (#1388)
- Use python3 from the core OS in Dockerfile
- Introduce v2 protocol and implement project and environment api in v2 (#1412)
- Improve agent documentation (#1389)
- Improve language reference documentation (#1419)
- Change autostart_agent_deploy_splay_time from 600 to 10 (#1447)
- Introduce the bind-address and bind-port config option (#1442)
- Switch to sequential version numbers instead of timestamps (#1011)
- Fixed memory leak in TaskHandler
- Don't install packages inherited from the parent virtualenv
- Added logging to CRUD methods of handler and a diff method with context
- HTTP errors are logged at DEBUG level only (#1282)
- Verify hashes when serving a file (#532)
- Mark resource as failed when code loading fails (#1520)
- Print extra env variables in init log and only store those in database (#1482)
- Add feature manager for enabling and disabling orchestrator features (#1530)
- Add get_environment_id to plugin context (#1331)
- Log server bind address and bind port on startup (#1475)
- Fix warning about transport config (#1203)
- Add setting to environment to disable purge on delete (#1546)

IMPORTANT CHANGES:
- Older compiler versions are no longer supported with this server
- The Inmanta server now listens on 127.0.0.1:8888 by default, while
  this was 0.0.0.0:8888 in previous versions. This behavior is
  configurable with the `bind-address` config option.

DEPRECATIONS:
- The `server_rest_transport.port` config option is deprecated in favor
  of the `server.bind-port` option.

v 2019.3 (2019-09-05) Changes in this release:
- Various bugfixes (#1148, #1157, #1163, #1167, #1188)
- Abort server startup if the database can not be reached (#1153)
- Use native coroutines everywhere (async def)
- Updated dockerfile and docker-compose to use postgres and centos
- Added extensions mechanism (#565, #1185)
- Add /serverstatus api call to get version info, loaded slices and extensions (#1184)
- Support to set environment variables on the Inmanta server and its agents
- Split of server recompile into separate server slice (#1183)
- Add API to inspect compiler service queue (#1252)
- Define explicit path in protocol methods
- Added support for schema management for multiple slices in the same database (#1207)
- Marked pypi package as typed
- Create pytest-inmanta-extensions package for extensions testing
- Added support for /etc/inmanta/inmanta.d style configuration files (#183)
- Increased the iteration limit to 10000. This value is controlled with INMANTA_MAX_ITERATIONS
  environment variable.
- Added support for custom resource deserialization by adding the 'populate' method
- Improve compiler scaling by using more efficient data structures
- Added the --export-plugin option to the export command (#1277)
- Only one of set_created, set_updated or set_purged may be called now from a handler
- Remove facts when the resource is no longer present in any version (#1027)
- Successful exports without resources or unknowns will now be exported
- Export plugins will not run when the compile has failed
- Documentation updates and improvements (#1209)

DEPRECATIONS:
* The files /etc/inmanta/agent.cfg and /etc/inmanta/server.cfg are not used anymore. More information about the available
configuration files can be found in the documentation pages under `Administrator Documentation -> Configuration files`.

v 2019.2 (2019-04-30)
Changes in this release:
- Various bugfixes (#1046, #968, #1045)
- Migration from mongodb to postgres (#1023, #1024, #1025, #1030)
- Added metering using pyformance
- Added influxdb reporter for protocol endpoint metrics
- Remove the configuration option agent-run-at-start (#1055)
- Add project id and environment id as optional parameters to API call (#1001)
- Fixed an issue which cleared the environment on remote python 2 interpreters
- Improve deploy command resilience and added option to work with dashboard
- Added API endpoint to trigger agents deploy (#1052)
- Documentation updates and improvements (#905)

v 2019.1 (2019-03-06)
Changes in this release:
- Various bugfixes and performance enhancements (#873, #772, #958, #959, #955)
- Dependency updates
- Introduce incremental deploy (#791, #794, #793, #792, #932, #795)
- Introduce deploying resource state (#931)
- Introduce request_timeout option for transport settings
- Add support to run the compiler on windows
- Add exception explainer to compiler for 'modified after freeze' (#876)
- Improve log format, added replace file name with logger name
- Split out logs, stdout and stderr in autostarted agents (#824, #234)
- Add logging of resource actions on the server and purging of resource actions in the database (#533)
- Improve agent logging
- Replace virtualenv by python standard venv (#783)
- Update to Tornado 5, moving from tornado ioloop to the standard python async framework (#765)
- Use urllib client for fetching jwks public keys
- Remove all io_loop references and only use current ioloop (#847)
- Remove environment directory from server when environment is removed (#838)
- Catch various silent test failures
- Extend mypy type annotations
- Port unit tests to pytest-asyncio and fix deprecation warnings (#743)
- Raise exception on bad export to make inmanta export fail with exit status > 0
- Refactor protocol
- Improve lazy execution for attributes
- Update autogenerated config file for agents with correct server hostname (#892)

DEPRECATIONS:
- Minimal python version is now python 3.6
- Removal of snapshot and restore functionality from the server (#789)
- Removed the non-version api (#526)
- The config option agent-interval, agent-splay, autostart_agent_interval and autostart_splay are
deprecated in favour of agent-deploy-interval, agent-deploy-splay-time, autostart_agent_deploy_interval
and autostart_agent_deploy_splay_time respectively. The deprecated options will be removed in release 2019.2

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
