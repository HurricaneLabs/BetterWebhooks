"""
Scrub known secret values out of every log line.

Exception text has no fixed shape (requests, for one, quotes a bad header value
in its error message), so rather than trust every log call, each line passes
through redact() before any handler writes it. Importing this module turns it on.
"""

import os
import sys

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
