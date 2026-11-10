"""Pin the exact request every pre-2.0 alert configuration sends (BWH-V2-7).

An alert that sets none of 2.0.0's new parameters (a second credential, header
rows) must send byte-for-byte what it sent before. EXPECTED was captured on
main at 8e0d645, before any BWH-V2-7 change, and was identical on Python 3.9
and 3.13. Never edit EXPECTED to make this test pass: a difference means an
existing alert would send something new.

Some of what it pins is odd and stays that way on purpose. URL user info beats
an OAuth or header credential's Authorization, and the automatic Content-Type
and User-Agent beat a header credential of the same name.
"""

from __future__ import annotations

import types
from typing import Callable

import pytest
import responses

PLAIN_URL = "https://hooks.example.com/webhook"
USER_INFO_URL = "https://svc:url-pass@hooks.example.com/webhook"
TOKEN_URL = "https://idp.example/token"
FROZEN_NOW = 1700000000.25
BODY = '{"search": $search_name$, "result": $full_result$}'
NO_BODY = "$none$"
_HMAC = {
    "type": "hmac",
    "hmac_secret": "hmac-secret",
    "hmac_hash_function": "sha256",
    "hmac_digest_type": "b64",
}
CREDENTIALS = {
    "none": None,
    "basic": {"type": "basic", "username": "user", "password": "pass"},
    "header": {"type": "header", "header_name": "X-Api-Key", "header_value": "key-1"},
    "header-content-type": {
        "type": "header",
        "header_name": "Content-Type",
        "header_value": "text/plain",
    },
    "header-lowercase-content-type": {
        "type": "header",
        "header_name": "content-type",
        "header_value": "text/plain",
    },
    "header-user-agent": {
        "type": "header",
        "header_name": "User-Agent",
        "header_value": "cred-agent",
    },
    "header-authorization": {
        "type": "header",
        "header_name": "Authorization",
        "header_value": "Token abc",
    },
    "hmac": {**_HMAC, "hmac_sig_header": "X-Sig"},
    "hmac-timestamp": {
        **_HMAC,
        "hmac_sig_header": "X-Sig",
        "hmac_time_header": "X-Time",
    },
    "hmac-same-header": {
        **_HMAC,
        "hmac_sig_header": "X-Sig",
        "hmac_time_header": "X-Sig",
    },
    "oauth": {
        "type": "oauth",
        "oauth_client_id": "client",
        "oauth_client_secret": "client-secret",
        "oauth_token_url": TOKEN_URL,
    },
}
CASES = [
    (f"{cred}-{url_id}-{body_id}", cred, url, body)
    for cred in CREDENTIALS
    for url_id, url in (("plain-url", PLAIN_URL), ("user-info-url", USER_INFO_URL))
    for body_id, body in (("body", BODY), ("no-body", NO_BODY))
]

# Captured on main 8e0d645; never edit (see the module docstring)
EXPECTED = {
    "none-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "none-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "none-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "none-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "basic-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic dXNlcjpwYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "basic-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic dXNlcjpwYXNz"),
        ],
        "body": None,
    },
    "basic-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic dXNlcjpwYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "basic-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic dXNlcjpwYXNz"),
        ],
        "body": None,
    },
    "header-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Api-Key", b"key-1"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Api-Key", b"key-1"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "header-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Api-Key", b"key-1"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Api-Key", b"key-1"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "header-content-type-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-content-type-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"text/plain"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "header-content-type-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-content-type-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"text/plain"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "header-lowercase-content-type-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-lowercase-content-type-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("content-type", b"text/plain"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "header-lowercase-content-type-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-lowercase-content-type-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("content-type", b"text/plain"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "header-user-agent-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-user-agent-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "header-user-agent-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-user-agent-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "header-authorization-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Authorization", b"Token abc"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-authorization-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Authorization", b"Token abc"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "header-authorization-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "header-authorization-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "hmac-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"TudhD/wEADNbS3NaQhuQeitZUIcUfU1I39TudXRu8jI="),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "hmac-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"Tb0ikgJfIb0HypAAWeGSht9a0UwFxPAPGaKVny0axWs="),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "hmac-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"TudhD/wEADNbS3NaQhuQeitZUIcUfU1I39TudXRu8jI="),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "hmac-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"Tb0ikgJfIb0HypAAWeGSht9a0UwFxPAPGaKVny0axWs="),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "hmac-timestamp-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Time", b"1700000000.25"),
            ("X-Sig", b"cE6ToZtYMbuVCaR48p/V76BYpEtxQvNhqoRj8/jb3bg="),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "hmac-timestamp-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Time", b"1700000000.25"),
            ("X-Sig", b"mi9N7cUIPjm9YFg79DIrwY0yGy8GlmCHMyyS/z68tGw="),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "hmac-timestamp-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Time", b"1700000000.25"),
            ("X-Sig", b"cE6ToZtYMbuVCaR48p/V76BYpEtxQvNhqoRj8/jb3bg="),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "hmac-timestamp-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Time", b"1700000000.25"),
            ("X-Sig", b"mi9N7cUIPjm9YFg79DIrwY0yGy8GlmCHMyyS/z68tGw="),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "hmac-same-header-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"cE6ToZtYMbuVCaR48p/V76BYpEtxQvNhqoRj8/jb3bg="),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "hmac-same-header-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"mi9N7cUIPjm9YFg79DIrwY0yGy8GlmCHMyyS/z68tGw="),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "hmac-same-header-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"cE6ToZtYMbuVCaR48p/V76BYpEtxQvNhqoRj8/jb3bg="),
            ("Content-Type", b"application/json"),
            ("Content-Length", b"54"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "hmac-same-header-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"*/*"),
            ("Connection", b"keep-alive"),
            ("X-Sig", b"mi9N7cUIPjm9YFg79DIrwY0yGy8GlmCHMyyS/z68tGw="),
            ("Content-Length", b"0"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
        ],
        "body": None,
    },
    "oauth-plain-url-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"application/json"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Authorization", b"Bearer tok-1"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "oauth-plain-url-no-body": {
        "url": "https://hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"application/json"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Authorization", b"Bearer tok-1"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
    "oauth-user-info-url-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"application/json"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
            ("Content-Length", b"54"),
        ],
        "body": b'{"search": "test search", "result": {"host": "web01"}}',
    },
    "oauth-user-info-url-no-body": {
        "url": "https://svc:url-pass@hooks.example.com/webhook",
        "headers": [
            ("User-Agent", b"Splunk/guid-1"),
            ("Accept", b"application/json"),
            ("Connection", b"keep-alive"),
            ("Content-Type", b"application/json"),
            ("Authorization", b"Basic c3ZjOnVybC1wYXNz"),
            ("Content-Length", b"0"),
        ],
        "body": None,
    },
}


# Once 2.0.0 is installed, Splunk merges alert_actions.conf's empty defaults for
# the new parameters into every alert's configuration, so an existing alert
# arrives with these keys set to "". It must still send exactly what it did.
CONF_DEFAULTS_2_0 = {
    "credential_2": "",
    **{
        f"header_{number}_{part}": ""
        for number in (1, 2, 3)
        for part in ("name", "value")
    },
}


def alert_settings(url: str, body_format: str, credential: str) -> dict:
    """Build the JSON payload Splunk passes an alert action on stdin."""
    return {
        "session_key": "session-key",
        "sid": "scheduler__admin__search__RMD5_at_1",
        "search_name": "test search",
        "app": "search",
        "owner": "admin",
        "results_link": "https://splunk.example/results",
        "result": {"host": "web01"},
        "configuration": {
            "url": url,
            "body_format": body_format,
            "credential": credential,
            "user_agent": "Splunk/guid-1",
            "body_failure_regex": "",
        },
    }


def on_the_wire(prepared: object) -> dict:
    """What the receiver gets: URL, headers in order with their bytes, and body.

    Leaves out Accept-Encoding, which lists whatever compression libraries are
    installed. http.client sends a str header value as latin-1.
    """
    return {
        "url": prepared.url,
        "headers": [
            (name, value.encode("latin-1") if isinstance(value, str) else value)
            for name, value in prepared.headers.items()
            if name != "Accept-Encoding"
        ],
        "body": prepared.body,
    }


@responses.activate
@pytest.mark.parametrize(
    "conf_defaults",
    [
        pytest.param({}, id="saved-before-2.0"),
        pytest.param(CONF_DEFAULTS_2_0, id="with-2.0-conf-defaults"),
    ],
)
@pytest.mark.parametrize(
    ("case_id", "credential", "url", "body_format"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_an_existing_alert_sends_exactly_what_it_sent_before(
    run_alert: Callable,
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    credential: str,
    url: str,
    body_format: str,
    conf_defaults: dict,
) -> None:
    """No credential or one, with and without a body and URL user info."""
    # Fixes the HMAC timestamp, so the signature is fixed too
    monkeypatch.setattr(
        "hmac_helper.time", types.SimpleNamespace(time=lambda: FROZEN_NOW)
    )
    responses.post(TOKEN_URL, json={"access_token": "tok-1"})
    responses.post(url, body="ok")
    stored = CREDENTIALS[credential]
    settings = alert_settings(
        url, body_format, "better_webhooks:cred:" if stored else "None"
    )
    settings["configuration"].update(conf_defaults)

    run = run_alert(settings, stored)

    assert run.exit_code == 0, run.log
    webhook_calls = [c for c in responses.calls if c.request.url != TOKEN_URL]
    assert len(webhook_calls) == 1
    assert on_the_wire(webhook_calls[0].request) == EXPECTED[case_id]
