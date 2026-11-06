"""End-to-end tests of the alert action: settings in on stdin, log out on stderr."""

from __future__ import annotations

import http.server
import json
import threading
from collections.abc import Iterator
from typing import Callable

import pytest
import responses
from better_webhook import send_webhook_request
from loguru import logger

WEBHOOK_URL = "https://hooks.example.com/webhook"
TOKEN_URL = "https://idp.example/token"

# Markers that must never show up in the log: one rides in the search result
# (the request body), one in the receiver's reply (the response body), one in
# the credential itself.
REQUEST_SECRET = "SEKRET-request-91c2"
RESPONSE_SECRET = "SEKRET-response-4b7f"
CREDENTIAL_SECRET = "SEKRET-credential-e03a"


def alert_settings(credential: str | None = None, body_failure_regex: str = "") -> dict:
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


# One case per secret field, hard-coded rather than built from SECRET_FIELDS, so
# a typo in or removal from that tuple drops a field this test still checks.
@responses.activate
@pytest.mark.parametrize(
    "credential",
    [
        pytest.param(
            {"type": "basic", "username": "user", "password": CREDENTIAL_SECRET},
            id="password",
        ),
        pytest.param(
            {
                "type": "header",
                "header_name": "X-Api-Key",
                "header_value": CREDENTIAL_SECRET,
            },
            id="header_value",
        ),
        pytest.param(
            {
                "type": "hmac",
                "hmac_secret": CREDENTIAL_SECRET,
                "hmac_hash_function": "sha256",
                "hmac_digest_type": "hex",
                "hmac_sig_header": "X-Sig",
            },
            id="hmac_secret",
        ),
        pytest.param(
            {
                "type": "oauth",
                "oauth_client_id": "client",
                "oauth_client_secret": CREDENTIAL_SECRET,
                "oauth_token_url": TOKEN_URL,
            },
            id="oauth_client_secret",
        ),
    ],
)
def test_every_secret_field_is_redacted(
    run_alert: Callable, capsys: pytest.CaptureFixture, credential: dict
) -> None:
    """Each secret field is registered, so any later log line quoting it is scrubbed."""
    responses.post(TOKEN_URL, json={"access_token": "token"})
    responses.post(WEBHOOK_URL, body="ok")

    run = run_alert(alert_settings(credential="better_webhooks:cred:"), credential)
    assert run.exit_code == 0

    logger.error("quoted in an exception: {}", CREDENTIAL_SECRET)
    log = capsys.readouterr().err

    assert "quoted in an exception: [REDACTED]" in log
    assert CREDENTIAL_SECRET not in log


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


@responses.activate
def test_an_hmac_credential_that_cannot_sign_fails_the_alert_unsent(
    run_alert: Callable,
) -> None:
    """An unknown hash function stops the alert before anything is sent."""
    responses.post(WEBHOOK_URL, body="ok")
    credential = {
        "type": "hmac",
        "hmac_secret": CREDENTIAL_SECRET,
        "hmac_hash_function": "md5",
        "hmac_digest_type": "hex",
        "hmac_sig_header": "X-Sig",
    }

    run = run_alert(alert_settings(credential="better_webhooks:cred:"), credential)

    assert run.exit_code == 2
    assert "Failed to compute HMAC signature" in run.log
    assert len(responses.calls) == 0
    assert CREDENTIAL_SECRET not in run.log


class _OkHandler(http.server.BaseHTTPRequestHandler):
    """A webhook receiver that accepts every POST."""

    def do_POST(self) -> None:
        """Read the body and answer 200."""
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        """Keep the server quiet."""


@pytest.fixture
def local_receiver() -> Iterator[str]:
    """Serve a real HTTP receiver on localhost and yield its URL.

    responses stubs out the HTTP adapter, so headers never reach http.client and a
    header it can't encode would go through. This receiver puts it back in the path.
    """
    server = http.server.HTTPServer(("127.0.0.1", 0), _OkHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/webhook"
    server.shutdown()
    server.server_close()


def test_a_header_value_http_cannot_encode_fails_the_delivery(
    local_receiver: str, log_lines: list[str]
) -> None:
    """http.client refuses a non-latin-1 header value with UnicodeEncodeError, not a RequestException."""
    delivered = send_webhook_request(
        local_receiver,
        b"{}",
        {"X-Api-Key": "caf\u2603"},
        None,
        user_agent="Splunk",
        proxy="",
    )

    assert delivered is False
    assert any("UnicodeEncodeError" in line for line in log_lines)


@pytest.mark.usefixtures("short_timeout")
def test_a_receiver_that_never_answers_fails_the_alert_with_a_timeout(
    run_alert: Callable, silent_receiver: int
) -> None:
    """Without a timeout, Splunk's maxtime kills the script before it can say why."""
    url = f"https://127.0.0.1:{silent_receiver}/webhook"
    settings = alert_settings()
    settings["configuration"]["url"] = url

    run = run_alert(settings)

    assert run.exit_code == 2
    assert f"Webhook request to url={url} timed out" in run.log


@pytest.mark.usefixtures("short_timeout")
def test_a_receiver_that_takes_the_post_and_never_replies_times_out(
    silent_receiver: int, log_lines: list[str]
) -> None:
    """Plain HTTP gets the request onto the wire, so this is the read timeout, not the connect one."""
    url = f"http://127.0.0.1:{silent_receiver}/webhook"

    delivered = send_webhook_request(
        url, b"{}", {}, None, user_agent="Splunk", proxy=""
    )

    assert delivered is False
    assert any(f"Webhook request to url={url} timed out" in line for line in log_lines)
