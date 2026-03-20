"""Common response/request models shared across API routes."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SuccessResponse(BaseModel):
    """Standard success envelope."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed",
                "data": None,
            }
        },
    )

    status: str = Field("success", description="Response status indicator")
    message: str = Field(..., description="Human-readable result message")
    data: Any | None = Field(None, description="Optional payload returned by the operation")


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Plugin 'foo' not found",
                "details": None,
            }
        },
    )

    status: str = Field("error", description="Response status indicator")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: dict[str, Any] | None = Field(None, description="Additional error context")


class PaginatedResponse(BaseModel):
    """Paginated list envelope."""

    model_config = ConfigDict(from_attributes=True)

    items: list[Any] = Field(..., description="List of items for the current page")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
