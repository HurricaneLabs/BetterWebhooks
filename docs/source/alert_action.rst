.. _alert_action:

Alert Action
=============

The "Better Webhook" alert action has only 3 parameters: The URL that the webhook
will POST to, an optional credential (see :doc:`credentials`), and the POST body
format. 

Body Format
------------

First of all, if you just need your POST body to look identical to Splunk's stock
webhook alert action, just leave this at the default, which should like this...

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

