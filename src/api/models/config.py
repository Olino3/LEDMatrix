"""Config-related request/response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DisplayHardwareConfig(BaseModel):
    """Display hardware settings."""

    model_config = ConfigDict(from_attributes=True)

    rows: int = Field(32, description="Number of pixel rows per panel")
    cols: int = Field(64, description="Number of pixel columns per panel")
    chain_length: int = Field(1, description="Number of daisy-chained panels")
    parallel: int = Field(1, description="Number of parallel chains")
    brightness: int = Field(100, description="LED brightness percentage (0-100)")
    hardware_mapping: str = Field("adafruit-hat", description="GPIO mapping profile")
    scan_mode: int = Field(0, description="Panel scan mode (0=progressive, 1=interlaced)")
    pwm_bits: int = Field(11, description="PWM bits for color depth")
    pwm_dither_bits: int = Field(0, description="Temporal dithering bits")
    pwm_lsb_nanoseconds: int = Field(130, description="PWM LSB duration in nanoseconds")
    disable_hardware_pulsing: bool = Field(False, description="Disable hardware PWM pulsing")
    inverse_colors: bool = Field(False, description="Invert display colors")
    show_refresh_rate: bool = Field(False, description="Show refresh rate on the matrix")
    led_rgb_sequence: str = Field("RGB", description="LED color channel order")
    limit_refresh_rate_hz: int = Field(0, description="Cap refresh rate (0=unlimited)")


class ScheduleConfig(BaseModel):
    """Schedule on/off settings."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool = Field(False, description="Whether the display schedule is active")
    mode: str = Field("global", description="Schedule mode (global or per-plugin)")
    start_time: str = Field("07:00", description="Daily display-on time (HH:MM)")
    end_time: str = Field("23:00", description="Daily display-off time (HH:MM)")


class SystemConfigResponse(BaseModel):
    """Full system configuration response."""

    model_config = ConfigDict(from_attributes=True)

    display: dict[str, Any] = Field(..., description="Display hardware configuration")
    schedule: dict[str, Any] = Field(..., description="Display schedule settings")
    general: dict[str, Any] = Field(..., description="General application settings")


class ConfigUpdateRequest(BaseModel):
    """Partial config update request (all fields optional)."""

    model_config = ConfigDict(from_attributes=True)

    display: dict[str, Any] | None = Field(None, description="Display settings to update")
    schedule: dict[str, Any] | None = Field(None, description="Schedule settings to update")
    general: dict[str, Any] | None = Field(None, description="General settings to update")
