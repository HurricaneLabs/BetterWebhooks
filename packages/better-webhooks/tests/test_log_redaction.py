"""Tests for the URL check that runs before anything logs or sends a URL."""

import pytest
from log_redaction import url_parses

PASSWORD_HEAD = "SEKRET-password-head-31f8"
PASSWORD_TAIL = "SEKRET-password-tail-d27a"


# A leading space reaches the alert action only from a quoted sendalert
# argument, and the alert's HTTPS check lets it through only on Python 3.11+,
# so this is checked here rather than end to end. Each case fails on one
# urllib3 version if the check reads the URL as written instead of as
# requests sends it, with the leading space stripped.
@pytest.mark.parametrize(
    ("url", "parses"),
    [
        # urllib3 2.8 reads " https" as a host with a space in it
        pytest.param(" https://hooks.example.com/x", True, id="valid"),
        # urllib3 2.6.3 reads " https" as the host and never sees the password
        pytest.param(
            f" https://svc:{PASSWORD_HEAD}#{PASSWORD_TAIL}@hooks.example.com/x",
            False,
            id="password-cut-short",
        ),
    ],
)
def test_a_url_with_a_leading_space_is_checked_as_requests_sends_it(
    url: str, parses: bool, log_lines: list[str]
) -> None:
    """requests strips a URL's leading whitespace before it parses it, so the check must too."""
    assert url_parses(url, "webhook") is parses
    for secret in (PASSWORD_HEAD, PASSWORD_TAIL):
        assert not any(secret in line for line in log_lines)


@pytest.mark.parametrize(
    ("url", "parses"),
    [
        # Past the host, both parsers agree: requests sends it percent-encoded
        pytest.param("https://hooks.example.com/a\\b", True, id="backslash-in-path"),
        pytest.param(
            "https://hooks.example.com/x?q=a\\b", True, id="backslash-in-query"
        ),
        # urllib3 encodes it, but urlsplit raises on it
        pytest.param(
            "https://svc:pa[ss@hooks.example.com/x", False, id="bracket-in-password"
        ),
    ],
)
def test_a_backslash_is_refused_only_before_the_path(url: str, parses: bool) -> None:
    """A \\ ends urllib3's host part but not urlsplit's; after the host it's just encoded."""
    assert url_parses(url, "webhook") is parses


@pytest.mark.parametrize(
    ("url", "parses"),
    [
        # Teams webhook URLs carry an @ in the path, with no user info
        pytest.param(
            "https://example.webhook.office.com/webhookb2/a@b/IncomingWebhook/c/d",
            True,
            id="at-in-path-no-user-info",
        ),
        pytest.param("https://svc:pw@hooks.example.com/x", True, id="user-info"),
        pytest.param(
            "https://svc:pw@hooks.example.com/x?to=a%40b",
            True,
            id="user-info-and-encoded-at-in-query",
        ),
        # Refused even when meant: the URL reads the same as a password cut short
        pytest.param(
            "https://svc:pw@hooks.example.com/a@b", False, id="user-info-and-at-in-path"
        ),
        pytest.param(
            "https://svc:pw@hooks.example.com/x?to=a@b",
            False,
            id="user-info-and-at-in-query",
        ),
        pytest.param("https://hooks.example.com/x#a@b", False, id="at-in-fragment"),
        # urllib3 reads an empty user info as none at all
        pytest.param(
            "https://@hooks.example.com/a@b", False, id="empty-user-info-and-at-in-path"
        ),
    ],
)
def test_an_at_after_the_host_is_refused_where_it_could_end_the_user_info(
    url: str, parses: bool
) -> None:
    """Both parsers split user info at its last @, so a cut ahead of one moves the host."""
    assert url_parses(url, "webhook") is parses
