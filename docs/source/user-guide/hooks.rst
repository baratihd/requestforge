Hooks
=====

Hooks provide extensible lifecycle management for HTTP requests and responses.

Overview
--------

Hooks allow you to:

* **Modify requests** before sending (add headers, log requests)
* **Process responses** after receiving (parse data, cache responses)
* **Handle errors** during the request lifecycle (metrics, alerting)
* **Implement cross-cutting concerns** (correlation IDs, distributed tracing)

Hook Types
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Hook Type
     - Purpose
   * - ``RequestHookInterface``
     - Modify requests before sending
   * - ``ResponseHookInterface``
     - Process responses after receiving
   * - ``ErrorHookInterface``
     - Handle errors during request lifecycle
   * - ``AuthHookInterface``
     - Manage authentication (token injection, refresh)

Execution Order
---------------

.. code-block:: text

    ┌─────────────────────────────────────┐
    │         Request Initiated           │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │      Request Hooks (in order)       │
    │  1. LoggingRequestHook              │
    │  2. CorrelationIdHook               │
    │  3. CustomRequestHook               │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │         Auth Hook                   │
    │  (Token injection if configured)    │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │      HTTP Request Sent              │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │     Response Received               │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │     Response Hooks (in order)       │
    │  1. RateLimitResponseHook           │
    │  2. LoggingResponseHook             │
    │  3. CustomResponseHook              │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │      Return Response                │
    └─────────────────────────────────────┘

    On Error:
    ┌─────────────────────────────────────┐
    │      Error Hooks (in order)         │
    │  1. LoggingErrorHook                │
    │  2. MetricsErrorHook                │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │      Raise Exception                │
    └─────────────────────────────────────┘

Built-in Hooks
--------------

Request Hooks
~~~~~~~~~~~~~

LoggingRequestHook
^^^^^^^^^^^^^^^^^^

Logs outgoing requests with optional header and body logging:

.. code-block:: python

    from requestforge import LoggingRequestHook

    hook = LoggingRequestHook(
        log_headers=True,      # Log request headers
        log_body=True,         # Log request body
        sensitive_keys={'authorization', 'x-api-key'}  # Mask sensitive data
    )

    config = builder.with_request_hook(hook).build()

Output example:

.. code-block:: text

    [a3f2c1b4] HTTP GET /users
    [a3f2c1b4] Headers: {'Authorization': '***', 'User-Agent': 'MyApp/1.0'}
    [a3f2c1b4] Body: {'query': 'john'}

CorrelationIdHook
^^^^^^^^^^^^^^^^^

Adds correlation IDs for distributed tracing:

.. code-block:: python

    from requestforge import CorrelationIdHook

    hook = CorrelationIdHook(header_name='X-Request-ID')
    config = builder.with_request_hook(hook).build()

    client = HttpClient(config)
    response = client.get('/users')

    # Request includes: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000

AuthorizationHook
^^^^^^^^^^^^^^^^^

Dynamic token provider:

.. code-block:: python

    from requestforge import AuthorizationHook

    def get_current_token():
        # Fetch token from session, cache, etc.
        return request.session.get('api_token')

    hook = AuthorizationHook(token_provider=get_current_token)
    config = builder.with_request_hook(hook).build()

Response Hooks
~~~~~~~~~~~~~~

LoggingResponseHook
^^^^^^^^^^^^^^^^^^^

Logs incoming responses:

.. code-block:: python

    from requestforge import LoggingResponseHook

    hook = LoggingResponseHook(
        log_headers=True,
        log_body=True  # Only logs body on errors
    )

    config = builder.with_response_hook(hook).build()

Output example:

.. code-block:: text

    [a3f2c1b4] Response: 200 (125.45ms)
    [a3f2c1b4] Response Headers: {'Content-Type': 'application/json'}

RateLimitResponseHook
^^^^^^^^^^^^^^^^^^^^^

Parses and stores rate limit information:

.. code-block:: python

    from requestforge import RateLimitResponseHook

    hook = RateLimitResponseHook()
    config = builder.with_response_hook(hook).build()

    client = HttpClient(config)
    response = client.get('/users')

    # Access rate limit info from context
    # context.metadata['rate_limit_remaining']
    # context.metadata['rate_limit_reset']

Error Hooks
~~~~~~~~~~~

LoggingErrorHook
^^^^^^^^^^^^^^^^

Logs errors during request lifecycle:

.. code-block:: python

    from requestforge import LoggingErrorHook

    hook = LoggingErrorHook()
    config = builder.with_error_hook(hook).build()

Output example:

.. code-block:: text

    [a3f2c1b4] Request failed (attempt 1/4): TimeoutException: Request timed out

Built-in Logging Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable all logging hooks at once:

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_logging(
            log_headers=True,
            log_body=False,
            sensitive_keys={'authorization', 'cookie', 'x-api-key'}
        )
        .build()
    )

    # Adds LoggingRequestHook, LoggingResponseHook, LoggingErrorHook

Custom Request Hooks
--------------------

Basic Request Hook
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RequestHookInterface
    from requestforge.models import HttpRequest, RequestContext

    class CustomHeaderHook(RequestHookInterface):
        def __init__(self, header_name, header_value):
            self._header_name = header_name
            self._header_value = header_value

        def before_request(self, request: HttpRequest, context: RequestContext) -> HttpRequest:
            # Add custom header
            return request.with_headers({
                self._header_name: self._header_value
            })

    # Usage
    hook = CustomHeaderHook('X-Client-Version', '2.0')
    config = builder.with_request_hook(hook).build()

Dynamic Headers Hook
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import time

    class TimestampHook(RequestHookInterface):
        def before_request(self, request, context):
            timestamp = str(int(time.time()))
            return request.with_headers({
                'X-Request-Timestamp': timestamp,
                'X-Request-ID': context.metadata.get('request_id', 'unknown')
            })

Request Signing Hook
~~~~~~~~~~~~~~~~~~~~

Sign requests with HMAC:

.. code-block:: python

    import hmac
    import hashlib

    class RequestSigningHook(RequestHookInterface):
        def __init__(self, secret_key):
            self._secret = secret_key.encode()

        def before_request(self, request, context):
            # Create signature
            content = f"{request.method.value}{request.url}".encode()
            signature = hmac.new(
                self._secret,
                content,
                hashlib.sha256
            ).hexdigest()

            return request.with_headers({
                'X-Signature': signature
            })

    hook = RequestSigningHook(secret_key='my-secret')
    config = builder.with_request_hook(hook).build()

Custom Response Hooks
---------------------

Metrics Hook
~~~~~~~~~~~~

Track request metrics:

.. code-block:: python

    from requestforge.interfaces import ResponseHookInterface

    class MetricsHook(ResponseHookInterface):
        def __init__(self, metrics_client):
            self._metrics = metrics_client

        def after_response(self, response, context):
            # Track response time
            self._metrics.timing(
                'http.request.duration',
                response.elapsed_ms,
                tags={
                    'method': response.request.method.value,
                    'status': response.status_code
                }
            )

            # Track status codes
            self._metrics.increment(
                f'http.status.{response.status_code}'
            )

            # Track errors
            if not response.is_success:
                self._metrics.increment('http.errors')

            return response

    # Usage with StatsD
    from statsd import StatsClient
    metrics = StatsClient('localhost', 8125)
    hook = MetricsHook(metrics)

Response Caching Hook
~~~~~~~~~~~~~~~~~~~~~

Cache GET responses:

.. code-block:: python

    class ResponseCacheHook(ResponseHookInterface):
        def __init__(self, cache):
            self._cache = cache

        def after_response(self, response, context):
            # Only cache successful GET requests
            if (response.request.method == HttpMethod.GET and
                response.is_success):

                cache_key = f"response:{response.url}"
                self._cache.set(
                    cache_key,
                    response.content,
                    timeout=300  # 5 minutes
                )

            return response

Data Transformation Hook
~~~~~~~~~~~~~~~~~~~~~~~~

Parse and transform response data:

.. code-block:: python

    class DataTransformHook(ResponseHookInterface):
        def after_response(self, response, context):
            if response.is_success and 'application/json' in response.headers.get('Content-Type', ''):
                # Store parsed JSON in context for easy access
                data = response.json_or_none()
                if data:
                    context.metadata['parsed_data'] = data

            return response

Custom Error Hooks
------------------

Alerting Hook
~~~~~~~~~~~~~

Send alerts on errors:

.. code-block:: python

    from requestforge.interfaces import ErrorHookInterface

    class AlertingErrorHook(ErrorHookInterface):
        def __init__(self, alert_service):
            self._alerts = alert_service

        def on_error(self, exception, context):
            # Only alert on critical errors
            if isinstance(exception, (TimeoutException, ConnectionException)):
                self._alerts.send_alert(
                    title=f'HTTP Client Error: {type(exception).__name__}',
                    message=str(exception),
                    severity='warning',
                    metadata={
                        'url': context.request.url,
                        'attempt': context.attempt,
                        'max_retries': context.max_retries
                    }
                )

Sentry Integration
~~~~~~~~~~~~~~~~~~

Report errors to Sentry:

.. code-block:: python

    import sentry_sdk

    class SentryErrorHook(ErrorHookInterface):
        def on_error(self, exception, context):
            with sentry_sdk.push_scope() as scope:
                # Add context
                scope.set_tag('http_method', context.request.method.value)
                scope.set_tag('http_url', context.request.url)
                scope.set_extra('attempt', context.attempt)
                scope.set_extra('max_retries', context.max_retries)

                # Capture exception
                sentry_sdk.capture_exception(exception)

Error Recovery Hook
~~~~~~~~~~~~~~~~~~~

Attempt recovery on specific errors:

.. code-block:: python

    class RecoveryErrorHook(ErrorHookInterface):
        def __init__(self, recovery_callback):
            self._recovery = recovery_callback

        def on_error(self, exception, context):
            # Try recovery on authentication errors
            if isinstance(exception, AuthenticationException):
                try:
                    self._recovery(exception, context)
                except Exception as e:
                    logger.error(f'Recovery failed: {e}')

Authentication Hooks
--------------------

See :doc:`authentication` for detailed auth hook documentation.

TokenAuthHook
~~~~~~~~~~~~~

Token-based authentication with auto-refresh:

.. code-block:: python

    from requestforge import TokenAuthHook, TokenManager

    auth_hook = TokenAuthHook(
        token_manager=token_manager,
        auth_header_name='Authorization',
        auth_header_prefix='Bearer',
        excluded_paths={'/auth/token', '/health'}
    )

    config = builder.with_auth_hook(auth_hook).build()

ApiKeyAuthHook
~~~~~~~~~~~~~~

Static API key authentication:

.. code-block:: python

    from requestforge import ApiKeyAuthHook

    auth_hook = ApiKeyAuthHook(
        api_key='your-api-key',
        header_name='X-API-Key',
        excluded_paths={'/public'}
    )

BasicAuthHook
~~~~~~~~~~~~~

HTTP Basic authentication:

.. code-block:: python

    from requestforge import BasicAuthHook

    auth_hook = BasicAuthHook(
        username='user',
        password='password',
        excluded_paths={'/login'}
    )

Hook Context
------------

Accessing Request Context
~~~~~~~~~~~~~~~~~~~~~~~~~~

All hooks receive a ``RequestContext`` object:

.. code-block:: python

    class ContextAwareHook(RequestHookInterface):
        def before_request(self, request, context):
            # Access attempt number
            print(f"Attempt: {context.attempt}")

            # Access max retries
            print(f"Max retries: {context.max_retries}")

            # Check if retry
            if context.is_retry:
                print("This is a retry")

            # Store/retrieve metadata
            context.metadata['custom_key'] = 'custom_value'
            previous_value = context.metadata.get('other_key')

            return request

Sharing Data Between Hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use context metadata to share data:

.. code-block:: python

    class HookA(RequestHookInterface):
        def before_request(self, request, context):
            # Store data in context
            context.metadata['start_time'] = time.time()
            return request

    class HookB(ResponseHookInterface):
        def after_response(self, response, context):
            # Retrieve data from context
            start_time = context.metadata.get('start_time')
            if start_time:
                duration = time.time() - start_time
                print(f"Total duration: {duration:.2f}s")
            return response

Hook Chaining
-------------

Multiple Hooks in Sequence
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        # Request hooks (executed in order)
        .with_request_hook(CorrelationIdHook())
        .with_request_hook(LoggingRequestHook())
        .with_request_hook(CustomHeaderHook('X-App', 'MyApp'))
        # Response hooks (executed in order)
        .with_response_hook(MetricsHook(metrics_client))
        .with_response_hook(LoggingResponseHook())
        # Error hooks (executed in order)
        .with_error_hook(SentryErrorHook())
        .with_error_hook(LoggingErrorHook())
        .build()
    )

Conditional Hook Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class ConditionalHook(RequestHookInterface):
        def __init__(self, condition_func, inner_hook):
            self._condition = condition_func
            self._hook = inner_hook

        def before_request(self, request, context):
            # Only execute inner hook if condition is met
            if self._condition(request, context):
                return self._hook.before_request(request, context)
            return request

    # Usage
    def only_post_requests(request, context):
        return request.method == HttpMethod.POST

    conditional_hook = ConditionalHook(
        condition_func=only_post_requests,
        inner_hook=CustomHeaderHook('X-POST-Header', 'value')
    )

Advanced Examples
-----------------

Circuit Breaker Hook
~~~~~~~~~~~~~~~~~~~~

Implement circuit breaker at hook level:

.. code-block:: python

    class CircuitBreakerHook(ErrorHookInterface):
        def __init__(self, failure_threshold=5, timeout=60):
            self._failures = 0
            self._last_failure = None
            self._threshold = failure_threshold
            self._timeout = timeout
            self._state = 'closed'  # closed, open, half_open

        def on_error(self, exception, context):
            import time

            if self._state == 'open':
                # Check if timeout passed
                if time.time() - self._last_failure > self._timeout:
                    self._state = 'half_open'
                    self._failures = 0
                else:
                    raise Exception('Circuit breaker is OPEN')

            self._failures += 1
            self._last_failure = time.time()

            if self._failures >= self._threshold:
                self._state = 'open'
                logger.warning(f'Circuit breaker opened after {self._failures} failures')

Request/Response Timing
~~~~~~~~~~~~~~~~~~~~~~~

Track detailed timing:

.. code-block:: python

    class TimingHooks:
        class Request(RequestHookInterface):
            def before_request(self, request, context):
                context.metadata['client_start'] = time.time()
                return request

        class Response(ResponseHookInterface):
            def after_response(self, response, context):
                start = context.metadata.get('client_start')
                if start:
                    client_duration = time.time() - start
                    server_duration = response.elapsed_ms / 1000
                    network_duration = client_duration - server_duration

                    logger.info(f'Client: {client_duration:.3f}s, '
                              f'Server: {server_duration:.3f}s, '
                              f'Network: {network_duration:.3f}s')
                return response

    config = (
        builder
        .with_request_hook(TimingHooks.Request())
        .with_response_hook(TimingHooks.Response())
        .build()
    )

Request Deduplication
~~~~~~~~~~~~~~~~~~~~~

Prevent duplicate requests:

.. code-block:: python

    class DeduplicationHook(RequestHookInterface):
        def __init__(self):
            self._in_flight = set()
            self._lock = threading.Lock()

        def before_request(self, request, context):
            # Create request fingerprint
            fingerprint = f"{request.method}:{request.url}"

            with self._lock:
                if fingerprint in self._in_flight:
                    raise HttpClientException(f'Duplicate request: {fingerprint}')
                self._in_flight.add(fingerprint)

            # Store for cleanup
            context.metadata['fingerprint'] = fingerprint
            return request

        def cleanup(self, fingerprint):
            with self._lock:
                self._in_flight.discard(fingerprint)

Best Practices
--------------

1. **Keep Hooks Focused**

   .. code-block:: python

       # Good ✅ - Single responsibility
       class CorrelationIdHook(RequestHookInterface):
           def before_request(self, request, context):
               return request.with_headers({'X-Correlation-ID': uuid.uuid4()})

       # Avoid ❌ - Too many responsibilities
       class EverythingHook(RequestHookInterface):
           def before_request(self, request, context):
               # Adds correlation ID, logs, signs request, etc.
               pass

2. **Handle Hook Failures Gracefully**

   .. code-block:: python

       class SafeHook(RequestHookInterface):
           def before_request(self, request, context):
               try:
                   # Hook logic
                   return self._modify_request(request)
               except Exception as e:
                   logger.error(f'Hook failed: {e}')
                   return request  # Return unmodified request

3. **Use Immutable Request Modifications**

   .. code-block:: python

       # Good ✅ - Returns new request
       def before_request(self, request, context):
           return request.with_headers({'X-Custom': 'value'})

       # Avoid ❌ - HttpRequest is immutable anyway
       def before_request(self, request, context):
           request.headers['X-Custom'] = 'value'  # This won't work!

4. **Order Hooks Appropriately**

   .. code-block:: python

       config = (
           builder
           # Early: Generate correlation ID
           .with_request_hook(CorrelationIdHook())
           # Later: Log request (with correlation ID)
           .with_request_hook(LoggingRequestHook())
           .build()
       )

Next Steps
----------

* Explore :doc:`../examples/custom-retry` for hook-based retry logic
* Learn about :doc:`authentication` for auth hook details
* Check :doc:`error-handling` for error hook patterns
