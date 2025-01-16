******************************************
Reverse proxy and Web Application Firewall
******************************************

Communication between inmanta components and to the northbound API uses REST over HTTP(S). This section describes how to move the API behind a reverse proxy and optionally enable a web Application firewall. This is meant for all external traffic towards the orchestrator. It is not supported to proxy traffic from the compiler and agents to the server.

This guide focuses on access to the web-console, and to the northbound API. This guide works for both the OSS and the full version of the product.

Setup a reverse proxy
#####################

A reverse proxy receives the calls and proxies them to the inmanta service orchestrator API. This guide gives examples
to set this up with Apache HTTPD, but similar rules could also be applied to NGINX or other reverse proxies. This guide assumes that the reverse proxy is installed on the same machine as the orchestrator.

    1. Make sure you do not bind the orchestrator to the IP used by the proxy server so it cannot be bypassed. If only auto started agents are used, it is recommended to set the bind-address to localhost. See :inmanta.config:option:`server.bind-address` and :inmanta.config:option:`server.bind-port`. If you have remote agents, make sure that either by having multiple IPs or using firewall rules that the agents can connect directly to the orchestrator.

    2. Install Apache HTTPD and make sure it is configured correctly (listen to the correct interfaces, ports, SSL, access control, ...)

    3a. The easiest setup is to proxy all traffic directly to the orchestrator:

    .. code-block:: apacheconf

        # Proxy all requests to the orchestrator
        <Location /console>
            ProxyPass http://localhost:8888/

            Allow from all
            # Or limit access to certain users or prefixes
            # Allow from 10.x.x.x/24
        </Location>

    3b. Only proxy the calls that the orchestrator has endpoints for. Everything else will be handled by the reverse proxy:

    .. code-block:: apacheconf

        # Web Console is a static single page application (SPA)
        <Location /console>
            ProxyPass http://localhost:8888/console

            # Limit the possible methods to only get the content
            AllowMethods GET HEAD OPTIONS

            Allow from all
            # Or limit access
            # Allow from 10.x.x.x/24
        </Location>

        # Generic API: used by agents, web-console, integrations, ...
        # Unless detailed error reports are requested, this API should not be made available to
        # any portals or tools
        <Location /api>
            ProxyPass http://localhost:8888/api

            Allow from all
            # Or limit access
            # Allow from 10.x.x.x/24
        </Location>

        # LSM API: the northbound API called by tools such as customer portals
        <Location /lsm>
            ProxyPass http://localhost:8888/lsm

            Allow from all
            # Or limit access
            # Allow from 10.x.x.x/24
        </Location>


When only exposing the LSM API even more specific proxy rules can be used. In the next section we provide example rules to restrict this with mod_security.

Web Application Firewall
########################

This section provides configuration guidelines to enable additional filtering using mod security. These rules can of course be ported to other types of web application firewalls.

    1. Install mod_security and enable it in Apache HTTPD according to their setup instructions.
    2. Optional: Enable JSON body decoding to make sure only valid JSON reaches the orchestrator. This is available since version 2.8, however it is not enabled in the RPMS included with RHEL and Centos. Third party repos provide versions with JSON decoding enabled or distribution such as NGINX WAF.

    JSON decoding is enabled when a similar config stanza is in the configuration:

    .. code-block:: apacheconf

        # Make sure mod security is on and it inspects the body
        SecRuleEngine On
        SecRequestBodyAccess On

        # Enable json body decoding when the content type is set to `application/json`
        SecRule REQUEST_HEADERS:Content-Type "application/json" \
            "id:'200001',phase:1,t:none,t:lowercase,pass,nolog,ctl:requestBodyProcessor=JSON"

    3. Add the generic inmanta rules. These will make sure that if the requests goes to an API it will only accept valid JSON. If the JSON processor is not enabled, these rules will still work, but the protection is reduced because invalid JSON can still reach the inmanta service orchestrator API. The rules are defined so that they will only trigger on calls to inmanta service orchestrator endpoints.

    .. code-block:: apacheconf

        # Classify the call based on the request uri.
        SecRule REQUEST_URI "@beginsWith /api/" \
            "id:'200501',phase:1,setvar:'tx.inmanta_context=api'"
        SecRule REQUEST_URI "@beginsWith /api/v2/docs" \
            "id:'200502',phase:1,setvar:'tx.inmanta_context=docs'"
        SecRule REQUEST_URI "@beginsWith /console" \
            "id:'200504',phase:1,setvar:'tx.inmanta_context=static'"
        SecRule REQUEST_URI "@beginsWith /lsm/" \
            "id:'200510',phase:1,setvar:'tx.inmanta_context=lsm'"
        SecRule REQUEST_URI "@beginsWith /lsm/v1/service_catalog_docs" \
            "id:'200511',phase:1,setvar:'tx.inmanta_context=docs'"

        # All api and lsm calls should be json content so that the body will be parsed by modsec
        # If JSON decoding is not enabled, it will force the content type however mod_security does not validate
        # if the body is JSON
        SecRule TX:INMANTA_CONTEXT "@rx api|lsm" \
            "id:'200600',phase:1,deny,status:400,msg:'API and LSM only accept json content',chain"
            SecRule REQUEST_HEADERS:Content-Type "!@rx application/json" \
                "t:lowercase"

        # Inmanta supports unicode, however this is often used in templates that generate
        # input for other systems. This rule will validate all utf8 encodings. It is only enabled
        # when sending data to inmanta backends
        SecRule TX:INMANTA_CONTEXT "!@streq ''" \
            "id:'200601',phase:1,deny,status:400,msg:'Invalid UTF provided',chain"
            SecRule ARGS "@validateUtf8Encoding" \
                "t:none"


This ruleset has been tested to be compatible with the OWASP core rule set. However, it does not do scoring. If an anomaly is detected a 400 request is returned. It does not return the default 403 because this tricks our web-console into warning the user to authenticate.

When the northbound API is only used for calls to LSM to manage service instances, mod_security can be used to restrict access even more. The following rules ensure that only calls for service "network" are allowed and callback management. The rules are set up in such a way that additional urls can be easily added to the ruleset:


.. code-block:: apacheconf

    # Only allow certain paths required for the "customer portal" to function:
    SecAction \
    "id:300001,\
        phase:1,\
        nolog,\
        pass,\
        t:none,\
        setvar:'tx.allowed_urls=|/lsm/v1/service_inventory/network| |/lsm/v1/callbacks'"

    SecRule REQUEST_URI "!@withIN %{tx.allowed_urls}" \
        "id:300002,phase:1,t:lowercase,deny,status:404"


When the OWASP core ruleset is enabled and particularly when JSON decoding is enabled, mod_security will also scan for SQL and XSS attacks. Especially the latter can be useful if a customer portal uses the API directly and the service model has free form attributes that can hold any content. In that case it may be useful to also use mod_security to protect against for example stored XSS attacks.
