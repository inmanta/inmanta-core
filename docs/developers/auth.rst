Authentication
==============

Inmanta authentication uses JSON Web Tokens for authentication.


The server issues JWT tokens for the agent and compilers it invokes. These tokens only authorize agent and compiler access. The
server signs these tokens with the server>jwt_secret secret. This secret needs to be shared with all other server instances. 
The tokens issued for standalone agents processes do not expire.

Inmanta uses inmanta specific claims:

prefix: urn:inmanta:

claims:
    - ct: A comma delimited list of client types for which this client is authenticated. Each API call has a role associated 
          with it. The list of valid client types (ct) are:
                - agent
                - compiler
                - api (cli, dashboard, 3rd party service)
                - public (the default role when no valid token is present
         
    - env: When this claim is present the token is scoped to this inmanta environment. Compiler and agent tokens have this
           to limit their access to the environment they belong to.
                
                
In the config file a list of valid token providers can be configured. Each token provider requires the algorithm used and the
secret or JKS url. Each token provider can also include a list of roles it is allowed to authenticate. This allows to seperate
the authentication of agents/compiler/... (m2m) and client (cli/dashboard/client).


JWT auth configuration
----------------------

The server searches for configuration sections that start with ``auth_jwt_``, after the last _ an id has to be present. This
section expects the following keys:

- algorithm: The algorithm used for this key. Currently only HS256 and RS256 is supported.
- sign: Whether the server can use this key to sign JWT it issues. Only one section may have this set to true.
- client_types: The client types from the urn:inmanta:ct claim that can be valided and/or signed with this key
- key: The secret key used by symmetric algorithms such as HS256. Generate the key with a secure prng with minimal length equal
       to the length of the HMAC (For HS256 == 256). The key should be a urlsafe base64 encoded bytestring without padding. 
- expire: The default expire for tokens issued with this key (when sign = true). Use 0 for tokens that do not expire.
- issuer: The url of the issuer that should match for tokens to be valid (also used to sign this). The default value is
          https://localhost:8888/
          This value is used to match auth_jwt_* sections configuration with JWT tokens. Make sure this is unique.
- audience: The audience for tokens, as per RFC this should match or the token is rejected.
- jwks_uri: The uri to the public key information. This is required for algorithm RS256. The keys are loaded the first time
            a token needs to be verified after a server restart. There is not key refresh mechanism.

An example configuration is:

```
[auth_jwt_default]
algorithm=HS256
sign=true
client_types=agent,compiler
key=rID3kG4OwGpajIsxnGDhat4UFcMkyFZQc1y3oKQTPRs
expire=0
issuer=https://localhost:8888/
audience=https://localhost:8888/
```

To generate a secure key symmetric key and encode it correctly use the following command:
```
openssl rand 32 | python3 -c "import sys; import base64; print(base64.urlsafe_b64encode(sys.stdin.buffer.read()).decode().rstrip('='));"
```

Authorization
-------------

Current implementation offers limited authorization. It enforce the client_type and environment claims in the token. So by 
providing a token with these claims set, the scope of that token can be limited.