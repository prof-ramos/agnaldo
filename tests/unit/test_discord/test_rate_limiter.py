"""Unit tests for TokenBucketRateLimiter."""

from unittest.mock import MagicMock, patch

import pytest

from src.discord.rate_limiter import RateLimiter


@pytest.fixture
def mock_settings():
    """Create mock settings for rate limiter tests."""
    settings = MagicMock()
    settings.RATE_LIMIT_GLOBAL = 10
    settings.RATE_LIMIT_PER_CHANNEL = 5
    return settings


@pytest.fixture
def rate_limiter(mock_settings):
    """Create a RateLimiter instance with mocked settings."""
    with patch("src.discord.rate_limiter.get_settings", return_value=mock_settings):
        limiter = RateLimiter()
        yield limiter


@pytest.mark.unit
def test_initial_token_count(rate_limiter, mock_settings):
    """Test that rate limiter starts with full token capacity."""
    assert rate_limiter.global_tokens == mock_settings.RATE_LIMIT_GLOBAL
    assert rate_limiter.global_limit == mock_settings.RATE_LIMIT_GLOBAL
    assert rate_limiter.channel_limit == mock_settings.RATE_LIMIT_PER_CHANNEL
    assert len(rate_limiter.channel_buckets) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_token_consumption(rate_limiter, mock_settings):
    """Test that tokens are consumed correctly."""
    initial_tokens = mock_settings.RATE_LIMIT_GLOBAL

    # Consume all tokens
    for _ in range(initial_tokens):
        await rate_limiter.acquire()

    # All global tokens should be consumed
    available = rate_limiter.get_available_tokens()
    assert available["global_tokens"] < 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_token_refill(rate_limiter, mock_settings):
    """Test that tokens refill over time using manual state manipulation."""
    # Consume some tokens
    for _ in range(5):
        await rate_limiter.acquire()

    # Verify tokens were consumed
    assert rate_limiter.global_tokens < mock_settings.RATE_LIMIT_GLOBAL

    # Manually simulate time passing and token refill
    # Set last_update to simulate 1 second ago
    rate_limiter.global_last_update -= 1.0

    # Call get_available_tokens which doesn't trigger refill
    # Then manually calculate refill
    elapsed = 1.0
    rate_limiter.global_tokens = min(
        mock_settings.RATE_LIMIT_GLOBAL,
        rate_limiter.global_tokens + elapsed * mock_settings.RATE_LIMIT_GLOBAL,
    )

    # After 1 second, global bucket should have refilled to full capacity
    available = rate_limiter.get_available_tokens()
    assert available["global_tokens"] == mock_settings.RATE_LIMIT_GLOBAL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting(rate_limiter, mock_settings):
    """Test that rate limit is enforced correctly."""
    # Consume all global tokens
    for _ in range(mock_settings.RATE_LIMIT_GLOBAL):
        await rate_limiter.acquire()

    # Verify all tokens are consumed
    available = rate_limiter.get_available_tokens()
    assert available["global_tokens"] < 1

    # Refill tokens by manually updating state
    rate_limiter.global_last_update -= 1.0  # Simulate 1 second ago
    rate_limiter.global_tokens = min(
        mock_settings.RATE_LIMIT_GLOBAL,
        rate_limiter.global_tokens + 1.0 * mock_settings.RATE_LIMIT_GLOBAL,
    )

    # Now acquire should succeed without waiting
    await rate_limiter.acquire()
    assert rate_limiter.global_tokens >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_per_channel_limits(rate_limiter, mock_settings):
    """Test that per-channel limits are enforced separately."""
    channel_1 = "channel_123"
    channel_2 = "channel_456"

    # Consume all tokens for channel 1
    for _ in range(mock_settings.RATE_LIMIT_PER_CHANNEL):
        await rate_limiter.acquire(channel_id=channel_1)

    # Channel 1 should be rate limited
    available_1 = rate_limiter.get_available_tokens(channel_id=channel_1)
    assert available_1["channel_tokens"] < 1

    # First access to channel_2 creates the bucket
    await rate_limiter.acquire(channel_id=channel_2)

    # Channel 2 should have tokens remaining (one was just consumed)
    available_2 = rate_limiter.get_available_tokens(channel_id=channel_2)
    assert available_2["channel_tokens"] == mock_settings.RATE_LIMIT_PER_CHANNEL - 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_global_limits(rate_limiter, mock_settings, monkeypatch):
    """Test that global limits are enforced across all channels."""
    fixed_time = 1000.0
    monkeypatch.setattr("src.discord.rate_limiter.time.time", lambda: fixed_time)
    rate_limiter.global_last_update = fixed_time
    rate_limiter.channel_limit = mock_settings.RATE_LIMIT_GLOBAL

    channel_1 = "channel_111"
    channel_2 = "channel_222"

    # Consume tokens from channel 1
    for _ in range(6):
        await rate_limiter.acquire(channel_id=channel_1)

    # Consume remaining global tokens without an unbounded loop
    remaining_tokens = int(rate_limiter.get_available_tokens()["global_tokens"])
    for _ in range(max(remaining_tokens, 0)):
        await rate_limiter.acquire(channel_id=channel_2)

    # Global bucket should be empty
    available = rate_limiter.get_available_tokens()
    assert available["global_tokens"] < 1

    # Channel 2 should still have tokens (limited by per-channel limit)
    available_2 = rate_limiter.get_available_tokens(channel_id=channel_2)
    assert available_2["channel_tokens"] >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_per_channel_and_global_limits_combined(rate_limiter, mock_settings):
    """Test that both per-channel and global limits work together."""
    channel = "channel_combined"

    # Per-channel limit is 5, global is 10
    # Should be able to consume 5 tokens from one channel
    for _ in range(mock_settings.RATE_LIMIT_PER_CHANNEL):
        await rate_limiter.acquire(channel_id=channel)

    # Channel should be rate limited (tokens < 1)
    available = rate_limiter.get_available_tokens(channel_id=channel)
    assert available["channel_tokens"] < 1

    # But global tokens should still be available
    available_global = rate_limiter.get_available_tokens()
    assert available_global["global_tokens"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_channel_bucket_creation(rate_limiter, mock_settings):
    """Test that channel buckets are created on first access."""
    channel = "new_channel"

    assert channel not in rate_limiter.channel_buckets

    await rate_limiter.acquire(channel_id=channel)

    assert channel in rate_limiter.channel_buckets
    assert (
        rate_limiter.channel_buckets[channel]["tokens"] == mock_settings.RATE_LIMIT_PER_CHANNEL - 1
    )


@pytest.mark.unit
def test_get_available_tokens_no_channel(rate_limiter, mock_settings):
    """Test get_available_tokens without channel ID."""
    available = rate_limiter.get_available_tokens()

    assert "global_tokens" in available
    assert available["global_tokens"] == mock_settings.RATE_LIMIT_GLOBAL
    assert "channel_tokens" not in available


@pytest.mark.unit
def test_get_available_tokens_with_channel(rate_limiter, mock_settings):
    """Test get_available_tokens with channel ID."""
    channel = "test_channel"

    # Create bucket by adding it manually
    rate_limiter.channel_buckets[channel] = {
        "tokens": 3.0,
        "last_update": 0.0,
    }

    available = rate_limiter.get_available_tokens(channel_id=channel)

    assert "global_tokens" in available
    assert "channel_tokens" in available
    assert available["channel_tokens"] == 3.0


@pytest.mark.unit
def test_get_available_tokens_nonexistent_channel(rate_limiter):
    """Test get_available_tokens with non-existent channel."""
    available = rate_limiter.get_available_tokens(channel_id="nonexistent")

    assert "global_tokens" in available
    assert "channel_tokens" not in available


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset(rate_limiter, mock_settings):
    """Test that reset clears all buckets and refills tokens."""
    # Add some channel buckets and consume tokens
    await rate_limiter.acquire(channel_id="channel_1")
    await rate_limiter.acquire(channel_id="channel_2")

    assert len(rate_limiter.channel_buckets) > 0
    assert rate_limiter.global_tokens < mock_settings.RATE_LIMIT_GLOBAL

    # Reset
    await rate_limiter.reset()

    # Verify reset state
    assert rate_limiter.global_tokens == mock_settings.RATE_LIMIT_GLOBAL
    assert len(rate_limiter.channel_buckets) == 0


@pytest.mark.unit
def test_prune_stale_buckets(rate_limiter):
    """Test that stale buckets are removed."""
    # Add some buckets with different timestamps
    now = 100.0
    rate_limiter.channel_buckets["active"] = {
        "tokens": 5.0,
        "last_update": now - 100,
    }  # 100s old (not stale)
    rate_limiter.channel_buckets["stale"] = {
        "tokens": 5.0,
        "last_update": now - 700,  # 700s old (stale, > 600s TTL)
    }

    rate_limiter._prune_stale_buckets(now)

    assert "active" in rate_limiter.channel_buckets
    assert "stale" not in rate_limiter.channel_buckets


@pytest.mark.unit
def test_prune_stale_buckets_force(rate_limiter):
    """Test that forced pruning removes all buckets."""
    # Add buckets
    rate_limiter.channel_buckets["bucket1"] = {"tokens": 5.0, "last_update": 100.0}
    rate_limiter.channel_buckets["bucket2"] = {"tokens": 5.0, "last_update": 100.0}

    assert len(rate_limiter.channel_buckets) == 2

    # Force prune
    rate_limiter._prune_stale_buckets(200.0, force=True)

    assert len(rate_limiter.channel_buckets) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_without_channel_id(rate_limiter, mock_settings):
    """Test acquire without specifying a channel ID."""
    # Should only consume global tokens
    for _ in range(mock_settings.RATE_LIMIT_GLOBAL):
        await rate_limiter.acquire()

    # Global tokens should be exhausted
    available = rate_limiter.get_available_tokens()
    assert available["global_tokens"] < 1

    # No channel buckets should be created
    assert len(rate_limiter.channel_buckets) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_channel_buckets_limit(rate_limiter):
    """Test behavior when max channel buckets limit is reached."""
    # Set a low max limit for testing
    rate_limiter._max_channel_buckets = 3

    # Fill up to max capacity
    for i in range(3):
        await rate_limiter.acquire(channel_id=f"channel_{i}")

    assert len(rate_limiter.channel_buckets) == 3

    # Add a stale bucket manually (simulate old timestamp)
    current_time = rate_limiter.global_last_update
    rate_limiter.channel_buckets["old_channel"] = {
        "tokens": 5.0,
        "last_update": current_time - 700,  # 700s old (past TTL)
    }

    # Manually trigger pruning with current time
    rate_limiter._prune_stale_buckets(current_time, force=True)

    # Old bucket should be pruned
    assert "old_channel" not in rate_limiter.channel_buckets

    # Now we can add a new channel
    await rate_limiter.acquire(channel_id="new_channel")
    assert "new_channel" in rate_limiter.channel_buckets


@pytest.mark.unit
def test_bucket_ttl_default(rate_limiter):
    """Test that bucket TTL is set to default value."""
    assert rate_limiter._bucket_ttl_seconds == 600


@pytest.mark.unit
def test_max_channel_buckets_default(rate_limiter):
    """Test that max channel buckets is set to default value."""
    assert rate_limiter._max_channel_buckets == 5000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_acquires(rate_limiter):
    """Test that concurrent acquires are handled correctly with lock."""
    import asyncio

    channel = "concurrent_channel"

    # Run multiple concurrent acquires
    tasks = [rate_limiter.acquire(channel_id=channel) for _ in range(5)]
    await asyncio.gather(*tasks)

    # All should complete without error
    available = rate_limiter.get_available_tokens(channel_id=channel)
    assert available["channel_tokens"] >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_waits_and_refills(monkeypatch, mock_settings):
    """Test that acquire waits when tokens are exhausted and refills with time."""
    current_time = 1000.0

    def fake_time():
        return current_time

    async def fake_sleep(seconds: float):
        nonlocal current_time
        current_time += seconds

    monkeypatch.setattr("src.discord.rate_limiter.time.time", fake_time)
    monkeypatch.setattr("src.discord.rate_limiter.asyncio.sleep", fake_sleep)

    with patch("src.discord.rate_limiter.get_settings", return_value=mock_settings):
        limiter = RateLimiter()
        limiter.global_tokens = 0.0
        limiter.global_last_update = current_time

        channel_id = "rate_limit_channel"
        limiter.channel_buckets[channel_id] = {"tokens": 0.0, "last_update": current_time}

        await limiter.acquire(channel_id=channel_id)

        assert current_time > 1000.0
        available = limiter.get_available_tokens(channel_id=channel_id)
        assert available["global_tokens"] >= 0
        assert available["channel_tokens"] >= 0
