from __future__ import annotations

from enum import Enum
import json
from typing import TYPE_CHECKING, Any
import dataclasses
from dataclasses import field, dataclass


if TYPE_CHECKING:
    from requestforge.config import TokenData


class HttpMethod(str, Enum):
    """HTTP methods enumeration."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass(frozen=True)
class HttpRequest:
    """Immutable HTTP request representation."""

    method: HttpMethod
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    files: dict[str, Any] | None = None
    timeout: float | None = None
    auth: tuple | None = None

    def with_headers(self, headers: dict[str, str]) -> HttpRequest:
        """Create new request with additional headers."""
        merged_headers = {**(self.headers or {}), **headers}
        return HttpRequest(
            method=self.method,
            url=self.url,
            headers=merged_headers,
            params=self.params,
            data=self.data,
            json_data=self.json_data,
            files=self.files,
            timeout=self.timeout,
            auth=self.auth,
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def to_curl(self) -> str:
        from requestforge.utils import to_curl

        return to_curl(self)


@dataclass(frozen=True)
class HttpResponse:
    """Immutable HTTP response representation."""

    status_code: int
    headers: dict[str, str]
    content: bytes
    elapsed_ms: float
    url: str
    request: HttpRequest
    encoding: str | None = None

    @property
    def text(self) -> str:
        """Decode content to text."""
        encoding = self.encoding or "utf-8"
        return self.content.decode(encoding, errors="replace")

    @property
    def is_success(self) -> bool:
        """Check if response status indicates success (2xx)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response status indicates client error (4xx)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response status indicates server error (5xx)."""
        return 500 <= self.status_code < 600

    def json(self) -> Any:
        """Parse response content as JSON."""
        from requestforge.exceptions import ResponseParseException

        try:
            return json.loads(self.text)
        except json.JSONDecodeError as e:
            raise ResponseParseException(
                message=f"Failed to parse JSON response: {e}",
                original_exception=e,
                context={"content_preview": self.text[:500]},
            )

    def json_or_none(self) -> Any | None:
        """Parse response as JSON, return None on failure."""
        try:
            return self.json()
        except Exception:
            return None


@dataclass
class RequestContext:
    """Mutable context for request lifecycle."""

    request: HttpRequest
    attempt: int = 0
    max_retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def increment_attempt(self) -> None:
        """Increment the attempt counter."""
        self.attempt += 1

    @property
    def is_retry(self) -> bool:
        """Check if this is a retry attempt."""
        return self.attempt > 0


@dataclass
class FetchContext:
    """Context passed through the token fetch pipeline."""

    tokens: dict[str, TokenData] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_token(self, name: str) -> TokenData | None:
        """Get token by step name."""
        return self.tokens.get(name)

    def get_token_value(self, name: str) -> str | None:
        """Get token access_token value by step name."""
        token = self.tokens.get(name)
        return token.access_token if token else None

    def add_token(self, name: str, token: TokenData) -> None:
        """Add token to context."""
        self.tokens[name] = token

    def has_token(self, name: str) -> bool:
        """Check if token exists in context."""
        return name in self.tokens

    def has_valid_token(self, name: str) -> bool:
        """Check if token exists and is not expired."""
        token = self.tokens.get(name)
        return token is not None and not token.is_expired
