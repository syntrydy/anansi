"""
Pytest configuration.
Sets up global fixtures for the test suite.
"""

import pytest

@pytest.fixture
def sample_fixture() -> str:
    """Sample fixture for testing."""
    return "sample"
