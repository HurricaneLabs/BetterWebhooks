"""Tests for fetching an OAuth client-credentials token."""

import json
from contextlib import AbstractContextManager, nullcontext

import pytest
import responses
from oauth_helper import OAuthTokenError, get_oauth_headers

SECRET = "SEKRET-oauth-5d1e"

# Markers for the token URL's path, query and user:password@, which can each
# carry a secret (an API key in the query, credentials in the userinfo).
TOKEN_URL_SECRETS = (
    "SEKRET-token-url-path-41b0",
    "SEKRET-token-url-query-9d2c",
    "SEKRET-token-url-password-e7f5",
)


def secret_token_url(host: str, scheme: str = "https") -> str:
    """Build a token URL with a secret in its userinfo, path and query."""
    path, query, password = TOKEN_URL_SECRETS
    return f"{scheme}://client:{password}@{host}/token/{path} é?key={query}"


def test_a_refused_token_url_stays_out_of_the_log(log_lines: list[str]) -> None:
    """The HTTPS refusal names the scheme, not the URL it refuses."""
    with pytest.raises(ValueError, match="HTTPS"):
        get_oauth_headers(
            "client", "client-secret", secret_token_url("idp.example", scheme="http")
        )

    assert any("must use HTTPS" in line for line in log_lines)
    for secret in TOKEN_URL_SECRETS:
        assert not any(secret in line for line in log_lines)


@responses.activate
@pytest.mark.parametrize(
    ("status", "body", "outcome"),
    [
        pytest.param(
            200, json.dumps({"access_token": "tok"}), nullcontext(), id="token"
        ),
        pytest.param(401, "", pytest.raises(OAuthTokenError), id="rejected"),
        pytest.param(200, "<html>", pytest.raises(OAuthTokenError), id="not-json"),
        pytest.param(200, "{}", pytest.raises(OAuthTokenError), id="no-access-token"),
    ],
)
def test_the_token_url_host_is_logged_but_no_other_part_of_it(
    status: int,
    body: str,
    outcome: AbstractContextManager,
    log_lines: list[str],
) -> None:
    """Every line about the token request names the endpoint by its host alone."""
    url = secret_token_url("idp.example")
    responses.post(url, body=body, status=status)

    with outcome:
        get_oauth_headers("client", "client-secret", url)

    assert any("host=idp.example" in line for line in log_lines)
    for secret in TOKEN_URL_SECRETS:
        assert not any(secret in line for line in log_lines)


@responses.activate
@pytest.mark.parametrize("token_url", ["http://idp.example/token", "idp.example/token"])
def test_refuses_a_token_url_that_is_not_https(token_url: str) -> None:
    """The client secret rides on this request, so plain HTTP must never be tried."""
    # A working endpoint, so the only thing that can stop the request is the check
    responses.post(token_url, json={"access_token": "tok"})

    with pytest.raises(ValueError, match="HTTPS"):
        get_oauth_headers("client", "client-secret", token_url)

    assert len(responses.calls) == 0


@responses.activate
@pytest.mark.parametrize(
    ("status", "body"),
    [
        pytest.param(
            401, json.dumps({"error": "invalid_client", "x": SECRET}), id="rejected"
        ),
        pytest.param(200, f"<html>{SECRET}</html>", id="not-json"),
        pytest.param(200, json.dumps({"refresh_token": SECRET}), id="no-access-token"),
        pytest.param(200, json.dumps([SECRET]), id="not-an-object"),
    ],
)
def test_a_failed_token_response_is_not_logged(
    status: int, body: str, log_lines: list[str]
) -> None:
    """The token endpoint's reply can carry tokens, so only its status is logged."""
    responses.post("https://idp.example/token", body=body, status=status)

    with pytest.raises(OAuthTokenError):
        get_oauth_headers("client", "client-secret", "https://idp.example/token")

    assert any(line.startswith("ERROR") for line in log_lines)
    assert not any(SECRET in line for line in log_lines)


@pytest.mark.usefixtures("short_timeout")
def test_a_token_endpoint_that_never_answers_times_out(
    silent_receiver: int, log_lines: list[str]
) -> None:
    """The token request runs inside Splunk's alert maxtime too, before the webhook."""
    with pytest.raises(OAuthTokenError):
        get_oauth_headers(
            "client", "client-secret", f"https://127.0.0.1:{silent_receiver}/token"
        )

    assert any("timed out" in line for line in log_lines)
