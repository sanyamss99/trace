class TraceAppError(Exception):
    """Base exception for all Trace application errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(TraceAppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} '{resource_id}' not found", status_code=404)


class AuthenticationError(TraceAppError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(TraceAppError):
    """Raised when a client exceeds the allowed request rate."""

    def __init__(
        self,
        message: str = "Too many failed authentication attempts. Try again later.",
    ) -> None:
        super().__init__(message, status_code=429)


class InvalidCursorError(TraceAppError):
    """Raised when a pagination cursor is malformed."""

    def __init__(self) -> None:
        super().__init__("Invalid pagination cursor", status_code=400)


class ConflictError(TraceAppError):
    """Raised when a resource is already in the requested state."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, status_code=409)
