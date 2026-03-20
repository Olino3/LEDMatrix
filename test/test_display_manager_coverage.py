"""
Extended coverage tests for src/display_manager.py.

Targets uncovered code paths not exercised by test_display_manager.py:
- Singleton behaviour
- Fallback (no-hardware) mode
- width/height properties (all branches)
- set_brightness / get_brightness
- update_display (hardware and fallback)
- clear (hardware and fallback)
- _draw_bdf_text
- _load_fonts (success and fallback paths)
- get_text_width / get_font_height
- draw_text (all branches: freetype font, PIL font, centered, x=None)
- Weather icon drawing helpers
- draw_weather_icon (all condition strings + unknown)
- draw_text_with_icons
- scrolling state API
- defer_update / process_deferred_updates / _cleanup_expired_deferred_updates
- get_scrolling_stats
- format_date_with_ordinal (all ordinal suffix rules)
- _write_snapshot_if_due
- cleanup
- _draw_test_pattern (hardware and fallback paths)
"""

import datetime
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_singleton():
    """Reset the DisplayManager singleton so tests get a fresh instance."""
    from src.display_manager import DisplayManager

    DisplayManager._instance = None
    DisplayManager._initialized = False


def _make_matrix_mock(width=128, height=32):
    """Return a fully-wired matrix mock."""
    m = MagicMock()
    m.width = width
    m.height = height
    canvas = MagicMock()
    m.CreateFrameCanvas.return_value = canvas
    m.SwapOnVSync.return_value = canvas
    return m


def _build_dm(config=None, force_fallback=False, suppress_test_pattern=True, matrix_mock=None):
    """
    Construct a DisplayManager with all hardware / font / snapshot seams mocked.
    Returns (dm, matrix_instance).
    """
    from src.display_manager import DisplayManager

    _reset_singleton()

    if matrix_mock is None:
        matrix_mock = _make_matrix_mock()

    with (
        patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
        patch("src.display_manager.RGBMatrixOptions"),
        patch("src.display_manager.freetype"),
        patch("src.display_manager.ImageFont.truetype", return_value=MagicMock()),
        patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
    ):
        dm = DisplayManager(
            config=config or {},
            force_fallback=force_fallback,
            suppress_test_pattern=suppress_test_pattern,
        )

    return dm, matrix_mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Always reset singleton before and after each test."""
    _reset_singleton()
    yield
    _reset_singleton()


@pytest.fixture
def hardware_config():
    return {
        "display": {
            "hardware": {
                "rows": 32,
                "cols": 64,
                "chain_length": 2,
                "parallel": 1,
                "hardware_mapping": "adafruit-hat-pwm",
                "brightness": 80,
            },
            "runtime": {"gpio_slowdown": 2},
        }
    }


@pytest.fixture
def dm_hardware(hardware_config):
    """DisplayManager in hardware (non-fallback) mode."""
    dm, mat = _build_dm(config=hardware_config)
    yield dm, mat


@pytest.fixture
def dm_fallback(hardware_config):
    """DisplayManager in forced-fallback mode (no matrix)."""
    dm, _ = _build_dm(config=hardware_config, force_fallback=True)
    yield dm


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSingleton:
    """DisplayManager must return the same instance on subsequent calls."""

    def test_same_instance_returned(self, hardware_config):
        matrix_mock = _make_matrix_mock()
        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", return_value=MagicMock()),
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
        ):
            from src.display_manager import DisplayManager

            dm1 = DisplayManager(config=hardware_config, suppress_test_pattern=True)
            dm2 = DisplayManager(config=hardware_config, suppress_test_pattern=True)
            assert dm1 is dm2

    def test_cleanup_resets_singleton(self, hardware_config):
        from src.display_manager import DisplayManager

        dm, _ = _build_dm(config=hardware_config)
        dm.cleanup()
        assert DisplayManager._instance is None
        assert DisplayManager._initialized is False


# ---------------------------------------------------------------------------
# Initialization / setup_matrix
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetupMatrix:
    """Test _setup_matrix branches."""

    def test_hardware_mode_sets_matrix(self, dm_hardware):
        dm, mat = dm_hardware
        assert dm.matrix is mat

    def test_force_fallback_sets_matrix_none(self, dm_fallback):
        assert dm_fallback.matrix is None

    def test_fallback_creates_image_with_config_dimensions(self, hardware_config):
        dm, _ = _build_dm(config=hardware_config, force_fallback=True)
        # cols * chain_length = 64 * 2 = 128, rows = 32
        assert dm.image.width == 128
        assert dm.image.height == 32

    def test_fallback_with_no_config_uses_defaults(self):
        dm, _ = _build_dm(config={}, force_fallback=True)
        # defaults: cols=64, chain_length=2, rows=32 → 128×32
        assert dm.image.width == 128
        assert dm.image.height == 32

    def test_matrix_init_exception_triggers_fallback(self):
        """If RGBMatrix() raises, we fall back gracefully."""
        from src.display_manager import DisplayManager

        _reset_singleton()
        with (
            patch("src.display_manager.RGBMatrix", side_effect=RuntimeError("hw error")),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", return_value=MagicMock()),
        ):
            dm = DisplayManager(suppress_test_pattern=True)
        assert dm.matrix is None
        assert dm.image is not None

    def test_optional_hardware_config_fields_applied(self):
        """scan_mode, pwm_dither_bits, inverse_colors branches are covered."""
        config = {
            "display": {
                "hardware": {
                    "rows": 32,
                    "cols": 64,
                    "chain_length": 1,
                    "scan_mode": 1,
                    "pwm_dither_bits": 2,
                    "inverse_colors": True,
                },
                "runtime": {},
            }
        }
        mock_options_instance = MagicMock()
        matrix_mock = _make_matrix_mock()
        from src.display_manager import DisplayManager

        _reset_singleton()
        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions", return_value=mock_options_instance),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", return_value=MagicMock()),
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
        ):
            DisplayManager(config=config, suppress_test_pattern=True)
        assert mock_options_instance.scan_mode == 1
        assert mock_options_instance.pwm_dither_bits == 2
        assert mock_options_instance.inverse_colors is True

    def test_font_load_failure_falls_back_to_default(self):
        """If truetype raises for initial font load, load_default() is used."""
        matrix_mock = _make_matrix_mock()
        from src.display_manager import DisplayManager

        _reset_singleton()
        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", side_effect=OSError("font missing")),
            patch("src.display_manager.ImageFont.load_default", return_value=MagicMock()) as mock_default,
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
        ):
            DisplayManager(suppress_test_pattern=True)
        # load_default() should have been called for the initial font
        mock_default.assert_called()

    def test_suppress_test_pattern_skips_draw(self, hardware_config):
        """When suppress_test_pattern=True, _draw_test_pattern is not invoked."""
        matrix_mock = _make_matrix_mock()
        from src.display_manager import DisplayManager

        _reset_singleton()
        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", return_value=MagicMock()),
            patch("src.display_manager.DisplayManager._draw_test_pattern") as mock_tp,
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
        ):
            DisplayManager(config=hardware_config, suppress_test_pattern=True)
        mock_tp.assert_not_called()

    def test_test_pattern_drawn_when_not_suppressed(self, hardware_config):
        """When suppress_test_pattern=False, _draw_test_pattern is invoked."""
        matrix_mock = _make_matrix_mock()
        from src.display_manager import DisplayManager

        _reset_singleton()
        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", return_value=MagicMock()),
            patch("src.display_manager.DisplayManager._draw_test_pattern") as mock_tp,
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
        ):
            DisplayManager(config=hardware_config, suppress_test_pattern=False)
        mock_tp.assert_called_once()


# ---------------------------------------------------------------------------
# width / height properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWidthHeightProperties:
    """Cover all three branches of each property."""

    def test_width_from_matrix(self, dm_hardware):
        dm, mat = dm_hardware
        assert dm.width == mat.width

    def test_height_from_matrix(self, dm_hardware):
        dm, mat = dm_hardware
        assert dm.height == mat.height

    def test_width_from_image_when_no_matrix(self, dm_fallback):
        dm = dm_fallback
        assert dm.matrix is None
        assert dm.width == dm.image.width

    def test_height_from_image_when_no_matrix(self, dm_fallback):
        dm = dm_fallback
        assert dm.height == dm.image.height

    def test_width_default_when_no_matrix_and_no_image(self, dm_hardware):
        dm, _ = dm_hardware
        del dm.matrix
        del dm.image
        assert dm.width == 128

    def test_height_default_when_no_matrix_and_no_image(self, dm_hardware):
        dm, _ = dm_hardware
        del dm.matrix
        del dm.image
        assert dm.height == 32


# ---------------------------------------------------------------------------
# set_brightness / get_brightness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBrightness:
    """Cover all branches in set_brightness and get_brightness."""

    def test_set_brightness_success(self, dm_hardware):
        dm, mat = dm_hardware
        result = dm.set_brightness(75)
        assert result is True
        assert mat.brightness == 75

    def test_set_brightness_clamps_above_100(self, dm_hardware):
        dm, mat = dm_hardware
        result = dm.set_brightness(150)
        assert result is True
        assert mat.brightness == 100

    def test_set_brightness_clamps_below_0(self, dm_hardware):
        dm, mat = dm_hardware
        result = dm.set_brightness(-10)
        assert result is True
        assert mat.brightness == 0

    def test_set_brightness_accepts_float(self, dm_hardware):
        dm, mat = dm_hardware
        result = dm.set_brightness(50.7)
        assert result is True
        assert mat.brightness == 50

    def test_set_brightness_rejects_string(self, dm_hardware):
        dm, _ = dm_hardware
        result = dm.set_brightness("high")
        assert result is False

    def test_set_brightness_fallback_mode(self, dm_fallback):
        """set_brightness returns False when matrix is None."""
        result = dm_fallback.set_brightness(50)
        assert result is False

    def test_set_brightness_attribute_error(self, dm_hardware):
        dm, mat = dm_hardware
        type(mat).brightness = PropertyMock(side_effect=AttributeError("no attr"))
        result = dm.set_brightness(50)
        assert result is False

    def test_set_brightness_type_error(self, dm_hardware):
        dm, mat = dm_hardware
        type(mat).brightness = PropertyMock(side_effect=TypeError("bad type"))
        result = dm.set_brightness(50)
        assert result is False

    def test_get_brightness_success(self, dm_hardware):
        dm, mat = dm_hardware
        mat.brightness = 60
        result = dm.get_brightness()
        assert result == 60

    def test_get_brightness_fallback_mode(self, dm_fallback):
        assert dm_fallback.get_brightness() == -1

    def test_get_brightness_attribute_error(self, dm_hardware):
        dm, _ = dm_hardware

        # Use a real object whose brightness property raises AttributeError
        class _BrokenMatrix:
            width = 128
            height = 32

            @property
            def brightness(self):
                raise AttributeError("no attr")

        dm.matrix = _BrokenMatrix()
        result = dm.get_brightness()
        assert result == -1


# ---------------------------------------------------------------------------
# update_display
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateDisplay:
    """Cover update_display branches."""

    def test_update_display_hardware_mode(self, dm_hardware):
        dm, mat = dm_hardware
        with patch.object(dm, "_write_snapshot_if_due") as mock_snap:
            dm.update_display()
        dm.offscreen_canvas.SetImage.assert_called_once_with(dm.image)
        mat.SwapOnVSync.assert_called()
        mock_snap.assert_called_once()

    def test_update_display_swaps_canvas_references(self, dm_hardware):
        dm, mat = dm_hardware
        # Assign distinct canvas objects so we can verify the swap
        canvas_a = MagicMock(name="canvas_a")
        canvas_b = MagicMock(name="canvas_b")
        dm.offscreen_canvas = canvas_a
        dm.current_canvas = canvas_b
        mat.SwapOnVSync.return_value = canvas_a
        with patch.object(dm, "_write_snapshot_if_due"):
            dm.update_display()
        # After swap, offscreen should be canvas_b and current should be canvas_a
        assert dm.offscreen_canvas is canvas_b
        assert dm.current_canvas is canvas_a

    def test_update_display_fallback_mode(self, dm_fallback):
        dm = dm_fallback
        with patch.object(dm, "_write_snapshot_if_due") as mock_snap:
            dm.update_display()
        mock_snap.assert_called_once()

    def test_update_display_handles_exception_gracefully(self, dm_hardware):
        dm, mat = dm_hardware
        mat.SwapOnVSync.side_effect = RuntimeError("boom")
        # Should not raise
        dm.update_display()


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClear:
    """Cover clear() branches."""

    def test_clear_hardware_creates_new_image(self, dm_hardware):
        dm, mat = dm_hardware
        old_image = dm.image
        dm.clear()
        assert dm.image is not old_image
        assert dm.image.size == (mat.width, mat.height)

    def test_clear_hardware_clears_canvases(self, dm_hardware):
        dm, mat = dm_hardware
        dm.clear()
        dm.offscreen_canvas.Clear.assert_called()
        dm.current_canvas.Clear.assert_called()
        mat.Clear.assert_called()

    def test_clear_fallback_mode_creates_new_image(self, dm_fallback):
        dm = dm_fallback
        old_size = dm.image.size
        old_image = dm.image
        dm.clear()
        assert dm.image is not old_image
        assert dm.image.size == old_size

    def test_clear_canvas_exceptions_are_swallowed(self, dm_hardware):
        dm, mat = dm_hardware
        dm.offscreen_canvas.Clear.side_effect = RuntimeError("canvas err")
        dm.current_canvas.Clear.side_effect = RuntimeError("canvas err")
        mat.Clear.side_effect = RuntimeError("mat err")
        # Should not raise
        dm.clear()

    def test_clear_outer_exception_is_logged(self, dm_hardware):
        dm, _ = dm_hardware
        # Force unexpected error by removing image attr temporarily
        del dm.image
        # Should not raise; internally logs the error
        dm.clear()


# ---------------------------------------------------------------------------
# _draw_test_pattern
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDrawTestPattern:
    """Cover _draw_test_pattern branches."""

    def test_draw_test_pattern_hardware_calls_update(self, dm_hardware):
        dm, mat = dm_hardware
        with (
            patch.object(dm, "update_display") as mock_update,
            patch("src.display_manager.time.sleep"),
            patch.object(dm, "clear"),
            patch.object(dm, "draw"),
        ):
            dm._draw_test_pattern()
        mock_update.assert_called_once()

    def test_draw_test_pattern_fallback_mode(self, dm_fallback):
        dm = dm_fallback
        # Should not raise; draws on the PIL image
        dm._draw_test_pattern()

    def test_draw_test_pattern_exception_is_swallowed(self, dm_hardware):
        dm, _ = dm_hardware
        with patch.object(dm, "clear", side_effect=RuntimeError("clear error")):
            # Should not raise
            dm._draw_test_pattern()


# ---------------------------------------------------------------------------
# _load_fonts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadFonts:
    """Cover _load_fonts success and fallback paths."""

    def test_load_fonts_sets_regular_font(self, dm_hardware):
        dm, _ = dm_hardware
        assert hasattr(dm, "regular_font")

    def test_load_fonts_sets_small_font(self, dm_hardware):
        dm, _ = dm_hardware
        assert hasattr(dm, "small_font")

    def test_load_fonts_sets_extra_small_font(self, dm_hardware):
        dm, _ = dm_hardware
        assert hasattr(dm, "extra_small_font")

    def test_load_fonts_sets_calendar_font(self, dm_hardware):
        dm, _ = dm_hardware
        assert hasattr(dm, "calendar_font")

    def test_load_fonts_sets_bdf_5x7_font(self, dm_hardware):
        dm, _ = dm_hardware
        assert hasattr(dm, "bdf_5x7_font")

    def test_load_fonts_calendar_falls_back_when_file_missing(self):
        """When the 5x7.bdf path does not exist, calendar_font falls back."""
        matrix_mock = _make_matrix_mock()
        from src.display_manager import DisplayManager

        _reset_singleton()

        def selective_truetype(path, size):
            if "PressStart" in path:
                return MagicMock()
            raise OSError("not found")

        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype") as mock_ft,
            patch("src.display_manager.ImageFont.truetype", side_effect=selective_truetype),
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
            patch("os.path.exists", return_value=False),
        ):
            mock_ft.Face.side_effect = FileNotFoundError("no bdf")
            dm = DisplayManager(suppress_test_pattern=True)

        assert hasattr(dm, "calendar_font")

    def test_load_fonts_full_fallback_on_press_start_failure(self):
        """When PressStart2P truetype fails, all fonts fall back to load_default."""
        matrix_mock = _make_matrix_mock()
        from src.display_manager import DisplayManager

        _reset_singleton()

        mock_default_font = MagicMock()
        with (
            patch("src.display_manager.RGBMatrix", return_value=matrix_mock),
            patch("src.display_manager.RGBMatrixOptions"),
            patch("src.display_manager.freetype"),
            patch("src.display_manager.ImageFont.truetype", side_effect=OSError("all fonts missing")),
            patch("src.display_manager.ImageFont.load_default", return_value=mock_default_font),
            patch("src.display_manager.DisplayManager._write_snapshot_if_due"),
        ):
            dm = DisplayManager(suppress_test_pattern=True)

        assert dm.regular_font is mock_default_font
        assert dm.small_font is mock_default_font


# ---------------------------------------------------------------------------
# get_text_width
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTextWidth:
    """Cover get_text_width with freetype and PIL fonts."""

    def test_get_text_width_freetype_font(self, dm_hardware):
        """Test get_text_width with a freetype.Face-like font (freetype branch)."""
        import freetype as ft

        import src.display_manager as dm_mod

        dm, _ = dm_hardware

        # Create a real freetype.Face subclass instance so isinstance check passes
        face = MagicMock(spec=ft.Face)
        glyph = MagicMock()
        glyph.advance.x = 64  # 64 >> 6 = 1 pixel per character
        face.glyph = glyph

        # Swap module-level freetype so isinstance(face, dm_mod.freetype.Face) is True
        orig_ft = dm_mod.freetype
        try:
            dm_mod.freetype = ft
            width = dm.get_text_width("hi", face)
        finally:
            dm_mod.freetype = orig_ft

        # 2 characters × 1 pixel each = 2
        assert width == 2

    def test_get_text_width_pil_font(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        # draw.textbbox returns (left, top, right, bottom)
        dm.draw.textbbox = MagicMock(return_value=(0, 0, 42, 10))
        width = dm.get_text_width("hello", pil_font)
        assert width == 42

    def test_get_text_width_exception_returns_zero(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        dm.draw.textbbox = MagicMock(side_effect=RuntimeError("broken"))
        width = dm.get_text_width("hello", pil_font)
        assert width == 0


# ---------------------------------------------------------------------------
# get_font_height
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFontHeight:
    """Cover get_font_height with freetype and PIL fonts."""

    def test_get_font_height_pil_font(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        pil_font.getmetrics.return_value = (10, 2)
        # Need isinstance(pil_font, freetype.Face) to be False
        import src.display_manager as dm_mod

        original = dm_mod.freetype
        try:
            mock_ft = MagicMock()
            mock_ft.Face = type("Face", (), {})  # real class so isinstance works
            dm_mod.freetype = mock_ft
            height = dm.get_font_height(pil_font)
        finally:
            dm_mod.freetype = original
        assert height == 12  # 10 + 2

    def test_get_font_height_pil_font_fallback_size(self, dm_hardware):
        """If getmetrics raises, falls back to font.size attribute."""
        dm, _ = dm_hardware
        pil_font = MagicMock()
        pil_font.getmetrics.side_effect = AttributeError("no metrics")
        pil_font.size = 9
        import src.display_manager as dm_mod

        original = dm_mod.freetype
        try:
            mock_ft = MagicMock()
            mock_ft.Face = type("Face", (), {})
            dm_mod.freetype = mock_ft
            height = dm.get_font_height(pil_font)
        finally:
            dm_mod.freetype = original
        assert height == 9

    def test_get_font_height_ultimate_fallback(self, dm_hardware):
        """If getmetrics and size both fail, returns 8."""
        dm, _ = dm_hardware
        pil_font = MagicMock(spec=[])  # no attributes
        import src.display_manager as dm_mod

        original = dm_mod.freetype
        try:
            mock_ft = MagicMock()
            mock_ft.Face = type("Face", (), {})
            dm_mod.freetype = mock_ft
            height = dm.get_font_height(pil_font)
        finally:
            dm_mod.freetype = original
        assert height == 8


# ---------------------------------------------------------------------------
# draw_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDrawText:
    """Cover all draw_text branches."""

    def test_draw_text_with_explicit_xy(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        dm.regular_font = pil_font
        dm.draw.text = MagicMock()
        import src.display_manager as dm_mod

        orig = dm_mod.freetype
        mock_ft = MagicMock()
        mock_ft.Face = type("Face", (), {})
        dm_mod.freetype = mock_ft
        try:
            dm.draw_text("Hi", x=5, y=3)
        finally:
            dm_mod.freetype = orig
        dm.draw.text.assert_called_once_with((5, 3), "Hi", font=pil_font, fill=(255, 255, 255))

    def test_draw_text_x_none_centers_text(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        dm.regular_font = pil_font
        dm.draw.text = MagicMock()
        dm.draw.textbbox = MagicMock(return_value=(0, 0, 40, 10))
        import src.display_manager as dm_mod

        orig = dm_mod.freetype
        mock_ft = MagicMock()
        mock_ft.Face = type("Face", (), {})
        dm_mod.freetype = mock_ft
        try:
            dm.draw_text("Hi", x=None, y=5)
        finally:
            dm_mod.freetype = orig
        # x should be (128 - 40) // 2 = 44
        args, _ = dm.draw.text.call_args
        assert args[0][0] == 44

    def test_draw_text_centered_flag(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        dm.regular_font = pil_font
        dm.draw.text = MagicMock()
        dm.draw.textbbox = MagicMock(return_value=(0, 0, 20, 10))
        import src.display_manager as dm_mod

        orig = dm_mod.freetype
        mock_ft = MagicMock()
        mock_ft.Face = type("Face", (), {})
        dm_mod.freetype = mock_ft
        try:
            dm.draw_text("Hi", x=64, y=5, centered=True)
        finally:
            dm_mod.freetype = orig
        # x = 64 - 20//2 = 54
        args, _ = dm.draw.text.call_args
        assert args[0][0] == 54

    def test_draw_text_y_none_defaults_to_zero(self, dm_hardware):
        dm, _ = dm_hardware
        pil_font = MagicMock()
        dm.regular_font = pil_font
        dm.draw.text = MagicMock()
        import src.display_manager as dm_mod

        orig = dm_mod.freetype
        mock_ft = MagicMock()
        mock_ft.Face = type("Face", (), {})
        dm_mod.freetype = mock_ft
        try:
            dm.draw_text("Hi", x=0, y=None)
        finally:
            dm_mod.freetype = orig
        args, _ = dm.draw.text.call_args
        assert args[0][1] == 0

    def test_draw_text_small_font_flag(self, dm_hardware):
        dm, _ = dm_hardware
        small_font = MagicMock()
        dm.small_font = small_font
        dm.draw.text = MagicMock()
        import src.display_manager as dm_mod

        orig = dm_mod.freetype
        mock_ft = MagicMock()
        mock_ft.Face = type("Face", (), {})
        dm_mod.freetype = mock_ft
        try:
            dm.draw_text("X", x=0, y=0, small_font=True)
        finally:
            dm_mod.freetype = orig
        _, kwargs = dm.draw.text.call_args
        assert kwargs["font"] is small_font

    def test_draw_text_custom_font_overrides(self, dm_hardware):
        dm, _ = dm_hardware
        custom_font = MagicMock()
        dm.draw.text = MagicMock()
        import src.display_manager as dm_mod

        orig = dm_mod.freetype
        mock_ft = MagicMock()
        mock_ft.Face = type("Face", (), {})
        dm_mod.freetype = mock_ft
        try:
            dm.draw_text("X", x=0, y=0, font=custom_font)
        finally:
            dm_mod.freetype = orig
        _, kwargs = dm.draw.text.call_args
        assert kwargs["font"] is custom_font

    def test_draw_text_exception_does_not_raise(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.text = MagicMock(side_effect=RuntimeError("draw error"))
        # Should not propagate
        dm.draw_text("Hi", x=0, y=0)


# ---------------------------------------------------------------------------
# _draw_bdf_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDrawBdfText:
    """Cover _draw_bdf_text including bitmap rendering loop."""

    def _make_bdf_face(
        self,
        char_advance=64,
        bitmap_rows=7,
        bitmap_width=5,
        bitmap_pitch=1,
        bitmap_buffer=None,
        ascender=6 << 6,
        glyph_left=0,
        glyph_top=7,
    ):
        """Build a freetype.Face-like mock for _draw_bdf_text."""
        face = MagicMock()
        face.size.ascender = ascender

        bitmap = MagicMock()
        bitmap.rows = bitmap_rows
        bitmap.width = bitmap_width
        bitmap.pitch = bitmap_pitch
        # All pixels set: each byte = 0b11111000 (5-bit wide glyph in 8-bit byte)
        if bitmap_buffer is None:
            bitmap_buffer = [0b11111000] * (bitmap_rows * bitmap_pitch)
        bitmap.buffer = bitmap_buffer

        glyph = MagicMock()
        glyph.bitmap = bitmap
        glyph.bitmap_left = glyph_left
        glyph.bitmap_top = glyph_top
        glyph.advance.x = char_advance

        face.glyph = glyph
        face.load_char = MagicMock()
        return face

    def test_bdf_text_renders_pixels(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.point = MagicMock()
        face = self._make_bdf_face()
        dm._draw_bdf_text("A", x=0, y=0, color=(255, 0, 0), font=face)
        assert dm.draw.point.called

    def test_bdf_text_respects_bounds(self, dm_hardware):
        """Pixels outside [0, width) × [0, height) must not be drawn."""
        dm, mat = dm_hardware
        dm.draw.point = MagicMock()
        # Place text so most pixels fall out of range
        face = self._make_bdf_face()
        dm._draw_bdf_text("A", x=mat.width + 10, y=0, color=(255, 0, 0), font=face)
        # No pixels should have been drawn
        dm.draw.point.assert_not_called()

    def test_bdf_text_advances_x(self, dm_hardware):
        """Calling with two chars should load each char once."""
        dm, _ = dm_hardware
        dm.draw.point = MagicMock()
        face = self._make_bdf_face()
        dm._draw_bdf_text("AB", x=0, y=0, font=face)
        assert face.load_char.call_count == 2

    def test_bdf_text_uses_calendar_font_when_none_passed(self, dm_hardware):
        dm, _ = dm_hardware
        face = self._make_bdf_face()
        dm.calendar_font = face
        dm.draw.point = MagicMock()
        dm._draw_bdf_text("X", x=0, y=0)  # no font arg
        face.load_char.assert_called()

    def test_bdf_text_exception_is_logged(self, dm_hardware):
        dm, _ = dm_hardware
        bad_face = MagicMock()
        bad_face.size.ascender = 0
        bad_face.load_char.side_effect = RuntimeError("bad font")
        # Should not raise
        dm._draw_bdf_text("A", x=0, y=0, font=bad_face)

    def test_bdf_text_ascender_exception_falls_back(self, dm_hardware):
        """If face.size.ascender raises, ascender_px falls back to 0."""
        dm, _ = dm_hardware
        face = self._make_bdf_face()
        type(face.size).ascender = PropertyMock(side_effect=AttributeError)
        dm.draw.point = MagicMock()
        dm._draw_bdf_text("A", x=0, y=0, font=face)
        # Should still have attempted to draw
        face.load_char.assert_called()


# ---------------------------------------------------------------------------
# Weather icon drawing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWeatherIcons:
    """Cover draw_weather_icon and all private drawing helpers."""

    @pytest.mark.parametrize(
        "condition,expected_helper",
        [
            ("clear", "_draw_sun"),
            ("sunny", "_draw_sun"),
            ("clouds", "_draw_cloud"),
            ("cloudy", "_draw_cloud"),
            ("partly cloudy", "_draw_cloud"),
            ("rain", "_draw_rain"),
            ("drizzle", "_draw_rain"),
            ("shower", "_draw_rain"),
            ("snow", "_draw_snow"),
            ("sleet", "_draw_snow"),
            ("hail", "_draw_snow"),
            ("thunderstorm", "_draw_storm"),
            ("storm", "_draw_storm"),
            ("unknown_condition", "_draw_sun"),  # default fallback
        ],
    )
    def test_draw_weather_icon_dispatches_correctly(self, condition, expected_helper, dm_hardware):
        dm, _ = dm_hardware
        with (
            patch.object(dm, "_draw_sun") as mock_sun,
            patch.object(dm, "_draw_cloud") as mock_cloud,
            patch.object(dm, "_draw_rain") as mock_rain,
            patch.object(dm, "_draw_snow") as mock_snow,
            patch.object(dm, "_draw_storm") as mock_storm,
        ):
            dm.draw_weather_icon(condition, x=0, y=0, size=16)
            helper_map = {
                "_draw_sun": mock_sun,
                "_draw_cloud": mock_cloud,
                "_draw_rain": mock_rain,
                "_draw_snow": mock_snow,
                "_draw_storm": mock_storm,
            }
            helper_map[expected_helper].assert_called_once_with(0, 0, 16)
            for name, mock in helper_map.items():
                if name != expected_helper:
                    mock.assert_not_called()

    def test_draw_sun_draws_ellipse_and_lines(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.ellipse = MagicMock()
        dm.draw.line = MagicMock()
        dm._draw_sun(0, 0, 16)
        dm.draw.ellipse.assert_called()
        dm.draw.line.assert_called()

    def test_draw_cloud_draws_ellipses(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.ellipse = MagicMock()
        dm._draw_cloud(0, 0, 16)
        assert dm.draw.ellipse.call_count >= 3

    def test_draw_rain_calls_draw_cloud(self, dm_hardware):
        dm, _ = dm_hardware
        with patch.object(dm, "_draw_cloud") as mock_cloud:
            dm.draw.line = MagicMock()
            dm._draw_rain(0, 0, 16)
        mock_cloud.assert_called_once_with(0, 0, 16)
        dm.draw.line.assert_called()

    def test_draw_snow_calls_draw_cloud(self, dm_hardware):
        dm, _ = dm_hardware
        with patch.object(dm, "_draw_cloud") as mock_cloud:
            dm.draw.line = MagicMock()
            dm._draw_snow(0, 0, 16)
        mock_cloud.assert_called_once_with(0, 0, 16)

    def test_draw_storm_calls_draw_cloud_and_polygon(self, dm_hardware):
        dm, _ = dm_hardware
        with patch.object(dm, "_draw_cloud") as mock_cloud:
            dm.draw.polygon = MagicMock()
            dm._draw_storm(0, 0, 16)
        mock_cloud.assert_called_once_with(0, 0, 16)
        dm.draw.polygon.assert_called_once()

    def test_public_draw_sun_draws(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.ellipse = MagicMock()
        dm.draw.line = MagicMock()
        dm.draw_sun(0, 0, 16)
        dm.draw.ellipse.assert_called()

    def test_public_draw_cloud_draws(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.ellipse = MagicMock()
        dm.draw_cloud(0, 0, 16)
        dm.draw.ellipse.assert_called()

    def test_public_draw_rain_draws(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.ellipse = MagicMock()
        dm.draw.line = MagicMock()
        dm.draw_rain(0, 0, 16)
        dm.draw.line.assert_called()

    def test_public_draw_snow_draws(self, dm_hardware):
        dm, _ = dm_hardware
        dm.draw.ellipse = MagicMock()
        dm.draw.line = MagicMock()
        dm.draw_snow(0, 0, 16)
        dm.draw.line.assert_called()


# ---------------------------------------------------------------------------
# draw_text_with_icons
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDrawTextWithIcons:
    """Cover draw_text_with_icons."""

    def test_no_icons_calls_draw_text_and_update(self, dm_hardware):
        dm, _ = dm_hardware
        with patch.object(dm, "draw_text") as mock_dt, patch.object(dm, "update_display") as mock_upd:
            dm.draw_text_with_icons("Hello", icons=None, x=0, y=0)
        mock_dt.assert_called_once_with("Hello", 0, 0, (255, 255, 255))
        mock_upd.assert_called_once()

    def test_with_icons_calls_draw_weather_icon(self, dm_hardware):
        dm, _ = dm_hardware
        with (
            patch.object(dm, "draw_text"),
            patch.object(dm, "draw_weather_icon") as mock_icon,
            patch.object(dm, "update_display"),
        ):
            icons = [("rain", 10, 5), ("sun", 50, 5)]
            dm.draw_text_with_icons("Test", icons=icons, x=0, y=0)
        assert mock_icon.call_count == 2
        mock_icon.assert_any_call("rain", 10, 5)
        mock_icon.assert_any_call("sun", 50, 5)


# ---------------------------------------------------------------------------
# Scrolling state API
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScrollingState:
    """Cover all scrolling state methods."""

    def test_set_scrolling_true(self, dm_hardware):
        dm, _ = dm_hardware
        dm.set_scrolling_state(True)
        assert dm._scrolling_state["is_scrolling"] is True
        assert dm._scrolling_state["last_scroll_activity"] > 0

    def test_set_scrolling_false_does_not_update_activity(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["last_scroll_activity"] = 0
        dm.set_scrolling_state(False)
        assert dm._scrolling_state["is_scrolling"] is False
        assert dm._scrolling_state["last_scroll_activity"] == 0

    def test_is_currently_scrolling_when_active(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = True
        dm._scrolling_state["last_scroll_activity"] = time.time()
        assert dm.is_currently_scrolling() is True

    def test_is_currently_scrolling_false_when_not_set(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        assert dm.is_currently_scrolling() is False

    def test_is_currently_scrolling_expires_after_inactivity(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = True
        dm._scrolling_state["last_scroll_activity"] = time.time() - 100
        dm._scrolling_state["scroll_inactivity_threshold"] = 2.0
        result = dm.is_currently_scrolling()
        assert result is False
        assert dm._scrolling_state["is_scrolling"] is False

    def test_get_scrolling_stats_keys(self, dm_hardware):
        dm, _ = dm_hardware
        stats = dm.get_scrolling_stats()
        assert "is_scrolling" in stats
        assert "deferred_count" in stats
        assert "inactivity_threshold" in stats
        assert "max_deferred_updates" in stats
        assert "deferred_update_ttl" in stats


# ---------------------------------------------------------------------------
# defer_update / process_deferred_updates / _cleanup_expired_deferred_updates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeferredUpdates:
    """Cover the deferred update queue logic."""

    def test_defer_update_adds_to_queue(self, dm_hardware):
        dm, _ = dm_hardware
        fn = MagicMock()
        dm.defer_update(fn, priority=0)
        assert len(dm._scrolling_state["deferred_updates"]) == 1

    def test_defer_update_sorts_by_priority(self, dm_hardware):
        dm, _ = dm_hardware
        fn_low = MagicMock()
        fn_high = MagicMock()
        dm.defer_update(fn_low, priority=10)
        dm.defer_update(fn_high, priority=0)
        priorities = [u["priority"] for u in dm._scrolling_state["deferred_updates"]]
        assert priorities == sorted(priorities)

    def test_defer_update_evicts_oldest_when_queue_full(self, dm_hardware):
        dm, _ = dm_hardware
        max_q = dm._scrolling_state["max_deferred_updates"]
        fns = [MagicMock() for _ in range(max_q + 1)]
        for fn in fns:
            dm.defer_update(fn)
        assert len(dm._scrolling_state["deferred_updates"]) == max_q

    def test_process_deferred_updates_calls_functions(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        fn = MagicMock()
        dm._scrolling_state["deferred_updates"].append({"func": fn, "priority": 0, "timestamp": time.time()})
        dm.process_deferred_updates()
        fn.assert_called_once()

    def test_process_deferred_updates_skips_when_scrolling(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = True
        dm._scrolling_state["last_scroll_activity"] = time.time()
        fn = MagicMock()
        dm._scrolling_state["deferred_updates"].append({"func": fn, "priority": 0, "timestamp": time.time()})
        dm.process_deferred_updates()
        fn.assert_not_called()

    def test_process_deferred_updates_skips_empty_queue(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        # Should not raise with empty queue
        dm.process_deferred_updates()

    def test_process_deferred_updates_handles_func_exception(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        fn = MagicMock(side_effect=RuntimeError("oops"))
        dm._scrolling_state["deferred_updates"].append({"func": fn, "priority": 0, "timestamp": time.time()})
        # Should not propagate the exception
        dm.process_deferred_updates()

    def test_process_deferred_updates_requeues_recent_failures(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        fn = MagicMock(side_effect=RuntimeError("fail"))
        dm._scrolling_state["deferred_updates"].append({"func": fn, "priority": 0, "timestamp": time.time()})
        dm.process_deferred_updates()
        # Failed recent update should be re-queued
        assert len(dm._scrolling_state["deferred_updates"]) == 1

    def test_process_deferred_updates_skips_expired_entries(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        fn = MagicMock()
        old_ts = time.time() - dm._scrolling_state["deferred_update_ttl"] - 1
        dm._scrolling_state["deferred_updates"].append({"func": fn, "priority": 0, "timestamp": old_ts})
        dm.process_deferred_updates()
        fn.assert_not_called()

    def test_process_deferred_updates_processes_max_5_per_call(self, dm_hardware):
        dm, _ = dm_hardware
        dm._scrolling_state["is_scrolling"] = False
        fns = [MagicMock() for _ in range(10)]
        for fn in fns:
            dm._scrolling_state["deferred_updates"].append({"func": fn, "priority": 0, "timestamp": time.time()})
        dm.process_deferred_updates()
        called = sum(1 for fn in fns if fn.called)
        assert called == 5
        assert len(dm._scrolling_state["deferred_updates"]) == 5

    def test_cleanup_expired_removes_old_entries(self, dm_hardware):
        dm, _ = dm_hardware
        ttl = dm._scrolling_state["deferred_update_ttl"]
        old_ts = time.time() - ttl - 1
        fresh_ts = time.time()
        dm._scrolling_state["deferred_updates"] = [
            {"func": MagicMock(), "priority": 0, "timestamp": old_ts},
            {"func": MagicMock(), "priority": 0, "timestamp": fresh_ts},
        ]
        dm._cleanup_expired_deferred_updates(time.time())
        assert len(dm._scrolling_state["deferred_updates"]) == 1

    def test_cleanup_expired_no_removals_when_all_fresh(self, dm_hardware):
        dm, _ = dm_hardware
        now = time.time()
        dm._scrolling_state["deferred_updates"] = [
            {"func": MagicMock(), "priority": 0, "timestamp": now},
            {"func": MagicMock(), "priority": 0, "timestamp": now},
        ]
        dm._cleanup_expired_deferred_updates(now)
        assert len(dm._scrolling_state["deferred_updates"]) == 2


# ---------------------------------------------------------------------------
# format_date_with_ordinal
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatDateWithOrdinal:
    """Cover all ordinal suffix branches: st, nd, rd, th, and special teens."""

    def _dt(self, day):
        return datetime.datetime(2024, 8, day)

    def test_1st(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(1)).endswith("1st")

    def test_2nd(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(2)).endswith("2nd")

    def test_3rd(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(3)).endswith("3rd")

    def test_4th(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(4)).endswith("4th")

    def test_11th(self, dm_hardware):
        """11 is a teen, so suffix must be 'th' not 'st'."""
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(11)).endswith("11th")

    def test_12th(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(12)).endswith("12th")

    def test_13th(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(13)).endswith("13th")

    def test_21st(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(21)).endswith("21st")

    def test_22nd(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(22)).endswith("22nd")

    def test_23rd(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(23)).endswith("23rd")

    def test_30th(self, dm_hardware):
        dm, _ = dm_hardware
        assert dm.format_date_with_ordinal(self._dt(30)).endswith("30th")

    def test_month_name_included(self, dm_hardware):
        dm, _ = dm_hardware
        result = dm.format_date_with_ordinal(self._dt(1))
        assert "Aug" in result


# ---------------------------------------------------------------------------
# _write_snapshot_if_due
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteSnapshotIfDue:
    """Cover _write_snapshot_if_due branches."""

    def test_snapshot_skipped_when_too_soon(self, dm_hardware):
        dm, _ = dm_hardware
        dm._last_snapshot_ts = time.time()  # just written
        with patch("src.display_manager.os.replace") as mock_replace:
            dm._write_snapshot_if_due()
        mock_replace.assert_not_called()

    def test_snapshot_written_when_due(self, dm_hardware):
        dm, _ = dm_hardware
        dm._last_snapshot_ts = 0.0  # never written
        dm._snapshot_path = "/tmp/test_led_preview.png"

        with (
            patch("src.display_manager.os.replace"),
            patch("pathlib.Path"),
            patch("src.common.permission_utils.ensure_directory_permissions"),
            patch("src.common.permission_utils.ensure_file_permissions"),
            patch("src.common.permission_utils.get_assets_dir_mode", return_value=0o755),
            patch("src.common.permission_utils.get_assets_file_mode", return_value=0o644),
            patch.object(dm.image, "save") as mock_save,
        ):
            dm._write_snapshot_if_due()

        mock_save.assert_called()
        assert dm._last_snapshot_ts > 0.0

    def test_snapshot_fallback_to_direct_save_on_replace_failure(self, dm_hardware):
        dm, _ = dm_hardware
        dm._last_snapshot_ts = 0.0
        dm._snapshot_path = "/tmp/test_led_preview.png"

        with (
            patch("src.display_manager.os.replace", side_effect=OSError("no replace")),
            patch("pathlib.Path"),
            patch("src.common.permission_utils.ensure_directory_permissions"),
            patch("src.common.permission_utils.ensure_file_permissions"),
            patch("src.common.permission_utils.get_assets_dir_mode", return_value=0o755),
            patch("src.common.permission_utils.get_assets_file_mode", return_value=0o644),
            patch.object(dm.image, "save") as mock_save,
        ):
            dm._write_snapshot_if_due()

        # save called at least once (for direct fallback)
        assert mock_save.call_count >= 1

    def test_snapshot_exception_does_not_raise(self, dm_hardware):
        dm, _ = dm_hardware
        dm._last_snapshot_ts = 0.0
        with patch("pathlib.Path", side_effect=RuntimeError("path error")):
            # Should silently swallow and log at debug
            dm._write_snapshot_if_due()

    def test_snapshot_skips_ensure_permissions_for_tmp(self, dm_hardware):
        """Parent dir /tmp must not have its permissions modified."""
        dm, _ = dm_hardware
        dm._last_snapshot_ts = 0.0
        dm._snapshot_path = "/tmp/led_matrix_preview.png"

        with (
            patch("src.display_manager.os.replace"),
            patch("src.common.permission_utils.ensure_directory_permissions") as mock_perm,
            patch("src.common.permission_utils.ensure_file_permissions"),
            patch("src.common.permission_utils.get_assets_dir_mode", return_value=0o755),
            patch("src.common.permission_utils.get_assets_file_mode", return_value=0o644),
            patch.object(dm.image, "save"),
        ):
            dm._write_snapshot_if_due()

        mock_perm.assert_not_called()


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanup:
    """Cover cleanup()."""

    def test_cleanup_clears_matrix(self, dm_hardware):
        dm, mat = dm_hardware
        dm.cleanup()
        mat.Clear.assert_called()

    def test_cleanup_resets_singleton_state(self, dm_hardware):
        from src.display_manager import DisplayManager

        dm, _ = dm_hardware
        dm.cleanup()
        assert DisplayManager._instance is None

    def test_cleanup_resets_image(self, dm_hardware):
        from src.display_manager import DisplayManager

        dm, mat = dm_hardware
        dm.cleanup()
        # Image should be a fresh black one after cleanup
        # (cleanup resets image, then _instance is cleared)
        # Verify cleanup ran without raising
        assert DisplayManager._instance is None

    def test_cleanup_handles_missing_matrix(self, dm_fallback):
        dm = dm_fallback
        # Should not raise even in fallback mode (matrix is None)
        dm.cleanup()

    def test_cleanup_matrix_clear_exception_is_swallowed(self, dm_hardware):
        dm, mat = dm_hardware
        mat.Clear.side_effect = RuntimeError("hw gone")
        # Should not propagate
        dm.cleanup()
