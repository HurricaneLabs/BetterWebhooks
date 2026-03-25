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

The alert action logs the response body from the webhook receiver at INFO level,
so it will appear in the standard search above without requiring any log level changes.
This is useful for capturing response data such as ticket numbers from systems like Jira.

If the log level for the "sendmodalert" alert channel is DEBUG, the alert action
will additionally log the full POST body sent with the request.

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
