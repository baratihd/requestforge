from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime, timedelta
from dataclasses import field, dataclass

from requestforge.retry import ExponentialBackoffRetryStrategy


if TYPE_CHECKING:
    from requestforge.interfaces import (
        AuthHookInterface,
        ErrorHookInterface,
        RequestHookInterface,
        ResponseHookInterface,
        TokenManagerInterface,
        RetryStrategyInterface,
        AuthRetryStrategyInterface,
    )


@dataclass
class TokenData:
    """
    Immutable token data container.

    Attributes:
        access_token: The access token string
        token_type: Token type (e.g., "Bearer")
        expires_at: Expiration datetime
        refresh_token: Optional refresh token
        scope: Optional token scope
        extra: Additional token metadata
    """

    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    refresh_token: str | None = None
    scope: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 30 second buffer)."""
        if self.expires_at is None:
            return False
        buffer = timedelta(seconds=30)
        return datetime.now() >= (self.expires_at - buffer)

    @property
    def authorization_header(self) -> str:
        """Get the authorization header value."""
        if self.token_type:
            return f"{self.token_type} {self.access_token}"
        return self.access_token

    @classmethod
    def from_response(
        cls,
        data: dict[str, Any],
        expires_in_key: str = "expires_in",
        access_token_key: str = "access_token",
        refresh_token_key: str = "refresh_token",
        token_type_key: str = "token_type",
    ) -> TokenData:
        """
        Create TokenData from API response.

        Args:
            data: Response data dictionary
            expires_in_key: Key for expires_in field
            access_token_key: Key for access_token field
            refresh_token_key: Key for refresh_token field
            token_type_key: Key for token_type field
        """
        expires_at = None
        if expires_in_key in data:
            expires_in = int(data[expires_in_key])
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return cls(
            access_token=data[access_token_key],
            token_type=data.get(token_type_key, "Bearer"),
            expires_at=expires_at,
            refresh_token=data.get(refresh_token_key),
            scope=data.get("scope"),
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    access_token_key,
                    refresh_token_key,
                    token_type_key,
                    expires_in_key,
                    "scope",
                }
            },
        )


@dataclass(frozen=True)
class HttpClientConfig:
    """
    Immutable configuration container for HTTP client settings.

    This class follows the Value Object pattern - immutable and validated.
    All configuration is set at creation time and cannot be modified.
    """

    base_url: str = ""
    default_timeout: float = 30.0
    default_headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    allow_redirects: bool = True
    max_redirects: int = 10
    retry_strategy: RetryStrategyInterface | None = None
    auth_hook: AuthHookInterface | None = None
    request_hooks: tuple = field(default_factory=tuple)
    response_hooks: tuple = field(default_factory=tuple)
    error_hooks: tuple = field(default_factory=tuple)
    pool_connection: int = 10
    pool_maxsize: int = 20

    def __post_init__(self) -> None:
        if self.default_timeout <= 0:
            raise ValueError("default_timeout must be positive")
        if self.max_redirects < 0:
            raise ValueError("max_redirects must be non-negative")


class HttpClientConfigBuilder:
    """
    Fluent builder for creating HttpClientConfig instances.

    Implements the Builder pattern for flexible, readable configuration.
    Methods return self for method chaining.
    """

    def __init__(self) -> None:
        self._base_url: str = ""
        self._default_timeout: float = 30.0
        self._default_headers: dict[str, str] = {}
        self._verify_ssl: bool = True
        self._allow_redirects: bool = True
        self._max_redirects: int = 10
        self._retry_strategy: RetryStrategyInterface | None = None
        self._auth_hook: AuthHookInterface | None = None
        self._request_hooks: list[RequestHookInterface] = []
        self._response_hooks: list[ResponseHookInterface] = []
        self._error_hooks: list[ErrorHookInterface] = []
        self._pool_connection: int = 10
        self._pool_maxsize: int = 20

    def with_base_url(self, url: str) -> HttpClientConfigBuilder:
        """Set base URL for all requests."""
        self._base_url = url.rstrip("/")
        return self

    def with_timeout(self, timeout: float) -> HttpClientConfigBuilder:
        """Set default timeout in seconds."""
        self._default_timeout = timeout
        return self

    def with_headers(self, headers: dict[str, str]) -> HttpClientConfigBuilder:
        """Set default headers."""
        self._default_headers.update(headers)
        return self

    def with_header(self, name: str, value: str) -> HttpClientConfigBuilder:
        """Add a single default header."""
        self._default_headers[name] = value
        return self

    def with_bearer_token(self, token: str) -> HttpClientConfigBuilder:
        """Add Bearer token authorization header."""
        self._default_headers["Authorization"] = f"Bearer {token}"
        return self

    def with_api_key(
        self, api_key: str, header_name: str = "X-API-Key"
    ) -> HttpClientConfigBuilder:
        """Add API key header."""
        self._default_headers[header_name] = api_key
        return self

    def with_verify_ssl(self, verify: bool) -> HttpClientConfigBuilder:
        """Set SSL verification."""
        self._verify_ssl = verify
        return self

    def with_redirects(
        self, allow: bool = True, max_redirects: int = 10
    ) -> HttpClientConfigBuilder:
        """Configure redirect behavior."""
        self._allow_redirects = allow
        self._max_redirects = max_redirects
        return self

    def with_retry_strategy(
        self, strategy: RetryStrategyInterface
    ) -> HttpClientConfigBuilder:
        """Set retry strategy."""
        self._retry_strategy = strategy
        return self

    def with_retry(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> HttpClientConfigBuilder:
        """Configure exponential backoff retry."""
        self._retry_strategy = ExponentialBackoffRetryStrategy(
            max_retries=max_retries, base_delay=base_delay, max_delay=max_delay
        )
        return self

    def with_pool_connection(
        self, pool_connection: int = 10
    ) -> HttpClientConfigBuilder:
        self._pool_connection = pool_connection
        return self

    def with_pool_maxsize(
        self, pool_maxsize: int = 20
    ) -> HttpClientConfigBuilder:
        self._pool_maxsize = pool_maxsize
        return self

    def with_auth_hook(
        self, auth_hook: AuthHookInterface
    ) -> HttpClientConfigBuilder:
        """Set authentication hook."""
        self._auth_hook = auth_hook
        return self

    def with_token_auth(
        self,
        token_manager: TokenManagerInterface,
        auth_retry_strategy: AuthRetryStrategyInterface | None = None,
        auth_header_name: str = "Authorization",
        auth_header_prefix: str = "Bearer",
        excluded_paths: set[str] | None = None,
        excluded_path_patterns: list[str] | None = None,
    ) -> HttpClientConfigBuilder:
        """Configure token-based authentication with automatic refresh."""
        from requestforge.hooks import TokenAuthHook

        self._auth_hook = TokenAuthHook(
            token_manager=token_manager,
            retry_strategy=auth_retry_strategy,
            auth_header_name=auth_header_name,
            auth_header_prefix=auth_header_prefix,
            excluded_paths=excluded_paths,
            excluded_path_patterns=excluded_path_patterns,
        )
        return self

    def with_api_key_auth(
        self,
        api_key: str,
        header_name: str = "X-API-Key",
        excluded_paths: set[str] | None = None,
    ) -> HttpClientConfigBuilder:
        """Configure API key authentication."""
        from requestforge.hooks import ApiKeyAuthHook

        self._auth_hook = ApiKeyAuthHook(
            api_key=api_key,
            header_name=header_name,
            excluded_paths=excluded_paths,
        )
        return self

    def with_basic_auth(
        self,
        username: str,
        password: str,
        excluded_paths: set[str] | None = None,
    ) -> HttpClientConfigBuilder:
        """Configure HTTP Basic authentication."""
        from requestforge.hooks import BasicAuthHook

        self._auth_hook = BasicAuthHook(
            username=username,
            password=password,
            excluded_paths=excluded_paths,
        )
        return self

    def with_request_hook(
        self, hook: RequestHookInterface
    ) -> HttpClientConfigBuilder:
        """Add request hook."""
        self._request_hooks.append(hook)
        return self

    def with_response_hook(
        self, hook: ResponseHookInterface
    ) -> HttpClientConfigBuilder:
        """Add response hook."""
        self._response_hooks.append(hook)
        return self

    def with_error_hook(
        self, hook: ErrorHookInterface
    ) -> HttpClientConfigBuilder:
        """Add error hook."""
        self._error_hooks.append(hook)
        return self

    def with_logging(
        self,
        log_headers: bool = False,
        log_body: bool = False,
        sensitive_keys: set[str] | None = None,
    ) -> HttpClientConfigBuilder:
        """Enable logging hooks."""
        from requestforge.hooks import (
            LoggingErrorHook,
            LoggingRequestHook,
            LoggingResponseHook,
        )

        self._request_hooks.append(
            LoggingRequestHook(log_headers, log_body, sensitive_keys)
        )
        self._response_hooks.append(LoggingResponseHook(log_headers, log_body))
        self._error_hooks.append(LoggingErrorHook())
        return self

    def build(self) -> HttpClientConfig:
        """Build the configuration."""
        return HttpClientConfig(
            base_url=self._base_url,
            default_timeout=self._default_timeout,
            default_headers=dict(self._default_headers),
            verify_ssl=self._verify_ssl,
            allow_redirects=self._allow_redirects,
            max_redirects=self._max_redirects,
            retry_strategy=self._retry_strategy,
            auth_hook=self._auth_hook,
            request_hooks=tuple(self._request_hooks),
            response_hooks=tuple(self._response_hooks),
            error_hooks=tuple(self._error_hooks),
            pool_connection=self._pool_connection,
            pool_maxsize=self._pool_maxsize,
        )
