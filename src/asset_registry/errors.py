from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Application error with a stable, vendor-readable body."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details or []

    def as_dict(self, duration_ms: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error": self.error,
            "message": self.message,
            "details": self.details,
        }
        if duration_ms is not None:
            body["duration_ms"] = duration_ms
        return body
