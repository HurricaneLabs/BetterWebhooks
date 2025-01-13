Better Webhooks
===================================

**Better Webhooks** is a Splunk app that implements a more-fully-featured alert action
for sending Webhooks. With it, you can authenticate your Webhooks (with either HTTP
basic auth, a custom HTTP header, or HMAC). Additionally, you can customize the HTTP
POST body. 

Release History
----------------
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


