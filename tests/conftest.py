import pytest
from app import limiter


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Reset in-memory rate limit counters before each test."""
    limiter.reset()
    yield
