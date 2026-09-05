"""Tests for the fixed demo reference clock."""

from app.engine.clock import DEMO_REFERENCE_TIME
from app.engine.compliance import is_within_business_hours


def test_demo_anchor_is_timezone_aware_and_within_business_hours() -> None:
    assert DEMO_REFERENCE_TIME.tzinfo is not None
    assert is_within_business_hours(DEMO_REFERENCE_TIME) is True
