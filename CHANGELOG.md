# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features
- Async/await support with httpx backend
- Response caching layer
- GraphQL client wrapper
- WebSocket support
- Request signing (AWS Signature V4, OAuth 1.0)
- Additional storage backends (Redis, Memcached)
- Metrics exporters (Prometheus, StatsD)
- OpenTelemetry integration
- Circuit breaker dashboard

---

## [1.0.0] - 2026-05-25

### Added

#### Core Features
- **HTTP Client**: Production-ready HTTP client with thread-safe session management
- **HTTP Methods**: Full support for GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- **Connection Pooling**: Configurable connection pool with max connections and pool size
- **Immutable Models**: Type-safe request/response models with validation
- **Context Managers**: Clean resource management with `with` statement support
- **Builder Pattern**: Fluent configuration interface for easy setup

#### Retry Strategies
- **NoRetryStrategy**: Fail immediately without retries
- **SimpleRetryStrategy**: Fixed delay between retry attempts
- **ExponentialBackoffRetryStrategy**: Exponential backoff with jitter
- **CircuitBreakerRetryStrategy**: Circuit breaker pattern implementation
- **Custom Strategies**: Interface for implementing custom retry logic

#### Authentication
- **Bearer Token**: Simple bearer token authentication
- **API Key**: API key authentication with custom headers
- **Basic Auth**: HTTP Basic authentication
- **Token Manager**: Automatic token caching and refresh
- **Multi-Step Auth**: Pipeline-based authentication for complex flows
- **Auth Retry**: Automatic retry on 401/403 with token refresh
- **Path Exclusion**: Exclude specific paths from authentication

#### Token Management
- **InMemoryTokenStorage**: Thread-safe in-memory token storage
- **DjangoCacheTokenStorage**: Django cache backend integration
- **ClientCredentialsTokenProvider**: OAuth2 client credentials flow
- **PasswordGrantTokenProvider**: OAuth2 password grant flow
- **Custom Providers**: Interface for custom token providers

#### Token Fetchers
- **HeaderTokenFetcher**: Extract tokens from response headers
- **BodyTokenFetcher**: Extract tokens from JSON/form response bodies
- **Custom Fetchers**: Base class for implementing custom fetchers
- **Multi-Step Pipelines**: Chain multiple token fetchers with dependencies
- **Per-Step Caching**: Independent caching with configurable TTL
- **Dependency Resolution**: Automatic execution order based on dependencies
- **Cascading Invalidation**: Invalidating a step clears dependent steps

#### Lifecycle Hooks
- **Request Hooks**: Modify requests before sending
- **Response Hooks**: Process responses after receiving
- **Error Hooks**: Handle errors during request lifecycle
- **LoggingRequestHook**: Built-in request logging with PII masking
- **LoggingResponseHook**: Built-in response logging
- **LoggingErrorHook**: Built-in error logging
- **CorrelationIdHook**: Automatic correlation ID injection
- **RateLimitResponseHook**: Parse rate limit headers
- **Custom Hooks**: Interface for implementing custom hooks

#### Error Handling
- **Exception Hierarchy**: Comprehensive custom exception types
- **HttpClientException**: Base exception for all HTTP errors
- **MaxRetryException**: Raised when max retries exceeded
- **TimeoutException**: Request timeout errors
- **ConnectionException**: Network connection failures
- **SSLException**: SSL/TLS errors
- **AuthenticationException**: Authentication failures
- **HttpStatusException**: HTTP status code errors
- **Status-Specific Exceptions**: 400, 401, 403, 404, 500 specific exceptions
- **Error Context**: Detailed error context and original exception preservation

#### Concurrency
- **ThreadPoolExecutor**: Built-in concurrent request execution
- **request_many()**: Execute multiple requests in parallel
- **Fail-Fast Mode**: Stop on first error or collect all results
- **Result Ordering**: Results returned in request order

#### Developer Experience
- **Type Hints**: Full type annotations throughout
- **Docstrings**: Comprehensive documentation in code
- **to_curl()**: Convert requests to cURL commands for debugging
- **Logging Integration**: Standard library logging support
- **Context Propagation**: Request metadata and correlation IDs

#### Testing
- **500+ Test Cases**: Comprehensive test coverage
- **95%+ Coverage**: High code coverage across all modules
- **Pytest Integration**: Full pytest test suite
- **Mock Support**: responses library integration
- **Tox Support**: Multi-version Python testing
- **Type Checking**: mypy type checking

#### Code Quality
- **Ruff**: Modern linting and formatting
- **Pre-commit Hooks**: Automatic code quality checks
- **SOLID Principles**: Clean architecture
- **Design Patterns**: Builder, Strategy, Chain of Responsibility
- **Thread Safety**: Safe for multi-threaded environments

### Dependencies
- requests >= 2.31.0 (only production dependency)

### Supported Python Versions
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

### Breaking Changes
- None (initial release)

### Deprecated
- None (initial release)

### Security
- Automatic sensitive header masking in logs
- SSL certificate verification enabled by default
- Token expiration validation with 30-second buffer

### Performance
- Connection pooling reduces overhead
- Per-step token caching minimizes API calls
- Lazy client initialization
- Thread-local session management

### Documentation
- Complete README.md with examples
- API documentation in docstrings
- Migration guide from vanilla requests
- Architecture documentation
- Contributing guidelines

---

## [0.1.0-beta] - 2026-01-01

### Added
- Initial beta release for testing
- Core Request Forge functionality
- Basic authentication support
- Simple retry logic

### Known Issues
- Limited test coverage
- Missing Django cache support
- No multi-step authentication

---

## Version Numbering

This project uses Semantic Versioning:
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

---

## Links

- [PyPI Package](https://pypi.org/project/requestforge/)
- [GitHub Repository](https://github.com/baratihd/requestforge)
- [Documentation](https://requestforge.readthedocs.io)
- [Issue Tracker](https://github.com/baratihd/requestforge/issues)
