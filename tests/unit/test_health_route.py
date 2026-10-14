"""Unit tests for api/routes/health.py — issue #62 regression."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestHealthRoute:
    """Regression tests for issue #62: Redis probe uses settings.redis_url."""

    @pytest.mark.asyncio
    async def test_redis_probe_uses_from_url(self):
        """Redis probe must call Redis.from_url, not access redis_host/redis_port."""
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True

        with (
            patch("redis.Redis.from_url", return_value=mock_redis_instance) as mock_from_url,
            patch("api.routes.health.get_db"),
            patch("core.config.settings") as mock_settings,
        ):

            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_settings.vector_db_url = "http://localhost:8001"

            # Import after patching so the patched settings is used
            from api.routes.health import health_check

            # Provide a mock db dependency
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=None)

            await health_check(db=mock_db)

            # The fix: from_url must have been called with settings.redis_url
            mock_from_url.assert_called_once_with(mock_settings.redis_url, decode_responses=True)
            mock_redis_instance.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_probe_no_redis_host_attribute(self):
        """Settings must not have redis_host; accessing it raised the original bug."""
        from core.config import settings

        assert not hasattr(
            settings, "redis_host"
        ), "settings.redis_host exists — the fix may be incomplete or Settings changed"
        assert not hasattr(
            settings, "redis_port"
        ), "settings.redis_port exists — the fix may be incomplete or Settings changed"
        assert hasattr(settings, "redis_url"), "settings.redis_url must exist for the probe to use"
