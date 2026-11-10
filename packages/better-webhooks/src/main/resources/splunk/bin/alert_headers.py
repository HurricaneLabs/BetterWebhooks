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

HEADER_ROWS = 3

# RFC 9110 field-name: one or more tchar
_FIELD_NAME = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")


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
            header name, or a line break or NUL inside its value.
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
        if "\r" in value or "\n" in value or "\0" in value:
            raise HeaderError(
                f"Header {number} ({name}) has a line break or NUL in its value, "
                "so the webhook isn't sent: check the token it uses"
            )
        rows.append(HeaderRow(number, name, value))
    return rows
