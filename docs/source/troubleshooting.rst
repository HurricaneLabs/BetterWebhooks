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
