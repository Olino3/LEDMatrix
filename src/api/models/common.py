"""Common response/request models shared across API routes."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class SuccessResponse(BaseModel):
    """Standard success envelope."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "success"
    message: str
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    model_config = ConfigDict(from_attributes=True)

    status: str = "error"
    error_code: str
    message: str
    details: dict[str, Any] | None = None


class PaginatedResponse(BaseModel):
    """Paginated list envelope."""

    model_config = ConfigDict(from_attributes=True)

    items: list[Any]
    total: int
    page: int
    page_size: int
