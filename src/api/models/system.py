"""System status and health response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class SystemStatusResponse(BaseModel):
    """Runtime system metrics."""

    model_config = ConfigDict(from_attributes=True)

    cpu_percent: float
    memory_percent: float
    cpu_temp: float | None = None
    disk_percent: float
    service_active: bool
    uptime: float


class SystemVersionResponse(BaseModel):
    """Application version info."""

    model_config = ConfigDict(from_attributes=True)

    version: str
    python_version: str
    platform: str


class HealthResponse(BaseModel):
    """Health check response with per-subsystem checks."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    checks: dict[str, Any]
