"""
Scrub known secret values out of every log line.

Exception text has no fixed shape (requests, for one, quotes a bad header value
in its error message), so rather than trust every log call, each line passes
through redact() before any handler writes it. Importing this module turns it on.
"""

import os
import sys
from urllib.parse import urlsplit

import requests

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


def url_host(url: str) -> str:
    """Return the host, and port if any, of ``url``: the one part safe to log.

    Args:
        url: The URL.

    Returns:
        The host as written in the URL, without any user:password@.
    """
    return urlsplit(url).netloc.rpartition("@")[2]


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
