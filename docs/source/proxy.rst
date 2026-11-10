.. _proxy:

Proxy Support
=============

Since version 1.1.6, Better Webhooks supports sending all outgoing webhook requests through an HTTP or HTTPS proxy. Since version 2.0.0, an OAuth credential's token request goes through it too.

How to Configure
----------------

1. Copy the ``$SPLUNK_HOME/etc/apps/BetterWebhooks/default/better_webhooks.conf`` to the ``local`` directory.
2. Add or update the ``proxy`` setting under the ``[settings]`` stanza. For example:

   ::

       [settings]
       proxy = http://proxy-server-ip:port

   Replace ``http://proxy-server-ip:port`` with the address and port of your proxy server.
3. Save the file and restart Splunk.

Notes
-----
- If the ``proxy`` setting is left blank or omitted, requests will be sent directly, without using a proxy.
- The proxy setting applies globally to all requests made by the app: every webhook, and the token request of an OAuth credential.
- No address can be excluded from the proxy. If the proxy can't reach your OAuth token endpoint (an internal identity provider, say), OAuth credentials fail with "Failed to obtain OAuth token".
- Authentication for the proxy (if required) can be included in the URL, e.g. ``http://user:password@proxy-server:port``. Percent-encode any ``#``, ``/``, ``?`` or ``\`` in the user name or password, or the URL won't parse (see :ref:`url_wont_parse`).
