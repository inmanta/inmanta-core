# Inmanta Web Console

The Inmanta Web Console is a web GUI for the Inmanta Service Orchestrator.

## Browser support

For using the web console, the last 2 versions of the Chrome, Firefox, Edge and Safari browsers are supported. For security reasons it's always recommended to use the latest version of these browsers.

## Proxy

When configuring a proxy for the web-console, the url should always end in `/console`. The web-console uses the `/console` part as an `anchor`. This anchor is something recognizable in the url that is always present. It is also considered to be the root of the app. So a potential proxy would come before the anchor. And the app pages come after the anchor. If no anchor is present in the url, we know the url is faulty. So from an app perspective, the url has the following structure: (`proxy`) + (`anchor`) + (`application defined urls`)

### Examples

Given the input url, the application will use the following `proxy` + `anchor`.

| Scenario              | input url                   | `proxy` + `anchor` |
| --------------------- | --------------------------- | ------------------ |
| Empty proxy respected | /console/resources?env=abcd | /console           |
| Proxy respected       | /someproxy/console          | /someproxy/console |
| Faulty url ignored    | /someproxy                  | /console           |
