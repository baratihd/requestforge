from typing import Any


class HttpClientException(Exception):
    """Base exception for all HTTP client errors."""

    def __init__(
        self,
        message: str,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception
        self.context = context or {}

    def __str__(self) -> str:
        base_msg = self.message
        if self.original_exception:
            base_msg += f" | Original: {type(self.original_exception).__name__}: {self.original_exception}"
        return base_msg


class MaxRetryException(HttpClientException):
    """Raised when maximum retry attempts are exceeded."""

    def __init__(
        self,
        message: str,
        attempts: int,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, original_exception, context)
        self.attempts = attempts


class TimeoutException(HttpClientException):
    """Raised when a request times out."""


class ConnectionException(HttpClientException):
    """Raised when a connection error occurs."""


class ResponseParseException(HttpClientException):
    """Raised when response parsing (e.g., JSON) fails."""


class HttpStatusException(HttpClientException):
    """Raised for HTTP error status codes (4xx, 5xx)."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: str | None = None,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, original_exception, context)
        self.status_code = status_code
        self.response_body = response_body


class RequestBuildException(HttpClientException):
    """Raised when request building fails."""


class SSLException(HttpClientException):
    """Raised when SSL/TLS errors occur."""


class AuthenticationException(HttpClientException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
        service_name: str | None = None,
    ):
        super().__init__(message, original_exception, context)
        self.service_name = service_name


class UnauthorizedException(HttpStatusException):
    """Raised specifically for 401 Unauthorized responses."""

    def __init__(
        self,
        message: str = "Unauthorized",
        response_body: str | None = None,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            response_body=response_body,
            original_exception=original_exception,
            context=context,
        )


class ForbiddenException(HttpStatusException):
    """Raised specifically for 403 Forbidden responses."""

    def __init__(
        self,
        message: str = "Forbidden",
        response_body: str | None = None,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            response_body=response_body,
            original_exception=original_exception,
            context=context,
        )


class NotFoundException(HttpStatusException):
    """Raised specifically for 404 Not Found responses."""

    def __init__(
        self,
        message: str = "Not Found",
        response_body: str | None = None,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=404,
            response_body=response_body,
            original_exception=original_exception,
            context=context,
        )


class BadRequestException(HttpStatusException):
    """Raised specifically for 400 Bad Request responses."""

    def __init__(
        self,
        message: str = "Bad Request",
        response_body: str | None = None,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            response_body=response_body,
            original_exception=original_exception,
            context=context,
        )


class ServerErrorException(HttpStatusException):
    """Raised for 5xx server error responses."""

    def __init__(
        self,
        message: str = "Server Error",
        status_code: int = 500,
        response_body: str | None = None,
        original_exception: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            response_body=response_body,
            original_exception=original_exception,
            context=context,
        )
