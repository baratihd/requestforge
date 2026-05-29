Configuration API Reference
===========================

This page documents the configuration classes and builders for HTTP Client.

TokenData
---------

.. class:: TokenData(access_token, token_type='Bearer', expires_at=None, refresh_token=None, scope=None, extra=None)

   Immutable token data container.

   :param str access_token: The access token string
   :param str token_type: Token type (default: 'Bearer')
   :param datetime expires_at: Token expiration datetime (optional)
   :param str refresh_token: Refresh token (optional)
   :param str scope: Token scope (optional)
   :param dict extra: Additional token metadata (optional)

Attributes
~~~~~~~~~~

.. attribute:: TokenData.access_token
   :type: str

   The access token string.

.. attribute:: TokenData.token_type
   :type: str

   Token type (e.g., 'Bearer', 'Basic').

.. attribute:: TokenData.expires_at
   :type: datetime | None

   Token expiration datetime.

.. attribute:: TokenData.refresh_token
   :type: str | None

   Refresh token for obtaining new access tokens.

.. attribute:: TokenData.scope
   :type: str | None

   Token scope/permissions.

.. attribute:: TokenData.extra
   :type: dict[str, Any]

   Additional token metadata.

Properties
~~~~~~~~~~

.. attribute:: TokenData.is_expired
   :type: bool

   Check if token is expired (with 30 second buffer).

   **Example:**

   .. code-block:: python

       if token.is_expired:
           print("Token needs refresh")

.. attribute:: TokenData.authorization_header
   :type: str

   Get the authorization header value.

   **Example:**

   .. code-block:: python

       token = TokenData(access_token='abc123', token_type='Bearer')
       print(token.authorization_header)  # 'Bearer abc123'

Class Methods
~~~~~~~~~~~~~

.. classmethod:: TokenData.from_response(data, expires_in_key='expires_in', access_token_key='access_token', refresh_token_key='refresh_token', token_type_key='token_type')

   Create TokenData from API response.

   :param dict data: Response data dictionary
   :param str expires_in_key: Key for expires_in field
   :param str access_token_key: Key for access_token field
   :param str refresh_token_key: Key for refresh_token field
   :param str token_type_key: Key for token_type field
   :returns: TokenData instance
   :rtype: TokenData

   **Example:**

   .. code-block:: python

       response_data = {
           'access_token': 'abc123',
           'token_type': 'Bearer',
           'expires_in': 3600,
           'refresh_token': 'xyz789',
           'scope': 'read write'
       }

       token = TokenData.from_response(response_data)

       print(token.access_token)     # 'abc123'
       print(token.token_type)       # 'Bearer'
       print(token.expires_at)       # datetime object (now + 3600s)
       print(token.refresh_token)    # 'xyz789'

   **Custom Field Names:**

   .. code-block:: python

       # For APIs with different field names
       response_data = {
           'token': 'abc123',
           'type': 'Bearer',
           'ttl': 3600
       }

       token = TokenData.from_response(
           response_data,
           access_token_key='token',
           token_type_key='type',
           expires_in_key='ttl'
       )

HttpClientConfig
----------------

.. class:: HttpClientConfig(base_url='', default_timeout=30.0, default_headers=None, verify_ssl=True, allow_redirects=True, max_redirects=10, retry_strategy=None, auth_hook=None, request_hooks=(), response_hooks=(), error_hooks=(), pool_connection=10, pool_maxsize=20)

   Immutable configuration container for HTTP client settings.

   **Note:** This class is frozen (immutable). Use :class:`HttpClientConfigBuilder` to create instances.

   :param str base_url: Base URL for all requests
   :param float default_timeout: Default timeout in seconds
   :param dict default_headers: Default headers for all requests
   :param bool verify_ssl: SSL certificate verification
   :param bool allow_redirects: Follow HTTP redirects
   :param int max_redirects: Maximum redirect hops
   :param RetryStrategyInterface retry_strategy: Retry strategy
   :param AuthHookInterface auth_hook: Authentication hook
   :param tuple request_hooks: Request hooks
   :param tuple response_hooks: Response hooks
   :param tuple error_hooks: Error hooks
   :param int pool_connection: Connection pool size
   :param int pool_maxsize: Maximum pool size

Attributes
~~~~~~~~~~

.. attribute:: HttpClientConfig.base_url
   :type: str

   Base URL for all requests.

.. attribute:: HttpClientConfig.default_timeout
   :type: float

   Default timeout in seconds.

.. attribute:: HttpClientConfig.default_headers
   :type: dict[str, str]

   Default headers included in all requests.

.. attribute:: HttpClientConfig.verify_ssl
   :type: bool

   Whether to verify SSL certificates.

.. attribute:: HttpClientConfig.allow_redirects
   :type: bool

   Whether to follow HTTP redirects.

.. attribute:: HttpClientConfig.max_redirects
   :type: int

   Maximum number of redirect hops.

.. attribute:: HttpClientConfig.retry_strategy
   :type: RetryStrategyInterface | None

   Retry strategy implementation.

.. attribute:: HttpClientConfig.auth_hook
   :type: AuthHookInterface | None

   Authentication hook.

.. attribute:: HttpClientConfig.request_hooks
   :type: tuple[RequestHookInterface, ...]

   Request lifecycle hooks.

.. attribute:: HttpClientConfig.response_hooks
   :type: tuple[ResponseHookInterface, ...]

   Response lifecycle hooks.

.. attribute:: HttpClientConfig.error_hooks
   :type: tuple[ErrorHookInterface, ...]

   Error handling hooks.

.. attribute:: HttpClientConfig.pool_connection
   :type: int

   Connection pool size.

.. attribute:: HttpClientConfig.pool_maxsize
   :type: int

   Maximum connection pool size.

Validation
~~~~~~~~~~

The configuration validates on creation:

.. code-block:: python

    # Raises ValueError
    HttpClientConfig(default_timeout=-1)      # Must be positive
    HttpClientConfig(max_redirects=-1)        # Must be non-negative

HttpClientConfigBuilder
-----------------------

.. class:: HttpClientConfigBuilder()

   Fluent builder for creating HttpClientConfig instances.

   Implements the Builder pattern for flexible, readable configuration.

Basic Configuration
~~~~~~~~~~~~~~~~~~~

.. method:: with_base_url(url)

   Set base URL for all requests.

   :param str url: Base URL
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_base_url('https://api.example.com')

.. method:: with_timeout(timeout)

   Set default timeout in seconds.

   :param float timeout: Timeout in seconds
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_timeout(60.0)

.. method:: with_verify_ssl(verify)

   Set SSL verification.

   :param bool verify: Whether to verify SSL certificates
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_verify_ssl(True)

.. method:: with_redirects(allow=True, max_redirects=10)

   Configure redirect behavior.

   :param bool allow: Whether to follow redirects
   :param int max_redirects: Maximum redirect hops
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_redirects(allow=True, max_redirects=5)

Headers Configuration
~~~~~~~~~~~~~~~~~~~~~

.. method:: with_headers(headers)

   Set default headers.

   :param dict headers: Headers dictionary
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_headers({
           'User-Agent': 'MyApp/1.0',
           'Accept': 'application/json'
       })

.. method:: with_header(name, value)

   Add a single default header.

   :param str name: Header name
   :param str value: Header value
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_header('User-Agent', 'MyApp/1.0')

.. method:: with_bearer_token(token)

   Add Bearer token authorization header.

   :param str token: Bearer token
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_bearer_token('your-api-token')

.. method:: with_api_key(api_key, header_name='X-API-Key')

   Add API key header.

   :param str api_key: API key value
   :param str header_name: Header name (default: 'X-API-Key')
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_api_key('your-key', header_name='X-API-Key')

Retry Configuration
~~~~~~~~~~~~~~~~~~~

.. method:: with_retry_strategy(strategy)

   Set retry strategy.

   :param RetryStrategyInterface strategy: Retry strategy instance
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       from requestforge import ExponentialBackoffRetryStrategy

       strategy = ExponentialBackoffRetryStrategy(max_retries=5)
       builder.with_retry_strategy(strategy)

.. method:: with_retry(max_retries=3, base_delay=1.0, max_delay=60.0)

   Configure exponential backoff retry.

   :param int max_retries: Maximum retry attempts
   :param float base_delay: Initial delay in seconds
   :param float max_delay: Maximum delay cap in seconds
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_retry(
           max_retries=3,
           base_delay=1.0,
           max_delay=60.0
       )

Connection Pool Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. method:: with_pool_connection(pool_connection=10)

   Set connection pool size.

   :param int pool_connection: Pool connection size
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_pool_connection(20)

.. method:: with_pool_maxsize(pool_maxsize=20)

   Set maximum pool size.

   :param int pool_maxsize: Maximum pool size
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_pool_maxsize(50)

Authentication Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. method:: with_auth_hook(auth_hook)

   Set authentication hook.

   :param AuthHookInterface auth_hook: Authentication hook
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       from requestforge import TokenAuthHook

       builder.with_auth_hook(TokenAuthHook(token_manager))

.. method:: with_token_auth(token_manager, auth_retry_strategy=None, auth_header_name='Authorization', auth_header_prefix='Bearer', excluded_paths=None, excluded_path_patterns=None)

   Configure token-based authentication with automatic refresh.

   :param TokenManagerInterface token_manager: Token manager instance
   :param AuthRetryStrategyInterface auth_retry_strategy: Auth retry strategy
   :param str auth_header_name: Header name for auth token
   :param str auth_header_prefix: Token prefix (e.g., 'Bearer')
   :param set excluded_paths: Paths to exclude from auth
   :param list excluded_path_patterns: Path patterns to exclude
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       from requestforge import TokenManager, SimpleAuthRetryStrategy

       builder.with_token_auth(
           token_manager=token_manager,
           auth_retry_strategy=SimpleAuthRetryStrategy(max_retries=1),
           excluded_paths={'/health', '/public'},
           excluded_path_patterns=['/docs/*']
       )

.. method:: with_api_key_auth(api_key, header_name='X-API-Key', excluded_paths=None)

   Configure API key authentication.

   :param str api_key: API key value
   :param str header_name: Header name
   :param set excluded_paths: Paths to exclude from auth
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_api_key_auth(
           api_key='your-key',
           header_name='X-API-Key',
           excluded_paths={'/public'}
       )

.. method:: with_basic_auth(username, password, excluded_paths=None)

   Configure HTTP Basic authentication.

   :param str username: Username
   :param str password: Password
   :param set excluded_paths: Paths to exclude from auth
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_basic_auth(
           username='user',
           password='pass',
           excluded_paths={'/login'}
       )

Hooks Configuration
~~~~~~~~~~~~~~~~~~~

.. method:: with_request_hook(hook)

   Add request hook.

   :param RequestHookInterface hook: Request hook
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       from requestforge import CorrelationIdHook

       builder.with_request_hook(CorrelationIdHook())

.. method:: with_response_hook(hook)

   Add response hook.

   :param ResponseHookInterface hook: Response hook
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       from requestforge import LoggingResponseHook

       builder.with_response_hook(LoggingResponseHook())

.. method:: with_error_hook(hook)

   Add error hook.

   :param ErrorHookInterface hook: Error hook
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       from requestforge import LoggingErrorHook

       builder.with_error_hook(LoggingErrorHook())

.. method:: with_logging(log_headers=False, log_body=False, sensitive_keys=None)

   Enable logging hooks.

   :param bool log_headers: Log request/response headers
   :param bool log_body: Log request/response bodies
   :param set sensitive_keys: Header keys to mask in logs
   :returns: Self for chaining
   :rtype: HttpClientConfigBuilder

   **Example:**

   .. code-block:: python

       builder.with_logging(
           log_headers=True,
           log_body=False,
           sensitive_keys={'authorization', 'x-api-key'}
       )

Building Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. method:: build()

   Build the configuration.

   :returns: Immutable configuration instance
   :rtype: HttpClientConfig
   :raises ValueError: If configuration is invalid

   **Example:**

   .. code-block:: python

       config = builder.build()

Complete Examples
-----------------

Basic Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .with_header('User-Agent', 'MyApp/1.0')
        .build()
    )

Production Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClientConfigBuilder,
        ExponentialBackoffRetryStrategy
    )

    config = (
        HttpClientConfigBuilder()
        # Base settings
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .with_verify_ssl(True)

        # Headers
        .with_header('User-Agent', 'MyApp/1.0')
        .with_header('Accept', 'application/json')

        # Retry with exponential backoff
        .with_retry(
            max_retries=5,
            base_delay=1.0,
            max_delay=60.0
        )

        # Connection pooling
        .with_pool_connection(20)
        .with_pool_maxsize(50)

        # Logging
        .with_logging(
            log_headers=True,
            log_body=False,
            sensitive_keys={'authorization'}
        )

        .build()
    )

With Authentication
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider,
        InMemoryTokenStorage,
        SimpleAuthRetryStrategy
    )

    # Setup token provider
    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api'
    )

    # Create token manager
    token_manager = TokenManager(
        provider=provider,
        storage=InMemoryTokenStorage()
    )

    # Build config
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=SimpleAuthRetryStrategy(max_retries=1),
            excluded_paths={'/health', '/public'}
        )
        .with_retry(max_retries=3)
        .with_logging()
        .build()
    )

Custom Hooks
~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClientConfigBuilder,
        LoggingRequestHook,
        LoggingResponseHook,
        CorrelationIdHook
    )

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')

        # Request hooks
        .with_request_hook(CorrelationIdHook('X-Request-ID'))
        .with_request_hook(LoggingRequestHook(log_headers=True))

        # Response hooks
        .with_response_hook(LoggingResponseHook(log_body=False))

        .build()
    )

Environment-Specific Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    from requestforge import HttpClientConfigBuilder

    def create_config():
        env = os.getenv('ENVIRONMENT', 'development')

        builder = HttpClientConfigBuilder()

        if env == 'production':
            return (
                builder
                .with_base_url('https://api.production.com')
                .with_timeout(30.0)
                .with_retry(max_retries=5)
                .with_pool_connection(50)
                .with_verify_ssl(True)
                .build()
            )
        elif env == 'staging':
            return (
                builder
                .with_base_url('https://api.staging.com')
                .with_timeout(30.0)
                .with_retry(max_retries=3)
                .with_logging(log_headers=True)
                .build()
            )
        else:  # development
            return (
                builder
                .with_base_url('http://localhost:8000')
                .with_timeout(60.0)
                .with_retry(max_retries=1)
                .with_logging(log_headers=True, log_body=True)
                .with_verify_ssl(False)
                .build()
            )

    config = create_config()

See Also
--------

* :doc:`client` - HTTP client API
* :doc:`retry` - Retry strategies
* :doc:`hooks` - Lifecycle hooks
* :doc:`token-manager` - Token management
