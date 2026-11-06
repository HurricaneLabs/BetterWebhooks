"""End-to-end tests of the alert action: settings in on stdin, log out on stderr."""

from __future__ import annotations

import http.server
import json
import socket
import threading
from collections.abc import Iterator
from typing import Callable
from urllib.parse import urlsplit

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

# Markers for the parts of a URL that can be the secret itself: Slack's
# /services/T…/B…/<token>, a signed ?sig=…, a user:password@.
URL_PATH_SECRET = "SEKRET-url-path-7a31"
URL_QUERY_SECRET = "SEKRET-url-query-c58d"
URL_PASSWORD_SECRET = "SEKRET-url-password-2e94"
URL_SECRETS = (URL_PATH_SECRET, URL_QUERY_SECRET, URL_PASSWORD_SECRET)


def secret_url(host: str, path: str = "/services/T0/B0") -> str:
    """Build an https URL with a secret in its userinfo, path and query.

    The space and the é make requests percent-encode the path, so its error
    messages quote it in a different form from the one configured.
    """
    return (
        f"https://user:{URL_PASSWORD_SECRET}@{host}{path}/{URL_PATH_SECRET} é"
        f"?sig={URL_QUERY_SECRET}"
    )


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


@responses.activate
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_a_redirect_fails_the_alert_and_nothing_follows_it(
    run_alert: Callable, status: int
) -> None:
    """requests strips only Authorization on a redirect, so a custom header would follow it.

    After a 301, 302 or 303 requests resends a bodyless GET, so the alert was
    never delivered; after a 307 or 308 it resends the POST, search results and all.
    """
    redirect_target = (
        f"http://collector.example/webhook/{URL_PATH_SECRET}?sig={URL_QUERY_SECRET}"
    )
    responses.post(WEBHOOK_URL, status=status, headers={"Location": redirect_target})
    # Both methods, so a followed redirect lands as a recorded call, not an error
    responses.get(redirect_target, body="ok")
    responses.post(redirect_target, body="ok")
    credential = {
        "type": "header",
        "header_name": "X-Api-Key",
        "header_value": CREDENTIAL_SECRET,
    }

    run = run_alert(alert_settings(credential="better_webhooks:cred:"), credential)

    assert [call.request.url for call in responses.calls] == [WEBHOOK_URL]
    assert run.exit_code == 2
    assert f"redirect (HTTP status={status})" in run.log
    assert CREDENTIAL_SECRET not in run.log
    # The Location can carry a secret too
    assert URL_PATH_SECRET not in run.log
    assert URL_QUERY_SECRET not in run.log


@responses.activate
def test_a_delivery_logs_the_webhook_host_but_no_other_part_of_its_url(
    run_alert: Callable,
) -> None:
    """For a Slack-style webhook the URL's path is the secret, so only the host is logged."""
    url = secret_url("hooks.example.com")
    responses.post(url, body="ok")
    settings = alert_settings()
    settings["configuration"]["url"] = url

    run = run_alert(settings)

    assert run.exit_code == 0
    assert "host=hooks.example.com" in run.log
    for secret in URL_SECRETS:
        assert secret not in run.log


def test_a_refused_connection_keeps_the_webhook_url_out_of_the_log(
    run_alert: Callable, closed_port: int
) -> None:
    """requests quotes the URL's path and query, percent-encoded, in its connection errors."""
    settings = alert_settings()
    settings["configuration"]["url"] = secret_url(f"127.0.0.1:{closed_port}")

    run = run_alert(settings)

    assert run.exit_code == 2
    assert "Max retries exceeded" in run.log
    assert "[REDACTED]" in run.log
    for secret in URL_SECRETS:
        assert secret not in run.log


@responses.activate
@pytest.mark.parametrize(
    "url", ["https://hooks.example.com", "https://hooks.example.com/"]
)
def test_a_url_with_no_path_leaves_the_slashes_in_the_log_alone(
    run_alert: Callable, capsys: pytest.CaptureFixture, url: str
) -> None:
    """requests sends an empty path as "/", which mustn't become a secret."""
    responses.post(url, body="ok")
    settings = alert_settings()
    settings["configuration"]["url"] = url

    run = run_alert(settings)
    assert run.exit_code == 0

    logger.error('File "/opt/splunk/bin/better_webhook.py", line 1')
    log = capsys.readouterr().err

    assert 'File "/opt/splunk/bin/better_webhook.py", line 1' in log


def test_an_unreachable_token_url_stays_out_of_the_log(
    run_alert: Callable, closed_port: int
) -> None:
    """The OAuth error chains requests' error, so the final traceback quotes the token URL too."""
    credential = {
        "type": "oauth",
        "oauth_client_id": "client",
        "oauth_client_secret": CREDENTIAL_SECRET,
        "oauth_token_url": secret_url(f"127.0.0.1:{closed_port}", path="/token"),
    }

    run = run_alert(alert_settings(credential="better_webhooks:cred:"), credential)

    assert run.exit_code == 2
    assert "Failed to obtain OAuth token" in run.log
    assert "[REDACTED]" in run.log
    for secret in (*URL_SECRETS, CREDENTIAL_SECRET):
        assert secret not in run.log


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


@pytest.mark.parametrize("port", ["80a", "99999"])
def test_a_proxy_url_that_does_not_parse_keeps_its_password_out_of_the_log(
    log_lines: list[str], port: str
) -> None:
    """requests quotes the whole proxy URL, password included, when its port won't parse."""
    delivered = send_webhook_request(
        WEBHOOK_URL,
        b"{}",
        {},
        None,
        user_agent="Splunk",
        proxy=f"http://user:{URL_PASSWORD_SECRET}@proxy.example:{port}",
    )

    assert delivered is False
    assert any("InvalidURL" in line for line in log_lines)
    assert not any(URL_PASSWORD_SECRET in line for line in log_lines)


@pytest.mark.usefixtures("short_timeout")
def test_a_receiver_that_never_answers_fails_the_alert_with_a_timeout(
    run_alert: Callable, silent_receiver: int
) -> None:
    """Without a timeout, Splunk's maxtime kills the script before it can say why.

    The timeout line names the receiver by its host alone.
    """
    settings = alert_settings()
    settings["configuration"]["url"] = secret_url(f"127.0.0.1:{silent_receiver}")

    run = run_alert(settings)

    assert run.exit_code == 2
    assert f"Webhook request to host=127.0.0.1:{silent_receiver} timed out" in run.log
    for secret in URL_SECRETS:
        assert secret not in run.log


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
    assert any(
        f"Webhook request to host=127.0.0.1:{silent_receiver} timed out" in line
        for line in log_lines
    )


@pytest.fixture
def stalled_body_receiver() -> Iterator[str]:
    """Answer the POST with headers that promise a body, never send it; yield the URL.

    Everything closes after 5 seconds, so a client with no timeout fails
    instead of hanging the suite.
    """
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    conns: list[socket.socket] = []

    def answer() -> None:
        conn, _ = sock.accept()
        conns.append(conn)
        conn.recv(65536)
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n")

    def close_all() -> None:
        for s in (sock, *conns):
            s.close()

    threading.Thread(target=answer, daemon=True).start()
    safety_net = threading.Timer(5, close_all)
    safety_net.start()
    yield f"http://127.0.0.1:{sock.getsockname()[1]}/webhook"
    safety_net.cancel()
    close_all()


@pytest.mark.usefixtures("short_timeout")
def test_a_receiver_that_stalls_partway_through_its_reply_times_out(
    stalled_body_receiver: str, log_lines: list[str]
) -> None:
    """requests raises a stall in the body as a ConnectionError, not a Timeout."""
    delivered = send_webhook_request(
        stalled_body_receiver, b"{}", {}, None, user_agent="Splunk", proxy=""
    )

    host = urlsplit(stalled_body_receiver).netloc
    assert delivered is False
    assert any(
        f"Webhook request to host={host} timed out" in line for line in log_lines
    )
