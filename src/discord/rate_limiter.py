"""Rate limiter using token bucket algorithm for Discord API."""

import asyncio
import time
from typing import Optional

from loguru import logger

from src.config.settings import get_settings


class RateLimiter:
    """
    Token bucket rate limiter for Discord API.

    Implements global and per-channel rate limits to prevent API throttling.
    """

    def __init__(self) -> None:
        """Initialize rate limiter with configured limits."""
        settings = get_settings()
        self.global_limit = settings.RATE_LIMIT_GLOBAL  # requests per second
        self.global_tokens = self.global_limit
        self.channel_limit = settings.RATE_LIMIT_PER_CHANNEL  # requests per second per channel
        self.channel_buckets: dict[str, dict[str, float]] = {}
        self.global_last_update = time.time()
        self._lock = asyncio.Lock()
        self._bucket_ttl_seconds = 600
        self._max_channel_buckets = 5000

    async def acquire(self, channel_id: Optional[str] = None) -> None:
        """
        Acquire a token from the bucket.

        Args:
            channel_id: Optional channel ID for per-channel rate limiting.

        Raises:
            RuntimeError: If rate limit acquisition fails after retries.
        """
        while True:
            wait_time = 0.0

            async with self._lock:
                now = time.time()
                self._prune_stale_buckets(now)

                # Refill global bucket
                global_elapsed = now - self.global_last_update
                self.global_tokens = min(
                    self.global_limit, self.global_tokens + global_elapsed * self.global_limit
                )
                self.global_last_update = now

                channel_wait = 0.0
                if channel_id:
                    bucket = self.channel_buckets.get(channel_id)
                    if bucket is None:
                        if len(self.channel_buckets) >= self._max_channel_buckets:
                            self._prune_stale_buckets(now, force=True)
                        bucket = {"tokens": float(self.channel_limit), "last_update": now}
                        self.channel_buckets[channel_id] = bucket

                    channel_elapsed = now - bucket["last_update"]
                    bucket["tokens"] = min(
                        self.channel_limit,
                        bucket["tokens"] + channel_elapsed * self.channel_limit,
                    )
                    bucket["last_update"] = now
                    if bucket["tokens"] < 1:
                        channel_wait = (1 - bucket["tokens"]) / self.channel_limit

                global_wait = 0.0
                if self.global_tokens < 1:
                    global_wait = (1 - self.global_tokens) / self.global_limit

                wait_time = max(global_wait, channel_wait)
                if wait_time <= 0:
                    self.global_tokens -= 1
                    if channel_id:
                        self.channel_buckets[channel_id]["tokens"] -= 1
                    return

            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def _prune_stale_buckets(self, now: float, force: bool = False) -> None:
        """Remove inactive channel buckets to avoid unbounded growth."""
        stale_cutoff = now - self._bucket_ttl_seconds
        to_remove = [
            channel_id
            for channel_id, bucket in self.channel_buckets.items()
            if force or bucket["last_update"] < stale_cutoff
        ]
        for channel_id in to_remove:
            self.channel_buckets.pop(channel_id, None)

    def get_available_tokens(self, channel_id: Optional[str] = None) -> dict[str, float]:
        """
        Get available tokens for debugging.

        Args:
            channel_id: Optional channel ID to check per-channel tokens.

        Returns:
            Dictionary with available global and channel tokens.
            Values are approximate and may change concurrently.
        """
        result = {"global_tokens": self.global_tokens}
        if channel_id and channel_id in self.channel_buckets:
            result["channel_tokens"] = self.channel_buckets[channel_id]["tokens"]
        return result

    async def reset(self) -> None:
        """Reset all rate limit buckets to full capacity."""
        async with self._lock:
            self.global_tokens = self.global_limit
            self.global_last_update = time.time()
            self.channel_buckets.clear()
            logger.debug("Rate limiter reset to full capacity")
