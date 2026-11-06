"""Tests for fetching an OAuth client-credentials token."""

import json

import pytest
import responses
from oauth_helper import OAuthTokenError, get_oauth_headers

SECRET = "SEKRET-oauth-5d1e"


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
