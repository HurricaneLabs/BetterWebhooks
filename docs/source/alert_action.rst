.. _alert_action:

Alert Action
=============

The "Better Webhook" alert action has only 3 parameters: The URL that the webhook
will POST to, an optional credential (see :doc:`credentials`), and the POST body
format. 

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
      "title": $$search_name,
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

