"""Pydantic request/response models for the FastAPI application."""

from src.api.models.common import ErrorResponse, PaginatedResponse, SuccessResponse
from src.api.models.config import (
    ConfigUpdateRequest,
    DisplayHardwareConfig,
    ScheduleConfig,
    SystemConfigResponse,
)
from src.api.models.plugin import (
    PluginConfigResponse,
    PluginInfo,
    PluginInstallRequest,
    PluginToggleRequest,
)
from src.api.models.system import (
    HealthResponse,
    SystemStatusResponse,
    SystemVersionResponse,
)

__all__ = [
    "ConfigUpdateRequest",
    "DisplayHardwareConfig",
    "ErrorResponse",
    "HealthResponse",
    "PaginatedResponse",
    "PluginConfigResponse",
    "PluginInfo",
    "PluginInstallRequest",
    "PluginToggleRequest",
    "ScheduleConfig",
    "SuccessResponse",
    "SystemConfigResponse",
    "SystemStatusResponse",
    "SystemVersionResponse",
]
