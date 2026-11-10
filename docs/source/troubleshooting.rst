.. _troubleshooting:

Troubleshooting
===============

Output from the alert action can be found with the following Splunk search:

.. code-block::  

    index=_internal sourcetype=splunkd sendmodalert better_webhook

If you only want to see errors...

.. code-block::  

    index=_internal sourcetype=splunkd sendmodalert better_webhook ERROR

NOTE: The above should work fine for find whether or not an error occurred, but
tracebacks are multiline and will be excluded. If you're investigating a specific
error I would use the first search so that no log events are missed.

The alert action logs the webhook receiver's HTTP status and the size of its
response at INFO level, so they appear in the standard search above without any
log level changes. It never logs the request or response body, which can carry
search results, tokens or ticket data, and it replaces any credential secret that
turns up in an error message with ``[REDACTED]``.

It names the webhook receiver and an OAuth credential's token endpoint by host
alone, for example ``host=hooks.slack.com``, because for some receivers (Slack's
incoming webhooks, for one) the URL's path is the secret. The path, the query
string and any ``user:password@`` are replaced with ``[REDACTED]`` when an error
message quotes them.

Timeouts
--------

The alert action waits up to 10 seconds to connect to the webhook receiver, and
then up to 60 seconds for each part of its reply. A receiver that doesn't answer
in time fails the alert with an error like::

    Webhook request to host=hooks.example.com timed out, giving up: ...

An OAuth credential's token request gets the same limits. Together they stay
under Splunk's 5-minute limit for an alert action (``maxtime``), so a receiver
that stops answering fails with a logged reason before Splunk stops the action.
A receiver that keeps sending its reply slowly can still run into ``maxtime``.

Redirects
---------

The alert action doesn't follow redirects. A receiver that answers with one
(HTTP 301, 302, 303, 307 or 308) fails the alert with an error like::

    Webhook receiver answered with a redirect (HTTP status=301), which is not followed: set the alert's URL to the address it redirects to

Following it would send a Custom HTTP Header credential, and for a 307 or 308 the
search results too, to wherever the receiver points, including a plain ``http://``
address. To find the new address, request the URL yourself, for example with
``curl -si -X POST <url>``, and read the ``Location`` header.

Headers that stop an alert
---------------------------

These errors stop the alert before anything is sent. None of them quotes a
header's value.

``Header 2 has a value but no name, so the webhook isn't sent``
   Fill in the row's name, or clear its value.

``Header 2's name isn't a valid header name, so the webhook isn't sent``
   A header name holds only letters, digits and the symbols
   ``! # $ % & ' * + - . ^ _ | ~`` and the backquote: no spaces or colons.

``Header 2 (X-Alert-Host) has a line break or another character a header can't carry in its value, so the webhook isn't sent: check the token it uses``
   A token in the value filled in text from the search result holding a line
   break, a control character or a character outside Latin-1, such as ``→``
   or an emoji. Change the search so the field holds one line of plain text,
   for example ``| eval host=replace(host, "[\r\n]", " ")``.

``Header 2 (Content-Length) is managed by the HTTP client, so the webhook isn't sent: remove the row``
   requests sets this header itself; remove the row. The same goes for
   ``Transfer-Encoding`` and ``Connection``.

``Header Authorization is set by both credential my_oauth and the alert's header 1, so the webhook isn't sent``
   Two sources set the same header. Remove one of the two: clear or rename a
   row, or pick a credential that doesn't set that header; the URL's user info
   sets ``Authorization`` too.

.. _url_wont_parse:

URLs that won't parse
---------------------

A webhook, proxy or token URL that can't be parsed fails the alert before any
request uses it, with an error like::

    The proxy URL won't parse, so it isn't used: check its host and port, and percent-encode any #, /, ?, \, @, [ or ] in its user name or password, and any @ after its host

A ``#``, ``/``, ``?`` or ``\`` in a user name or password ends the URL's host
part early, so write it percent-encoded: ``%23``, ``%2F``, ``%3F`` and ``%5C``.
Write an ``@`` in a user name or password as ``%40``, and a ``[`` or ``]`` as
``%5B`` or ``%5D`` (brackets belong only around an IPv6 host). For example, the
password ``P@ss#2026`` goes in the URL as ``P%40ss%232026``. The error doesn't
quote the URL, because the part it would quote is the start of the password.

A URL with a user name or password also can't have a raw ``@`` anywhere after
its host, and no URL can have one after a ``#``: write those as ``%40`` too.
That URL would read the same as a password cut short, so it's refused even when
the ``@`` is meant. Most receivers read ``%40`` the same as ``@``. A URL with no
user name or password, such as a Microsoft Teams webhook, can keep the ``@`` in
its path.

Encode them even when the URL seems to work: in ``https://svc:1234/Q4@host/x``,
``svc`` reads as the host and ``1234`` as its port, so the alert goes to the
wrong place and the log names ``host=svc:1234``.

SSL Certificate Errors (Internal / Private CA)
-----------------------------------------------

If you see an error like::

    requests.exceptions.SSLError: HTTPSConnectionPool(...): Max retries exceeded
    (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
    certificate verify failed: self signed certificate in certificate chain')))

the cause is that Python's ``requests`` library uses its own bundled CA certificate
store (from the ``certifi`` package) rather than the operating system's certificate
store. This applies to all platforms. On Windows, adding your internal CA to the
Windows certificate store or setting ``caTrustStore = splunk,OS`` in ``server.conf``
has no effect on this.

**Workaround:**

.. warning::
   Setting ``REQUESTS_CA_BUNDLE`` replaces certifi's CA bundle entirely. If you
   point it to only your internal CA certificate, webhooks to public HTTPS endpoints
   will fail. You must create a **combined bundle** that includes both the standard
   public CAs and your internal CA.

1. Find the path to certifi's CA bundle. On Linux/macOS::

       $SPLUNK_HOME/bin/python3 -c "import certifi; print(certifi.where())"

   On Windows::

       & "$env:SPLUNK_HOME\bin\python3.exe" -c "import certifi; print(certifi.where())"

2. Copy that file to a writable location (e.g. ``/etc/ssl/splunk-ca-bundle.pem`` on
   Linux, or ``C:\certs\ca-bundle.pem`` on Windows).

3. Append your internal CA certificate (PEM format) to the end of the copied file.
   If your CA chain has multiple certificates, append each one.

4. Add the following line to ``$SPLUNK_HOME/etc/splunk-launch.conf``
   (use the path from step 2)::

       REQUESTS_CA_BUNDLE=/etc/ssl/splunk-ca-bundle.pem

5. Restart Splunk.

When ``REQUESTS_CA_BUNDLE`` is set, ``requests`` will use that file instead of
certifi's default bundle. Because it contains both the standard public CAs and your
internal CA, all webhook destinations (public or internal) will continue to work.

.. note::
   After upgrading Splunk, certifi's bundle may be updated. If you see certificate
   errors reappear after an upgrade, repeat steps 1–3 to refresh your combined bundle.
