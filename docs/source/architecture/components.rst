Components Overview
===================

This page provides an overview of the major components in Request Forge and how they interact.

System Architecture
-------------------

High-Level Architecture
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────┐
    │                      Application Code                       │
    └────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                      Request Forge                            │
    │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
    │  │  Request       │→ │  Hook          │→ │  Auth        │   │
    │  │  Processing    │  │  Pipeline      │  │  Injection   │   │
    │  └────────────────┘  └────────────────┘  └──────────────┘   │
    │           ↓                   ↓                    ↓        │
    │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
    │  │  Retry         │  │  HTTP          │  │  Response    │   │
    │  │  Logic         │  │  Execution     │  │  Processing  │   │
    │  └────────────────┘  └────────────────┘  └──────────────┘   │
    └────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                   Token Management Layer                    │
    │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
    │  │  Token         │  │  Token         │  │  Token       │   │
    │  │  Manager       │  │  Provider      │  │  Storage     │   │
    │  └────────────────┘  └────────────────┘  └──────────────┘   │
    └────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
    ┌─────────────────────────────────────────────────────────────┐
    │              Multi-Step Authentication Pipeline             │
    │  ┌────────┐      ┌────────┐      ┌────────┐                 │
    │  │ Step 1 │  →   │ Step 2 │  →   │ Step 3 │                 │
    │  └────────┘      └────────┘      └────────┘                 │
    └────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                    External Services                        │
    │        (Auth Servers, APIs, Token Endpoints)                │
    └─────────────────────────────────────────────────────────────┘

Core Components
---------------

HttpClient
~~~~~~~~~~

**Responsibility:** Execute HTTP requests with retry logic and lifecycle hooks.

**Key Features:**

* Thread-safe session management
* Request/response/error hook execution
* Authentication injection
* Retry logic with multiple strategies
* Concurrent request execution
* Resource management

**Dependencies:**

* ``HttpClientConfig`` - Configuration
* ``RetryStrategyInterface`` - Retry logic
* ``AuthHookInterface`` - Authentication
* ``RequestHookInterface`` - Request hooks
* ``ResponseHookInterface`` - Response hooks
* ``ErrorHookInterface`` - Error hooks

**Interaction Diagram:**

.. code-block:: text

    Application
        ↓
    HttpClient.get('/users')
        ↓
    ┌─────────────────────────────────────┐
    │ 1. Execute request hooks            │
    │ 2. Execute auth hook (inject token) │
    │ 3. Execute HTTP request             │
    │ 4. Check for auth error (401)       │
    │    ├─ Yes → Refresh token & retry   │
    │    └─ No → Continue                 │
    │ 5. Check for retryable error        │
    │    ├─ Yes → Retry with backoff      │
    │    └─ No → Continue                 │
    │ 6. Execute response hooks           │
    │ 7. Return response                  │
    └─────────────────────────────────────┘

**Example:**

.. code-block:: python

    config = HttpClientConfigBuilder().build()
    client = HttpClient(config)
    response = client.get('/users')

HttpClientConfig
~~~~~~~~~~~~~~~~

**Responsibility:** Hold immutable configuration data.

**Key Features:**

* Immutable (frozen dataclass)
* Validation on creation
* Default values
* Type-safe attributes

**Attributes:**

* ``base_url`` - Base URL for requests
* ``default_timeout`` - Default timeout
* ``default_headers`` - Default headers
* ``verify_ssl`` - SSL verification
* ``retry_strategy`` - Retry strategy instance
* ``auth_hook`` - Authentication hook
* ``request_hooks`` - Request hooks tuple
* ``response_hooks`` - Response hooks tuple
* ``error_hooks`` - Error hooks tuple

**Created via:** ``HttpClientConfigBuilder``

HttpClientConfigBuilder
~~~~~~~~~~~~~~~~~~~~~~~

**Responsibility:** Build HttpClientConfig using fluent interface.

**Key Features:**

* Fluent API (method chaining)
* Validation at build time
* Sensible defaults
* Helper methods for common configurations

**Example:**

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .with_retry(max_retries=3)
        .with_bearer_token('token')
        .build()
    )

Retry Components
----------------

RetryStrategyInterface
~~~~~~~~~~~~~~~~~~~~~~

**Responsibility:** Define retry behavior.

**Key Methods:**

* ``should_retry(context, exception)`` - Determine if should retry
* ``get_delay(context)`` - Calculate delay before retry
* ``max_retries`` - Maximum retry attempts

**Implementations:**

* ``NoRetryStrategy`` - No retries
* ``SimpleRetryStrategy`` - Fixed delay
* ``ExponentialBackoffRetryStrategy`` - Exponential backoff with jitter
* ``CircuitBreakerRetryStrategy`` - Circuit breaker pattern

**Interaction:**

.. code-block:: text

    Request fails
        ↓
    RetryStrategy.should_retry(context, exception)
        ↓
    if True:
        delay = RetryStrategy.get_delay(context)
        sleep(delay)
        retry request
    else:
        raise MaxRetryException

Hook Components
---------------

Hook Pipeline
~~~~~~~~~~~~~

**Responsibility:** Execute hooks in order during request lifecycle.

**Hook Types:**

1. **RequestHookInterface** - Modify requests before sending
2. **ResponseHookInterface** - Process responses after receiving
3. **ErrorHookInterface** - Handle errors during lifecycle
4. **AuthHookInterface** - Manage authentication

**Execution Flow:**

.. code-block:: text

    Request initiated
        ↓
    Execute request hooks (in order)
        hook1.before_request()
        hook2.before_request()
        hook3.before_request()
        ↓
    Execute auth hook
        auth_hook.before_request()
        ↓
    HTTP request sent
        ↓
    Response received
        ↓
    Execute response hooks (in order)
        hook1.after_response()
        hook2.after_response()
        hook3.after_response()
        ↓
    Return response

    (On error)
        ↓
    Execute error hooks (in order)
        hook1.on_error()
        hook2.on_error()
        hook3.on_error()

Built-in Hooks
~~~~~~~~~~~~~~

**Request Hooks:**

* ``LoggingRequestHook`` - Log outgoing requests
* ``CorrelationIdHook`` - Add correlation IDs
* ``AuthorizationHook`` - Dynamic authorization

**Response Hooks:**

* ``LoggingResponseHook`` - Log incoming responses
* ``RateLimitResponseHook`` - Parse rate limit headers

**Error Hooks:**

* ``LoggingErrorHook`` - Log errors

**Auth Hooks:**

* ``TokenAuthHook`` - Token-based auth with refresh
* ``ApiKeyAuthHook`` - API key auth
* ``BasicAuthHook`` - HTTP Basic auth
* ``CompositeAuthHook`` - Combine multiple auth methods

Token Management Components
---------------------------

TokenManager
~~~~~~~~~~~~

**Responsibility:** Manage token lifecycle with caching.

**Key Features:**

* Automatic token caching
* Thread-safe token refresh
* Prevents concurrent fetches
* Expiration handling

**Dependencies:**

* ``TokenProviderInterface`` - Fetches tokens
* ``TokenStorageInterface`` - Stores tokens

**Flow:**

.. code-block:: text

    get_token()
        ↓
    Check storage for cached token
        ↓
    if cached and not expired:
        return cached token
    else:
        ↓
        Lock (prevent concurrent fetches)
            ↓
        Double-check cache
            ↓
        if still need new token:
            ↓
            provider.fetch_token() or provider.refresh_token()
                ↓
            Store in cache
                ↓
            Return new token

TokenProviderInterface
~~~~~~~~~~~~~~~~~~~~~~

**Responsibility:** Fetch and refresh tokens.

**Key Methods:**

* ``fetch_token()`` - Fetch new token
* ``refresh_token(current)`` - Refresh existing token
* ``service_name`` - Service identifier

**Implementations:**

* ``ClientCredentialsTokenProvider`` - OAuth2 client credentials
* ``PasswordGrantTokenProvider`` - OAuth2 password grant
* ``PipelineTokenProvider`` - Wraps multi-step pipeline
* Custom implementations

TokenStorageInterface
~~~~~~~~~~~~~~~~~~~~~

**Responsibility:** Store and retrieve tokens.

**Key Methods:**

* ``get(key)`` - Retrieve token
* ``set(key, token)`` - Store token
* ``delete(key)`` - Delete token
* ``exists(key)`` - Check existence

**Implementations:**

* ``InMemoryTokenStorage`` - In-memory storage (single process)
* ``DjangoCacheTokenStorage`` - Django cache (multi-process)
* Custom implementations (Redis, Memcached, etc.)

**Storage Comparison:**

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Storage
     - Scope
     - Persistence
     - Use Case
   * - InMemoryTokenStorage
     - Single process
     - Lost on restart
     - Development, single-instance
   * - DjangoCacheTokenStorage
     - Multi-process
     - Depends on backend
     - Production, multi-instance
   * - RedisTokenStorage
     - Multi-process
     - Persistent
     - Production, high availability

Multi-Step Authentication Components
-------------------------------------

TokenFetchPipeline
~~~~~~~~~~~~~~~~~~

**Responsibility:** Execute multi-step token fetching with dependencies.

**Key Features:**

* Dependency resolution
* Per-step caching
* Selective invalidation
* Cascading invalidation

**Dependencies:**

* ``TokenFetcherInterface`` - Individual fetch steps
* ``TokenStorageInterface`` - Cache storage

**Execution Flow:**

.. code-block:: text

    pipeline.execute()
        ↓
    For each step in order:
        ↓
        Check cache
            ↓
        if cached and valid:
            Use cached token
        else:
            ↓
            Verify dependencies available
                ↓
            Fetch new token (passing dependency tokens)
                ↓
            Cache with step's TTL
                ↓
            Add to context for next steps
        ↓
    Return final token

**Example:**

.. code-block:: text

    Step 1: device_token (no deps)
        → Fetch → Cache (30 days)
            ↓
    Step 2: app_token (depends on device_token)
        → Fetch using device_token → Cache (1 hour)
            ↓
    Step 3: user_token (depends on app_token)
        → Fetch using app_token → Cache (15 min)
            ↓
    Return user_token

TokenFetcherInterface
~~~~~~~~~~~~~~~~~~~~~

**Responsibility:** Fetch a single token in a pipeline step.

**Key Methods:**

* ``fetch(context)`` - Fetch token with dependency context
* ``name`` - Step name
* ``depends_on`` - Dependency step names
* ``ttl`` - Cache TTL for this step

**Implementations:**

* ``HeaderTokenFetcher`` - Extract from response headers
* ``BodyTokenFetcher`` - Extract from response body (JSON)
* Custom implementations

PipelineTokenProvider
~~~~~~~~~~~~~~~~~~~~~

**Responsibility:** Wrap TokenFetchPipeline as TokenProviderInterface.

**Purpose:** Allow pipeline to be used with TokenManager.

**Example:**

.. code-block:: python

    pipeline = TokenFetchPipeline(steps=[...], storage=storage)
    provider = PipelineTokenProvider(pipeline, 'myapp')
    token_manager = TokenManager(provider)

Data Models
-----------

HttpRequest
~~~~~~~~~~~

**Responsibility:** Represent an HTTP request (immutable).

**Key Attributes:**

* ``method`` - HTTP method
* ``url`` - Request URL
* ``headers`` - Request headers
* ``params`` - Query parameters
* ``json_data`` - JSON body
* ``data`` - Form data
* ``timeout`` - Request timeout

**Methods:**

* ``with_headers(headers)`` - Create copy with additional headers
* ``to_dict()`` - Convert to dictionary
* ``to_curl()`` - Convert to cURL command

HttpResponse
~~~~~~~~~~~~

**Responsibility:** Represent an HTTP response (immutable).

**Key Attributes:**

* ``status_code`` - HTTP status code
* ``headers`` - Response headers
* ``content`` - Raw bytes
* ``elapsed_ms`` - Request duration
* ``url`` - Final URL
* ``request`` - Original request

**Properties:**

* ``text`` - Decoded content
* ``is_success`` - 2xx status
* ``is_client_error`` - 4xx status
* ``is_server_error`` - 5xx status

**Methods:**

* ``json()`` - Parse JSON
* ``json_or_none()`` - Safe JSON parse

RequestContext
~~~~~~~~~~~~~~

**Responsibility:** Track request lifecycle state (mutable).

**Key Attributes:**

* ``request`` - The HTTP request
* ``attempt`` - Current attempt number
* ``max_retries`` - Maximum retries
* ``metadata`` - Additional context data

**Methods:**

* ``increment_attempt()`` - Increment attempt counter
* ``is_retry`` - Check if retry

TokenData
~~~~~~~~~

**Responsibility:** Represent token data (immutable).

**Key Attributes:**

* ``access_token`` - Token string
* ``token_type`` - Token type
* ``expires_at`` - Expiration datetime
* ``refresh_token`` - Refresh token
* ``scope`` - Token scope

**Properties:**

* ``is_expired`` - Check expiration
* ``authorization_header`` - Get header value

**Methods:**

* ``from_response(data)`` - Create from API response

Component Interactions
----------------------

Request Flow
~~~~~~~~~~~~

.. code-block:: text

    Application
        ↓
    client.get('/users')
        ↓
    HttpClient
        ├─→ Request Hooks
        │   └─→ Modify request
        ├─→ Auth Hook
        │   ├─→ TokenManager.get_token()
        │   │   ├─→ Check TokenStorage
        │   │   └─→ TokenProvider.fetch_token() if needed
        │   └─→ Inject token into headers
        ├─→ Execute HTTP request
        ├─→ Check response
        │   ├─→ If 401: Refresh token & retry
        │   └─→ If retryable: RetryStrategy determines retry
        ├─→ Response Hooks
        │   └─→ Process response
        └─→ Return HttpResponse

Token Management Flow
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

    TokenAuthHook.before_request()
        ↓
    TokenManager.get_token()
        ↓
    Check TokenStorage
        ↓
    if cached and valid:
        return cached
    else:
        ↓
        TokenProvider.fetch_token()
            ↓
        (If PipelineTokenProvider)
            ↓
        TokenFetchPipeline.execute()
            ↓
        For each step:
            ↓
            TokenFetcher.fetch(context)
                ↓
            HTTP request to auth endpoint
                ↓
            Parse response
                ↓
            Return TokenData
                ↓
            Store in TokenStorage
                ↓
        Return final token
            ↓
        Store in TokenStorage
            ↓
        Return token

Thread Safety
-------------

**Thread-Safe Components:**

* ``HttpClient`` - Thread-local sessions
* ``TokenManager`` - Locking for token refresh
* ``InMemoryTokenStorage`` - RLock for dictionary access
* ``TokenFetchPipeline`` - Lock-free (relies on storage locking)

**Not Thread-Safe (by design):**

* ``HttpRequest`` - Immutable (inherently thread-safe)
* ``HttpResponse`` - Immutable (inherently thread-safe)
* ``HttpClientConfig`` - Immutable (inherently thread-safe)
* ``TokenData`` - Immutable (inherently thread-safe)

See :doc:`thread-safety` for detailed thread-safety analysis.

Extension Points
----------------

Applications can extend Request Forge by:

1. **Custom Retry Strategies**

   .. code-block:: python

       class CustomRetryStrategy(RetryStrategyInterface):
           def should_retry(self, context, exception): ...
           def get_delay(self, context): ...

2. **Custom Hooks**

   .. code-block:: python

       class CustomRequestHook(RequestHookInterface):
           def before_request(self, request, context): ...

3. **Custom Token Providers**

   .. code-block:: python

       class CustomTokenProvider(TokenProviderInterface):
           def fetch_token(self): ...
           def refresh_token(self, current): ...

4. **Custom Token Storage**

   .. code-block:: python

       class CustomTokenStorage(TokenStorageInterface):
           def get(self, key): ...
           def set(self, key, token): ...

5. **Custom Token Fetchers**

   .. code-block:: python

       class CustomTokenFetcher(TokenFetcherInterface):
           def fetch(self, context): ...

See Also
--------

* :doc:`design-principles` - Design principles
* :doc:`thread-safety` - Thread-safety design
* :doc:`../api-reference/client` - Client API
* :doc:`../api-reference/token-manager` - Token management API
