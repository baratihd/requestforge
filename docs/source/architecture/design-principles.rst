Design Principles
=================

Request Forge is built following industry-standard design principles and patterns to ensure maintainability, extensibility, and robustness.

SOLID Principles
----------------

Single Responsibility Principle (SRP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Definition:** A class should have only one reason to change.

**Implementation:**

Each class in Request Forge has a single, well-defined responsibility:

* ``HttpClient`` - Execute HTTP requests
* ``HttpClientConfig`` - Hold configuration data
* ``TokenManager`` - Manage token lifecycle
* ``RetryStrategy`` - Determine retry behavior
* ``TokenStorage`` - Store and retrieve tokens

**Example:**

.. code-block:: python

    # Good ✅ - Single responsibility
    class TokenManager:
        """Manages token lifecycle: fetch, cache, refresh."""

        def get_token(self): ...
        def invalidate_token(self): ...
        def force_refresh(self): ...

    class TokenStorage:
        """Stores tokens: get, set, delete."""

        def get(self, key): ...
        def set(self, key, token): ...
        def delete(self, key): ...

    # Avoid ❌ - Multiple responsibilities
    class TokenManagerAndStorage:
        """Manages tokens AND stores them."""

        def get_token(self): ...
        def invalidate_token(self): ...
        def _store_token(self): ...
        def _retrieve_token(self): ...

**Benefits:**

* Easier to test (mock single responsibility)
* Easier to maintain (changes isolated)
* Better code organization

Open/Closed Principle (OCP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Definition:** Software entities should be open for extension but closed for modification.

**Implementation:**

Request Forge uses interfaces and abstract base classes to allow extension without modification:

.. code-block:: python

    # Base interface (closed for modification)
    class RetryStrategyInterface(ABC):
        @abstractmethod
        def should_retry(self, context, exception) -> bool: ...

        @abstractmethod
        def get_delay(self, context) -> float: ...

    # Built-in implementations
    class ExponentialBackoffRetryStrategy(RetryStrategyInterface): ...
    class CircuitBreakerRetryStrategy(RetryStrategyInterface): ...

    # Custom implementation (extension without modification)
    class MyCustomRetryStrategy(RetryStrategyInterface):
        def should_retry(self, context, exception) -> bool:
            # Custom logic
            return my_custom_logic(exception)

        def get_delay(self, context) -> float:
            return calculate_my_delay(context)

**Extension Points:**

* Retry strategies via ``RetryStrategyInterface``
* Hooks via ``RequestHookInterface``, ``ResponseHookInterface``, ``ErrorHookInterface``
* Token providers via ``TokenProviderInterface``
* Token storage via ``TokenStorageInterface``
* Token fetchers via ``TokenFetcherInterface``

**Benefits:**

* Add new behavior without changing existing code
* Maintain backward compatibility
* Reduce risk of breaking existing functionality

Liskov Substitution Principle (LSP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Definition:** Objects of a superclass should be replaceable with objects of a subclass without breaking the application.

**Implementation:**

All implementations of an interface can be used interchangeably:

.. code-block:: python

    # Any TokenStorageInterface can be substituted
    def create_token_manager(storage: TokenStorageInterface):
        return TokenManager(provider, storage)

    # All these work identically from caller's perspective
    manager1 = create_token_manager(InMemoryTokenStorage())
    manager2 = create_token_manager(DjangoCacheTokenStorage())
    manager3 = create_token_manager(RedisTokenStorage())

    # All behave the same
    token1 = manager1.get_token()
    token2 = manager2.get_token()
    token3 = manager3.get_token()

**Contract Preservation:**

.. code-block:: python

    class RetryStrategyInterface:
        """Contract: should_retry returns bool, get_delay returns non-negative float."""

        @abstractmethod
        def should_retry(self, context, exception) -> bool: ...

        @abstractmethod
        def get_delay(self, context) -> float: ...

    # Good ✅ - Preserves contract
    class CustomRetryStrategy(RetryStrategyInterface):
        def should_retry(self, context, exception) -> bool:
            return True  # Returns bool

        def get_delay(self, context) -> float:
            return 1.0  # Returns float >= 0

    # Bad ❌ - Violates contract
    class BadRetryStrategy(RetryStrategyInterface):
        def should_retry(self, context, exception) -> bool:
            return "yes"  # Returns string, not bool!

        def get_delay(self, context) -> float:
            return -1.0  # Returns negative, violates contract!

**Benefits:**

* Polymorphism works correctly
* Easier to swap implementations
* Predictable behavior

Interface Segregation Principle (ISP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Definition:** No client should be forced to depend on methods it does not use.

**Implementation:**

Request Forge uses focused, specific interfaces rather than large, monolithic ones:

.. code-block:: python

    # Good ✅ - Focused interfaces
    class RequestHookInterface:
        """Only for request modification."""
        def before_request(self, request, context): ...

    class ResponseHookInterface:
        """Only for response processing."""
        def after_response(self, response, context): ...

    class ErrorHookInterface:
        """Only for error handling."""
        def on_error(self, exception, context): ...

    # Avoid ❌ - Fat interface
    class HookInterface:
        """Forces implementation of all methods even if not needed."""
        def before_request(self, request, context): ...
        def after_response(self, response, context): ...
        def on_error(self, exception, context): ...

**Specialized Interfaces:**

.. code-block:: python

    # Implement only what you need
    class LoggingRequestHook(RequestHookInterface):
        """Only implements before_request."""
        def before_request(self, request, context):
            logger.info(f"Request: {request.url}")

    class MetricsResponseHook(ResponseHookInterface):
        """Only implements after_response."""
        def after_response(self, response, context):
            metrics.timing('request_duration', response.elapsed_ms)

**Benefits:**

* Simpler implementations
* Clearer intent
* Less coupling

Dependency Inversion Principle (DIP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Definition:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Implementation:**

Request Forge depends on interfaces, not concrete implementations:

.. code-block:: python

    # High-level class depends on abstractions
    class HttpClient:
        def __init__(
            self,
            config: HttpClientConfig,  # Concrete config is fine (data)
            session: requests.Session | None = None
        ):
            self._config = config
            self._session = session

            # Depends on interface, not concrete implementation
            self._retry_strategy: RetryStrategyInterface = config.retry_strategy
            self._auth_hook: AuthHookInterface = config.auth_hook

    # Good ✅ - Injection of abstraction
    class TokenManager:
        def __init__(
            self,
            provider: TokenProviderInterface,  # Abstraction
            storage: TokenStorageInterface     # Abstraction
        ):
            self._provider = provider
            self._storage = storage

    # Bad ❌ - Direct dependency on concrete class
    class TokenManager:
        def __init__(self):
            self._provider = ClientCredentialsTokenProvider(...)  # Concrete
            self._storage = InMemoryTokenStorage()                # Concrete

**Dependency Injection:**

.. code-block:: python

    # Dependencies injected, not created internally
    provider = ClientCredentialsTokenProvider(...)
    storage = DjangoCacheTokenStorage()
    token_manager = TokenManager(provider, storage)

    config = (
        HttpClientConfigBuilder()
        .with_token_auth(token_manager=token_manager)
        .with_retry_strategy(ExponentialBackoffRetryStrategy())
        .build()
    )

**Benefits:**

* Easy to test (inject mocks)
* Easy to swap implementations
* Loose coupling

Design Patterns
---------------

Builder Pattern
~~~~~~~~~~~~~~~

**Purpose:** Separate construction of complex objects from their representation.

**Implementation:** ``HttpClientConfigBuilder``

.. code-block:: python

    # Fluent builder for complex configuration
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .with_retry(max_retries=3)
        .with_bearer_token('token')
        .with_logging()
        .build()  # Returns immutable HttpClientConfig
    )

**Benefits:**

* Readable, fluent API
* Immutable result
* Validation at build time
* Optional parameters easy to handle

Strategy Pattern
~~~~~~~~~~~~~~~~

**Purpose:** Define a family of algorithms, encapsulate each one, and make them interchangeable.

**Implementation:** Retry strategies

.. code-block:: python

    # Strategy interface
    class RetryStrategyInterface:
        def should_retry(self, context, exception) -> bool: ...
        def get_delay(self, context) -> float: ...

    # Concrete strategies
    class NoRetryStrategy(RetryStrategyInterface): ...
    class SimpleRetryStrategy(RetryStrategyInterface): ...
    class ExponentialBackoffRetryStrategy(RetryStrategyInterface): ...
    class CircuitBreakerRetryStrategy(RetryStrategyInterface): ...

    # Context uses strategy
    class HttpClient:
        def __init__(self, config):
            self._retry_strategy = config.retry_strategy

        def request(self, request):
            # Strategy determines retry behavior
            if self._retry_strategy.should_retry(context, exception):
                delay = self._retry_strategy.get_delay(context)
                # Retry logic

**Benefits:**

* Runtime algorithm selection
* Easy to add new strategies
* Testable in isolation

Chain of Responsibility Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Pass request along a chain of handlers.

**Implementation:** Hooks pipeline

.. code-block:: python

    # Chain of request hooks
    request_hooks = [
        CorrelationIdHook(),
        LoggingRequestHook(),
        CustomHeaderHook()
    ]

    # Execute chain
    for hook in request_hooks:
        request = hook.before_request(request, context)

    # Chain of response hooks
    response_hooks = [
        RateLimitResponseHook(),
        LoggingResponseHook(),
        MetricsHook()
    ]

    for hook in response_hooks:
        response = hook.after_response(response, context)

**Benefits:**

* Flexible request/response processing
* Easy to add/remove handlers
* Each handler independent

Factory Pattern
~~~~~~~~~~~~~~~

**Purpose:** Create objects without specifying exact class.

**Implementation:** Client factory functions

.. code-block:: python

    def create_client(
        base_url: str = '',
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs
    ) -> HttpClient:
        """Factory function creates configured client."""
        builder = (
            HttpClientConfigBuilder()
            .with_base_url(base_url)
            .with_timeout(timeout)
            .with_retry(max_retries=max_retries)
        )

        # Additional configuration
        if kwargs.get('headers'):
            builder.with_headers(kwargs['headers'])

        return HttpClient(builder.build())

**Benefits:**

* Simple client creation
* Encapsulates configuration complexity
* Consistent defaults

Template Method Pattern
~~~~~~~~~~~~~~~~~~~~~~~

**Purpose:** Define skeleton of algorithm, let subclasses override specific steps.

**Implementation:** Token fetchers

.. code-block:: python

    class HttpTokenFetcher(TokenFetcherInterface):
        """Template for HTTP token fetching."""

        def fetch(self, context=None) -> TokenData:
            # Template method
            headers = self._build_request_headers(context)  # Hook
            data = self._build_request_data(context)        # Hook

            response = self._make_request(headers, data)    # Common

            return self._parse_response(response)           # Hook

        def _build_request_headers(self, context):
            """Override in subclass."""
            return {}

        def _build_request_data(self, context):
            """Override in subclass."""
            return {}

        def _parse_response(self, response):
            """Override in subclass."""
            raise NotImplementedError

    # Subclass overrides specific steps
    class CustomTokenFetcher(HttpTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'app_token' in context:
                headers['X-App-Token'] = context['app_token'].access_token
            return headers

**Benefits:**

* Code reuse
* Consistent structure
* Easy customization

Value Object Pattern
~~~~~~~~~~~~~~~~~~~~

**Purpose:** Immutable objects representing descriptive aspects.

**Implementation:** All models (HttpRequest, HttpResponse, TokenData, etc.)

.. code-block:: python

    @dataclass(frozen=True)
    class HttpRequest:
        """Immutable request representation."""
        method: HttpMethod
        url: str
        headers: dict | None = None
        # ... other fields

        def with_headers(self, headers: dict) -> HttpRequest:
            """Returns new instance with merged headers."""
            merged = {**(self.headers or {}), **headers}
            return HttpRequest(
                method=self.method,
                url=self.url,
                headers=merged,
                # ... copy other fields
            )

**Benefits:**

* Thread-safe (immutable)
* No side effects
* Easy to reason about

Immutability
------------

**Principle:** Data objects should not change after creation.

**Implementation:**

All data transfer objects (DTOs) are immutable:

.. code-block:: python

    # All frozen dataclasses
    @dataclass(frozen=True)
    class HttpRequest: ...

    @dataclass(frozen=True)
    class HttpResponse: ...

    @dataclass(frozen=True)
    class HttpClientConfig: ...

    @dataclass
    class TokenData: ...  # Effectively immutable in practice

**Benefits:**

* Thread-safe
* Prevents accidental mutations
* Makes data flow explicit
* Easier to debug

**Modification Pattern:**

.. code-block:: python

    # Cannot modify directly
    request = HttpRequest(method=HttpMethod.GET, url='/users')
    # request.headers = {'X-Custom': 'value'}  # ❌ Error: frozen

    # Create new instance with changes
    modified = request.with_headers({'X-Custom': 'value'})  # ✅

Separation of Concerns
----------------------

**Principle:** Different concerns should be in different modules/classes.

**Implementation:**

.. code-block:: text

    requestforge/
    ├── client.py         # HTTP execution
    ├── config.py         # Configuration
    ├── models.py         # Data models
    ├── retry.py          # Retry logic
    ├── hooks.py          # Lifecycle hooks
    ├── token_manager.py  # Token management
    ├── pipelines.py      # Multi-step auth
    ├── fetcher.py        # Token fetching
    ├── exceptions.py     # Error types
    └── utils.py          # Utilities

**Concerns:**

* **HTTP execution:** client.py
* **Configuration:** config.py
* **Data representation:** models.py
* **Retry logic:** retry.py
* **Request/response lifecycle:** hooks.py
* **Token management:** token_manager.py, pipelines.py, fetcher.py
* **Error handling:** exceptions.py
* **Utilities:** utils.py

**Benefits:**

* Easy to navigate codebase
* Easy to find relevant code
* Changes localized to specific modules

Fail-Fast Principle
-------------------

**Principle:** Validate early and fail immediately on invalid input.

**Implementation:**

.. code-block:: python

    # Configuration validation
    @dataclass(frozen=True)
    class HttpClientConfig:
        default_timeout: float = 30.0
        max_redirects: int = 10

        def __post_init__(self) -> None:
            # Fail fast on invalid configuration
            if self.default_timeout <= 0:
                raise ValueError('default_timeout must be positive')
            if self.max_redirects < 0:
                raise ValueError('max_redirects must be non-negative')

    # Token validation
    class TokenData:
        def __init__(self, access_token: str, ...):
            if not access_token:
                raise ValueError('access_token is required')
            self.access_token = access_token

**Benefits:**

* Catch errors early
* Clear error messages
* Easier debugging

Explicit over Implicit
-----------------------

**Principle:** Make behavior explicit rather than relying on magic or hidden behavior.

**Implementation:**

.. code-block:: python

    # Good ✅ - Explicit
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry(max_retries=3)
        .with_timeout(30.0)
        .with_bearer_token('token')
        .build()
    )

    # Avoid ❌ - Implicit/magic
    config = HttpClientConfig.from_env()  # Reads from environment variables
    # Where does base_url come from? What env vars? Not clear!

**Explicit Error Handling:**

.. code-block:: python

    # Explicit exception hierarchy
    try:
        response = client.get('/users')
    except TimeoutException:  # Explicit timeout error
        handle_timeout()
    except ConnectionException:  # Explicit connection error
        handle_connection_error()

**Benefits:**

* Code is self-documenting
* Easy to understand
* No hidden surprises

Composition over Inheritance
-----------------------------

**Principle:** Prefer object composition to class inheritance.

**Implementation:**

.. code-block:: python

    # Good ✅ - Composition
    class HttpClient:
        def __init__(self, config):
            self._config = config
            self._retry_strategy = config.retry_strategy  # Composed
            self._auth_hook = config.auth_hook            # Composed
            self._request_hooks = config.request_hooks    # Composed

    # Avoid ❌ - Deep inheritance
    class BaseClient: ...
    class RetryableClient(BaseClient): ...
    class AuthenticatedClient(RetryableClient): ...
    class LoggingClient(AuthenticatedClient): ...

**Benefits:**

* More flexible
* Easier to change behavior at runtime
* Avoids fragile base class problem

Type Safety
-----------

**Principle:** Use type hints for better IDE support and runtime safety.

**Implementation:**

.. code-block:: python

    # Full type annotations
    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs,
    ) -> HttpResponse:
        """Execute a GET request."""
        ...

    # Generic types
    T = TypeVar('T')

    def request_many(
        self,
        requests_list: list[HttpRequest],
        max_workers: int = 5,
        fail_fast: bool = False,
    ) -> Generator[tuple[int, HttpResponse | HttpClientException], None, None]:
        """Execute multiple requests concurrently."""
        ...

**Benefits:**

* IDE autocomplete
* Type checking with mypy
* Self-documenting code
* Catch errors before runtime

See Also
--------

* :doc:`components` - System components overview
* :doc:`thread-safety` - Thread-safety design
* :doc:`../contributing/code-style` - Code style guide
