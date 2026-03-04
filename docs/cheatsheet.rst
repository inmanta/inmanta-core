.. _cheatsheet:

DSL Cheat Sheet
***************

A single-page quick reference for the Inmanta modeling language. For full details, see :doc:`language`.


Entities
========

.. code-block:: inmanta

    entity File:
        string path
        string content
        int mode = 640
        string? owner = null      # nullable attribute
        string[] tags = []        # list attribute
        dict metadata = {}        # dictionary attribute
    end

Inheritance:

.. code-block:: inmanta

    entity Base extends std::PurgeableResource:
        bool send_event = true
    end

    entity Child extends Base:
        string extra
    end

    # Empty extension (inherit without adding attributes)
    entity Leaf extends Child: end


Relations
=========

.. code-block:: inmanta

    # Bidirectional with cardinalities: [min:max]
    Host.files [0:]  -- File.host [1]        # one-to-many
    A.b [1]          -- B.a [1]              # one-to-one
    A.bs [0:]        -- B.as [0:]            # many-to-many
    A.maybe_b [0:1]  -- B.a [1]             # optional

    # Unidirectional (no reverse end name)
    Service.config [1:] -- ConfigFile


Index and lookup
================

.. code-block:: inmanta

    index Host(name)
    index File(host, path)

    # Lookup by index
    h = Host[name="web1"]
    f = File[host=h, path="/etc/motd"]

    # Selector-style lookup on relation
    f = h.files[path="/etc/motd"]


Typedef
=======

.. code-block:: inmanta

    # Matching with condition
    typedef tcp_port as int matching self > 0 and self < 65535

    # Matching with regex
    typedef mac_addr as string matching /([0-9a-fA-F]{2})(:[0-9a-fA-F]{2}){5}$/

    # Matching with list membership
    typedef protocol as string matching self in ["tcp", "udp", "icmp"]

    # Using pydantic validation
    typedef vlan_id as int matching std::validate_type("pydantic.conint", self, {"ge": 1, "le": 4094})

    # Using a plugin function
    typedef valid_name as string matching my_module::validate_name(self)

    # Chained constraint (building on existing typedef)
    typedef short_word as std::ascii_word matching std::length(self) <= 20


Implementation and implement
============================

.. code-block:: inmanta

    implementation webSetup for WebServer:
        self.config = std::template("mymod/web.conf.tmpl")
        self.requires += self.network
    end

    # Unconditional binding
    implement WebServer using webSetup

    # Conditional binding
    implement WebServer using sslSetup when self.ssl_enabled

    # Multiple implementations
    implement WebServer using webSetup, loggingSetup

    # No-op implementation
    implement HelperEntity using std::none

    # Inherit parent implementations
    implement ChildEntity using parents

    # Cross-module implementation
    implement other_module::TheirEntity using my_local_impl


For loop
========

.. code-block:: inmanta

    for i in std::sequence(5, 1):
        Host(name=f"app{i}")
    end

    hosts = [Host(name="vm-1"), Host(name="vm-2")]
    for host in all_hosts:
        File(host=host, path="/etc/motd", content="Welcome")
    end


If / elif / else
================

.. code-block:: inmanta

    if self.mode == "ha":
        self.replicas = 3
    elif self.mode == "single":
        self.replicas = 1
    else:
        self.replicas = 0
    end


Conditional (ternary) expression
================================

.. code-block:: inmanta

    x = count > 0 ? count : 1
    label = is_production ? "prod" : "dev"


List comprehension
==================

.. code-block:: inmanta

    short_paths = [f.path for f in host.files if std::length(f.path) < 20]

    # Nested for
    all_files = [f for h in hosts for f in h.files]


String types
============

.. code-block:: inmanta

    regular   = "hello\nworld"                  # escape sequences interpreted
    raw       = r"no\nescapes"                  # backslashes are literal
    fstring   = f"host={hostname}, port={port}" # f-string formatting
    interp    = "host={{hostname}}"              # string interpolation (legacy)
    multiline = """line one
    line two"""                                  # triple-quoted multi-line
    concat    = "hello " + "world"              # string concatenation


Imports and aliases
===================

.. code-block:: inmanta

    import mymodule
    import mymodule::subns
    import mymodule::subns as sub


Constructor with dict spread
============================

.. code-block:: inmanta

    config = {"path": "/etc/app.conf", "mode": 644}
    f = File(host=h, **config)


Module-level constants
======================

.. code-block:: inmanta

    # In module infra, model/_init.cf
    nokia_sros = "nokia_sros"
    juniper_mx = "juniper_mx"

    # From another module
    implement Router using sros_impl when self.kind == infra::nokia_sros


``is defined`` check
====================

.. code-block:: inmanta

    if self.gateway is defined:
        # use self.gateway
    end

    implement Host using monitoringSetup when monitoring_server is defined


``in`` for list and dict membership
====================================

.. code-block:: inmanta

    if "tcp" in protocols:
        # ...
    end

    if "host" in config_dict:
        addr = config_dict["host"]
    end


``+=`` for relation append
==========================

.. code-block:: inmanta

    self.requires += self.network
    self.requires += self.subnet
    host.files += File(path="/etc/motd")


Type casting
============

.. code-block:: inmanta

    s = string(42)        # "42"
    n = int("42")         # 42
    f = float("3.14")     # 3.14
    b = bool(1)           # true


Common ``std`` functions
========================

.. code-block:: inmanta

    std::print("debug info")
    std::assert(count > 0, "count must be positive")

    content = std::template("mymod/config.tmpl")
    path = std::file("mymod/data.json")
    data = std::source("mymod/schema.json")

    items = std::sequence(10, 1)       # [1, 2, ..., 10]
    elem = std::at(my_list, 0)         # first element
    n = std::count(my_list)            # number of elements
    l = std::length("hello")           # 5

    parts = std::split("a,b,c", ",")   # ["a", "b", "c"]
    result = std::replace(s, "old", "new")

    ip = std::ipindex("10.0.0.0/24", 5, true)  # "10.0.0.5/24"

    env_val = std::get_env("MY_VAR", "default")
    env_int = std::get_env_int("RETRY_COUNT", 3)

    fact_val = std::getfact(my_resource, "ip_address")


Resource dependencies
=====================

.. code-block:: inmanta

    implementation setup for MyService:
        # Deploy network before this service
        self.requires += self.network

        # Deploy this service before the monitor
        self.provides += self.monitor
    end
