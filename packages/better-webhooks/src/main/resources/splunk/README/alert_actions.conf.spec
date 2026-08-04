[better_webhook]

param.user_agent = <string>
* Configure value of the User-Agent header sent to the webhook receiver.

param.url = <string>
* Specified URL to send JSON payload via HTTP POST (ex., https://your.server.com/api/v1/webhook).

param.body_format = <string>
* Format of JSON POST body. For a POST body identical to the stock Splunk Webhook action, leave this at the default value.

param.credential = <string>
* The saved credential to use.

param.body_failure_regex = <string>
* Optional regular expression matched against the response body of a 2xx
  response. A match is treated as a failed delivery.
* Use this for receivers that report errors in the response body of an
  otherwise successful HTTP response, e.g. "ok":\s*false for the Slack Web
  API or "status":\s*"error".
* An invalid pattern is logged and ignored; it never fails a delivery.
* Defaults to empty (disabled).
