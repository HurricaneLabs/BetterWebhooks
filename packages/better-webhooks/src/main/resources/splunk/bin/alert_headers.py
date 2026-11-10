"""
Headers an alert sets itself, and the check that no two sources set one header.

An alert can set up to three headers of its own, each a name box and a value
box. Splunk fills tokens like $result.host$ into them before this script runs,
so a value can hold anything a search result holds, line breaks included. A
line break would start a header the alert's author never wrote, so a value
holding one is refused, never sent.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from requests.utils import get_auth_from_url

HEADER_ROWS = 3

# RFC 9110 field-name: one or more tchar
_FIELD_NAME = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")

# What a value may hold: tab, printable ASCII and Latin-1. requests sends
# headers as Latin-1, so anything above U+00FF can't go out, and a control
# character (CR, LF, NUL and the rest) or DEL could break the header apart.
_BAD_VALUE_CHAR = re.compile(r"[^\t\x20-\x7e\x80-\xff]")

# requests sets these from the body and the connection itself; a second copy
# would garble the request's framing. Host stays allowed.
_FRAMING_HEADERS = ("content-length", "transfer-encoding", "connection")


class HeaderError(Exception):
    """The alert's headers can't be sent as configured. The message quotes no header value."""


class HeaderRow(NamedTuple):
    """One of the alert's own headers, numbered as the form shows it."""

    number: int
    name: str
    value: str


def read_header_rows(configuration: dict) -> list[HeaderRow]:
    """Read the alert's header rows, trimmed, skipping the empty ones.

    Args:
        configuration: The alert's parameters, as Splunk passes them.

    Returns:
        The rows that have a name, in form order.

    Raises:
        HeaderError: A row has a value but no name, a name that isn't a
            header name or is one requests sets itself, or a character a
            header can't carry inside its value: a line break or other
            control character, DEL, or anything outside Latin-1.
    """
    rows = []
    for number in range(1, HEADER_ROWS + 1):
        name = (configuration.get(f"header_{number}_name") or "").strip()
        value = (configuration.get(f"header_{number}_value") or "").strip()
        if not name:
            if value:
                raise HeaderError(
                    f"Header {number} has a value but no name, so the webhook isn't sent"
                )
            continue
        if not _FIELD_NAME.fullmatch(name):
            raise HeaderError(
                f"Header {number}'s name isn't a valid header name, "
                "so the webhook isn't sent"
            )
        if name.lower() in _FRAMING_HEADERS:
            raise HeaderError(
                f"Header {number} ({name}) is one the alert action sets itself, "
                "so the webhook isn't sent: remove the row"
            )
        if _BAD_VALUE_CHAR.search(value):
            raise HeaderError(
                f"Header {number} ({name}) has a line break or another character "
                "a header can't carry in its value, so the webhook isn't sent: "
                "check the token it uses"
            )
        rows.append(HeaderRow(number, name, value))
    return rows


class Source(NamedTuple):
    """Something that sets headers: a credential, the URL's user info, or a header row."""

    label: str  # as the log names it: "credential oauth_app", "the alert's header 2"
    names: tuple[str, ...]
    new: bool  # a header row or the second credential: only these can clash


def stored_name(credential_name: str) -> str:
    """Name a credential as the credentials page shows it.

    A saved alert passes the storage key, better_webhooks:<name>:, and
    | sendalert the bare name.
    """
    return credential_name.removeprefix("better_webhooks:").removesuffix(":")


def credential_claims(credential: dict) -> tuple[str, ...]:
    """Name the headers a stored credential sets, without building them.

    Reads stored fields only, so the clash check can run before an OAuth token
    request or an HMAC signature. An unknown type claims nothing: the alert
    action refuses it later anyway.
    """
    kind = credential.get("type")
    if kind in ("basic", "oauth"):
        names = ["Authorization"]
    elif kind == "header":
        names = [credential.get("header_name") or ""]
    elif kind == "hmac":
        names = [
            credential.get("hmac_sig_header") or "",
            credential.get("hmac_time_header") or "",
        ]
    else:
        names = []
    return tuple(name.strip() for name in names if name.strip())


def url_claims(url: str) -> tuple[str, ...]:
    """Name the header a URL's user info sets: Authorization, when requests would send it.

    Reads the user info the way requests does, so a user name with no
    password, which requests doesn't send, claims nothing. Strips leading
    whitespace first, as requests does: urlsplit on Python 3.9 doesn't.
    """
    try:
        user_info = get_auth_from_url(url.lstrip())
    except ValueError:  # an unbalanced [; url_parses() refuses the URL later
        return ()
    return ("Authorization",) if any(user_info) else ()


def check_clashes(sources: list[Source]) -> None:
    """Refuse two sources that set one header, when either of them is new in 2.0.0.

    Names compare case-insensitively, as HTTP and requests compare them. A
    source naming one header twice never clashes with itself, and two pre-2.0
    sources keep the precedence they had, so no existing alert changes.

    Args:
        sources: Every source of headers, in the order the alert applies them.

    Raises:
        HeaderError: Naming the header and both sources, never a value.
    """
    first: dict[str, Source] = {}
    for source in sources:
        for name in source.names:
            earlier = first.setdefault(name.lower(), source)
            if earlier is not source and (earlier.new or source.new):
                raise HeaderError(
                    f"Header {name} is set by both {earlier.label} and "
                    f"{source.label}, so the webhook isn't sent"
                )
