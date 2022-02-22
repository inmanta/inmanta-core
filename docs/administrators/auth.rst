.. _auth-setup:

Setting up authentication
=========================

This guide explains how to enable ssl and setup authentication.

SSL is not strictly required for authentication but higly recommended. Inmanta uses bearer tokens
for authorizing users and services. These tokens should be kept private and are visible in plain-text in the request headers
without SSL.


SSL: server side
----------------
Setting a private key and a public key in the server configuration enables SSL on the server. The two
options to set are :inmanta.config:option:`server.ssl-cert-file` and :inmanta.config:option:`server.ssl-key-file`.

For the autostarted agents and compiler to work, either add the CA cert to the trusted certificates of the system or
set :inmanta.config:option:`server.ssl-ca-cert-file` to the truststore.

.. code-block:: ini
    [server]
    # The ssl certificate used by the server
    ssl_cert_file=/etc/inmanta/server.crt
    # The private key used by the server, associated with the certificate
    ssl_key_file=/etc/inmanta/server.key.open

    # The certificate chain that the compiler and agents should use to validate the server certificate
    ssl_ca_cert_file=/etc/inmanta/server.chain
    # The address at which the compiler and agent should connect
    # Must correspond to hostname the ssl certificate is bound to
    server_address=localhost



SSL: remote agents and remote compiler
--------------------------------------
When using SSL, all remote components connecting to the server need to have SSL enabled as well.

For each of the transport configurations (compiler, agent, rpc client, ...) ``ssl`` has to be
enabled: :inmanta.config:group:`agent_rest_transport`, :inmanta.config:group:`cmdline_rest_transport` and
:inmanta.config:group:`compiler_rest_transport`.

The client needs to trust the SSL certificate of the server. When a self-signed SSL cert is used on the server,
either add the CA cert to the trusted certificates of the system running the agent or configure the ``ssl-ca-cert-file`` option
in the transport configuration.

For example for an agent this is :inmanta.config:option:`agent_rest_transport.ssl` and
:inmanta.config:option:`agent_rest_transport.ssl-ca-cert-file`

Autostarted agents and compiles on the server also use SSL to communicate with the server. This requires either for the server
SSL certificate to be trusted by the OS or by setting :inmanta.config:option:`server.ssl-ca-cert-file`. The server will use
this value to set :inmanta.config:option:`compiler_rest_transport.ssl-ca-cert-file` and
:inmanta.config:option:`server.ssl-ca-cert-file` for the compiler and the agents.

Authentication
--------------
Inmanta authentication uses JSON Web Tokens for authentication (bearer token). Inmanta issues tokens for service to service
interaction (agent to server, compiler to server, cli to server and 3rd party API interactions). For user interaction through
the web-console Inmanta uses 3rd party auth brokers. Currently the web-console only supports redirecting users to keycloak for
authentication.

Inmanta expects a token of which it can validate the signature. Inmanta can verify both symmetric signatures with
HS256 and asymmetric signatures with RSA (RS256). Tokens it signs itself for other processes are always signed using HS256.
There are no key distribution issues because the server is both the signing and the validating party.

The server also provides limited authorization by checking for inmanta specific claims inside the token. All inmanta claims
are prefixed with ``urn:inmanta:``. These claims are:

 * ``urn:inmanta:ct`` A *required* comma delimited list of client types for which this client is authenticated. Each API call
   has a one or more allowed client types. The list of valid client types (ct) are:

    - agent
    - compiler
    - api (cli, web-console, 3rd party service)
 * ``urn:inmanta:env`` An *optional* claim. When this claim is present the token is scoped to this inmanta environment. All
   tokens that the server generates for agents and compilers have this claim present to limit their access to the environment
   they belong to.

Setup server auth
*****************
The server requests authentication for all API calls when :inmanta.config:option:`server.auth` is set to true. When
authentication is enabled all other components require a valid token.

.. warning:: When multiple servers are used in a HA setup, each server requires the same configuration (SSL enabled and
    private keys).

In the server configuration multiple token providers (issuers) can be configured (See :ref:`auth-config`). Inmanta requires at
least one issuer with the HS256 algorithm. The server uses this to sign tokens it issues itself. This provider is indicated with
sign set to true. Inmanta issues tokens for compilers the servers runs itself and for autostarted agents.

Compilers, cli and agents that are not started by the server itself, require a token in their transport configuration. This
token is configured with the ``token`` option in the groups :inmanta.config:group:`agent_rest_transport`,
:inmanta.config:group:`cmdline_rest_transport` and :inmanta.config:group:`compiler_rest_transport`.

A token can be retrieved either with ``inmanta-cli token create`` or via the web-console using the ``tokens`` tab on
the settings page.

.. figure:: /administrators/images/web_console_token.png
   :width: 100%
   :align: center
   :alt: Generating a new token in the web-console.

   Generating a new token in the web-console.


Configure an external issuer (See :ref:`auth-ext`) for web-console access to bootstrap access to the create token api call.
When no external issuer is available and web-console access is not required, the ``inmanta-cli token bootstrap`` command
can be used to create a token that has access to everything. However, it expires after 3600s for security reasons.

For this command to function, it requires the issuers configuration with sign=true to be available for the cli command.

.. _auth-config:

JWT auth configuration
**********************

The server searches for configuration sections that start with ``auth_jwt_``, after the last _ an id has to be present. This
section expects the following keys:

* algorithm: The algorithm used for this key. Only HS256 and RS256 are supported.
* sign: Whether the server can use this key to sign JWT it issues. Only one section may have this set to true.
* client_types: The client types from the ``urn:inmanta:ct`` claim that can be validated and/or signed with this key.
* key: The secret key used by symmetric algorithms such as HS256. Generate the key with a secure prng with minimal length equal
  to the length of the HMAC (For HS256 == 256). The key should be a urlsafe base64 encoded bytestring without padding.
  (see below of a command to generate such a key)
* expire: The default expire for tokens issued with this key (when sign = true). Use 0 for tokens that do not expire.
* issuer: The url of the issuer that should match for tokens to be valid (also used to sign this). The default value is
  https://localhost:8888/ This value is used to match auth_jwt_* sections configuration with JWT tokens. Make sure this is
  unique.
* audience: The audience for tokens, as per RFC this should match or the token is rejected.
* jwks_uri: The uri to the public key information. This is required for algorithm RS256. The keys are loaded the first time
  a token needs to be verified after a server restart. There is not key refresh mechanism.

An example configuration is:

.. code-block:: ini

    [auth_jwt_default]
    algorithm=HS256
    sign=true
    client_types=agent,compiler
    key=rID3kG4OwGpajIsxnGDhat4UFcMkyFZQc1y3oKQTPRs
    expire=0
    issuer=https://localhost:8888/
    audience=https://localhost:8888/

To generate a secure key symmetric key and encode it correctly use the following command:

.. code-block:: sh

    openssl rand 32 | python3 -c "import sys; import base64; print(base64.urlsafe_b64encode(sys.stdin.buffer.read()).decode().rstrip('='));"

.. _auth-ext:

External authentication providers
---------------------------------

Inmanta supports all external authentication providers that support JWT tokens with RS256 or HS256. These providers need to
add a claims that indicate the allowed client type (``urn:inmanta:ct``). Currently, the web-console only has support for keycloak.
However, each provider that can insert custom (private) claims should work. The web-console now relies on the keycloak js library
to implement the OAuth2 implicit flow, required to obtain a JWT.

.. tip:: All patches to support additional providers such as Auth0 are welcome. Alternatively contact Inmanta NV for custom
    integration services.

Keycloak configuration
**********************
The web-console has out of the box support for authentication with `Keycloak <http://www.keycloak.org>`_. Install keycloak and
create an initial login as described in the Keycloak documentation and login with admin credentials.

This guide was made based on Keycloak 3.3

If inmanta is configured to use SSL, the authentication provider should also use SSL. Otherwise, the web-console will not be
able to fetch user information from the authentication provider.


Step 1: Optionally create a new realm
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a new realm if you want to use keycloak for other purposes (it is an SSO solution) than Inmanta authentication. Another
reason to create a new realm (or not) is that the master realm also provides the credentials to configure keycloak itself.

For example call the realm inmanta

.. figure:: /administrators/images/kc_realm.png
   :width: 100%
   :align: center

   Create a new realm


.. figure:: /administrators/images/kc_add_realm.png
   :width: 100%
   :align: center

   Specify a name for the realm


Step 2: Add a new client to keycloak
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure the correct realm is active (the name is shown in the title of the left sidebar) to which you want to add a new client.

.. figure:: /administrators/images/kc_start.png
   :width: 100%
   :align: center

   The start page of a realm. Here you can edit names, policies, ... of the realm. The defaults are sufficient for inmanta
   authentication. This shows the inmanta realm.

Go to client and click create on the right hand side of the screen.

.. figure:: /administrators/images/kc_clients.png
   :width: 100%
   :align: center

   Clients in the master realm. Click the create button to create an inmanta client.

Provide an id for the client and make sure that the client protocol is ``openid-connect`` and click save.

.. figure:: /administrators/images/kc_new_client.png
   :width: 100%
   :align: center

   Create client screen

After clicking save, keycloak opens the configuration of the client. Modify the client to allow implicit flows and add
vallid callback URLs. As a best practice, also add the allowed origins. See the screenshot below as an example.

.. figure:: /administrators/images/kc_client_details.png
   :width: 100%
   :align: center

   Allow implicit flows (others may be disabled) and configure allowed callback urls of the web-console.

Add a mapper to add custom claims to the issued tokens for the API client type. Open de mappers tab of your new client and click
`add`.

.. figure:: /administrators/images/kc_mappers.png
   :width: 100%
   :align: center

   Add a custom mapper to the client to include ``:urn:inmanta:ct``

Select hardcoded claim, enter ``:urn:inmanta:ct`` as claim name and `api` as claim value and string as type. It should only be
added to the access token.

.. figure:: /administrators/images/kc_ct_mapper.png
   :width: 100%
   :align: center

   Add the ct claim to all access tokens for this client.

Add a second mapper to add inmanta to the audience (only required for Keycloak 4.6 and higher). Click `add` again as in the
previous step. Fill in the following values:

* Name: inmanta-audience
* Mapper type: Audience
* Included Client Audience: inmanta
* Add to access token: on

Click save.

Step 3: Configure inmanta server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Go to the installation tab and select JSON format in the select box. This JSON string provides you with the details to
configure the server correctly to redirect web-console users to this keycloak instance and to validate the tokens
issued by keycloak.

.. figure:: /administrators/images/kc_install.png
   :width: 100%
   :align: center

   Show the correct configuration parameters in JSON format.

Add the keycloak configuration parameters to the dashboard section of the server configuration file. Add a configuration
file called `/etc/inmanta/inmanta.d/keycloak.cfg`. Add the realm, auth_url and client_id to the dashboard section. Use
the parameters from the installation json file created by keycloak.

.. code-block:: ini

    [dashboard]
    # keycloak specific configuration
    realm=master
    auth_url=http://localhost:8080/auth
    client_id=inmanta

.. warning:: In a real setup, the url should contain public names instead of localhost, otherwise logins will only work
   on the machine that hosts inmanta server.

Configure a ``auth_jwt_`` block (for example ``auth_jwt_keycloak``) and configure it to validate the tokens keycloak issues.

.. code-block:: ini

    [auth_jwt_keycloak]
    algorithm=RS256
    sign=false
    client_types=api
    issuer=http://localhost:8080/auth/realms/master
    audience=inmanta
    jwks_uri=http://localhost:8080/auth/realms/master/protocol/openid-connect/certs

Set the algorithm to RS256, sign should be false and client_types should be limited to api only. Next set the issuer to the
correct value (watch out for the realm). Set the audience to the value of the resource key in the json file. Finally, set the
jwks_uri so the server knows how to fetch the public keys to verify the signature on the tokens. (inmanta server needs to be
able to access this url).

Both the correct url for the issuer and the jwks_uri is also defined in the openid-configuration endpoint of keycloack. For
the examples above this url is http://localhost:8080/auth/realms/master/.well-known/openid-configuration
(https://www.keycloak.org/docs/latest/securing_apps/index.html#endpoints)

.. warning:: When the certificate of keycloak is not trusted by the system on which inmanta is installed, set ``validate_cert``
    to false in the ``auth_jwt_keycloak`` block for keycloak.
