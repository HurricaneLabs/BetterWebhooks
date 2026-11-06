.. _installation:

Installation
=============

Better Webhooks requires Splunk 10.4 or later, because the credentials page uses a page
template that Splunk ships from 10.4 on. Splunk Web refuses the install on older versions.
On Splunk 9.x through 10.3, stay on Better Webhooks 1.3.0.

Install this app on your search head by either extracting the app tarball into 
$SPLUNK_HOME/etc/apps or by installing through Splunkweb. There are no additional
required setup steps, though you may want to add a credential (see :doc:`credentials`).

.. autosummary::
   :toctree: generated
