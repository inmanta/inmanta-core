Authorization providers
=======================

The Inmanta server supports two authorization providers: ``policy-engine`` and ``legacy``.

* ``policy-engine``: The policy-engine authorization provider allows fine grained access control by writing a access policy file.
* ``legacy``: The legacy authorization provider is the old authorization provider that provides limited, coarse grained access control.

The details of each these providers are discussed in more detail in the following sections.

Policy-engine authorization provider
------------------------------------

The picture below provides a high-level overview on how the policy-engine authorization provider works:

.. TODO: High level overview
.. TODO: Where find overview of properties set on API endpoints.

* When the policy-engine authorization provider is enabled, the Inmanta server starts a policy engine (The `Open Policy Agent<https://www.openpolicyagent.org/>`_ policy engine). This engine has access to two sources of information: The access policy defined by the user and the details about the different API endpoints defined on the Inmanta server.
* When an API call arrives on the Inmanta server, it request the policy engine whether the request is allowed by the access policy. It does so by providing the parameters of the API endpoint and the decoded access token to the policy engine. If the policy allows the request, the API call is executed. Otherwise a permission denied is returned to the client.


Data sources for policy engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An mentioned above, the policy engine interacts with three pieces on of information: the access policy, the properties of each API endpoint in the server and the data provided by an API call. The sections below discuss each of these three elements in more detail.


Properties API endpoints
""""""""""""""""""""""""

Every API endpoint on the server is annotated with the following properties:

* client_types: The client types for which the API endpoint is intended (api, agent, compiler). 
* auth_label: API endpoints that manipulate/inspect similar data are grouped together by applying the same label to them. This property indicates the label of authorization label of the endpoint. The labels can be used to define shorter and better structured access policies.
* read_only: A boolean value indicating whether the API endpoint is read-only or not.
* environment_param: The parameter in the API request that contains the ID of the environment on which the API call is executed. Or null, if the API endpoint doesn't act on a specific environment.

All this information is available in the access policy in the variable ``data.endpoints``. The snippet below provides an example on what the endpoints dictionary looks like:

.. TODO: Check value auth_label + explain it can be a name of a header

.. code-block:: rego

    {   
        "endpoints": {
            "GET /api/v1/project/{id}": {
                "client_types": ["api"],
                "auth_label": "project.read",
                "read_only": true,
                "environment_param": "id",
            },
            "POST /lsm/v1/service_inventory/{service_entity}": {
                "client_types": ["api", "agent"],
                "auth_label": "instance.write", 
                "read_only": false,
                "environment_param": "X-Inmanta-tid",
            },
            ...
        }
    }


Data API request
""""""""""""""""

The parameters of the API call and the decoded access token are available in the access policy using respectively
the ``input.request`` and ``input.token`` variable. The snippet below provides an example about what these
datastructures look like.

.. code-block:: rego

   {
       "input": {
           "request": {
               "endpoint_id": "PUT /api/v2/environment",
               "parameters": {
                   "branch": "master",
                   "description": "",
                   "environment_id": UUID("c5136bf0-76f9-42db-be6f-ce7a90d587b6"),
                   "icon": "",
                   "name": "env",
                   "project_id": UUID("e89f1a3a-7a98-4be2-a23f-3eb01183bef2"),
                   "repository": "https://github.com/inmanta/example.git",
               }
           },
           "token": {
               "aud": ["https://localhost:8888/"],
               "iss": "https://localhost:8888/",
               "urn:inmanta:ct": ["api"],
               "urn:inmanta:is_admin": True,
               "urn:inmanta:roles": {},
           }
       }
   }


Access policy
"""""""""""""

An access policy is written in the `Rego query language<https://www.openpolicyagent.org/docs/policy-language>`_. The policy must contain a rule named ``allow`` that evaluates to a boolean value. This rule is evaluated for each API call. If the value evaluates to True the API call is authorized, otherwise it's not. The snippet below provides a short policy that grants read-only access to user having the read-only role and any access to user with the user role.

.. code-block:: rego

    # Get the metadata for the specific endpoint that is called.
    endpoint_data := data.endpoints[input.request.endpoint_id]
    
    # Don't allow anything that is not explicitly allowed.
    default allow := false
    
    # Give read-only access to users with the read-only role.
    allow if {
        input.token.role == "read-only"
        endpoint_data.read_only == true
    }
    
    # Users with the user role are allowed to call any API endpoint.
    allow if {
        input.token.role == "user"
    }


Default access policy
^^^^^^^^^^^^^^^^^^^^^

The Inmanta server comes with a default policy that is defined in ``/etc/inmanta/authorization/policy.rego``. The policy assumes that there are two types of roles: environment-scoped roles and global roles. Environment-scoped roles are relevant within a specific environment. Global roles are relevant or the entire server. The following roles are defined in the default policy:

1. Environment-scoped roles:
   * read-only: Users with this role has read-only access on everything in a certain environment.
   * noc: The user can do all operations on a certain environment that do not alter the desired state or modify the settings.
   * operator: A user with the operator role can create, update and delete service instances in a certain environment next to the actions allowed by a user with the noc role.
   * environment-admin: Users with this role can do anything in a certain environment, except for expert actions.
   * environment-expert-admin: Users with this role can do anything in a certain environment.
2. Global admin role: A user with this role can execute any API endpoint on the Inmanta server.

The default policy makes the following assumptions about the content of the access token:

* The ``sub`` claim contains the username the token is for.
* Environment-scoped roles are defined in the ``urn:inmanta:roles`` claim of the access token. The value must be a dictionary that maps the uuid of the environment to a list of roles the user has in that environment.
* Global admins must have the claim ``urn:inmanta:is_admin`` in the access token with the value set to ``true``.


Integration with database authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default policy integrates seemlessly with database authentication.

* The admin user created using the ``/opt/inmanta/bin/inmanta-initial-user-setup`` command will have the ``urn:inmanta:is_admin`` claim set to true.
* The global admin role can be managed using the ``/api/v2/is_admin`` endpoint.
* Environment-scoped roles can be managed using the ``/api/v2/role`` endpoints.
* Role assignents can be managed using the ``/role_assignment/<username>`` endpoints.

If the policy contains a ``roles`` variable that contains a list role names, these roles will be created automatically when the server starts. Like that there is no need to create the roles using the ``POST /api/v2/role`` endpoint. Removing a role from this list will not remove that role when the server starts.


Enable the policy-engine authorization provider
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. By default, the Inmanta server will use the policy file defined in ``/etc/inmanta/authorization/policy.rego``.
   The location of the policy file can be changed using the :inmanta.config:option:`policy_engine.policy-file` if desired.
2. Set the :inmanta.config:option:`server.authorization-provider` config option to ``policy-engine``.
3. If a 3rd party auth broker is used, it must be configured to add the claims to the access token in correspondance to the access policy.
4. Restart the inmanta server. 

Writing a custom access policy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section provides some guidence when writing your own access policy.


Troubleshooting: Policy engine fails to start
"""""""""""""""""""""""""""""""""""""""""""""

.. TODO: Increase log policy engine + try to start server


Debugging/Testing an access policy
""""""""""""""""""""""""""""""""""

.. TODO: Show how to obtain data input
.. TODO: Reference default testing an debug tools of OPA


Legacy authorization provider
-----------------------------

The legacy provider provides limited support for authorization by checking for inmanta specific claims inside the token. All inmanta claims
are prefixed with ``urn:inmanta:``. These claims are:

* ``urn:inmanta:ct`` A *required* comma delimited list of client types for which this client is authenticated. Each API call
  has one or more allowed client types. The list of valid client types (ct) are:

  * agent
  * compiler
  * api (cli, web-console, 3rd party service)
* ``urn:inmanta:env`` An *optional* claim. When this claim is present, the token is scoped to this inmanta environment. All
  tokens that the server generates for agents and compilers have this claim present to limit their access to the environment
  they belong to.

