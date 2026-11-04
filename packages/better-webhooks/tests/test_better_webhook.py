"""End-to-end tests of the alert action: settings in on stdin, log out on stderr."""

import json
from typing import Callable, Optional

import pytest
import responses

WEBHOOK_URL = "https://hooks.example.com/webhook"
TOKEN_URL = "https://idp.example/token"

# Markers that must never show up in the log: one rides in the search result
# (the request body), one in the receiver's reply (the response body), one in
# the credential itself.
REQUEST_SECRET = "SEKRET-request-91c2"
RESPONSE_SECRET = "SEKRET-response-4b7f"
CREDENTIAL_SECRET = "SEKRET-credential-e03a"


def alert_settings(
    credential: Optional[str] = None, body_failure_regex: str = ""
) -> dict:
    """Build the JSON payload Splunk passes an alert action on stdin."""
    return {
        "session_key": "session-key",
        "sid": "scheduler__admin__search__RMD5_at_1",
        "search_name": "test search",
        "app": "search",
        "owner": "admin",
        "results_link": "https://splunk.example/results",
        "result": {"host": "web01", "token": REQUEST_SECRET},
        "configuration": {
            "url": WEBHOOK_URL,
            "body_format": '{"search": $search_name$, "result": $full_result$}',
            "credential": credential or "None",
            "user_agent": "Splunk",
            "body_failure_regex": body_failure_regex,
        },
    }


@responses.activate
@pytest.mark.parametrize(
    ("status", "body", "pattern", "exit_code", "expected"),
    [
        pytest.param(
            200, f"ticket {RESPONSE_SECRET}", "", 0, "status=200", id="delivered"
        ),
        pytest.param(
            500, f"error {RESPONSE_SECRET}", "", 2, "status=500", id="http-error"
        ),
        pytest.param(
            200,
            json.dumps({"ok": False, "error": RESPONSE_SECRET}),
            '"ok": false',
            2,
            "matched the failure pattern",
            id="failure-pattern",
        ),
    ],
)
def test_delivery_logs_the_status_but_neither_body(
    run_alert: Callable,
    status: int,
    body: str,
    pattern: str,
    exit_code: int,
    expected: str,
) -> None:
    """Request and response bodies can hold search results or tokens; only sizes are logged."""
    responses.post(WEBHOOK_URL, body=body, status=status)

    run = run_alert(alert_settings(body_failure_regex=pattern))

    assert run.exit_code == exit_code
    assert expected in run.log
    assert REQUEST_SECRET not in run.log
    assert RESPONSE_SECRET not in run.log


@responses.activate
def test_a_secret_inside_an_exception_message_is_redacted(run_alert: Callable) -> None:
    """requests quotes a bad header value in its error, and the traceback gets logged."""
    responses.post(WEBHOOK_URL, body="ok")
    credential = {
        "type": "header",
        "header_name": "X-Api-Key",
        "header_value": f"{CREDENTIAL_SECRET}\nsecond-line",
    }

    run = run_alert(alert_settings(credential="better_webhooks:cred:"), credential)

    assert run.exit_code == 2
    assert "InvalidHeader" in run.log
    assert "[REDACTED]" in run.log
    assert CREDENTIAL_SECRET not in run.log


@responses.activate
def test_an_oauth_access_token_inside_an_exception_message_is_redacted(
    run_alert: Callable,
) -> None:
    """The bearer token is a secret too, though it never sat in the credential store."""
    responses.post(
        TOKEN_URL, json={"access_token": f"{CREDENTIAL_SECRET}\nsecond-line"}
    )
    responses.post(WEBHOOK_URL, body="ok")
    credential = {
        "type": "oauth",
        "oauth_client_id": "client",
        "oauth_client_secret": "client-secret",
        "oauth_token_url": TOKEN_URL,
    }

    run = run_alert(alert_settings(credential="better_webhooks:cred:"), credential)

    assert run.exit_code == 2
    assert "InvalidHeader" in run.log
    assert CREDENTIAL_SECRET not in run.log


@responses.activate
def test_an_http_oauth_token_url_fails_the_alert_before_anything_is_sent(
    run_alert: Callable,
) -> None:
    """A plain-HTTP token URL would send the client secret in the clear."""
    http_token_url = "http://idp.example/token"
    responses.post(http_token_url, json={"access_token": "tok"})
    responses.post(WEBHOOK_URL, body="ok")
    credential = {
        "type": "oauth",
        "oauth_client_id": "client",
        "oauth_client_secret": CREDENTIAL_SECRET,
        "oauth_token_url": http_token_url,
    }

    run = run_alert(alert_settings(credential="better_webhooks:my_oauth:"), credential)

    assert run.exit_code == 2
    assert len(responses.calls) == 0
    assert "must use HTTPS" in run.log
    assert "my_oauth" in run.log
    assert CREDENTIAL_SECRET not in run.log
