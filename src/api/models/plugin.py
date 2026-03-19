"""Plugin-related request/response models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PluginInfo(BaseModel):
    """Summary information about a plugin."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    enabled: bool
    description: str = ""
    display_modes: list[str] = Field(default_factory=list)


class PluginConfigResponse(BaseModel):
    """Plugin configuration — config stays as a plain dict."""

    model_config = ConfigDict(from_attributes=True)

    plugin_id: str
    config: dict[str, Any]
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")


class PluginToggleRequest(BaseModel):
    """Request to enable/disable a plugin."""

    plugin_id: str
    enabled: bool


class PluginInstallRequest(BaseModel):
    """Request to install a plugin from a remote source."""

    plugin_id: str
    source_url: str
