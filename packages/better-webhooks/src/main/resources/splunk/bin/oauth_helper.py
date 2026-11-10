import os
import sys
import traceback
from urllib.parse import urlparse

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from log_redaction import register_secret, register_url, url_host, url_parses
from loguru import logger

# Seconds to wait for a connection, then for each read of the reply, on both of
# the alert action's POSTs: this token request and the webhook itself. They run
# one after the other inside Splunk's 5-minute alert maxtime, and the worst case
# (2 x 70s) leaves the action time to log why it gave up before Splunk kills it.
REQUEST_TIMEOUT = (10, 60)


class OAuthTokenError(Exception):
    """The token endpoint couldn't be reached or didn't hand back a usable token."""


def get_oauth_headers(
    client_id: str,
    client_secret: str,
    token_url: str,
    scope: str = "",
    proxy: str = "",
):
    """
    Request a client_credentials OAuth token and return headers for the bearer token.
    Goes through ``proxy`` when one is set, like the webhook itself.
    Logs status and errors, naming the token URL by its host alone; raises on failure.
    """
    # Raised here, not from an except: a chained error would quote the URL
    if not url_parses(token_url, "OAuth token"):
        raise ValueError("OAuth token URL won't parse")
    if proxy and not url_parses(proxy, "proxy"):
        raise ValueError("Proxy URL won't parse")

    # Its path, query or user:password@ can hold a key, and errors quote them
    register_url(token_url)
    host = url_host(token_url)

    if proxy:
        # requests quotes the whole proxy URL, password and all, when it won't parse
        register_url(proxy)
        proxies = {"http": proxy, "https": proxy}
    else:
        proxies = None

    # The client secret goes out as basic auth on this request, so never over plain HTTP
    scheme = urlparse(token_url).scheme
    if scheme != "https":
        logger.error("OAuth token URL must use HTTPS, refusing scheme={!r}", scheme)
        raise ValueError("OAuth token URL must use HTTPS")

    payload = {"grant_type": "client_credentials"}
    if scope:
        payload["scope"] = scope

    logger.debug(
        "Requesting OAuth token from host={} for client_id={} scope={}",
        host,
        client_id,
        scope,
    )

    try:
        resp = requests.post(
            token_url,
            data=payload,
            auth=(client_id, client_secret),
            proxies=proxies,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.error(
            "OAuth token request to host={} failed with exception:\n{}",
            host,
            traceback.format_exc(),
        )
        raise OAuthTokenError("OAuth token request failed (network error)") from exc

    logger.debug("OAuth token endpoint responded with status={}", resp.status_code)

    if not (200 <= resp.status_code < 300):
        # Not the body: an error reply can still carry a token
        logger.error(
            "Failed to obtain OAuth token: HTTP {} from host={}",
            resp.status_code,
            host,
        )
        raise OAuthTokenError(f"OAuth token request failed: HTTP {resp.status_code}")

    try:
        j = resp.json()
    except ValueError as exc:
        logger.error("OAuth token response from host={} is not valid JSON", host)
        raise OAuthTokenError("OAuth token response is not valid JSON") from exc

    # Valid JSON can still be a list or a bare string, which has no .get()
    access_token = j.get("access_token") if isinstance(j, dict) else None
    if not access_token:
        logger.error("OAuth token response from host={} has no access_token", host)
        raise OAuthTokenError("OAuth token missing in response")
    register_secret(access_token)

    logger.info("Successfully obtained OAuth access token for client_id={}", client_id)

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
