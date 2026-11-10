"""Unit tests for the alert's own headers and the check that no two sources set one header."""

from __future__ import annotations

import pytest
from alert_headers import HeaderError, HeaderRow, read_header_rows


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
