.. _credentials:

Credentials
============


Overview
------------

If you want to pass credentials with your webhooks, you'll need to store them first
by navigating to the app's "Credentials" page. Click "New credential" to add one.
All credentials are encrypted at rest by utilizing Splunk's credential store. 

Once a credential is added, it will be available as an option when you add the 
"Better Webhook" alert action to an alert. 


To use Lumache, first install it using pip:

Types of credentials
---------------------

HTTP Basic Auth
________________

Enter a username and password, and it will be properly sent with your webhooks. Simple as
that.

* **Name**: The name of the credential.
* **Username**: A username.
* **Password**: A password.

Custom HTTP Header
___________________

This allows you to set a specific HTTP header. This is useful for API key
authentication, for instance with an AWS API gateway.

* **Name**: The name of the credential.
* **Header name**: The name of the HTTP header which will be sent with each webhook.
* **Header value**: The content of the HTTP header.

HMAC Secret
_____________

This is the most secure of the three options as it allows you to authenticate the
request *and* prevent the message from being tampered in transit. However there is in
my experience a lack of consistency in how various services implement HMAC. I've tried
to handle the vast majority of use cases. If you need something different, please reach
out.

* **Name**: The name of the credential.
* **HMAC Secret**: The shared secret that the receiver also has. 
* **Hash Function**: The hash function used to calculate the HMAC signature.
* | **Digest type**: This is how the HMAC signature is encoded in the HTTP header. I usually
  | see base64 here but have seen a hex digest once. A sample base64 header would look
  | like
  | :code:`X-HMAC: KEV3NsvZzZjsJV0zNsQ97HVJbPtF6zYceUp1ZTXHPso=`
  | whereas the same signature as a hex digest would look like 
  | :code:`X-HMAC: 28457736cbd9cd98ec255d3336c43dec75496cfb45eb361c794a756535c73eca`
* **HMAC Signature Header**: The header where the HMAC signature will be sent in.
* | **HMAC Timestamp Header**: For added security, some implementations expect the
  | sender to include a second header with the current timestamp. The timestamp is
  | then appended to the body before the signature is calculate. This prevents
  | against replay attacks.
  |
  | If you don't need this functionality, leave this field blank. Otherwise, set it
  | to the name of the header the webhook receiver expects to find the timestamp.
  | If this field is blank, the timestamp won't be sent and won't be added to the
  | body as part of the signature calculation.

.. autosummary::
   :toctree: generated

