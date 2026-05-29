from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
import logging


if TYPE_CHECKING:
    from types import TracebackType
    from datetime import timedelta

    from requestforge.config import TokenData
    from requestforge.models import HttpRequest, HttpResponse, RequestContext

logger = logging.getLogger(__name__)


class HttpClientInterface(ABC):
    """Abstract interface for HTTP client."""

    @abstractmethod
    def request(self, request: HttpRequest) -> HttpResponse:
        """Execute an HTTP request."""

    @abstractmethod
    def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """Execute GET request."""

    @abstractmethod
    def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """Execute POST request."""

    @abstractmethod
    def put(self, url: str, **kwargs: Any) -> HttpResponse:
        """Execute PUT request."""

    @abstractmethod
    def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        """Execute PATCH request."""

    @abstractmethod
    def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        """Execute DELETE request."""


class RetryStrategyInterface(ABC):
    """Abstract interface for retry strategies."""

    @abstractmethod
    def should_retry(
        self, context: RequestContext, exception: Exception
    ) -> bool:
        """Determine if request should be retried."""

    @abstractmethod
    def get_delay(self, context: RequestContext) -> float:
        """Get delay in seconds before next retry."""

    @property
    @abstractmethod
    def max_retries(self) -> int:
        """Maximum number of retry attempts."""


class RequestHookInterface(ABC):
    """Interface for request modification hooks."""

    @abstractmethod
    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        """Modify request before sending."""


class ResponseHookInterface(ABC):
    """Interface for response processing hooks."""

    @abstractmethod
    def after_response(
        self, response: HttpResponse, context: RequestContext
    ) -> HttpResponse:
        """Process response after receiving."""


class ErrorHookInterface(ABC):
    """Interface for error handling hooks."""

    @abstractmethod
    def on_error(self, exception: Exception, context: RequestContext) -> None:
        """Handle errors during request lifecycle."""


class HttpSessionInterface(ABC):
    """Interface for session management."""

    @abstractmethod
    def close(self) -> None:
        """Close the session and release resources."""

    @abstractmethod
    def __enter__(self) -> HttpSessionInterface:
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""


class AuthRetryStrategyInterface(ABC):
    """Interface for authentication retry strategies."""

    @property
    @abstractmethod
    def max_retries(self) -> int:
        """Maximum number of auth retry attempts."""

    @abstractmethod
    def should_retry(self, response: HttpResponse, attempt: int) -> bool:
        """Determine if authentication should be retried."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get delay in seconds before next auth retry."""

    @abstractmethod
    def is_auth_error(self, response: HttpResponse) -> bool:
        """Check if response indicates authentication error."""


class AuthHookInterface(ABC):
    """Interface for authentication hooks."""

    @abstractmethod
    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        """Add authentication to request."""

    @abstractmethod
    def should_authenticate(self, request: HttpRequest) -> bool:
        """Determine if request should be authenticated."""

    @abstractmethod
    def is_auth_error(self, response: HttpResponse) -> bool:
        """Check if response indicates authentication error."""

    @abstractmethod
    def refresh_auth(self) -> bool:
        """Refresh authentication credentials."""

    @abstractmethod
    def invalidate_auth(self) -> None:
        """Invalidate current authentication credentials."""

    @abstractmethod
    def get_token(self) -> TokenData:
        """Get current valid token."""

    @property
    @abstractmethod
    def retry_strategy(self) -> AuthRetryStrategyInterface:
        """Get the auth retry strategy for this hook."""


class TokenStorageInterface(ABC):
    """Abstract interface for token storage."""

    @abstractmethod
    def get(self, key: str) -> TokenData | None:
        """Retrieve token by key."""

    @abstractmethod
    def set(self, key: str, token: TokenData) -> None:
        """Store token with key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete token by key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if token exists."""


class TokenProviderInterface(ABC):
    """Abstract interface for token providers."""

    @abstractmethod
    def fetch_token(self) -> TokenData:
        """Fetch a new token from the authentication server."""

    @abstractmethod
    def refresh_token(self, current_token: TokenData) -> TokenData:
        """Refresh an existing token."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Unique identifier for this token provider."""


class TokenManagerInterface(ABC):
    """Abstract interface for token management."""

    def __init__(
        self,
        provider: TokenProviderInterface,
        storage: TokenStorageInterface | None = None,
    ):
        self._provider = provider
        self._storage = storage

    @abstractmethod
    def get_token(self) -> TokenData:
        """Get a valid token (from cache or fetch new)."""

    @abstractmethod
    def invalidate_token(self) -> None:
        """Invalidate the current cached token."""

    @abstractmethod
    def force_refresh(self) -> TokenData:
        """Force fetch a new token regardless of cache."""


class TokenFetcherInterface(ABC):
    """Interface for a single token fetch operation."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this fetcher/step."""

    @property
    def depends_on(self) -> list[str]:
        """Names of fetcher steps this depends on."""
        return []

    @property
    def ttl(self) -> timedelta | None:
        """Time-to-live for cached token."""
        return None

    @abstractmethod
    def fetch(self, context: dict[str, TokenData] | None = None) -> TokenData:
        """Fetch token for this step."""

    def on_fetch_error(
        self, error: Exception, context: dict[str, TokenData] | None = None
    ) -> None:
        """Called when fetch fails."""
        logger.error(f"Token fetch failed for {self.name}: {error}")
