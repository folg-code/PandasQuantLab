import pytest
from datetime import datetime, timezone

@pytest.fixture
def fixed_now():
    return datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)