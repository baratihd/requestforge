Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased
----------

Planned features for future releases.

Planned Features
~~~~~~~~~~~~~~~~

* Async/await support with httpx backend
* Response caching layer
* GraphQL client wrapper
* WebSocket support
* Request signing (AWS Signature V4, OAuth 1.0)
* Additional storage backends (Redis direct, Memcached)
* Metrics exporters (Prometheus, StatsD)
* OpenTelemetry integration
* Circuit breaker dashboard
* Rate limiter component

[1.0.0] - 2026-05-25
--------------------

Initial production release.

Added
~~~~~

**Core Features:**

* Production-ready HTTP client with thread-safe session management
* Full support for GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS methods
* Configurable connection pooling (max connections and pool size)
* Type-safe immutable request/response models
* Context manager support for automatic resource cleanup
* Fluent builder pattern for configuration

**Retry Strategies:**

* ``NoRetryStrategy`` - Fail immediately without retries
* ``SimpleRetryStrategy`` - Fixed delay between retry attempts
* ``ExponentialBackoffRetryStrategy`` - Exponential backoff with configurable jitter
* ``CircuitBreakerRetryStrategy`` - Circuit breaker pattern implementation
* Custom retry strategy interface for implementing custom logic
* Retry on configurable HTTP status codes (408, 429, 500, 502, 503, 504)

**Authentication:**

* Bearer token authentication
* API key authentication with custom headers
* HTTP Basic authentication
* Token manager with automatic caching and refresh
* Multi-step authentication pipeline for complex flows
* Automatic retry on 401/403 with token refresh
* Path exclusion support (exact match and glob patterns)
* Multiple authentication retry strategies

**Token Management:**

* ``InMemoryTokenStorage`` - Thread-safe in-memory storage
* ``DjangoCacheTokenStorage`` - Django cache backend integration
* ``ClientCredentialsTokenProvider`` - OAuth2 client credentials flow
* ``PasswordGrantTokenProvider`` - OAuth2 password grant flow
* Custom token provider interface
* Automatic token expiration handling with 30-second buffer

**Token Fetchers:**

* ``HeaderTokenFetcher`` - Extract tokens from response headers
* ``BodyTokenFetcher`` - Extract tokens from JSON/form response bodies
* Custom token fetcher base class
* Multi-step pipeline support with dependency resolution
* Per-step caching with configurable TTL
* Cascading invalidation for dependent steps

**Lifecycle Hooks:**

* Request hooks for modifying requests before sending
* Response hooks for processing responses after receiving
* Error hooks for handling errors during lifecycle
* Built-in logging hooks with PII masking
* Correlation ID hook for distributed tracing
* Rate limit response hook
* Custom hook interface for implementing custom behavior

**Error Handling:**

* Comprehensive exception hierarchy
* ``HttpClientException`` - Base exception for all HTTP errors
* ``MaxRetryException`` - Raised when max retries exceeded
* ``TimeoutException`` - Request timeout errors
* ``ConnectionException`` - Network connection failures
* ``SSLException`` - SSL/TLS errors
* ``AuthenticationException`` - Authentication failures
* ``HttpStatusException`` - HTTP status code errors (4xx, 5xx)
* Status-specific exceptions (400, 401, 403, 404, 5xx)
* Detailed error context and original exception preservation

**Concurrency:**

* ``request_many()`` for executing multiple requests in parallel
* ThreadPoolExecutor-based concurrent execution
* Configurable number of worker threads
* Fail-fast mode for stopping on first error
* Results returned in original request order

**Developer Experience:**

* Full type hints throughout the codebase
* Comprehensive docstrings in Google style
* ``to_curl()`` utility for debugging
* Standard library logging integration
* Request context propagation
* Immutable data models for thread safety

**Testing:**

* 500+ test cases across all modules
* 95%+ code coverage
* Pytest-based test suite
* responses library integration for HTTP mocking
* Tox support for multi-version testing
* Type checking with mypy compatibility

**Code Quality:**

* Ruff for linting and formatting
* Pre-commit hooks for automatic quality checks
* SOLID principles throughout
* Design patterns: Builder, Strategy, Chain of Responsibility, Factory
* Thread-safe implementation

**Documentation:**

* Comprehensive README with examples
* API documentation in docstrings
* Architecture documentation
* User guides for all major features
* Examples for common use cases
* Contributing guidelines

Dependencies
~~~~~~~~~~~~

* requests >= 2.31.0 (only production dependency)

Supported Python Versions
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Python 3.10
* Python 3.11
* Python 3.12
* Python 3.13

Security
~~~~~~~~

* Automatic sensitive header masking in logs
* SSL certificate verification enabled by default
* Token expiration validation with 30-second buffer
* No credentials stored in logs

Performance
~~~~~~~~~~~

* Connection pooling reduces overhead
* Per-step token caching minimizes API calls
* Lazy client initialization
* Thread-local session management
* Efficient retry with exponential backoff

Breaking Changes
~~~~~~~~~~~~~~~~

None (initial release)

Deprecated
~~~~~~~~~~

None (initial release)

[0.1.0-beta] - 2026-01-01
--------------------------

Beta release for testing and feedback.

Added
~~~~~

* Initial beta release for community testing
* Core HTTP client functionality
* Basic authentication support
* Simple retry logic
* Fundamental error handling

Known Issues
~~~~~~~~~~~~

* Limited test coverage (< 70%)
* Missing Django cache support
* No multi-step authentication
* Documentation incomplete

Fixed
~~~~~

None

Version History
---------------

* **1.0.0** (2026-05-25) - Production release
* **0.1.0-beta** (2026-01-01) - Beta release

Version Numbering
-----------------

This project uses `Semantic Versioning <https://semver.org/>`_:

* **MAJOR** version for incompatible API changes
* **MINOR** version for backwards-compatible functionality additions
* **PATCH** version for backwards-compatible bug fixes

Migration Guides
----------------

Migrating from 0.1.0-beta to 1.0.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Configuration Changes:**

.. code-block:: python

    # Old (0.1.0-beta)
    client = HttpClient(base_url='https://api.example.com')

    # New (1.0.0)
    config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
    client = HttpClient(config)

**Authentication Changes:**

.. code-block:: python

    # Old (0.1.0-beta)
    client = HttpClient(token='bearer-token')

    # New (1.0.0)
    config = (
        HttpClientConfigBuilder()
        .with_bearer_token('bearer-token')
        .build()
    )
    client = HttpClient(config)

**Retry Changes:**

.. code-block:: python

    # Old (0.1.0-beta)
    client = HttpClient(max_retries=3)

    # New (1.0.0)
    config = (
        HttpClientConfigBuilder()
        .with_retry(max_retries=3)
        .build()
    )
    client = HttpClient(config)

Links
-----

* `PyPI Package <https://pypi.org/project/requestforge/>`_
* `GitHub Repository <https://github.com/baratihd/requestforge>`_
* `Documentation <https://requestforge.readthedocs.io>`_
* `Issue Tracker <https://github.com/baratihd/requestforge/issues>`_
* `Changelog (Markdown) <https://github.com/baratihd/requestforge/blob/main/CHANGELOG.md>`_
