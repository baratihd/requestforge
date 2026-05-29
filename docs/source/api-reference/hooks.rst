Hooks API Reference
===================

This page documents the lifecycle hooks and their interfaces.

Hook Interfaces
---------------

RequestHookInterface
~~~~~~~~~~~~~~~~~~~~

.. class:: RequestHookInterface

   Abstract interface for request modification hooks.

   Hooks implementing this interface can modify requests before they are sent.

   .. method:: before_request(request, context)

      Modify request before sending.

      :param HttpRequest request: The HTTP request
      :param RequestContext context: Request context
      :returns: Modified request (or original)
      :rtype: HttpRequest

      **Example:**

      .. code-block:: python

          from requestforge.interfaces import RequestHookInterface

          class CustomHeaderHook(RequestHookInterface):
              def before_request(self, request, context):
                  return request.with_headers({
                      'X-Custom-Header': 'value'
                  })

ResponseHookInterface
~~~~~~~~~~~~~~~~~~~~~

.. class:: ResponseHookInterface

   Abstract interface for response processing hooks.

   .. method:: after_response(response, context)

      Process response after receiving.

      :param HttpResponse response: The HTTP response
      :param RequestContext context: Request context
      :returns: Modified response (or original)
      :rtype: HttpResponse

      **Example:**

      .. code-block:: python

          from requestforge.interfaces import ResponseHookInterface

          class MetricsHook(ResponseHookInterface):
              def after_response(self, response, context):
                  metrics.timing('api.duration', response.elapsed_ms)
                  return response

ErrorHookInterface
~~~~~~~~~~~~~~~~~~

.. class:: ErrorHookInterface

   Abstract interface for error handling hooks.

   .. method:: on_error(exception, context)

      Handle errors during request lifecycle.

      :param Exception exception: The exception that occurred
      :param RequestContext context: Request context
      :returns: None
      :rtype: None

      **Example:**

      .. code-block:: python

          from requestforge.interfaces import ErrorHookInterface

          class LoggingErrorHook(ErrorHookInterface):
              def on_error(self, exception, context):
                  logger.error(f"Request failed: {exception}")

AuthHookInterface
~~~~~~~~~~~~~~~~~

.. class:: AuthHookInterface

   Abstract interface for authentication hooks.

   .. method:: before_request(request, context)

      Add authentication to request.

      :param HttpRequest request: The HTTP request
      :param RequestContext context: Request context
      :returns: Authenticated request
      :rtype: HttpRequest

   .. method:: should_authenticate(request)

      Determine if request should be authenticated.

      :param HttpRequest request: The HTTP request
      :returns: True if should authenticate
      :rtype: bool

   .. method:: is_auth_error(response)

      Check if response indicates authentication error.

      :param HttpResponse response: The HTTP response
      :returns: True if auth error
      :rtype: bool

   .. method:: refresh_auth()

      Refresh authentication credentials.

      :returns: True if refresh successful
      :rtype: bool

   .. method:: invalidate_auth()

      Invalidate current authentication credentials.

      :returns: None
      :rtype: None

   .. method:: get_token()

      Get current valid token.

      :returns: Current token data
      :rtype: TokenData

   .. attribute:: retry_strategy
      :type: AuthRetryStrategyInterface

      Get the auth retry strategy for this hook.

Built-in Request Hooks
----------------------

LoggingRequestHook
~~~~~~~~~~~~~~~~~~

.. class:: LoggingRequestHook(log_headers=False, log_body=False, sensitive_keys=None)

   Hook for logging outgoing requests.

   :param bool log_headers: Log request headers
   :param bool log_body: Log request body
   :param set sensitive_keys: Header keys to mask (e.g., {'authorization'})

   **Features:**

   * Generates unique request ID
   * Logs HTTP method and URL
   * Optionally logs headers (with sensitive data masking)
   * Optionally logs request body
   * Stores start time in context

   **Example:**

   .. code-block:: python

       from requestforge import LoggingRequestHook

       hook = LoggingRequestHook(
           log_headers=True,
           log_body=False,
           sensitive_keys={'authorization', 'x-api-key', 'cookie'}
       )

       config = builder.with_request_hook(hook).build()

   **Output:**

   .. code-block:: text

       [a3f2c1b4] HTTP GET /users
       [a3f2c1b4] Headers: {'Authorization': '***', 'User-Agent': 'MyApp/1.0'}

CorrelationIdHook
~~~~~~~~~~~~~~~~~

.. class:: CorrelationIdHook(header_name='X-Correlation-ID')

   Adds correlation ID to requests for distributed tracing.

   :param str header_name: Header name for correlation ID

   **Features:**

   * Generates unique correlation ID (UUID)
   * Stores in request context metadata
   * Adds as request header

   **Example:**

   .. code-block:: python

       from requestforge import CorrelationIdHook

       hook = CorrelationIdHook(header_name='X-Request-ID')
       config = builder.with_request_hook(hook).build()

       client = HttpClient(config)
       response = client.get('/users')
       # Request includes: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000

AuthorizationHook
~~~~~~~~~~~~~~~~~

.. class:: AuthorizationHook(token_provider)

   Dynamic authorization hook with token provider.

   :param callable token_provider: Function that returns current token

   **Example:**

   .. code-block:: python

       from requestforge import AuthorizationHook

       def get_token():
           return session.get('api_token')

       hook = AuthorizationHook(token_provider=get_token)
       config = builder.with_request_hook(hook).build()

Built-in Response Hooks
-----------------------

LoggingResponseHook
~~~~~~~~~~~~~~~~~~~

.. class:: LoggingResponseHook(log_headers=False, log_body=False)

   Hook for logging incoming responses.

   :param bool log_headers: Log response headers
   :param bool log_body: Log response body (only on errors)

   **Features:**

   * Logs status code and duration
   * Optionally logs response headers
   * Logs body only for failed requests
   * Uses request ID from context

   **Example:**

   .. code-block:: python

       from requestforge import LoggingResponseHook

       hook = LoggingResponseHook(
           log_headers=True,
           log_body=True
       )

       config = builder.with_response_hook(hook).build()

   **Output:**

   .. code-block:: text

       [a3f2c1b4] Response: 200 (125.45ms)
       [a3f2c1b4] Response Headers: {'Content-Type': 'application/json'}

RateLimitResponseHook
~~~~~~~~~~~~~~~~~~~~~

.. class:: RateLimitResponseHook()

   Parses and stores rate limit information from response headers.

   **Features:**

   * Extracts ``X-RateLimit-Remaining`` header
   * Extracts ``X-RateLimit-Reset`` header
   * Stores values in request context metadata

   **Example:**

   .. code-block:: python

       from requestforge import RateLimitResponseHook

       hook = RateLimitResponseHook()
       config = builder.with_response_hook(hook).build()

       client = HttpClient(config)
       # Access rate limit info from context
       # context.metadata['rate_limit_remaining']
       # context.metadata['rate_limit_reset']

Built-in Error Hooks
--------------------

LoggingErrorHook
~~~~~~~~~~~~~~~~

.. class:: LoggingErrorHook()

   Hook for logging errors during request lifecycle.

   **Features:**

   * Logs exception type and message
   * Logs request details (URL, method)
   * Logs attempt number
   * Uses request ID from context

   **Example:**

   .. code-block:: python

       from requestforge import LoggingErrorHook

       hook = LoggingErrorHook()
       config = builder.with_error_hook(hook).build()

   **Output:**

   .. code-block:: text

       [a3f2c1b4] Request failed (attempt 1/4): TimeoutException: Request timed out

Built-in Auth Hooks
-------------------

TokenAuthHook
~~~~~~~~~~~~~

.. class:: TokenAuthHook(token_manager, retry_strategy=None, auth_header_name='Authorization', auth_header_prefix='Bearer', excluded_paths=None, excluded_path_patterns=None)

   Token-based authentication hook with automatic refresh.

   :param TokenManagerInterface token_manager: Token manager
   :param AuthRetryStrategyInterface retry_strategy: Auth retry strategy
   :param str auth_header_name: Header name for auth token
   :param str auth_header_prefix: Token prefix (e.g., 'Bearer')
   :param set excluded_paths: Paths to exclude from auth
   :param list excluded_path_patterns: Path patterns to exclude (glob style)

   **Features:**

   * Automatic token injection
   * Token refresh on expiration
   * Auto-retry on 401 errors
   * Path exclusion support
   * Pattern matching for exclusions

   **Properties:**

   .. attribute:: retry_strategy
      :type: AuthRetryStrategyInterface

      Get the auth retry strategy.

   .. attribute:: token_manager
      :type: TokenManagerInterface

      Get the token manager.

   **Methods:**

   .. method:: should_authenticate(request)

      Check if request should be authenticated.

      :param HttpRequest request: The request
      :returns: True if should authenticate
      :rtype: bool

   .. method:: before_request(request, context)

      Add authentication token to request.

   .. method:: is_auth_error(response)

      Check if response is auth error.

   .. method:: refresh_auth()

      Refresh authentication token.

   .. method:: invalidate_auth()

      Invalidate cached token.

   .. method:: get_token()

      Get current valid token.

   **Example:**

   .. code-block:: python

       from requestforge import TokenAuthHook, TokenManager, SimpleAuthRetryStrategy

       hook = TokenAuthHook(
           token_manager=token_manager,
           retry_strategy=SimpleAuthRetryStrategy(max_retries=1),
           auth_header_name='Authorization',
           auth_header_prefix='Bearer',
           excluded_paths={'/health', '/public'},
           excluded_path_patterns=['/docs/*', '*/public/*']
       )

       config = builder.with_auth_hook(hook).build()

ApiKeyAuthHook
~~~~~~~~~~~~~~

.. class:: ApiKeyAuthHook(api_key, header_name='X-API-Key', retry_strategy=None, excluded_paths=None)

   API key authentication hook.

   :param str api_key: API key value
   :param str header_name: Header name for API key
   :param AuthRetryStrategyInterface retry_strategy: Auth retry strategy
   :param set excluded_paths: Paths to exclude

   **Example:**

   .. code-block:: python

       from requestforge import ApiKeyAuthHook

       hook = ApiKeyAuthHook(
           api_key='your-api-key',
           header_name='X-API-Key',
           excluded_paths={'/public'}
       )

       config = builder.with_auth_hook(hook).build()

BasicAuthHook
~~~~~~~~~~~~~

.. class:: BasicAuthHook(username, password, retry_strategy=None, excluded_paths=None)

   HTTP Basic authentication hook.

   :param str username: Username
   :param str password: Password
   :param AuthRetryStrategyInterface retry_strategy: Auth retry strategy
   :param set excluded_paths: Paths to exclude

   **Example:**

   .. code-block:: python

       from requestforge import BasicAuthHook

       hook = BasicAuthHook(
           username='user',
           password='password',
           excluded_paths={'/login'}
       )

       config = builder.with_auth_hook(hook).build()

CompositeAuthHook
~~~~~~~~~~~~~~~~~

.. class:: CompositeAuthHook(hooks, strategy='first_match', retry_strategy=None)

   Composite auth hook that combines multiple authentication methods.

   :param list hooks: List of auth hooks
   :param str strategy: Strategy ('first_match' or 'all')
   :param AuthRetryStrategyInterface retry_strategy: Auth retry strategy

   **Strategies:**

   * **first_match**: Use first hook that matches
   * **all**: Apply all matching hooks

   **Example:**

   .. code-block:: python

       from requestforge import CompositeAuthHook, ApiKeyAuthHook, TokenAuthHook

       hook = CompositeAuthHook(
           hooks=[
               ApiKeyAuthHook('key1'),
               TokenAuthHook(token_manager)
           ],
           strategy='first_match'
       )

       config = builder.with_auth_hook(hook).build()

Custom Hook Examples
--------------------

Custom Request Hook
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RequestHookInterface
    import time

    class TimestampHook(RequestHookInterface):
        """Add timestamp to requests."""

        def before_request(self, request, context):
            timestamp = str(int(time.time()))
            request_id = context.metadata.get('request_id', 'unknown')

            return request.with_headers({
                'X-Timestamp': timestamp,
                'X-Request-ID': request_id
            })

    # Usage
    config = builder.with_request_hook(TimestampHook()).build()

Custom Response Hook
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ResponseHookInterface

    class CacheResponseHook(ResponseHookInterface):
        """Cache successful GET responses."""

        def __init__(self, cache):
            self.cache = cache

        def after_response(self, response, context):
            if (response.request.method == HttpMethod.GET and
                response.is_success):

                cache_key = f"response:{response.url}"
                self.cache.set(cache_key, response.content, timeout=300)

            return response

    # Usage
    from django.core.cache import cache
    hook = CacheResponseHook(cache)
    config = builder.with_response_hook(hook).build()

Custom Error Hook
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ErrorHookInterface
    import sentry_sdk

    class SentryErrorHook(ErrorHookInterface):
        """Report errors to Sentry."""

        def on_error(self, exception, context):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag('http_method', context.request.method.value)
                scope.set_tag('http_url', context.request.url)
                scope.set_extra('attempt', context.attempt)

                sentry_sdk.capture_exception(exception)

    # Usage
    config = builder.with_error_hook(SentryErrorHook()).build()

Custom Auth Hook
~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import AuthHookInterface
    from requestforge.config import TokenData
    import hmac
    import hashlib
    import time

    class HMACAuthHook(AuthHookInterface):
        """HMAC request signing."""

        def __init__(self, access_key, secret_key):
            self.access_key = access_key
            self.secret_key = secret_key.encode()
            self._retry_strategy = NoAuthRetryStrategy()

        @property
        def retry_strategy(self):
            return self._retry_strategy

        def should_authenticate(self, request):
            return True

        def before_request(self, request, context):
            timestamp = str(int(time.time()))

            # Create signature
            sign_string = f"{request.method.value}\n{request.url}\n{timestamp}"
            signature = hmac.new(
                self.secret_key,
                sign_string.encode(),
                hashlib.sha256
            ).hexdigest()

            return request.with_headers({
                'X-Access-Key': self.access_key,
                'X-Timestamp': timestamp,
                'X-Signature': signature
            })

        def is_auth_error(self, response):
            return response.status_code == 401

        def refresh_auth(self):
            return False

        def invalidate_auth(self):
            pass

        def get_token(self):
            return TokenData(access_token=self.access_key, token_type='HMAC')

    # Usage
    hook = HMACAuthHook('access-key', 'secret-key')
    config = builder.with_auth_hook(hook).build()

Hook Execution Order
--------------------

Hooks are executed in the following order:

**Request Flow:**

.. code-block:: text

    1. Request Hooks (in registration order)
       ├─ LoggingRequestHook
       ├─ CorrelationIdHook
       └─ CustomRequestHook

    2. Auth Hook
       └─ TokenAuthHook (if configured)

    3. → HTTP Request →

    4. Response Hooks (in registration order)
       ├─ RateLimitResponseHook
       ├─ LoggingResponseHook
       └─ CustomResponseHook

    5. Return Response

**Error Flow:**

.. code-block:: text

    1. Exception Occurs

    2. Error Hooks (in registration order)
       ├─ SentryErrorHook
       ├─ LoggingErrorHook
       └─ CustomErrorHook

    3. Retry Logic
       ├─ Should retry? → Yes → Wait → Goto Request Flow
       └─ Should retry? → No → Raise Exception

Example: Combining Multiple Hooks
----------------------------------

.. code-block:: python

    from requestforge import (
        HttpClientConfigBuilder,
        LoggingRequestHook,
        LoggingResponseHook,
        LoggingErrorHook,
        CorrelationIdHook,
        RateLimitResponseHook,
        TokenAuthHook
    )

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')

        # Request hooks
        .with_request_hook(CorrelationIdHook('X-Request-ID'))
        .with_request_hook(LoggingRequestHook(
            log_headers=True,
            sensitive_keys={'authorization'}
        ))

        # Auth hook
        .with_token_auth(token_manager=token_manager)

        # Response hooks
        .with_response_hook(RateLimitResponseHook())
        .with_response_hook(LoggingResponseHook(log_body=False))

        # Error hooks
        .with_error_hook(SentryErrorHook())
        .with_error_hook(LoggingErrorHook())

        .build()
    )

See Also
--------

* :doc:`../user-guide/hooks` - Hooks user guide
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`client` - HTTP client API
