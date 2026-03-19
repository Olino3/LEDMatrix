"""Tests for BACK-007: SSE streaming endpoints migration."""

import asyncio
import json

import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestStreamsRouterStructure:
    """Tests for the streams router module structure."""

    def test_router_is_importable(self):
        from src.api.routers.streams import router

        assert router is not None

    def test_router_has_prefix(self):
        from src.api.routers.streams import router

        assert router.prefix == "/stream"

    def test_router_has_streams_tag(self):
        from src.api.routers.streams import router

        assert "streams" in router.tags

    def test_router_has_three_routes(self):
        from src.api.routers.streams import router

        paths = [r.path for r in router.routes]
        assert "/stream/stats" in paths
        assert "/stream/display" in paths
        assert "/stream/logs" in paths


@pytest.mark.unit
class TestStatsGenerator:
    """Tests for the stats async generator helper."""

    def test_stats_event_yields_dict_with_expected_keys(self):
        from src.api.routers.streams import _generate_stats_event

        result = asyncio.run(_generate_stats_event())
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "cpu_percent" in result
        assert "memory_used_percent" in result
        assert "cpu_temp" in result
        assert "service_active" in result
        assert "disk_used_percent" in result
        assert "uptime" in result

    def test_stats_event_values_are_numeric(self):
        from src.api.routers.streams import _generate_stats_event

        result = asyncio.run(_generate_stats_event())
        assert isinstance(result["cpu_percent"], (int, float))
        assert isinstance(result["memory_used_percent"], (int, float))
        assert isinstance(result["cpu_temp"], (int, float))
        assert isinstance(result["timestamp"], (int, float))

    @patch("src.api.routers.streams.psutil", None)
    def test_stats_event_handles_missing_psutil(self):
        """When psutil is unavailable, values default to 0."""
        from src.api.routers.streams import _generate_stats_event

        result = asyncio.run(_generate_stats_event())
        assert result["cpu_percent"] == 0
        assert result["memory_used_percent"] == 0

    def test_stats_event_service_active_is_bool(self):
        from src.api.routers.streams import _generate_stats_event

        result = asyncio.run(_generate_stats_event())
        assert isinstance(result["service_active"], bool)


@pytest.mark.unit
class TestDisplayGenerator:
    """Tests for the display preview async generator helper."""

    def test_display_event_returns_dict_with_expected_keys(self):
        from src.api.routers.streams import _generate_display_event

        result = asyncio.run(
            _generate_display_event(config_manager=None)
        )
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "width" in result
        assert "height" in result
        assert "image" in result

    @patch("src.api.routers.streams.SNAPSHOT_PATH", "/tmp/nonexistent_snapshot.png")
    def test_display_event_no_snapshot_returns_null_image(self):
        """When snapshot file doesn't exist, image should be None."""
        from src.api.routers.streams import _generate_display_event

        result = asyncio.run(
            _generate_display_event(config_manager=None)
        )
        assert result["image"] is None

    def test_display_event_default_dimensions(self):
        """Without config, defaults to 128x64."""
        from src.api.routers.streams import _generate_display_event

        result = asyncio.run(
            _generate_display_event(config_manager=None)
        )
        assert result["width"] == 128
        assert result["height"] == 64

    def test_display_event_reads_dimensions_from_config(self):
        """Config manager provides display dimensions."""
        from unittest.mock import MagicMock
        from src.api.routers.streams import _generate_display_event

        mock_cm = MagicMock()
        mock_cm.load_config.return_value = {
            "display": {
                "hardware": {
                    "cols": 64,
                    "chain_length": 3,
                    "rows": 32,
                    "parallel": 2,
                }
            }
        }
        result = asyncio.run(
            _generate_display_event(config_manager=mock_cm)
        )
        assert result["width"] == 192  # 64 * 3
        assert result["height"] == 64  # 32 * 2


@pytest.mark.unit
class TestLogsGenerator:
    """Tests for the logs async generator helper."""

    def test_logs_event_returns_dict_with_expected_keys(self):
        from src.api.routers.streams import _generate_logs_event

        result = asyncio.run(
            _generate_logs_event()
        )
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "logs" in result

    def test_logs_event_handles_missing_journalctl(self):
        """On non-Pi systems where journalctl may fail, should not raise."""
        from src.api.routers.streams import _generate_logs_event

        result = asyncio.run(
            _generate_logs_event()
        )
        assert isinstance(result["logs"], str)
        assert len(result["logs"]) > 0

    def test_logs_event_timestamp_is_numeric(self):
        from src.api.routers.streams import _generate_logs_event

        result = asyncio.run(
            _generate_logs_event()
        )
        assert isinstance(result["timestamp"], (int, float))


@pytest.mark.unit
class TestStreamGeneratorsYieldJSON:
    """Verify the infinite generators yield valid JSON strings."""

    def test_stats_stream_yields_json(self):
        from src.api.routers.streams import _stats_stream

        async def _get_first():
            async for item in _stats_stream():
                return item

        result = asyncio.run(_get_first())
        data = json.loads(result)
        assert "timestamp" in data
        assert "cpu_percent" in data

    def test_display_stream_yields_json(self):
        from src.api.routers.streams import _display_stream

        async def _get_first():
            async for item in _display_stream(config_manager=None):
                return item

        result = asyncio.run(_get_first())
        data = json.loads(result)
        assert "width" in data
        assert "image" in data

    def test_logs_stream_yields_json(self):
        from src.api.routers.streams import _logs_stream

        async def _get_first():
            async for item in _logs_stream():
                return item

        result = asyncio.run(_get_first())
        data = json.loads(result)
        assert "logs" in data


@pytest.mark.unit
class TestStreamEndpointsRegistered:
    """Verify SSE endpoints are wired into the FastAPI app."""

    @patch("src.api.main.init_services")
    @patch("src.api.main.shutdown_services")
    def test_stream_routes_are_registered_on_app(self, mock_sd, mock_init):
        from src.api.main import create_app

        app = create_app()
        route_paths = [r.path for r in app.routes]
        assert "/api/v3/stream/stats" in route_paths
        assert "/api/v3/stream/display" in route_paths
        assert "/api/v3/stream/logs" in route_paths


@pytest.mark.unit
class TestStreamModuleUsesAsyncPatterns:
    """Verify the module uses async patterns, not blocking calls."""

    def test_no_time_sleep_in_module(self):
        """streams.py must not use blocking time.sleep()."""
        import inspect
        import src.api.routers.streams as mod

        source = inspect.getsource(mod)
        assert "time.sleep" not in source

    def test_uses_asyncio_sleep(self):
        """streams.py must use asyncio.sleep()."""
        import inspect
        import src.api.routers.streams as mod

        source = inspect.getsource(mod)
        assert "asyncio.sleep" in source

    def test_uses_event_source_response(self):
        """streams.py must use sse-starlette's EventSourceResponse."""
        import inspect
        import src.api.routers.streams as mod

        source = inspect.getsource(mod)
        assert "EventSourceResponse" in source
