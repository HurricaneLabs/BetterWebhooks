import os
import sys
import traceback
from urllib.parse import urlparse

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from log_redaction import register_secret
from loguru import logger


class OAuthTokenError(Exception):
    """The token endpoint couldn't be reached or didn't hand back a usable token."""


def get_oauth_headers(
    client_id: str, client_secret: str, token_url: str, scope: str = ""
):
    """
    Request a client_credentials OAuth token and return headers for the bearer token.
    Logs status and errors; raises on failure.
    """
    # The client secret goes out as basic auth on this request, so never over plain HTTP
    if urlparse(token_url).scheme != "https":
        logger.error("OAuth token URL must use HTTPS, refusing {}", token_url)
        raise ValueError("OAuth token URL must use HTTPS")

    payload = {"grant_type": "client_credentials"}
    if scope:
        payload["scope"] = scope

    logger.debug(
        "Requesting OAuth token from {} for client_id={} scope={}",
        token_url,
        client_id,
        scope,
    )

    try:
        resp = requests.post(
            token_url, data=payload, auth=(client_id, client_secret), timeout=300
        )
    except requests.RequestException as exc:
        logger.error(
            "OAuth token request to {} failed with exception:\n{}",
            token_url,
            traceback.format_exc(),
        )
        raise OAuthTokenError("OAuth token request failed (network error)") from exc

    logger.debug("OAuth token endpoint responded with status={}", resp.status_code)

    if not (200 <= resp.status_code < 300):
        # Not the body: an error reply can still carry a token
        logger.error(
            "Failed to obtain OAuth token: HTTP {} from {}",
            resp.status_code,
            token_url,
        )
        raise OAuthTokenError(f"OAuth token request failed: HTTP {resp.status_code}")

    try:
        j = resp.json()
    except ValueError as exc:
        logger.error("OAuth token response from {} is not valid JSON", token_url)
        raise OAuthTokenError("OAuth token response is not valid JSON") from exc

    # Valid JSON can still be a list or a bare string, which has no .get()
    access_token = j.get("access_token") if isinstance(j, dict) else None
    if not access_token:
        logger.error("OAuth token response from {} has no access_token", token_url)
        raise OAuthTokenError("OAuth token missing in response")
    register_secret(access_token)

    logger.info("Successfully obtained OAuth access token for client_id={}", client_id)

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
