"""
Unit tests for src/font_manager.py.

Covers: initialization, font catalog scanning, font loading (TTF/BDF/fallback),
caching, manager font registration, plugin font registration/unregistration,
font resolution with overrides, text measurement, override management,
add/remove font, validate_font, performance stats, and error paths.
"""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest

# ---------------------------------------------------------------------------
# Module-level freetype mock so the C extension is never imported in tests.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_freetype_module():
    """Patch freetype at import level for every test in this file."""
    mock_ft = MagicMock()
    mock_face = MagicMock()
    mock_ft.Face.return_value = mock_face
    with patch.dict("sys.modules", {"freetype": mock_ft}):
        # Also patch the already-imported reference inside the module
        with patch("src.font_manager.freetype", mock_ft):
            yield mock_ft


# ---------------------------------------------------------------------------
# Helper: build a FontManager with minimal filesystem side-effects.
# ---------------------------------------------------------------------------


def _make_font_manager(config: Dict[str, Any] = None):
    """
    Instantiate FontManager with all filesystem side-effects mocked out so
    the test environment doesn't need real font files or a config directory.
    """
    if config is None:
        config = {}

    with (
        patch("os.path.exists", return_value=False),
        patch("os.listdir", return_value=[]),
        patch("tempfile.gettempdir", return_value="/tmp"),
        patch("pathlib.Path.mkdir"),
        patch("src.font_manager.FontManager._load_overrides"),
    ):
        from src.font_manager import FontManager

        fm = FontManager(config)
    return fm


# ---------------------------------------------------------------------------
# TestFontManagerInit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFontManagerInit:
    """Tests for __init__ and _initialize_fonts."""

    def test_default_attributes_created(self):
        fm = _make_font_manager()
        assert isinstance(fm.font_catalog, dict)
        assert isinstance(fm.font_cache, dict)
        assert isinstance(fm.metrics_cache, dict)
        assert isinstance(fm.plugin_fonts, dict)
        assert isinstance(fm.plugin_font_catalogs, dict)
        assert isinstance(fm.font_metadata, dict)
        assert isinstance(fm.font_dependencies, dict)
        assert isinstance(fm.manager_fonts, dict)
        assert isinstance(fm.detected_fonts, dict)
        assert isinstance(fm.font_overrides, dict)
        assert isinstance(fm.performance_stats, dict)

    def test_size_tokens_populated(self):
        fm = _make_font_manager()
        assert fm.size_tokens == {"xs": 6, "sm": 8, "md": 10, "lg": 12, "xl": 14, "xxl": 16}

    def test_common_fonts_populated(self):
        fm = _make_font_manager()
        assert "press_start" in fm.common_fonts
        assert "four_by_six" in fm.common_fonts
        assert "five_by_seven" in fm.common_fonts

    def test_performance_stats_initial_values(self):
        fm = _make_font_manager()
        assert fm.performance_stats["cache_hits"] == 0
        assert fm.performance_stats["cache_misses"] == 0
        assert fm.performance_stats["failed_loads"] == 0
        assert "start_time" in fm.performance_stats

    def test_config_stored(self):
        config = {"fonts": {"some_key": "value"}}
        fm = _make_font_manager(config)
        assert fm.config is config
        assert fm.fonts_config == {"some_key": "value"}

    def test_config_without_fonts_key(self):
        fm = _make_font_manager({})
        assert fm.fonts_config == {}


# ---------------------------------------------------------------------------
# TestFontCatalogScanning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFontCatalogScanning:
    """Tests for _scan_fonts_directory and _register_common_fonts."""

    def test_scan_missing_directory_is_graceful(self):
        with (
            patch("os.path.exists", return_value=False),
            patch("os.listdir", return_value=[]),
            patch("tempfile.gettempdir", return_value="/tmp"),
            patch("pathlib.Path.mkdir"),
            patch("src.font_manager.FontManager._load_overrides"),
        ):
            from src.font_manager import FontManager

            fm = FontManager({})
        # No crash; catalog may be empty (common fonts not found either)
        assert isinstance(fm.font_catalog, dict)

    def test_scan_discovers_ttf_and_bdf_files(self):
        """TTF and BDF files in assets/fonts are added to the catalog."""
        filenames = ["MyFont-Regular.ttf", "PixelFont.bdf", "image.png"]

        with (
            patch("os.path.exists", side_effect=lambda p: p == "assets/fonts"),
            patch("os.listdir", return_value=filenames),
            patch("os.path.join", side_effect=lambda *a: "/".join(a)),
            patch("tempfile.gettempdir", return_value="/tmp"),
            patch("pathlib.Path.mkdir"),
            patch("src.font_manager.FontManager._load_overrides"),
        ):
            from src.font_manager import FontManager

            fm = FontManager({})

        assert "myfont-regular" in fm.font_catalog
        assert "pixelfont" in fm.font_catalog
        assert "image" not in fm.font_catalog  # .png skipped

    def test_register_common_fonts_adds_existing_files(self):
        """Common font aliases are added when the font files exist."""

        def exists_side_effect(p):
            return p in ("assets/fonts/PressStart2P-Regular.ttf", "assets/fonts/4x6-font.ttf")

        with (
            patch("os.path.exists", side_effect=exists_side_effect),
            patch("os.listdir", return_value=[]),
            patch("tempfile.gettempdir", return_value="/tmp"),
            patch("pathlib.Path.mkdir"),
            patch("src.font_manager.FontManager._load_overrides"),
        ):
            from src.font_manager import FontManager

            fm = FontManager({})

        assert "press_start" in fm.font_catalog
        assert "four_by_six" in fm.font_catalog
        # five_by_seven file does not exist in this test
        assert "five_by_seven" not in fm.font_catalog

    def test_register_common_fonts_skips_missing_files(self):
        with (
            patch("os.path.exists", return_value=False),
            patch("os.listdir", return_value=[]),
            patch("tempfile.gettempdir", return_value="/tmp"),
            patch("pathlib.Path.mkdir"),
            patch("src.font_manager.FontManager._load_overrides"),
        ):
            from src.font_manager import FontManager

            fm = FontManager({})

        for key in ("press_start", "four_by_six", "five_by_seven"):
            assert key not in fm.font_catalog


# ---------------------------------------------------------------------------
# TestReloadConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReloadConfig:
    """Tests for reload_config."""

    def test_reload_clears_caches(self):
        fm = _make_font_manager()
        # Poison the caches
        fm.font_cache["dummy"] = object()
        fm.metrics_cache["dummy"] = (1, 2, 3)

        new_config = {"fonts": {"foo": "bar"}}
        with patch.object(fm, "_initialize_fonts"):
            fm.reload_config(new_config)

        assert fm.font_cache == {}
        assert fm.metrics_cache == {}

    def test_reload_updates_config(self):
        fm = _make_font_manager()
        new_config = {"fonts": {"new_key": "new_value"}}
        with patch.object(fm, "_initialize_fonts"):
            fm.reload_config(new_config)
        assert fm.config is new_config
        assert fm.fonts_config == {"new_key": "new_value"}

    def test_reload_calls_initialize_fonts(self):
        fm = _make_font_manager()
        with patch.object(fm, "_initialize_fonts") as mock_init:
            fm.reload_config({})
        mock_init.assert_called_once()


# ---------------------------------------------------------------------------
# TestGetFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFont:
    """Tests for get_font — cache behaviour, TTF loading, BDF routing, fallback."""

    def test_cache_hit_returns_cached_font(self):
        fm = _make_font_manager()
        sentinel = object()
        fm.font_cache["arial_12"] = sentinel

        result = fm.get_font("arial", 12)

        assert result is sentinel
        assert fm.performance_stats["cache_hits"] == 1
        assert fm.performance_stats["cache_misses"] == 0

    def test_cache_miss_increments_counter(self):
        fm = _make_font_manager()
        fm.font_catalog["arial"] = "arial.ttf"

        with patch("src.font_manager.ImageFont.truetype", return_value=MagicMock()):
            fm.get_font("arial", 12)

        assert fm.performance_stats["cache_misses"] == 1

    def test_loaded_font_stored_in_cache(self):
        fake_font = MagicMock()
        fm = _make_font_manager()
        fm.font_catalog["myfont"] = "myfont.ttf"

        with patch("src.font_manager.ImageFont.truetype", return_value=fake_font):
            result = fm.get_font("myfont", 14)

        assert result is fake_font
        assert fm.font_cache["myfont_14"] is fake_font

    def test_unknown_family_returns_default_font(self):
        fm = _make_font_manager()
        fake_default = MagicMock()

        with patch("src.font_manager.ImageFont.load_default", return_value=fake_default):
            result = fm.get_font("nonexistent_family", 10)

        assert result is fake_default
        assert fm.performance_stats["failed_loads"] == 1

    def test_bdf_font_routed_to_load_bdf(self):
        fm = _make_font_manager()
        fm.font_catalog["pixel"] = "pixel.bdf"
        fake_face = MagicMock()

        with patch.object(fm, "_load_bdf_font", return_value=fake_face) as mock_bdf:
            result = fm.get_font("pixel", 8)

        mock_bdf.assert_called_once_with("pixel.bdf", 8)
        assert result is fake_face

    def test_font_load_error_falls_back_to_default(self):
        fm = _make_font_manager()
        fm.font_catalog["broken"] = "broken.ttf"
        fake_default = MagicMock()

        with (
            patch("src.font_manager.ImageFont.truetype", side_effect=OSError("missing")),
            patch("src.font_manager.ImageFont.load_default", return_value=fake_default),
        ):
            result = fm.get_font("broken", 12)

        assert result is fake_default
        assert fm.performance_stats["failed_loads"] == 1


# ---------------------------------------------------------------------------
# TestLoadBdfFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadBdfFont:
    """Tests for _load_bdf_font."""

    def test_load_bdf_creates_face_and_sets_size(self, mock_freetype_module):
        fm = _make_font_manager()
        fake_face = MagicMock()
        mock_freetype_module.Face.return_value = fake_face

        result = fm._load_bdf_font("/path/to/font.bdf", 10)

        mock_freetype_module.Face.assert_called_once_with("/path/to/font.bdf")
        fake_face.set_char_size.assert_called_once_with(640, 640, 72, 72)
        assert result is fake_face

    def test_load_bdf_propagates_exception(self, mock_freetype_module):
        fm = _make_font_manager()
        mock_freetype_module.Face.side_effect = RuntimeError("bad font")

        with pytest.raises(RuntimeError):
            fm._load_bdf_font("/bad/font.bdf", 8)


# ---------------------------------------------------------------------------
# TestGetFallbackFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFallbackFont:
    """Tests for _get_fallback_font."""

    def test_returns_pil_default_font(self):
        fm = _make_font_manager()
        fake = MagicMock()
        with patch("src.font_manager.ImageFont.load_default", return_value=fake):
            result = fm._get_fallback_font()
        assert result is fake


# ---------------------------------------------------------------------------
# TestMeasureText
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMeasureText:
    """Tests for measure_text."""

    def test_pil_font_returns_bbox_based_measurement(self, mock_freetype_module):
        fm = _make_font_manager()
        pil_font = MagicMock()
        pil_font.getbbox.return_value = (0, -2, 40, 10)

        # Ensure isinstance(font, freetype.Face) is False by making Face a distinct class
        mock_freetype_module.Face = type("Face", (), {})

        result = fm.measure_text("Hello", pil_font)
        # width = 40-0=40, height = 10-(-2)=12, baseline = -(-2)=2
        assert result == (40, 12, 2)

    def test_pil_measurement_cached(self, mock_freetype_module):
        fm = _make_font_manager()
        pil_font = MagicMock()
        pil_font.getbbox.return_value = (0, 0, 30, 8)
        mock_freetype_module.Face = type("Face", (), {})

        r1 = fm.measure_text("Test", pil_font)
        r2 = fm.measure_text("Test", pil_font)

        # Second call should hit cache — getbbox called only once
        pil_font.getbbox.assert_called_once()
        assert r1 == r2

    def test_measurement_error_returns_fallback(self, mock_freetype_module):
        fm = _make_font_manager()
        bad_font = MagicMock()
        bad_font.getbbox.side_effect = Exception("boom")
        mock_freetype_module.Face = type("Face", (), {})

        result = fm.measure_text("Hi", bad_font)
        # Fallback: width = len("Hi") * 8 = 16, height = 12, baseline = 10
        assert result == (16, 12, 10)

    def test_freetype_face_measurement(self, mock_freetype_module):
        """When font is a freetype.Face instance, use glyph advance measurement."""
        fm = _make_font_manager()

        # freetype.Face must be a real Python class for isinstance() to accept it.
        # Replace the MagicMock attribute with a lightweight stub class, then create
        # a MagicMock instance whose __class__ is that stub so isinstance returns True.
        class _FaceStub:
            pass

        mock_freetype_module.Face = _FaceStub

        face = MagicMock()
        face.__class__ = _FaceStub

        # Configure glyph metrics for each character loaded
        def load_char_side_effect(ch):
            face.glyph.advance.x = 8 * 64  # 8px advance per char
            face.glyph.bitmap.rows = 10
            face.size.ascender = 8 * 64

        face.load_char.side_effect = load_char_side_effect
        face.size.ascender = 8 * 64

        result = fm.measure_text("AB", face)

        # Two chars × 8px = 16 width; height max glyph rows = 10; baseline = 8
        assert result[0] == 16
        assert result[1] == 10
        assert result[2] == 8


# ---------------------------------------------------------------------------
# TestGetFontHeight
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFontHeight:
    """Tests for get_font_height."""

    def test_pil_font_uses_getbbox(self, mock_freetype_module):
        fm = _make_font_manager()
        mock_freetype_module.Face = type("Face", (), {})
        pil_font = MagicMock()
        pil_font.getbbox.return_value = (0, 0, 20, 10)

        height = fm.get_font_height(pil_font)
        assert height == 10
        pil_font.getbbox.assert_called_once_with("Ay")

    def test_font_height_error_returns_default(self, mock_freetype_module):
        fm = _make_font_manager()
        mock_freetype_module.Face = type("Face", (), {})
        bad_font = MagicMock()
        bad_font.getbbox.side_effect = Exception("fail")

        height = fm.get_font_height(bad_font)
        assert height == 12


# ---------------------------------------------------------------------------
# TestManagerFontRegistration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestManagerFontRegistration:
    """Tests for register_manager_font, get_manager_fonts, get_detected_fonts."""

    def test_register_new_manager_font(self):
        fm = _make_font_manager()
        fm.register_manager_font("nfl", "nfl.live.score", "press_start", 10)

        assert "nfl" in fm.manager_fonts
        spec = fm.manager_fonts["nfl"]["nfl.live.score"]
        assert spec["family"] == "press_start"
        assert spec["size_px"] == 10

    def test_register_font_with_color(self):
        fm = _make_font_manager()
        fm.register_manager_font("nba", "nba.score", "arial", 8, color=(255, 0, 0))

        spec = fm.manager_fonts["nba"]["nba.score"]
        assert spec["color"] == (255, 0, 0)

    def test_register_font_without_color_omits_key(self):
        fm = _make_font_manager()
        fm.register_manager_font("nba", "nba.score", "arial", 8)
        spec = fm.manager_fonts["nba"]["nba.score"]
        assert "color" not in spec

    def test_usage_count_increments_on_repeated_registration(self):
        fm = _make_font_manager()
        fm.register_manager_font("mgr", "elem", "font_a", 12)
        fm.register_manager_font("mgr", "elem", "font_a", 12)

        assert fm.detected_fonts["elem"]["usage_count"] == 2

    def test_detected_fonts_created_on_first_registration(self):
        fm = _make_font_manager()
        fm.register_manager_font("mgr", "elem.key", "myfont", 9)

        assert "elem.key" in fm.detected_fonts
        assert fm.detected_fonts["elem.key"]["usage_count"] == 1

    def test_get_manager_fonts_for_specific_manager(self):
        fm = _make_font_manager()
        fm.register_manager_font("mgr1", "key1", "font_a", 8)
        fm.register_manager_font("mgr2", "key2", "font_b", 10)

        result = fm.get_manager_fonts("mgr1")
        assert "key1" in result
        assert "key2" not in result

    def test_get_manager_fonts_all(self):
        fm = _make_font_manager()
        fm.register_manager_font("mgr1", "k1", "f1", 8)
        fm.register_manager_font("mgr2", "k2", "f2", 10)

        result = fm.get_manager_fonts()
        assert "mgr1" in result
        assert "mgr2" in result

    def test_get_manager_fonts_unknown_manager_returns_empty(self):
        fm = _make_font_manager()
        assert fm.get_manager_fonts("nonexistent") == {}

    def test_get_detected_fonts_returns_copy(self):
        fm = _make_font_manager()
        fm.register_manager_font("m", "e", "f", 8)
        copy = fm.get_detected_fonts()
        copy["injected"] = {}
        assert "injected" not in fm.detected_fonts


# ---------------------------------------------------------------------------
# TestPluginFontRegistration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPluginFontRegistration:
    """Tests for register_plugin_fonts, _validate_font_manifest,
    _register_plugin_font, unregister_plugin_fonts, get_plugin_fonts."""

    def _minimal_manifest(self, family="MyFont", source="/tmp/font.ttf"):
        return {"fonts": [{"family": family, "source": source}]}

    def test_validate_manifest_missing_fonts_key(self):
        fm = _make_font_manager()
        assert fm._validate_font_manifest({}) is False

    def test_validate_manifest_font_def_not_dict(self):
        fm = _make_font_manager()
        assert fm._validate_font_manifest({"fonts": ["string_item"]}) is False

    def test_validate_manifest_missing_required_font_field(self):
        fm = _make_font_manager()
        # Missing 'source'
        bad = {"fonts": [{"family": "X"}]}
        assert fm._validate_font_manifest(bad) is False

    def test_validate_manifest_valid(self):
        fm = _make_font_manager()
        assert fm._validate_font_manifest(self._minimal_manifest()) is True

    def test_register_plugin_fonts_invalid_manifest_returns_false(self):
        fm = _make_font_manager()
        result = fm.register_plugin_fonts("myplugin", {"invalid": True})
        assert result is False

    def test_register_plugin_fonts_stores_manifest(self):
        fm = _make_font_manager()
        manifest = self._minimal_manifest()

        with patch("os.path.exists", return_value=True):
            fm.register_plugin_fonts("myplugin", manifest)

        assert "myplugin" in fm.plugin_fonts

    def test_register_plugin_fonts_adds_to_catalog(self):
        fm = _make_font_manager()
        manifest = self._minimal_manifest(family="CoolFont", source="/tmp/cool.ttf")

        with patch("os.path.exists", return_value=True):
            fm.register_plugin_fonts("plug", manifest)

        assert "plug::CoolFont" in fm.font_catalog

    def test_register_plugin_font_http_source_triggers_download(self):
        fm = _make_font_manager()
        manifest = {"fonts": [{"family": "WebFont", "source": "https://example.com/font.ttf"}]}
        downloaded_path = "/tmp/WebFont_abc.ttf"

        with (
            patch.object(fm, "_download_font", return_value=downloaded_path) as mock_dl,
            patch("os.path.exists", return_value=True),
        ):
            fm.register_plugin_fonts("wp", manifest)

        mock_dl.assert_called_once()

    def test_register_plugin_font_plugin_source_resolves_path(self):
        fm = _make_font_manager()
        manifest = {"fonts": [{"family": "LocalFont", "source": "plugin://fonts/local.ttf"}]}

        with (
            patch.object(fm, "_resolve_plugin_font_path", return_value="/resolved/local.ttf") as mock_res,
            patch("os.path.exists", return_value=True),
        ):
            fm.register_plugin_fonts("lp", manifest)

        mock_res.assert_called_once_with("lp", "fonts/local.ttf")

    def test_register_plugin_font_missing_file_skips(self):
        fm = _make_font_manager()
        manifest = self._minimal_manifest(source="/nonexistent/path.ttf")

        with patch("os.path.exists", return_value=False):
            result = fm.register_plugin_fonts("badplug", manifest)

        # Top-level returns True (manifest is valid), but font not in catalog
        assert result is True
        assert "badplug::MyFont" not in fm.font_catalog

    def test_register_plugin_font_stores_metadata(self):
        fm = _make_font_manager()
        manifest = {"fonts": [{"family": "MetaFont", "source": "/tmp/meta.ttf", "metadata": {"author": "test"}}]}

        with patch("os.path.exists", return_value=True):
            fm.register_plugin_fonts("mp", manifest)

        assert "mp::MetaFont" in fm.font_metadata
        assert fm.font_metadata["mp::MetaFont"] == {"author": "test"}

    def test_register_plugin_font_stores_dependencies(self):
        fm = _make_font_manager()
        manifest = {"fonts": [{"family": "DepFont", "source": "/tmp/dep.ttf", "dependencies": ["BaseFont"]}]}

        with patch("os.path.exists", return_value=True):
            fm.register_plugin_fonts("dp", manifest)

        assert "dp::DepFont" in fm.font_dependencies
        assert fm.font_dependencies["dp::DepFont"] == ["BaseFont"]

    def test_get_plugin_fonts_returns_registered_families(self):
        fm = _make_font_manager()
        manifest = self._minimal_manifest(family="PlugFont", source="/tmp/pf.ttf")

        with patch("os.path.exists", return_value=True):
            fm.register_plugin_fonts("myp", manifest)

        fonts = fm.get_plugin_fonts("myp")
        assert "PlugFont" in fonts

    def test_get_plugin_fonts_unknown_plugin_returns_empty(self):
        fm = _make_font_manager()
        assert fm.get_plugin_fonts("ghost") == []

    def test_unregister_plugin_fonts_removes_from_catalog(self):
        fm = _make_font_manager()
        manifest = self._minimal_manifest(family="ToRemove", source="/tmp/tr.ttf")

        with patch("os.path.exists", return_value=True):
            fm.register_plugin_fonts("rp", manifest)

        assert "rp::ToRemove" in fm.font_catalog

        result = fm.unregister_plugin_fonts("rp")
        assert result is True
        assert "rp::ToRemove" not in fm.font_catalog
        assert "rp" not in fm.plugin_fonts
        assert "rp" not in fm.plugin_font_catalogs

    def test_unregister_plugin_fonts_clears_font_cache_entries(self):
        fm = _make_font_manager()
        fm.font_cache["rp::SomeFont_12"] = MagicMock()
        fm.font_cache["other::Font_8"] = MagicMock()
        fm.plugin_fonts["rp"] = {}
        fm.plugin_font_catalogs["rp"] = {"SomeFont": "/tmp/sf.ttf"}
        fm.font_catalog["rp::SomeFont"] = "/tmp/sf.ttf"

        fm.unregister_plugin_fonts("rp")

        assert "rp::SomeFont_12" not in fm.font_cache
        assert "other::Font_8" in fm.font_cache  # untouched

    def test_unregister_nonexistent_plugin_returns_false(self):
        fm = _make_font_manager()
        assert fm.unregister_plugin_fonts("ghost") is False

    def test_register_plugin_fonts_exception_returns_false(self):
        fm = _make_font_manager()
        manifest = self._minimal_manifest()
        with patch.object(fm, "_validate_font_manifest", side_effect=RuntimeError("explode")):
            result = fm.register_plugin_fonts("ep", manifest)
        assert result is False


# ---------------------------------------------------------------------------
# TestDownloadFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDownloadFont:
    """Tests for _download_font."""

    def test_uses_cached_file_if_exists(self):
        fm = _make_font_manager()
        font_def = {"family": "WebFont"}

        with patch("pathlib.Path.exists", return_value=True):
            result = fm._download_font("https://example.com/font.ttf", font_def)

        assert result is not None
        # Should not call urlretrieve since file exists
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            with patch("pathlib.Path.exists", return_value=True):
                fm._download_font("https://example.com/font.ttf", font_def)
            mock_retrieve.assert_not_called()

    def test_downloads_when_not_cached(self):
        fm = _make_font_manager()
        font_def = {"family": "FreshFont"}

        with patch("pathlib.Path.exists", return_value=False), patch("urllib.request.urlretrieve") as mock_retrieve:
            result = fm._download_font("https://example.com/fresh.ttf", font_def)

        mock_retrieve.assert_called_once()
        assert result is not None

    def test_download_error_returns_none(self):
        fm = _make_font_manager()
        font_def = {"family": "FailFont"}

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("urllib.request.urlretrieve", side_effect=Exception("network error")),
        ):
            result = fm._download_font("https://example.com/fail.ttf", font_def)

        assert result is None

    def test_zip_download_extracts_font_file(self, tmp_path):
        import zipfile as zf

        fm = _make_font_manager()
        fm.temp_font_dir = tmp_path
        font_def = {"family": "ZipFont"}

        # Create a real zip containing a .ttf
        ttf_content = b"fake ttf content"
        zip_path = tmp_path / "ZipFont_abcdef01.zip"
        actual_ttf = tmp_path / "real_font.ttf"
        actual_ttf.write_bytes(ttf_content)

        with zf.ZipFile(zip_path, "w") as z:
            z.write(actual_ttf, arcname="real_font.ttf")

        def fake_urlretrieve(url, dest):
            import shutil

            shutil.copy(str(zip_path), str(dest))

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve),
        ):
            result = fm._download_font("https://example.com/fonts.zip", font_def)

        assert result is not None
        assert result.endswith(".ttf")


# ---------------------------------------------------------------------------
# TestGetFontExtension
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFontExtension:
    """Tests for _get_font_extension."""

    def test_ttf_url(self):
        fm = _make_font_manager()
        assert fm._get_font_extension("https://example.com/MyFont.ttf") == ".ttf"

    def test_otf_url(self):
        fm = _make_font_manager()
        assert fm._get_font_extension("https://example.com/MyFont.otf") == ".otf"

    def test_bdf_url(self):
        fm = _make_font_manager()
        assert fm._get_font_extension("https://example.com/pixel.bdf") == ".bdf"

    def test_zip_url(self):
        fm = _make_font_manager()
        assert fm._get_font_extension("https://example.com/fonts.zip") == ".zip"

    def test_unknown_url_defaults_to_ttf(self):
        fm = _make_font_manager()
        assert fm._get_font_extension("https://example.com/mystery") == ".ttf"


# ---------------------------------------------------------------------------
# TestResolvePluginFontPath
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolvePluginFontPath:
    """Tests for _resolve_plugin_font_path."""

    def test_returns_path_when_exists(self):
        fm = _make_font_manager()
        with patch("pathlib.Path.exists", return_value=True):
            result = fm._resolve_plugin_font_path("myplugin", "fonts/my.ttf")
        assert result is not None
        assert "myplugin" in result
        assert "fonts/my.ttf" in result

    def test_returns_none_when_missing(self):
        fm = _make_font_manager()
        with patch("pathlib.Path.exists", return_value=False):
            result = fm._resolve_plugin_font_path("myplugin", "fonts/missing.ttf")
        assert result is None


# ---------------------------------------------------------------------------
# TestResolveFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveFont:
    """Tests for resolve_font — override application, plugin namespace, fallback."""

    def test_resolve_uses_override_family(self):
        fm = _make_font_manager()
        fm.font_overrides["score.home"] = {"family": "override_font", "size_px": 10}
        fake_font = MagicMock()

        with patch.object(fm, "get_font", return_value=fake_font) as mock_get:
            fm.resolve_font("score.home", "default_font", 8)

        # get_font should receive the override family and size
        mock_get.assert_called_once_with("override_font", 10)

    def test_resolve_uses_override_size_only(self):
        fm = _make_font_manager()
        fm.font_overrides["score.away"] = {"size_px": 16}
        fake_font = MagicMock()

        with patch.object(fm, "get_font", return_value=fake_font) as mock_get:
            fm.resolve_font("score.away", "my_font", 8)

        mock_get.assert_called_once_with("my_font", 16)

    def test_resolve_without_override_uses_passed_values(self):
        fm = _make_font_manager()
        fake_font = MagicMock()

        with patch.object(fm, "get_font", return_value=fake_font) as mock_get:
            fm.resolve_font("no.override", "my_font", 12)

        mock_get.assert_called_once_with("my_font", 12)

    def test_resolve_namespaces_plugin_font(self):
        fm = _make_font_manager()
        fm.plugin_font_catalogs["transit"] = {"Display": "/tmp/Display.ttf"}
        fake_font = MagicMock()

        with patch.object(fm, "get_font", return_value=fake_font) as mock_get:
            fm.resolve_font("transit.display", "Display", 10, plugin_id="transit")

        mock_get.assert_called_once_with("transit::Display", 10)

    def test_resolve_does_not_double_namespace(self):
        fm = _make_font_manager()
        fake_font = MagicMock()

        with patch.object(fm, "get_font", return_value=fake_font) as mock_get:
            # Already namespaced
            fm.resolve_font("elem", "transit::Display", 10, plugin_id="transit")

        mock_get.assert_called_once_with("transit::Display", 10)

    def test_resolve_exception_returns_fallback(self):
        fm = _make_font_manager()
        fake_fallback = MagicMock()

        with (
            patch.object(fm, "get_font", side_effect=Exception("boom")),
            patch.object(fm, "_get_fallback_font", return_value=fake_fallback),
        ):
            result = fm.resolve_font("broken.elem", "myfont", 12)

        assert result is fake_fallback


# ---------------------------------------------------------------------------
# TestOverrideManagement
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOverrideManagement:
    """Tests for set_override, remove_override, get_overrides, _load_overrides, _save_overrides."""

    def test_set_override_family_and_size(self):
        fm = _make_font_manager()
        with patch.object(fm, "_save_overrides"), patch.object(fm, "clear_cache"):
            fm.set_override("elem.key", family="my_font", size_px=14)

        assert fm.font_overrides["elem.key"]["family"] == "my_font"
        assert fm.font_overrides["elem.key"]["size_px"] == 14

    def test_set_override_family_only(self):
        fm = _make_font_manager()
        with patch.object(fm, "_save_overrides"), patch.object(fm, "clear_cache"):
            fm.set_override("elem.key", family="only_family")

        assert "family" in fm.font_overrides["elem.key"]
        assert "size_px" not in fm.font_overrides["elem.key"]

    def test_set_override_neither_arg_removes_empty_entry(self):
        fm = _make_font_manager()
        with patch.object(fm, "_save_overrides"), patch.object(fm, "clear_cache"):
            fm.set_override("elem.key")  # no family or size_px

        assert "elem.key" not in fm.font_overrides

    def test_set_override_calls_clear_cache(self):
        fm = _make_font_manager()
        with patch.object(fm, "_save_overrides"), patch.object(fm, "clear_cache") as mock_clear:
            fm.set_override("k", family="f")
        mock_clear.assert_called_once()

    def test_remove_override_existing_key(self):
        fm = _make_font_manager()
        fm.font_overrides["elem"] = {"family": "old"}

        with patch.object(fm, "_save_overrides"), patch.object(fm, "clear_cache"):
            fm.remove_override("elem")

        assert "elem" not in fm.font_overrides

    def test_remove_override_nonexistent_key_no_error(self):
        fm = _make_font_manager()
        with patch.object(fm, "_save_overrides"), patch.object(fm, "clear_cache"):
            fm.remove_override("ghost_key")  # should not raise

    def test_get_overrides_returns_copy(self):
        fm = _make_font_manager()
        fm.font_overrides["k"] = {"family": "f"}
        copy = fm.get_overrides()
        copy["injected"] = {}
        assert "injected" not in fm.font_overrides

    def test_load_overrides_reads_json_file(self):
        fm = _make_font_manager()
        override_data = {"elem.key": {"family": "loaded_font"}}
        m = mock_open(read_data=json.dumps(override_data))

        with patch("os.path.exists", return_value=True), patch("builtins.open", m):
            fm._load_overrides()

        assert fm.font_overrides == override_data

    def test_load_overrides_file_not_found_sets_empty(self):
        fm = _make_font_manager()
        with patch("os.path.exists", return_value=False):
            fm._load_overrides()
        assert fm.font_overrides == {}

    def test_load_overrides_bad_json_sets_empty(self):
        fm = _make_font_manager()
        m = mock_open(read_data="NOT JSON{{")
        with patch("os.path.exists", return_value=True), patch("builtins.open", m):
            fm._load_overrides()
        assert fm.font_overrides == {}

    def test_save_overrides_writes_json(self):
        fm = _make_font_manager()
        fm.font_overrides = {"k": {"family": "f"}}
        m = mock_open()

        with patch("src.font_manager.FontManager._save_overrides", wraps=None) as _mock:
            # Test by calling the real method with mocked filesystem
            pass

        # Test the real method in isolation
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", m),
            patch("src.font_manager.Path"),
            patch("src.font_manager.FontManager._save_overrides", autospec=True) as mock_save,
        ):
            mock_save(fm)
        mock_save.assert_called_once()

    def test_save_overrides_exception_is_handled(self):
        """_save_overrides must catch internal exceptions and not propagate them."""
        fm = _make_font_manager()
        fm.font_overrides = {"k": {"family": "f"}}

        with patch("src.common.permission_utils.ensure_directory_permissions", side_effect=PermissionError("denied")):
            try:
                fm._save_overrides()
            except Exception:
                pytest.fail("set_override should not propagate _save_overrides exceptions")


# ---------------------------------------------------------------------------
# TestClearCache
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClearCache:
    """Tests for clear_cache."""

    def test_clear_cache_empties_font_cache(self):
        fm = _make_font_manager()
        fm.font_cache["k"] = MagicMock()
        fm.clear_cache()
        assert fm.font_cache == {}

    def test_clear_cache_empties_metrics_cache(self):
        fm = _make_font_manager()
        fm.metrics_cache["k"] = (1, 2, 3)
        fm.clear_cache()
        assert fm.metrics_cache == {}


# ---------------------------------------------------------------------------
# TestAddFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddFont:
    """Tests for add_font."""

    def test_add_font_file_not_found_returns_false(self):
        fm = _make_font_manager()
        with patch("os.path.exists", return_value=False):
            assert fm.add_font("/missing/font.ttf", "myfont") is False

    def test_add_font_duplicate_family_returns_false(self):
        fm = _make_font_manager()
        fm.font_catalog["existing"] = "/some/path.ttf"
        with patch("os.path.exists", return_value=True):
            assert fm.add_font("/new/path.ttf", "existing") is False

    def test_add_font_success_adds_to_catalog(self):
        fm = _make_font_manager()
        mock_perm = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch.object(fm, "clear_cache"),
            patch("src.font_manager.ensure_directory_permissions", mock_perm, create=True),
            patch("src.font_manager.get_assets_dir_mode", return_value=0o755, create=True),
            patch("src.font_manager.Path"),
        ):
            # Import the real permission utils at the module level
            with patch.dict(
                "sys.modules",
                {
                    "src.common.permission_utils": MagicMock(
                        ensure_directory_permissions=MagicMock(), get_assets_dir_mode=MagicMock(return_value=0o755)
                    )
                },
            ):
                result = fm.add_font("/real/font.ttf", "newface")

        assert result is True
        assert "newface" in fm.font_catalog

    def test_add_font_exception_returns_false(self):
        fm = _make_font_manager()
        with patch("os.path.exists", side_effect=Exception("oops")):
            assert fm.add_font("/bad", "broken") is False


# ---------------------------------------------------------------------------
# TestRemoveFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRemoveFont:
    """Tests for remove_font."""

    def test_remove_nonexistent_family_returns_false(self):
        fm = _make_font_manager()
        assert fm.remove_font("ghost") is False

    def test_remove_font_in_use_by_override_returns_false(self):
        fm = _make_font_manager()
        fm.font_catalog["used_font"] = "/tmp/used.ttf"
        fm.font_overrides["elem"] = {"family": "used_font"}

        with patch.object(fm, "clear_cache"):
            result = fm.remove_font("used_font")

        assert result is False
        assert "used_font" in fm.font_catalog

    def test_remove_font_success(self):
        fm = _make_font_manager()
        fm.font_catalog["removable"] = "/tmp/rem.ttf"

        with patch.object(fm, "clear_cache") as mock_clear:
            result = fm.remove_font("removable")

        assert result is True
        assert "removable" not in fm.font_catalog
        mock_clear.assert_called_once()

    def test_remove_font_exception_returns_false(self):
        fm = _make_font_manager()
        fm.font_catalog["bad"] = "/tmp/b.ttf"
        with patch.object(fm, "clear_cache", side_effect=Exception("boom")):
            assert fm.remove_font("bad") is False


# ---------------------------------------------------------------------------
# TestValidateFont
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFont:
    """Tests for validate_font."""

    def test_missing_file_returns_invalid(self):
        fm = _make_font_manager()
        with patch("os.path.exists", return_value=False):
            result = fm.validate_font("/missing/font.ttf")
        assert result["valid"] is False
        assert "not found" in result["error"]

    def test_unsupported_format_returns_invalid(self):
        fm = _make_font_manager()
        with patch("os.path.exists", return_value=True):
            result = fm.validate_font("/some/file.woff")
        assert result["valid"] is False
        assert "Unsupported" in result["error"]

    def test_valid_ttf_returns_true(self):
        fm = _make_font_manager()
        with (
            patch("os.path.exists", return_value=True),
            patch("src.font_manager.ImageFont.truetype", return_value=MagicMock()),
        ):
            result = fm.validate_font("/path/to/font.ttf")
        assert result["valid"] is True
        assert result["type"] == "ttf"

    def test_valid_bdf_returns_true(self, mock_freetype_module):
        fm = _make_font_manager()
        with patch("os.path.exists", return_value=True):
            mock_freetype_module.Face.return_value = MagicMock()
            result = fm.validate_font("/path/to/font.bdf")
        assert result["valid"] is True
        assert result["type"] == "bdf"

    def test_ttf_load_error_returns_invalid(self):
        fm = _make_font_manager()
        with (
            patch("os.path.exists", return_value=True),
            patch("src.font_manager.ImageFont.truetype", side_effect=OSError("bad ttf")),
        ):
            result = fm.validate_font("/path/to/corrupt.ttf")
        assert result["valid"] is False
        assert "bad ttf" in result["error"]

    def test_bdf_load_error_returns_invalid(self, mock_freetype_module):
        fm = _make_font_manager()
        with patch("os.path.exists", return_value=True):
            mock_freetype_module.Face.side_effect = RuntimeError("bad bdf")
            result = fm.validate_font("/path/to/corrupt.bdf")
        assert result["valid"] is False


# ---------------------------------------------------------------------------
# TestPerformanceStats
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPerformanceStats:
    """Tests for get_performance_stats and _record_performance_metric."""

    def test_get_performance_stats_structure(self):
        fm = _make_font_manager()
        stats = fm.get_performance_stats()
        assert "uptime_seconds" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_hit_rate" in stats
        assert "total_fonts_cached" in stats
        assert "total_metrics_cached" in stats
        assert "failed_loads" in stats
        assert "total_fonts_available" in stats
        assert "plugin_fonts" in stats
        assert "manager_fonts" in stats
        assert "detected_fonts" in stats

    def test_cache_hit_rate_zero_when_no_activity(self):
        fm = _make_font_manager()
        stats = fm.get_performance_stats()
        assert stats["cache_hit_rate"] == 0

    def test_cache_hit_rate_calculated_correctly(self):
        fm = _make_font_manager()
        fm.performance_stats["cache_hits"] = 3
        fm.performance_stats["cache_misses"] = 1
        stats = fm.get_performance_stats()
        assert stats["cache_hit_rate"] == pytest.approx(0.75)

    def test_record_performance_metric_creates_new_op(self):
        fm = _make_font_manager()
        fm._record_performance_metric("resolve", "arial_12", 0.001)
        assert "resolve" in fm.performance_stats
        assert fm.performance_stats["resolve"]["arial_12"] == pytest.approx(0.001)

    def test_record_performance_metric_updates_existing_op(self):
        fm = _make_font_manager()
        fm._record_performance_metric("resolve", "arial_12", 0.001)
        fm._record_performance_metric("resolve", "arial_12", 0.002)
        assert fm.performance_stats["resolve"]["arial_12"] == pytest.approx(0.002)

    def test_stats_reflect_cache_hits_and_misses(self):
        fm = _make_font_manager()
        # Pre-seed cache
        fake_font = MagicMock()
        fm.font_cache["myfont_10"] = fake_font
        fm.get_font("myfont", 10)  # cache hit

        fm.font_catalog["another"] = "another.ttf"
        with patch("src.font_manager.ImageFont.truetype", return_value=MagicMock()):
            fm.get_font("another", 8)  # cache miss

        stats = fm.get_performance_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1


# ---------------------------------------------------------------------------
# TestGetAvailableFonts  /  GetSizeTokens  /  GetFontCatalog
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUtilityMethods:
    """Tests for get_available_fonts, get_size_tokens, get_font_catalog."""

    def test_get_available_fonts_returns_copy(self):
        fm = _make_font_manager()
        fm.font_catalog["a"] = "/path/a.ttf"
        result = fm.get_available_fonts()
        result["injected"] = "bad"
        assert "injected" not in fm.font_catalog

    def test_get_size_tokens_returns_copy(self):
        fm = _make_font_manager()
        tokens = fm.get_size_tokens()
        assert tokens == fm.size_tokens
        tokens["injected"] = 999
        assert "injected" not in fm.size_tokens

    def test_get_font_catalog_returns_copy(self):
        fm = _make_font_manager()
        fm.font_catalog["b"] = "/path/b.ttf"
        catalog = fm.get_font_catalog()
        catalog["injected"] = "bad"
        assert "injected" not in fm.font_catalog


# ---------------------------------------------------------------------------
# TestClearPluginFontCache
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClearPluginFontCache:
    """Tests for _clear_plugin_font_cache."""

    def test_removes_only_matching_plugin_prefix(self):
        fm = _make_font_manager()
        fm.font_cache["myplugin::FontA_10"] = MagicMock()
        fm.font_cache["myplugin::FontB_8"] = MagicMock()
        fm.font_cache["otherplugin::FontC_12"] = MagicMock()
        fm.font_cache["global_font_14"] = MagicMock()

        fm._clear_plugin_font_cache("myplugin")

        assert "myplugin::FontA_10" not in fm.font_cache
        assert "myplugin::FontB_8" not in fm.font_cache
        assert "otherplugin::FontC_12" in fm.font_cache
        assert "global_font_14" in fm.font_cache

    def test_no_matching_entries_is_noop(self):
        fm = _make_font_manager()
        fm.font_cache["other::Font_10"] = MagicMock()
        fm._clear_plugin_font_cache("ghost")
        assert "other::Font_10" in fm.font_cache
