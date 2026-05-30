"""Tests for Jablotron config flow helpers."""

from __future__ import annotations

import pytest

from custom_components.jablotron.config_flow import (
    InvalidDeviceMappingsError,
    _format_device_mappings,
    _format_sections,
    _parse_device_mappings,
    _parse_sections,
)


def test_parse_sections_removes_duplicates_and_whitespace() -> None:
    """Test parsing configured sections."""
    assert _parse_sections("1, 2,1, 3 ") == [1, 2, 3]


@pytest.mark.parametrize("value", ["", "0", "-1", "one"])
def test_parse_sections_rejects_invalid_values(value: str) -> None:
    """Test invalid configured sections."""
    with pytest.raises(ValueError):
        _parse_sections(value)


def test_format_sections() -> None:
    """Test formatting configured sections."""
    assert _format_sections([1, 2, 3]) == "1,2,3"


def test_parse_device_mappings() -> None:
    """Test parsing PRFSTATE device mappings."""
    assert _parse_device_mappings(
        '{"0":{"name":"Front Door","device_class":"door"},'
        '"5":{"name":"Hall Motion"}}'
    ) == {
        "0": {"name": "Front Door", "device_class": "door"},
        "5": {"name": "Hall Motion"},
    }


@pytest.mark.parametrize(
    "value",
    [
        "[]",
        '{"zero":{"name":"Front Door"}}',
        '{"0":{}}',
        '{"0":{"name":""}}',
        '{"0":{"name":"Front Door","device_class":""}}',
    ],
)
def test_parse_device_mappings_rejects_invalid_values(value: str) -> None:
    """Test invalid PRFSTATE device mappings."""
    with pytest.raises(InvalidDeviceMappingsError):
        _parse_device_mappings(value)


def test_format_device_mappings() -> None:
    """Test formatting PRFSTATE device mappings."""
    assert _format_device_mappings({"0": {"name": "Front Door"}}) == (
        '{\n  "0": {\n    "name": "Front Door"\n  }\n}'
    )
