"""
Request Forge - A production-ready Request Forge library.

This package provides a robust HTTP client with features like:
- Automatic retry with exponential backoff
- Token-based authentication with automatic refresh
- Request/response hooks for cross-cutting concerns
- Thread-safe session management
- Comprehensive error handling
"""

from requestforge.hooks import (
    BasicAuthHook,
    TokenAuthHook,
    ApiKeyAuthHook,
    LoggingErrorHook,
    AuthorizationHook,
    CompositeAuthHook,
    CorrelationIdHook,
    LoggingRequestHook,
    LoggingResponseHook,
    RateLimitResponseHook,
)
from requestforge.retry import (
    NoRetryStrategy,
    NoAuthRetryStrategy,
    SimpleRetryStrategy,
    SimpleAuthRetryStrategy,
    CircuitBreakerRetryStrategy,
    ConditionalAuthRetryStrategy,
    ExponentialAuthRetryStrategy,
    ExponentialBackoffRetryStrategy,
)
from requestforge.client import HttpClient, http_client, create_client
from requestforge.config import (
    TokenData,
    HttpClientConfig,
    HttpClientConfigBuilder,
)
from requestforge.models import (
    HttpMethod,
    HttpRequest,
    FetchContext,
    HttpResponse,
    RequestContext,
)
from requestforge.exceptions import (
    SSLException,
    TimeoutException,
    MaxRetryException,
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    ConnectionException,
    HttpClientException,
    HttpStatusException,
    ServerErrorException,
    RequestBuildException,
    UnauthorizedException,
    ResponseParseException,
    AuthenticationException,
)
from requestforge.interfaces import (
    AuthHookInterface,
    ErrorHookInterface,
    HttpClientInterface,
    HttpSessionInterface,
    RequestHookInterface,
    ResponseHookInterface,
    TokenFetcherInterface,
    TokenManagerInterface,
    TokenStorageInterface,
    RetryStrategyInterface,
    TokenProviderInterface,
    AuthRetryStrategyInterface,
)
from requestforge.token_manager import (
    TokenManager,
    InMemoryTokenStorage,
    PasswordGrantTokenProvider,
    ClientCredentialsTokenProvider,
)


__version__ = "1.0.0"

__all__ = [
    # Main client
    "HttpClient",
    "create_client",
    "http_client",
    # Configuration
    "HttpClientConfig",
    "HttpClientConfigBuilder",
    "TokenData",
    # Models
    "HttpMethod",
    "HttpRequest",
    "HttpResponse",
    "RequestContext",
    "FetchContext",
    # Exceptions
    "HttpClientException",
    "MaxRetryException",
    "TimeoutException",
    "ConnectionException",
    "ResponseParseException",
    "RequestBuildException",
    "SSLException",
    "AuthenticationException",
    "HttpStatusException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "BadRequestException",
    "ServerErrorException",
    # Hooks
    "LoggingRequestHook",
    "LoggingResponseHook",
    "LoggingErrorHook",
    "AuthorizationHook",
    "CorrelationIdHook",
    "RateLimitResponseHook",
    "TokenAuthHook",
    "ApiKeyAuthHook",
    "BasicAuthHook",
    "CompositeAuthHook",
    # Retry Strategies
    "NoRetryStrategy",
    "SimpleRetryStrategy",
    "ExponentialBackoffRetryStrategy",
    "CircuitBreakerRetryStrategy",
    "NoAuthRetryStrategy",
    "SimpleAuthRetryStrategy",
    "ExponentialAuthRetryStrategy",
    "ConditionalAuthRetryStrategy",
    # Token Management
    "TokenManager",
    "InMemoryTokenStorage",
    "ClientCredentialsTokenProvider",
    "PasswordGrantTokenProvider",
    # Interfaces
    "HttpClientInterface",
    "HttpSessionInterface",
    "RetryStrategyInterface",
    "RequestHookInterface",
    "ResponseHookInterface",
    "ErrorHookInterface",
    "AuthHookInterface",
    "AuthRetryStrategyInterface",
    "TokenStorageInterface",
    "TokenProviderInterface",
    "TokenManagerInterface",
    "TokenFetcherInterface",
]
