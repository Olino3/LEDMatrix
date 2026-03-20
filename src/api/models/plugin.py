"""Plugin-related request/response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PluginInfo(BaseModel):
    """Summary information about a plugin."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "clock",
                "name": "Clock",
                "version": "1.0.0",
                "enabled": True,
                "description": "Displays the current time",
                "display_modes": ["default"],
            }
        },
    )

    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Semantic version string")
    enabled: bool = Field(..., description="Whether the plugin is currently enabled")
    description: str = Field("", description="Short description of the plugin")
    display_modes: list[str] = Field(default_factory=list, description="Available display modes")


class PluginConfigResponse(BaseModel):
    """Plugin configuration — config stays as a plain dict."""

    model_config = ConfigDict(from_attributes=True)

    plugin_id: str = Field(..., description="Plugin identifier")
    config: dict[str, Any] = Field(..., description="Current plugin configuration")
    schema_: dict[str, Any] = Field(
        default_factory=dict, alias="schema", description="JSON Schema for plugin config"
    )


class PluginToggleRequest(BaseModel):
    """Request to enable/disable a plugin."""

    plugin_id: str = Field(..., description="Plugin identifier to toggle")
    enabled: bool = Field(..., description="Desired enabled state")


class PluginInstallRequest(BaseModel):
    """Request to install a plugin from a remote source."""

    plugin_id: str = Field(..., description="Plugin identifier to install")
    source_url: str = Field(..., description="URL of the plugin package or repository")
