"""Tests for API counter service and web_interface_v2 compatibility shim."""
import warnings


class TestApiCounter:
    """Tests for src.api.services.api_counter."""

    def test_increment_adds_to_counter(self):
        from src.api.services.api_counter import _counts, get_api_counts, increment_api_counter
        _counts.clear()
        increment_api_counter("test_kind")
        assert get_api_counts()["test_kind"] == 1

    def test_increment_with_count(self):
        from src.api.services.api_counter import _counts, get_api_counts, increment_api_counter
        _counts.clear()
        increment_api_counter("bulk", 5)
        assert get_api_counts()["bulk"] == 5

    def test_increment_accumulates(self):
        from src.api.services.api_counter import _counts, get_api_counts, increment_api_counter
        _counts.clear()
        increment_api_counter("acc", 2)
        increment_api_counter("acc", 3)
        assert get_api_counts()["acc"] == 5

    def test_get_counts_returns_copy(self):
        from src.api.services.api_counter import _counts, get_api_counts
        _counts.clear()
        counts = get_api_counts()
        counts["injected"] = 999
        assert "injected" not in get_api_counts()


class TestWebInterfaceV2Shim:
    """Tests for the web_interface_v2 compatibility shim."""

    def test_import_emits_deprecation_warning(self):
        import importlib
        import sys
        # Force re-import to trigger warning
        sys.modules.pop("web_interface_v2", None)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            importlib.import_module("web_interface_v2")
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 1
            assert "deprecated" in str(deprecation_warnings[0].message).lower()

    def test_shim_exports_increment_api_counter(self):
        from web_interface_v2 import increment_api_counter
        assert callable(increment_api_counter)

    def test_shim_function_works(self):
        import sys
        sys.modules.pop("web_interface_v2", None)
        from src.api.services.api_counter import _counts
        _counts.clear()
        from web_interface_v2 import increment_api_counter
        increment_api_counter("shim_test", 3)
        from src.api.services.api_counter import get_api_counts
        assert get_api_counts()["shim_test"] == 3
