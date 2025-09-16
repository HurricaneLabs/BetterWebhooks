Better Webhooks
===================================

**Better Webhooks** is a Splunk app that implements a more-fully-featured alert action
for sending Webhooks. With it, you can authenticate your Webhooks (with either HTTP
basic auth, a custom HTTP header, or HMAC). Additionally, you can customize the HTTP
POST body. 

Release History
----------------

1.1.8
-----
* Add support for sending empty POST bodies by using the ``$none$`` token in the body format field. When this token is used, no Content-Type header is sent with the request.
* Refactor HTTP code in the webhook credentials management interface for better error handling and maintainability.
* Fix bug where ampersands (&) in passwords would break HTTP calls due to improper URL encoding.

1.1.7
-----
* Fix bug where HMAC timestamp header being unset in a credential would cause the alert action to fail.

1.1.6
-----
* Adds a proxy setting which can be set in ``better_webhooks.conf`` to apply to all requests made by the alert action.
* Fixes a bug where the credential dropdown was not populated when used as an ES adaptive response action.
* Adds default alert action settings to alert_actions.conf (Thanks Matt Anderson!)

1.1.5
-----
Remove some (accidental) whitespace in the default POST body which can break some JSON
parsers (thanks to Matt Anderson!)

1.1.3/1.1.4
-----
Changes requested by Splunk Cloud vetting.

1.1.2
-----
Restrict write access in metadata in order to comply with new app vetting requirement.
Add error messages when user is lacking permissions to list/edit credentials.

1.1.1
_____
Add back an apparently-important item to default.meta that was removed in 1.1.0.

1.1.0
_____
Adds the ability to store credentials in different apps, as well as the ability to
set sharing/permissions.

1.0.1
_____
Minor bugfix involving is_configured in app.conf.

1.0.0
_____
Initial release.

Documentation
--------------

.. toctree::

   installation
   credentials
   alert_action
   troubleshooting
   proxy

