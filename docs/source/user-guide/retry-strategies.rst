Retry Strategies
================

Request Forge provides robust retry mechanisms to handle transient failures gracefully.

Overview
--------

Retry strategies determine:

* **When** to retry (which errors/status codes)
* **How many times** to retry
* **How long** to wait between retries
* **When to give up** (max retries or circuit breaker)

Available Strategies
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Strategy
     - Description
     - Use Case
   * - ``NoRetryStrategy``
     - No retries, fail immediately
     - Testing, non-critical requests
   * - ``SimpleRetryStrategy``
     - Fixed delay between retries
     - Simple retry logic
   * - ``ExponentialBackoffRetryStrategy``
     - Exponential delay with jitter
     - Production use (recommended)
   * - ``CircuitBreakerRetryStrategy``
     - Circuit breaker pattern
     - Prevent cascade failures

No Retry Strategy
-----------------

Fail immediately on any error:

.. code-block:: python

    from requestforge import NoRetryStrategy, HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry_strategy(NoRetryStrategy())
        .build()
    )

    # No retries - fails on first error

When to Use
~~~~~~~~~~~

* Unit tests where you want immediate failures
* Non-critical requests where retry overhead isn't worth it
* Requests that should never be retried (e.g., POST that creates resources)

Simple Retry Strategy
---------------------

Fixed delay between retry attempts:

.. code-block:: python

    from requestforge import SimpleRetryStrategy

    strategy = SimpleRetryStrategy(
        max_retries=3,      # Retry up to 3 times
        delay=2.0           # Wait 2 seconds between retries
    )

    config = builder.with_retry_strategy(strategy).build()

Timeline Example
~~~~~~~~~~~~~~~~

.. code-block:: text

    Attempt 1 → Fail
    Wait 2s
    Attempt 2 → Fail
    Wait 2s
    Attempt 3 → Fail
    Wait 2s
    Attempt 4 → Fail
    → Raise MaxRetryException

Custom Retryable Exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only retry specific exception types:

.. code-block:: python

    from requestforge import TimeoutException, ConnectionException

    strategy = SimpleRetryStrategy(
        max_retries=3,
        delay=1.0,
        retryable_exceptions=frozenset({
            TimeoutException,
            ConnectionException
        })
    )

    # Only retries on TimeoutException or ConnectionException
    # Other exceptions fail immediately

Exponential Backoff Strategy
-----------------------------

**Recommended for production use.**

Exponential delay with optional jitter to prevent thundering herd:

.. code-block:: python

    from requestforge import ExponentialBackoffRetryStrategy

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=5,        # Maximum 5 retry attempts
        base_delay=1.0,       # Start with 1 second
        max_delay=60.0,       # Cap at 60 seconds
        multiplier=2.0,       # Double delay each time
        jitter=True           # Add randomization
    )

    config = builder.with_retry_strategy(strategy).build()

Delay Calculation
~~~~~~~~~~~~~~~~~

Without jitter:

.. code-block:: python

    delay = min(base_delay * (multiplier ^ attempt), max_delay)

With jitter (±25% randomization):

.. code-block:: python

    delay = min(base_delay * (multiplier ^ attempt), max_delay)
    jitter_range = delay * 0.25
    delay += random(-jitter_range, jitter_range)

Timeline Example
~~~~~~~~~~~~~~~~

.. code-block:: text

    Attempt 1 → Fail
    Wait ~1s   (1.0 * 2^0 = 1.0s ± jitter)

    Attempt 2 → Fail
    Wait ~2s   (1.0 * 2^1 = 2.0s ± jitter)

    Attempt 3 → Fail
    Wait ~4s   (1.0 * 2^2 = 4.0s ± jitter)

    Attempt 4 → Fail
    Wait ~8s   (1.0 * 2^3 = 8.0s ± jitter)

    Attempt 5 → Fail
    Wait ~16s  (1.0 * 2^4 = 16.0s ± jitter)

    Attempt 6 → Fail
    → Raise MaxRetryException

Retryable Status Codes
~~~~~~~~~~~~~~~~~~~~~~~

Configure which HTTP status codes trigger retries:

.. code-block:: python

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=1.0,
        retryable_status_codes=frozenset({
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        })
    )

    client = HttpClient(config)

    # Automatically retries on 503, 502, etc.
    response = client.get('/unstable-endpoint')

Default retryable status codes:

* 408 - Request Timeout
* 429 - Too Many Requests
* 500 - Internal Server Error
* 502 - Bad Gateway
* 503 - Service Unavailable
* 504 - Gateway Timeout

Retryable Exceptions
~~~~~~~~~~~~~~~~~~~~

Specify which exceptions to retry:

.. code-block:: python

    from requestforge import TimeoutException, ConnectionException, HttpStatusException

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=3,
        retryable_exceptions=frozenset({
            TimeoutException,
            ConnectionException,
            HttpStatusException  # Retry on HTTP errors
        })
    )

By default, retries on:

* ``TimeoutException``
* ``ConnectionException``
* ``HttpStatusException`` (when status code is retryable)

Why Use Jitter?
~~~~~~~~~~~~~~~

Without jitter, synchronized clients retry at the same time:

.. code-block:: text

    100 clients fail at t=0
    All retry at t=1s → Server overload
    All retry at t=3s → Server overload
    All retry at t=7s → Server overload

With jitter, retries are spread out:

.. code-block:: text

    100 clients fail at t=0
    Retry between t=0.75s-1.25s → Distributed load
    Retry between t=1.5s-2.5s → Distributed load
    Retry between t=3s-5s → Distributed load

Configuration Examples
~~~~~~~~~~~~~~~~~~~~~~

Conservative (slow to retry):

.. code-block:: python

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=5.0,    # Start with 5 seconds
        max_delay=300.0,   # Cap at 5 minutes
        multiplier=3.0,    # Triple delay each time
        jitter=True
    )

Aggressive (fast retries):

.. code-block:: python

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=5,
        base_delay=0.5,    # Start with 500ms
        max_delay=30.0,    # Cap at 30 seconds
        multiplier=2.0,
        jitter=True
    )

Balanced (recommended):

.. code-block:: python

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        multiplier=2.0,
        jitter=True
    )

Circuit Breaker Strategy
-------------------------

Implements the circuit breaker pattern to prevent cascade failures.

States
~~~~~~

.. code-block:: text

    ┌──────────┐
    │  CLOSED  │ ◄──┐ Normal operation
    └────┬─────┘    │
         │          │ Success threshold met
         │ Failures │
         │ exceed   │
         │ threshold│
         ▼          │
    ┌──────────┐    │
    │   OPEN   │    │ Fail fast (no requests sent)
    └────┬─────┘    │
         │          │
         │ Recovery │
         │ timeout  │
         ▼          │
    ┌──────────┐    │
    │HALF-OPEN │ ───┘ Testing recovery
    └──────────┘

**CLOSED**: Normal operation, requests pass through

**OPEN**: Too many failures, reject requests immediately (fail fast)

**HALF-OPEN**: Testing if service recovered

Configuration
~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import CircuitBreakerRetryStrategy

    strategy = CircuitBreakerRetryStrategy(
        max_retries=3,           # Retries per request
        failure_threshold=5,     # Open after 5 failures
        recovery_timeout=30.0,   # Try again after 30 seconds
        half_open_max_calls=3,   # Test with 3 calls before closing
        base_delay=1.0           # Delay between retries
    )

    config = builder.with_retry_strategy(strategy).build()

How It Works
~~~~~~~~~~~~

.. code-block:: python

    client = HttpClient(config)

    # Normal operation (CLOSED)
    client.get('/api')  # Success
    client.get('/api')  # Success

    # Service starts failing
    client.get('/api')  # Fail (1/5)
    client.get('/api')  # Fail (2/5)
    client.get('/api')  # Fail (3/5)
    client.get('/api')  # Fail (4/5)
    client.get('/api')  # Fail (5/5) → Circuit OPENS

    # Circuit is OPEN - fail fast
    client.get('/api')  # Immediate failure (no request sent)
    client.get('/api')  # Immediate failure (no request sent)

    # After 30 seconds → HALF-OPEN
    client.get('/api')  # Try request (1/3)
    client.get('/api')  # Try request (2/3)
    client.get('/api')  # Try request (3/3)

    # If all 3 succeed → CLOSED (back to normal)
    # If any fail → OPEN again

When to Use
~~~~~~~~~~~

* Protecting downstream services from overload
* Preventing cascade failures in microservices
* When failures are likely to persist (server down, not transient network issues)

Checking Circuit State
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    strategy = CircuitBreakerRetryStrategy(...)

    print(strategy.state)  # 'closed', 'open', or 'half_open'

    # Reset circuit manually
    strategy.reset()

Custom Retry Strategy
---------------------

Implement ``RetryStrategyInterface`` for custom logic:

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    from requestforge.models import RequestContext

    class CustomRetryStrategy(RetryStrategyInterface):
        def __init__(self, max_retries=3):
            self._max_retries = max_retries

        @property
        def max_retries(self) -> int:
            return self._max_retries

        def should_retry(self, context: RequestContext, exception: Exception) -> bool:
            # Custom logic: only retry on weekdays
            import datetime
            if datetime.datetime.now().weekday() >= 5:  # Weekend
                return False

            if context.attempt >= self._max_retries:
                return False

            # Only retry on specific error
            return isinstance(exception, TimeoutException)

        def get_delay(self, context: RequestContext) -> float:
            # Custom delay: based on time of day
            import datetime
            hour = datetime.datetime.now().hour

            if 9 <= hour <= 17:  # Business hours
                return 1.0  # Short delay
            else:
                return 5.0  # Longer delay

    # Use custom strategy
    config = builder.with_retry_strategy(CustomRetryStrategy()).build()

Combining Strategies
--------------------

Request-Level vs. Auth-Level Retries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Different retry strategies for general requests vs. authentication:

.. code-block:: python

    from requestforge import (
        ExponentialBackoffRetryStrategy,
        SimpleAuthRetryStrategy
    )

    # General retry (network errors, 5xx)
    request_retry = ExponentialBackoffRetryStrategy(
        max_retries=5,
        base_delay=1.0,
        max_delay=60.0
    )

    # Auth retry (401 errors)
    auth_retry = SimpleAuthRetryStrategy(
        max_retries=1,  # Only retry auth once
        delay=0.5
    )

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry_strategy(request_retry)
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=auth_retry
        )
        .build()
    )

Retry Flow
~~~~~~~~~~

.. code-block:: text

    Request → Execute
              ↓
              Fail (401 Unauthorized)
              ↓
              Auth Retry Strategy
              ├─ Should retry? Yes
              ├─ Refresh token
              └─ Retry request → Fail (503 Service Unavailable)
                                 ↓
                                 Request Retry Strategy
                                 ├─ Should retry? Yes
                                 ├─ Wait (exponential backoff)
                                 └─ Retry request → Success

Best Practices
--------------

1. **Use Exponential Backoff in Production**

   .. code-block:: python

       # Good ✅
       strategy = ExponentialBackoffRetryStrategy(
           max_retries=3,
           base_delay=1.0,
           jitter=True
       )

2. **Enable Jitter**

   .. code-block:: python

       # Good ✅ - Prevents thundering herd
       strategy = ExponentialBackoffRetryStrategy(jitter=True)

       # Avoid ❌ - All clients retry simultaneously
       strategy = ExponentialBackoffRetryStrategy(jitter=False)

3. **Set Reasonable Max Delay**

   .. code-block:: python

       # Good ✅ - Caps at 1 minute
       strategy = ExponentialBackoffRetryStrategy(max_delay=60.0)

       # Avoid ❌ - Could wait hours
       strategy = ExponentialBackoffRetryStrategy(max_delay=3600.0)

4. **Don't Retry Non-Idempotent Operations by Default**

   .. code-block:: python

       # Careful with POST requests that create resources
       client = HttpClient(config_with_retry)

       # This could create duplicate users on retry
       response = client.post('/users', json_data={'name': 'John'})

       # Solution: Use idempotency keys
       response = client.post('/users',
           json_data={'name': 'John'},
           headers={'Idempotency-Key': 'unique-key-123'}
       )

5. **Log Retry Attempts**

   .. code-block:: python

       # Enable logging to track retries
       config = (
           HttpClientConfigBuilder()
           .with_retry(max_retries=3)
           .with_logging()  # Logs retry attempts
           .build()
       )

6. **Set Max Retries Based on SLA**

   .. code-block:: python

       # If SLA allows 30s total timeout:
       # 3 retries with exponential backoff (1s, 2s, 4s) = ~7s
       # 5 retries with exponential backoff (1s, 2s, 4s, 8s, 16s) = ~31s

       strategy = ExponentialBackoffRetryStrategy(
           max_retries=3,
           base_delay=1.0
       )

Monitoring Retries
------------------

Track retry metrics for observability:

.. code-block:: python

    from requestforge.interfaces import ErrorHookInterface

    class RetryMetricsHook(ErrorHookInterface):
        def on_error(self, exception, context):
            attempt = context.attempt
            max_retries = context.max_retries

            # Send to metrics system
            metrics.increment('http.retry.attempt', tags={
                'attempt': attempt,
                'url': context.request.url,
                'exception_type': type(exception).__name__
            })

            if attempt >= max_retries:
                metrics.increment('http.retry.exhausted')

    config = builder.with_error_hook(RetryMetricsHook()).build()

Testing Retry Logic
-------------------

Test with mock failures:

.. code-block:: python

    import pytest
    from unittest.mock import Mock, patch
    from requestforge import HttpClient, ExponentialBackoffRetryStrategy

    def test_retry_on_timeout():
        config = (
            HttpClientConfigBuilder()
            .with_base_url('https://api.example.com')
            .with_retry_strategy(
                ExponentialBackoffRetryStrategy(
                    max_retries=2,
                    base_delay=0.01  # Fast retry for testing
                )
            )
            .build()
        )
        client = HttpClient(config)

        call_count = 0
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutException('Timeout')
            return Mock(status_code=200)

        with patch.object(client.session, 'request', side_effect=mock_request):
            response = client.get('/test')
            assert response.status_code == 200
            assert call_count == 3  # Initial + 2 retries

Common Patterns
---------------

Retry with Rate Limiting
~~~~~~~~~~~~~~~~~~~~~~~~~

Respect rate limit headers:

.. code-block:: python

    from requestforge.interfaces import ResponseHookInterface

    class RateLimitRetryHook(ResponseHookInterface):
        def after_response(self, response, context):
            if response.status_code == 429:  # Too Many Requests
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    # Store in context for retry strategy
                    context.metadata['retry_after'] = int(retry_after)
            return response

Conditional Retry
~~~~~~~~~~~~~~~~~

Retry based on response content:

.. code-block:: python

    class ConditionalRetryStrategy(RetryStrategyInterface):
        def should_retry(self, context, exception):
            if isinstance(exception, HttpStatusException):
                # Check if error is retryable
                if exception.response_body:
                    return 'temporary' in exception.response_body.lower()
            return False

Next Steps
----------

* Learn about :doc:`hooks` for custom retry logic
* Explore :doc:`error-handling` for exception management
* Check :doc:`../examples/custom-retry` for advanced examples
