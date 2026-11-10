"""Unit tests for the alert's own headers and the check that no two sources set one header."""

from __future__ import annotations

import pytest
from alert_headers import (
    HeaderError,
    HeaderRow,
    Source,
    check_clashes,
    credential_claims,
    read_header_rows,
    stored_name,
    url_claims,
)


def configuration(*rows: tuple[str, str]) -> dict:
    """Build an alert configuration holding ``rows`` as header_<n>_name / _value."""
    config: dict = {"url": "https://hooks.example.com/webhook"}
    for number, (name, value) in enumerate(rows, start=1):
        config[f"header_{number}_name"] = name
        config[f"header_{number}_value"] = value
    return config


def test_an_alert_saved_before_2_0_has_no_header_rows() -> None:
    """Its configuration has no header_<n> keys at all."""
    assert read_header_rows({"url": "https://hooks.example.com/webhook"}) == []


def test_rows_are_read_in_order_with_their_number_and_trimmed() -> None:
    """An empty row is skipped; the others keep the number the form shows."""
    rows = configuration((" X-Source ", " splunk "), ("", ""), ("X-Host", "web01"))
    assert read_header_rows(rows) == [
        HeaderRow(1, "X-Source", "splunk"),
        HeaderRow(3, "X-Host", "web01"),
    ]


def test_a_name_with_an_empty_value_sends_an_empty_value() -> None:
    """A token that fills in nothing leaves the value empty, which HTTP allows."""
    assert read_header_rows(configuration(("X-Host", ""))) == [
        HeaderRow(1, "X-Host", "")
    ]


def test_a_value_with_no_name_is_refused() -> None:
    """Most likely a name deleted by mistake."""
    with pytest.raises(HeaderError) as refused:
        read_header_rows(configuration(("X-Source", "splunk"), ("  ", "orphan")))
    assert (
        str(refused.value)
        == "Header 2 has a value but no name, so the webhook isn't sent"
    )


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("X Source", id="space"),
        pytest.param("X-Source:", id="colon"),
        pytest.param("X-Søurce", id="non-ascii"),
        pytest.param("X-Source\nX-Evil", id="line-break"),
    ],
)
def test_a_name_that_is_not_a_header_name_is_refused_without_quoting_it(
    name: str,
) -> None:
    """RFC 9110 allows letters, digits and !#$%&'*+-.^_`|~ in a field name."""
    with pytest.raises(HeaderError) as refused:
        read_header_rows(configuration((name, "v")))
    assert (
        str(refused.value)
        == "Header 1's name isn't a valid header name, so the webhook isn't sent"
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("web01\nX-Original-URL: /admin", id="line-feed"),
        pytest.param("web01\rX-Original-URL: /admin", id="carriage-return"),
        pytest.param("web01\x00X-Original-URL: /admin", id="nul"),
    ],
)
def test_a_line_break_or_nul_inside_a_value_is_refused_without_quoting_it(
    value: str,
) -> None:
    """A token filled from a search result can hold one, which would start a header nobody wrote."""
    with pytest.raises(HeaderError) as refused:
        read_header_rows(configuration(("X-Alert-Host", value)))
    assert str(refused.value) == (
        "Header 1 (X-Alert-Host) has a line break or NUL in its value, "
        "so the webhook isn't sent: check the token it uses"
    )


def test_a_line_break_at_either_end_of_a_value_is_trimmed_away() -> None:
    """Trim first, then check, so a trailing newline from a token is harmless."""
    rows = configuration(("X-Alert-Host", "\nweb01\r\n"))
    assert read_header_rows(rows) == [HeaderRow(1, "X-Alert-Host", "web01")]


def test_a_fourth_row_is_not_read() -> None:
    """The form has three rows; a header_4 from SPL is ignored."""
    config = configuration(*[(f"X-{n}", "v") for n in range(1, 5)])
    assert [row.number for row in read_header_rows(config)] == [1, 2, 3]


@pytest.mark.parametrize(
    ("credential", "claims"),
    [
        pytest.param(
            {"type": "basic", "username": "u", "password": "p"},
            ("Authorization",),
            id="basic",
        ),
        pytest.param(
            {
                "type": "oauth",
                "oauth_client_id": "c",
                "oauth_client_secret": "s",
                "oauth_token_url": "https://idp.example/token",
            },
            ("Authorization",),
            id="oauth",
        ),
        pytest.param(
            {"type": "header", "header_name": " X-Api-Key ", "header_value": "k"},
            ("X-Api-Key",),
            id="header",
        ),
        pytest.param(
            {"type": "hmac", "hmac_sig_header": "X-Sig"}, ("X-Sig",), id="hmac"
        ),
        pytest.param(
            {
                "type": "hmac",
                "hmac_sig_header": "X-Sig",
                "hmac_time_header": " X-Time ",
            },
            ("X-Sig", "X-Time"),
            id="hmac-timestamp",
        ),
        pytest.param({"type": "carrier-pigeon"}, (), id="unknown-type"),
    ],
)
def test_each_credential_type_claims_the_headers_it_sets(
    credential: dict, claims: tuple
) -> None:
    """Read from stored fields only, so no token is fetched and nothing is signed."""
    assert credential_claims(credential) == claims


@pytest.mark.parametrize(
    ("url", "claims"),
    [
        pytest.param("https://hooks.example.com/x", (), id="no-user-info"),
        pytest.param(
            "https://svc:pw@hooks.example.com/x",
            ("Authorization",),
            id="user-and-password",
        ),
        pytest.param(
            "https://:pw@hooks.example.com/x", ("Authorization",), id="password-only"
        ),
        pytest.param(
            "  https://svc:pw@hooks.example.com/x",
            ("Authorization",),
            id="leading-space",
        ),
        pytest.param("https://svc@hooks.example.com/x", (), id="user-name-only"),
        pytest.param("https://[::1/x", (), id="unbalanced-bracket"),
        pytest.param("", (), id="no-url"),
    ],
)
def test_url_user_info_claims_authorization_when_requests_would_send_it(
    url: str, claims: tuple
) -> None:
    """requests sends no Authorization for a user name with no password."""
    assert url_claims(url) == claims


@pytest.mark.parametrize("name", ["better_webhooks:my_cred:", "my_cred"])
def test_a_credential_is_named_as_the_credentials_page_shows_it(name: str) -> None:
    """A saved alert passes the storage key; | sendalert passes the bare name."""
    assert stored_name(name) == "my_cred"


OAUTH_CREDENTIAL = Source("credential oauth_app", ("Authorization",), new=False)
URL_USER_INFO = Source("the URL's user info", ("Authorization",), new=False)


def row(number: int, name: str) -> Source:
    """A header row as a source."""
    return Source(f"the alert's header {number}", (name,), new=True)


@pytest.mark.parametrize("spelled", ["Authorization", "authorization", "AUTHORIZATION"])
def test_a_row_setting_a_header_a_credential_sets_is_refused(spelled: str) -> None:
    """HTTP header names ignore case, and so does requests."""
    with pytest.raises(HeaderError) as refused:
        check_clashes([OAUTH_CREDENTIAL, row(1, spelled)])
    assert str(refused.value) == (
        f"Header {spelled} is set by both credential oauth_app and the alert's header 1, "
        "so the webhook isn't sent"
    )


def test_two_rows_with_one_name_are_refused() -> None:
    """Two new sources clash with each other too."""
    with pytest.raises(
        HeaderError, match="set by both the alert's header 1 and the alert's header 3"
    ):
        check_clashes([row(1, "X-Source"), row(3, "x-source")])


def test_two_old_sources_keep_the_precedence_they_had() -> None:
    """An OAuth credential and URL user info: requests sends the URL's, as it did before 2.0."""
    check_clashes([OAUTH_CREDENTIAL, URL_USER_INFO])


def test_one_source_naming_a_header_twice_is_not_a_clash() -> None:
    """An HMAC second credential whose signature and timestamp headers share a name still works."""
    check_clashes(
        [Source("credential signed", ("X-Sig", "X-Sig"), new=True), row(1, "X-Other")]
    )


def test_a_row_clashing_with_the_first_of_two_old_sources_is_refused() -> None:
    """The message names the first source that set the header."""
    with pytest.raises(
        HeaderError, match="set by both credential oauth_app and the alert's header 1"
    ):
        check_clashes([OAUTH_CREDENTIAL, URL_USER_INFO, row(1, "Authorization")])


def test_sources_setting_different_headers_pass() -> None:
    """Rows naming the automatic Content-Type and User-Agent aren't clashes: those aren't sources."""
    check_clashes(
        [
            OAUTH_CREDENTIAL,
            URL_USER_INFO,
            row(1, "X-Source"),
            row(2, "Content-Type"),
            row(3, "User-Agent"),
        ]
    )
