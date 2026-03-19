"""Config-related request/response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class DisplayHardwareConfig(BaseModel):
    """Display hardware settings."""

    model_config = ConfigDict(from_attributes=True)

    rows: int = 32
    cols: int = 64
    chain_length: int = 1
    parallel: int = 1
    brightness: int = 100
    hardware_mapping: str = "adafruit-hat"
    scan_mode: int = 0
    pwm_bits: int = 11
    pwm_dither_bits: int = 0
    pwm_lsb_nanoseconds: int = 130
    disable_hardware_pulsing: bool = False
    inverse_colors: bool = False
    show_refresh_rate: bool = False
    led_rgb_sequence: str = "RGB"
    limit_refresh_rate_hz: int = 0


class ScheduleConfig(BaseModel):
    """Schedule on/off settings."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool = False
    mode: str = "global"
    start_time: str = "07:00"
    end_time: str = "23:00"


class SystemConfigResponse(BaseModel):
    """Full system configuration response."""

    model_config = ConfigDict(from_attributes=True)

    display: dict[str, Any]
    schedule: dict[str, Any]
    general: dict[str, Any]


class ConfigUpdateRequest(BaseModel):
    """Partial config update request (all fields optional)."""

    model_config = ConfigDict(from_attributes=True)

    display: dict[str, Any] | None = None
    schedule: dict[str, Any] | None = None
    general: dict[str, Any] | None = None
