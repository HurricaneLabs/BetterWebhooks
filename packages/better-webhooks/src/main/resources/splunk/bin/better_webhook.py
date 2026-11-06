"""
Lovingly adapted from the original "alert_webhook" app which ships with Splunk.
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from urllib.parse import quote, urlparse

import requests
import splunk.rest  # type: ignore
from hmac_helper import get_hmac_headers
from log_redaction import register_secret
from oauth_helper import OAuthTokenError, get_oauth_headers
from splunk.clilib import cli_common as cli  # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from loguru import logger

logger.remove()  # Remove default formatter
logger.add(sys.stderr, format="{level} {message}", level="DEBUG")

# Credential fields that hold a secret, across every credential type. A new
# secret field must be added here, or it can reach the log in an exception.
SECRET_FIELDS = ("password", "header_value", "hmac_secret", "oauth_client_secret")


class CredentialError(Exception):
    """splunkd wouldn't hand back the stored credential."""


def get_credential(name: str, session_key: str):
    """
    Grab a specific credential from Splunk's credential store and JSON-decode it
    """
    # When invoked via | sendalert, users pass just the credential name (e.g. "my_cred").
    # When invoked via a saved alert, Splunk passes the full storage/passwords key
    # (e.g. "better_webhooks:my_cred:"). Normalize to the full key format either way.
    if not name.startswith("better_webhooks:"):
        name = f"better_webhooks:{name}:"
    url = f"/servicesNS/nobody/BetterWebhooks/storage/passwords/{quote(name, safe=':')}"

    server_response, server_content = splunk.rest.simpleRequest(
        url, getargs={"output_mode": "json"}, sessionKey=session_key
    )

    if server_response["status"] != "200":
        logger.error(
            "Error grabbing credential {}. Response from splunkd was {}",
            name,
            str(server_response),
        )
        raise CredentialError("Error grabbing credential from splunkd")

    # The server response is JSON-encoded
    credential = json.loads(server_content)["entry"][0]["content"]["clear_password"]

    # And so is the credential itself
    return json.loads(credential)


def send_webhook_request(
    url: str,
    body: bytes,
    headers: dict,
    auth: tuple | None,
    user_agent: str,
    proxy: str,
    body_failure_regex: str = "",
):
    """
    Send the webhook and log why it failed, if it does. Never logs the request or
    response body: they can carry search results, tokens or ticket data.
    """
    if url is None:
        logger.error("No URL provided")
        return False

    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy,
        }
    else:
        proxies = None

    if len(body) > 0:
        headers["Content-Type"] = "application/json"

    headers["User-Agent"] = user_agent
    logger.info(
        "Sending POST request to url={} with size={} bytes payload",
        url,
        len(body),
    )

    try:
        r = requests.post(url, data=body, headers=headers, auth=auth, proxies=proxies)

        if 200 <= r.status_code < 300:
            logger.info(
                "Webhook receiver responded with HTTP status={}, response size={} bytes",
                r.status_code,
                len(r.content),
            )

            # Some receivers report failures in the body of an otherwise
            # successful HTTP response (e.g. the Slack Web API answers HTTP 200
            # with {"ok": false, "error": "..."}). An optional user-supplied
            # pattern matched against the body of a 2xx response covers any such
            # convention, JSON or not. A match fails the delivery; an invalid
            # pattern is logged but never fails an otherwise good one.
            if body_failure_regex:
                try:
                    if re.search(body_failure_regex, r.text):
                        logger.error(
                            "Webhook receiver responded with HTTP status={} but the response body matched the failure pattern {}",
                            r.status_code,
                            body_failure_regex,
                        )
                        return False
                except re.error as exc:
                    logger.error(
                        "Invalid failure pattern {} configured on the alert action, ignoring it: {}",
                        body_failure_regex,
                        exc,
                    )

            return True
        else:
            logger.error(
                "Webhook receiver responded with HTTP status={}, response size={} bytes",
                r.status_code,
                len(r.content),
            )
            return False

    # A failed delivery: network, TLS, proxy and HTTP errors, plus a header value
    # http.client can't encode (not latin-1), which isn't a RequestException.
    # Anything else is a bug and goes to the top-level handler.
    except (requests.RequestException, UnicodeEncodeError):
        logger.error(
            "Unhandled exception when attempting to execute alert action. {}",
            traceback.format_exc(),
        )
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.error("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    try:
        settings = json.loads(sys.stdin.read())
        global_settings = cli.getConfStanza("better_webhooks", "settings")
        proxy = global_settings.get("proxy").strip()

        session_key = settings["session_key"]

        url = settings["configuration"].get("url")
        if url:
            parsed_url = urlparse(url)
            if parsed_url.scheme != "https":
                logger.error("URL scheme must be HTTPS")
                sys.exit(1)
        body_format = settings["configuration"].get("body_format")
        credential_name = settings["configuration"].get("credential")
        if credential_name == "None":
            credential_name = None

        if credential_name:
            credential = get_credential(credential_name, session_key=session_key)
            for field in SECRET_FIELDS:
                register_secret(credential.get(field))
        else:
            credential = None

        sid = settings.get("sid")
        search_name = settings.get("search_name")
        app = settings.get("app")
        owner = settings.get("owner")
        results_link = settings.get("results_link")
        result = settings.get("result")

        if body_format.strip() == "$none$":
            body = ""
        else:
            body = (
                body_format.replace("$sid$", json.dumps(sid))
                .replace("$search_name$", json.dumps(search_name))
                .replace("$app$", json.dumps(app))
                .replace("$owner$", json.dumps(owner))
                .replace("$results_link$", json.dumps(results_link))
                .replace("$full_result$", json.dumps(result))
            )

        body = body.encode()

        if not credential:
            auth = None
            headers = {}
        elif credential["type"] == "basic":
            auth = (credential.get("username"), credential.get("password"))
            headers = {}
        elif credential["type"] == "header":
            auth = None
            headers = {
                credential.get("header_name").strip(): credential.get(
                    "header_value"
                ).strip()
            }
        elif credential["type"] == "hmac":
            auth = None
            hmac_secret = credential.get("hmac_secret")
            hmac_hash_function = credential.get("hmac_hash_function")
            hmac_digest_type = credential.get("hmac_digest_type")
            hmac_sig_header = credential.get("hmac_sig_header", "").strip()
            hmac_time_header = credential.get("hmac_time_header", "").strip()

            try:
                headers = get_hmac_headers(
                    body=body,
                    hmac_secret=hmac_secret,
                    hmac_hash_function=hmac_hash_function,
                    hmac_digest_type=hmac_digest_type,
                    hmac_sig_header=hmac_sig_header,
                    hmac_time_header=hmac_time_header,
                )
            # An unknown hash function or digest type
            except ValueError:
                logger.error(
                    "Failed to compute HMAC signature, cannot send webhook. {}",
                    traceback.format_exc(),
                )
                sys.exit(2)
        elif credential["type"] == "oauth":
            auth = None
            oauth_client_id = credential.get("oauth_client_id")
            oauth_client_secret = credential.get("oauth_client_secret")
            oauth_token_url = credential.get("oauth_token_url", "").strip()
            oauth_scope = credential.get("oauth_scope", "").strip()

            try:
                headers = get_oauth_headers(
                    client_id=oauth_client_id,
                    client_secret=oauth_client_secret,
                    token_url=oauth_token_url,
                    scope=oauth_scope,
                )
            # ValueError: the token URL isn't HTTPS
            except (OAuthTokenError, ValueError):
                logger.error(
                    "Failed to obtain OAuth token for credential {}, cannot send webhook. {}",
                    credential_name,
                    traceback.format_exc(),
                )
                sys.exit(2)
        else:
            logger.error("Unknown credential type: {}", credential["type"])
            sys.exit(2)

        user_agent = settings["configuration"].get("user_agent", "Splunk")
        # Keep the pattern verbatim — stripping would break regexes with
        # significant leading/trailing whitespace. Only whitespace-only
        # input is treated as unset.
        body_failure_regex = settings["configuration"].get("body_failure_regex") or ""
        if not body_failure_regex.strip():
            body_failure_regex = ""
        if not send_webhook_request(
            url,
            body,
            headers,
            auth,
            user_agent=user_agent,
            proxy=proxy,
            body_failure_regex=body_failure_regex,
        ):
            sys.exit(2)
    # Blind on purpose: past this point Python's own handler prints the traceback,
    # unredacted. Keep format_exc() in the message, too: logger.exception() puts
    # the traceback outside the message, where log_redaction can't scrub it.
    except Exception:  # noqa: BLE001
        logger.error(
            "Unhandled exception when attempting to execute alert action. {}",
            traceback.format_exc(),
        )
        sys.exit(3)
