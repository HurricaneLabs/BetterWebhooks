.. _alert_action:

Alert Action
=============

The "Better Webhook" alert action has these parameters: the URL that the
webhook will POST to, an optional credential (see :doc:`credentials`), the
POST body format, an optional failure pattern, and up to three headers of its
own.

Body Format
------------

First of all, if you just need your POST body to look identical to Splunk's stock
webhook alert action, just leave this at the default, which should look like this...

.. code-block::  

   {
      "sid": $$sid$$,
      "search_name": $$search_name$$,
      "app": $$app$$,
      "owner": $$owner$$,
      "results_link": $$results_link$$,
      "result": $$full_result$$
   }      

However, you may want or need to change the format here. For example, if your receiver
expected the Splunk results to be the entirety of the POST request, you could do this
instead:

.. code-block:: 


   $$full_result$$


If your webhook receiver expected the Splunk results to be in a property called
"details", with the webhook name in a property called "title", you could do this:

.. code-block:: 

   {
      "title": $$search_name$$,
      "details": $$full_result$$
   }

If you need to send an empty POST body (useful for simple notification webhooks that
don't require data), you can use the special ``$$none$$`` token (this cannot be combined with other tokens):

.. code-block:: 

   $$none$$

Available Tokens
-----------------

The following tokens are available for use in the POST body format:

* ``$$sid$$`` - The search ID
* ``$$search_name$$`` - The name of the search
* ``$$app$$`` - The app name
* ``$$owner$$`` - The owner of the search
* ``$$results_link$$`` - A link to the search results
* ``$$full_result$$`` - The complete search results
* ``$$none$$`` - Special token that sends an empty POST body with no Content-Type header

Failure Pattern
----------------

Some receivers answer with HTTP 200 even when they rejected the message, and put
the error in the response body instead, like the Slack Web API's ``"ok": false``.
Set **Failure Pattern** to a regular expression, and a 2xx response whose body
matches it is logged as a failed delivery. For example:

* ``"ok":\s*false`` for the Slack Web API
* ``"status":\s*"error"`` for receivers that report a status field

The pattern is checked only on 2xx responses; any other status already fails the
delivery. Leave it empty to turn the check off. An invalid pattern is logged and
ignored, so it never fails a delivery on its own. In SPL, the parameter is
``param.body_failure_regex``.

Headers
--------

An alert can send up to three headers of its own, in the **Header 1** to
**Header 3** rows: a name and a value each. For example, to tell the receiver
which host raised the alert, set a row's name to ``X-Alert-Host`` and its
value to ``$result.host$``.

Values can use Splunk tokens. Splunk fills them in before the alert action
runs, so a value can hold anything a search result holds. If a value ends up
holding a line break, the alert fails without sending anything, since a line
break would let the search result add a header of its own.

A row may replace the two headers the alert action sets itself:
``Content-Type`` (``application/json`` whenever there's a body) and
``User-Agent``. It may also replace the ``Accept`` and ``Content-Type`` an
OAuth credential sends, both ``application/json``. It may not set a header a credential sets, such as
``Authorization`` with an OAuth credential, or ``Authorization`` when the URL
holds a user name and password. Such an alert fails without sending anything,
and the log names the header and both sources. Nor can a row set
``Content-Length``, ``Transfer-Encoding`` or ``Connection``: requests sets
those itself.

Header values are saved with the alert in plain text, like the URL. Put a
secret, such as an API key, in a credential instead.

In SPL, the parameters are ``param.header_1_name`` and
``param.header_1_value``, through ``param.header_3_name`` and
``param.header_3_value``.

Using sendalert in SPL
-----------------------

The alert action can be triggered directly from SPL using the ``| sendalert`` command:

.. code-block::

   index=my_index
   | sendalert better_webhook
       param.url="https://hooks.example.com/webhook"
       param.credential="my_credential_name"
       param.header_1_name="X-Source"
       param.header_1_value="splunk"
       param.body_format="$$none$$"

Pass ``param.credential`` as the credential **name** as it appears on the credentials page —
not the full internal storage key. ``param.body_format`` accepts the same tokens listed above
and behaves identically to the GUI field.

Adaptive response (Enterprise Security)
----------------------------------------
At the time of writing, this app doesn't completely work with Enterprise Security
"adaptive response" actions. You will be able to add the Better Webhook action and set
a URL as well as a format template, but auth will not save. A workaround for this is to,
after adding the adaptive response action, navigate to the search in the 
"Searches, Reports, and Alerts", click "Edit Alert", and add the authentication there.

A warning about tokens
-----------------------
You may notice the odd double-dollar-sign tokens in these POST bodies. These are *not*
built-in Splunk tokens and are instead implemented by the alert action themself. This
is because the default alert action tokens can potentially be non-JSON and thus 
inadvertently make the entire payload invalid JSON. For example, if you tried to use
:code:`$name$` to send the search name in your webhook, a search with a :code:`"` in its name
would result in invalid JSON. These "custom" tokens do not have this issue, but if you
are confident the tokens you are using will result in valid JSON, feel free to use any
alert action tokens.


.. autosummary::
   :toctree: generated

