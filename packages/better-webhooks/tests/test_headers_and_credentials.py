"""End-to-end tests of the alert's own headers and its second credential (BWH-V2-7)."""

from __future__ import annotations

from typing import Callable

import pytest
import responses

WEBHOOK_URL = "https://hooks.example.com/webhook"
TOKEN_URL = "https://idp.example/token"
CLIENT_SECRET = "SEKRET-client-secret-6d0b"
INJECTED = "X-Original-URL: /admin"

CREDENTIALS = {
    "basic": {"type": "basic", "username": "user", "password": "pass"},
    "header": {"type": "header", "header_name": "X-Api-Key", "header_value": "key-1"},
    "hmac": {
        "type": "hmac",
        "hmac_secret": "hmac-secret",
        "hmac_hash_function": "sha256",
        "hmac_digest_type": "hex",
        "hmac_sig_header": "X-Sig",
        "hmac_time_header": "X-Time",
    },
    "oauth": {
        "type": "oauth",
        "oauth_client_id": "client",
        "oauth_client_secret": CLIENT_SECRET,
        "oauth_token_url": TOKEN_URL,
    },
}


def alert_settings(
    *rows: tuple[str, str], url: str = WEBHOOK_URL, credential: str = "None"
) -> dict:
    """Build the JSON payload Splunk passes an alert action, with ``rows`` as its header rows."""
    configuration = {
        "url": url,
        "body_format": '{"search": $search_name$}',
        "credential": credential,
        "user_agent": "Splunk/guid-1",
        "body_failure_regex": "",
    }
    for number, (name, value) in enumerate(rows, start=1):
        configuration[f"header_{number}_name"] = name
        configuration[f"header_{number}_value"] = value
    return {
        "session_key": "session-key",
        "sid": "sid-1",
        "search_name": "test search",
        "app": "search",
        "owner": "admin",
        "results_link": "https://splunk.example/results",
        "result": {"host": "web01"},
        "configuration": configuration,
    }


@responses.activate
def test_the_alerts_own_headers_reach_the_receiver_beside_the_credentials(
    run_alert: Callable,
) -> None:
    """Rows add to what the credential sends."""
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(
        alert_settings(
            ("X-Source", "splunk"),
            ("X-Alert-Host", "web01"),
            credential="better_webhooks:key:",
        ),
        CREDENTIALS["header"],
    )

    assert run.exit_code == 0, run.log
    sent = responses.calls[0].request.headers
    assert (sent["X-Source"], sent["X-Alert-Host"], sent["X-Api-Key"]) == (
        "splunk",
        "web01",
        "key-1",
    )


@responses.activate
def test_a_row_replaces_the_automatic_content_type_and_user_agent(
    run_alert: Callable,
) -> None:
    """The row's spelling and value win over the automatic Content-Type."""
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(
        alert_settings(
            ("content-type", "application/json; charset=utf-8"),
            ("User-Agent", "my-agent"),
        )
    )

    assert run.exit_code == 0, run.log
    sent = responses.calls[0].request.headers
    # requests' headers ignore case, so only the row's lowercase spelling
    # surviving proves the row went on last
    assert [name for name in sent if name.lower() == "content-type"] == ["content-type"]
    assert sent["Content-Type"] == "application/json; charset=utf-8"
    assert sent["User-Agent"] == "my-agent"


@responses.activate
def test_a_row_replaces_the_oauth_credentials_accept(run_alert: Callable) -> None:
    """The OAuth credential's Accept and Content-Type are defaults, like the automatic headers."""
    responses.post(TOKEN_URL, json={"access_token": "tok-1"})
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(
        alert_settings(
            ("Accept", "text/plain"), credential="better_webhooks:my_oauth:"
        ),
        CREDENTIALS["oauth"],
    )

    assert run.exit_code == 0, run.log
    sent = responses.calls[-1].request
    assert sent.url == WEBHOOK_URL
    assert (sent.headers["Accept"], sent.headers["Authorization"]) == (
        "text/plain",
        "Bearer tok-1",
    )


@responses.activate
@pytest.mark.parametrize(
    ("kind", "header"),
    [
        ("basic", "Authorization"),
        ("oauth", "authorization"),
        ("header", "X-API-KEY"),
        ("hmac", "X-Sig"),
        ("hmac", "x-time"),
    ],
)
def test_a_row_naming_a_header_the_credential_sets_refuses_the_alert_unsent(
    run_alert: Callable, kind: str, header: str
) -> None:
    """Checked before the credential builds anything: no token request, no signature, no webhook."""
    responses.post(TOKEN_URL, json={"access_token": "tok-1"})
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(
        alert_settings(
            (header, "from-the-alert"), credential=f"better_webhooks:my_{kind}:"
        ),
        CREDENTIALS[kind],
    )

    assert run.exit_code == 2
    assert len(responses.calls) == 0
    assert (
        f"Header {header} is set by both credential my_{kind} and the alert's header 1, "
        "so the webhook isn't sent"
    ) in run.log
    assert "from-the-alert" not in run.log
    assert CLIENT_SECRET not in run.log


@responses.activate
def test_a_row_setting_authorization_beside_url_user_info_refuses_the_alert_unsent(
    run_alert: Callable,
) -> None:
    """requests would otherwise swap the row's Authorization for the URL's, silently."""
    url = "https://svc:url-pass@hooks.example.com/webhook"
    responses.post(url, body="ok")

    run = run_alert(alert_settings(("Authorization", "Bearer from-the-alert"), url=url))

    assert run.exit_code == 2
    assert len(responses.calls) == 0
    assert (
        "Header Authorization is set by both the URL's user info and the alert's header 1"
        in run.log
    )


@responses.activate
def test_a_search_result_putting_a_line_break_in_a_row_refuses_the_alert_unsent(
    run_alert: Callable,
) -> None:
    """Splunk fills $result.host$ before the script runs, so this is what the script sees."""
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(alert_settings(("X-Alert-Host", f"web01\n{INJECTED}")))

    assert run.exit_code == 2
    assert len(responses.calls) == 0
    assert (
        "Header 1 (X-Alert-Host) has a line break or another character a header "
        "can't carry in its value, so the webhook isn't sent: check the token it uses"
    ) in run.log
    assert INJECTED not in run.log


@responses.activate
def test_a_value_outside_latin_1_refuses_the_alert_before_the_token_request(
    run_alert: Callable,
) -> None:
    """requests can't send it, so the alert stops before the OAuth credential fetches a token."""
    responses.post(TOKEN_URL, json={"access_token": "tok-1"})
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(
        alert_settings(
            ("X-Role", "José→Admin"), credential="better_webhooks:my_oauth:"
        ),
        CREDENTIALS["oauth"],
    )

    assert run.exit_code == 2
    assert len(responses.calls) == 0
    assert (
        "Header 1 (X-Role) has a line break or another character a header "
        "can't carry in its value, so the webhook isn't sent: check the token it uses"
    ) in run.log
    assert "José→Admin" not in run.log


@responses.activate
def test_two_rows_with_one_name_refuse_the_alert_unsent(run_alert: Callable) -> None:
    """Neither row wins quietly."""
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(alert_settings(("X-Source", "a"), ("x-source", "b")))

    assert run.exit_code == 2
    assert len(responses.calls) == 0
    assert (
        "Header x-source is set by both the alert's header 1 and the alert's header 2"
        in run.log
    )
