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

Timeouts
--------

The alert action waits up to 10 seconds to connect to the webhook receiver, and
then up to 60 seconds for each part of its reply. A receiver that doesn't answer
in time fails the alert with an error like::

    Webhook request to url=https://hooks.example.com/webhook timed out, giving up: ...

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
