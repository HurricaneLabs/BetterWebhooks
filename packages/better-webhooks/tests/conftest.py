"""Shared fixtures for the alert action tests.

The scripts under ``bin/`` only run inside Splunk: ``better_webhook.py`` imports
``splunk.rest`` and ``splunk.clilib`` at module level. Those two modules are
stubbed here, before any test imports a script, so the tests run on plain Python.
"""

from __future__ import annotations

import io
import json
import runpy
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Callable

import pytest

BIN = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "main"
    / "resources"
    / "splunk"
    / "bin"
)

# The vendored loguru the app ships, not one from the test environment, so the
# tests and the scripts share one logger.
sys.path.insert(0, str(BIN.parent / "lib"))

from loguru import logger  # noqa: E402


def _stub_splunk() -> None:
    """Install fake ``splunk.rest`` and ``splunk.clilib.cli_common`` modules."""
    splunk = types.ModuleType("splunk")
    rest = types.ModuleType("splunk.rest")
    clilib = types.ModuleType("splunk.clilib")
    cli_common = types.ModuleType("splunk.clilib.cli_common")

    rest.simpleRequest = None  # set per test by the run_alert fixture
    cli_common.getConfStanza = lambda conf, stanza: {"proxy": ""}

    splunk.rest = rest
    splunk.clilib = clilib
    clilib.cli_common = cli_common
    sys.modules.update(
        {
            "splunk": splunk,
            "splunk.rest": rest,
            "splunk.clilib": clilib,
            "splunk.clilib.cli_common": cli_common,
        }
    )


_stub_splunk()


@pytest.fixture(autouse=True)
def _isolate_logging() -> Iterator[None]:
    """Give each test a logger with no handlers and no remembered secrets."""
    logger.remove()
    redaction = sys.modules.get("log_redaction")
    if redaction is not None:
        redaction._secrets.clear()
    yield
    logger.remove()


@pytest.fixture
def log_lines() -> Iterator[list[str]]:
    """Collect every log line, at DEBUG and up, as the alert action would write it."""
    lines: list[str] = []
    logger.add(lines.append, format="{level} {message}", level="DEBUG")
    yield lines


@pytest.fixture
def run_alert(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> Callable[..., AlertRun]:
    """Run ``better_webhook.py --execute`` the way Splunk does, in this process.

    The settings go in on stdin, the credential comes back from the stubbed
    ``storage/passwords`` call, and the log is whatever the script writes to stderr.
    """

    def run(settings: dict, credential: dict | None = None) -> AlertRun:
        def simple_request(url: str, getargs: dict, sessionKey: str) -> tuple:
            content = {
                "entry": [{"content": {"clear_password": json.dumps(credential)}}]
            }
            return {"status": "200"}, json.dumps(content)

        monkeypatch.setattr(sys.modules["splunk.rest"], "simpleRequest", simple_request)
        monkeypatch.setattr(sys, "argv", [str(BIN / "better_webhook.py"), "--execute"])
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(settings)))

        exit_code = 0
        try:
            runpy.run_path(str(BIN / "better_webhook.py"), run_name="__main__")
        except SystemExit as exc:
            exit_code = exc.code
        return AlertRun(exit_code=exit_code, log=capsys.readouterr().err)

    return run


class AlertRun:
    """What one alert action run left behind: its exit code and its log."""

    def __init__(self, exit_code: object, log: str) -> None:
        """Store the exit code and the captured stderr log."""
        self.exit_code = exit_code
        self.log = log
