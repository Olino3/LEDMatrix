"""System status and health response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemStatusResponse(BaseModel):
    """Runtime system metrics."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "cpu_percent": 12.5,
                "memory_percent": 43.2,
                "cpu_temp": 52.0,
                "disk_percent": 31.8,
                "service_active": True,
                "uptime": 86400.0,
            }
        },
    )

    cpu_percent: float = Field(..., description="CPU utilization percentage")
    memory_percent: float = Field(..., description="Memory utilization percentage")
    cpu_temp: float | None = Field(None, description="CPU temperature in Celsius (Pi only)")
    disk_percent: float = Field(..., description="Disk utilization percentage")
    service_active: bool = Field(..., description="Whether the display service is running")
    uptime: float = Field(..., description="System uptime in seconds")


class SystemVersionResponse(BaseModel):
    """Application version info."""

    model_config = ConfigDict(from_attributes=True)

    version: str = Field(..., description="LEDMatrix application version")
    python_version: str = Field(..., description="Python interpreter version")
    platform: str = Field(..., description="Operating system platform identifier")


class HealthResponse(BaseModel):
    """Health check response with per-subsystem checks."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Overall health status (healthy/degraded/unhealthy)")
    checks: dict[str, Any] = Field(..., description="Per-subsystem health check results")
