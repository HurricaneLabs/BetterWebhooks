"""
Scrub known secret values out of every log line.

Exception text has no fixed shape (requests, for one, quotes a bad header value
in its error message), so rather than trust every log call, each line passes
through redact() before any handler writes it. Importing this module turns it on.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

import requests
from urllib3.util import parse_url

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from loguru import logger

REDACTED = "[REDACTED]"

_secrets = set()


def register_secret(value: object) -> None:
    """Scrub ``value`` from every later log line, both raw and as repr() quotes it.

    Args:
        value: The secret. Anything other than a non-empty string is ignored.
    """
    if not isinstance(value, str):
        return
    for form in (value, value.strip()):
        # Exception messages quote values with repr(), which turns a newline into \n
        for variant in (form, repr(form)[1:-1]):
            if variant:  # an empty string would match between every character
                _secrets.add(variant)


def register_url(url: object) -> None:
    """Scrub the parts of ``url`` that can hold a secret from every later log line.

    A URL's path or query can be the secret itself (Slack's /services/T…/B…/<token>,
    a signed ?sig=…), and so can a user:password@. requests and urllib3 quote them
    in error messages the way they were sent, percent-encoded: the path and query,
    or the whole URL behind a proxy or when it won't parse. So each part is
    registered both as configured and as sent.

    Args:
        url: The URL. Anything other than a string is ignored.
    """
    if not isinstance(url, str):
        return
    forms = [url]
    try:
        forms.append(requests.Request("POST", url).prepare().url)
    except (requests.RequestException, ValueError):
        pass  # requests won't send it, and its error quotes the URL as configured
    for form in forms:
        register_secret(form)
        try:
            parts = urlsplit(form)
        except ValueError:  # an unbalanced [ in the host
            continue
        for part in (parts.path, parts.query, parts.password):
            # Registering "/" would redact every slash in every traceback
            if part != "/":
                register_secret(part)


def url_parses(url: str, name: str) -> bool:
    """Tell whether requests can read ``url``; if not, log so without quoting it.

    A raw #, /, ? or \\ in a password ends the URL's host part early, so the
    user name and the start of the password read as a host and port. urllib3
    then quotes them in its error, in a form register_url() can't predict, and
    url_host() returns them. So check a URL here before anything logs or sends
    it. requests parses with urllib3 too, and its own URL check skips a proxy
    on any scheme but http and https, so this is urllib3's check, not that one.
    Like requests, it strips leading whitespace first.

    A \\ cut doesn't always make urllib3 fail: in user:pass@word\\x@host the
    text before the \\ is a valid host, and requests would send there. Only
    urlsplit reads past a \\ to the real host, so a \\ anywhere in its host
    part is refused too. It's never valid there.

    Args:
        url: The URL.
        name: What the URL is for, as the log line names it ("webhook").

    Returns:
        True if the URL parses.
    """
    url = url.lstrip()
    try:
        parse_url(url)
        refused = "\\" in urlsplit(url).netloc
    # LocationParseError is a ValueError; urlsplit raises one on an unbalanced [
    except ValueError:
        refused = True
    if refused:
        logger.error(
            "The {} URL won't parse, so it isn't used: check its host and port, "
            "and percent-encode any #, /, ? or \\ in its user name or password",
            name,
        )
        return False
    return True


def url_host(url: str) -> str | None:
    """Return the host, and port if any, of ``url``: the one part safe to log.

    Only for a URL url_parses() accepted: in one it refuses, the "host" can be
    the user name and the start of the password. Read the way requests reads
    it, not with urlsplit, which deletes a tab or newline anywhere in the URL
    and can then find the host in what urllib3 reads as the path.

    Args:
        url: The URL.

    Returns:
        The host as urllib3 normalizes it (lower case, non-ASCII names
        IDNA-encoded), without any user:password@; None if there is none.
    """
    return parse_url(url.lstrip()).netloc


def redact(record: dict) -> None:
    """Replace every registered secret in a log record's message.

    Args:
        record: The loguru record, with its message already formatted.
    """
    message = record["message"]
    # Longest first, so a secret that contains another is replaced whole
    for secret in sorted(_secrets, key=len, reverse=True):
        message = message.replace(secret, REDACTED)
    record["message"] = message


logger.configure(patcher=redact)
