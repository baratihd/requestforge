Custom Retry Examples
=====================

This page demonstrates custom retry strategies and patterns.

Custom Retry Strategy
---------------------

Business Hours Retry
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    from requestforge.models import RequestContext
    from requestforge import TimeoutException, ConnectionException
    import datetime

    class BusinessHoursRetryStrategy(RetryStrategyInterface):
        """Only retry during business hours (9 AM - 5 PM)."""

        def __init__(self, max_retries=3, base_delay=1.0):
            self._max_retries = max_retries
            self._base_delay = base_delay

        @property
        def max_retries(self):
            return self._max_retries

        def should_retry(self, context, exception):
            # Check max retries
            if context.attempt >= self._max_retries:
                return False

            # Only retry during business hours
            now = datetime.datetime.now()
            if not (9 <= now.hour < 17):  # 9 AM - 5 PM
                return False

            # Only retry timeout and connection errors
            return isinstance(exception, (TimeoutException, ConnectionException))

        def get_delay(self, context):
            # Exponential backoff
            return self._base_delay * (2 ** context.attempt)

    # Usage
    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry_strategy(BusinessHoursRetryStrategy(max_retries=3))
        .build()
    )

    client = HttpClient(config)

Conditional Retry Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    from requestforge import HttpStatusException

    class ConditionalRetryStrategy(RetryStrategyInterface):
        """Retry based on response content."""

        def __init__(self, max_retries=3):
            self._max_retries = max_retries

        @property
        def max_retries(self):
            return self._max_retries

        def should_retry(self, context, exception):
            if context.attempt >= self._max_retries:
                return False

            # Only retry HTTP status exceptions
            if not isinstance(exception, HttpStatusException):
                return False

            # Check response body for retryable errors
            if exception.response_body:
                body_lower = exception.response_body.lower()

                # Retry if error is temporary
                if 'temporary' in body_lower or 'retry' in body_lower:
                    return True

                # Don't retry if error is permanent
                if 'permanent' in body_lower or 'invalid' in body_lower:
                    return False

            # Retry 5xx errors
            return 500 <= exception.status_code < 600

        def get_delay(self, context):
            return 2.0 ** context.attempt

Adaptive Retry Strategy
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    import statistics

    class AdaptiveRetryStrategy(RetryStrategyInterface):
        """Adjust retry delay based on response times."""

        def __init__(self, max_retries=5):
            self._max_retries = max_retries
            self._response_times = []

        @property
        def max_retries(self):
            return self._max_retries

        def should_retry(self, context, exception):
            return context.attempt < self._max_retries

        def get_delay(self, context):
            # Record response time from context if available
            if 'response_time' in context.metadata:
                self._response_times.append(context.metadata['response_time'])
                # Keep only last 10 measurements
                self._response_times = self._response_times[-10:]

            # Calculate delay based on average response time
            if self._response_times:
                avg_time = statistics.mean(self._response_times)
                # Delay is proportional to average response time
                return min(avg_time * 0.5, 60.0)
            else:
                # Default delay
                return 1.0 * (2 ** context.attempt)

Rate-Limit Aware Retry
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    from requestforge import HttpStatusException
    import time

    class RateLimitRetryStrategy(RetryStrategyInterface):
        """Respect rate limit headers."""

        def __init__(self, max_retries=5):
            self._max_retries = max_retries

        @property
        def max_retries(self):
            return self._max_retries

        def should_retry(self, context, exception):
            if context.attempt >= self._max_retries:
                return False

            # Always retry rate limit errors
            if isinstance(exception, HttpStatusException):
                if exception.status_code == 429:  # Too Many Requests
                    return True

            # Retry other transient errors
            from requestforge import TimeoutException, ConnectionException
            return isinstance(exception, (TimeoutException, ConnectionException))

        def get_delay(self, context):
            # Check for Retry-After header in context
            retry_after = context.metadata.get('retry_after')

            if retry_after:
                # Use Retry-After header value
                try:
                    return float(retry_after)
                except ValueError:
                    # Could be HTTP-date
                    pass

            # Check for rate limit reset timestamp
            rate_limit_reset = context.metadata.get('rate_limit_reset')
            if rate_limit_reset:
                delay = rate_limit_reset - time.time()
                return max(delay, 0)

            # Default exponential backoff
            return 2.0 ** context.attempt

Custom Retry with Hooks
------------------------

Capture Rate Limit Headers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ResponseHookInterface, ErrorHookInterface

    class RateLimitHook(ResponseHookInterface):
        """Capture rate limit information."""

        def after_response(self, response, context):
            # Store rate limit headers in context
            if 'Retry-After' in response.headers:
                context.metadata['retry_after'] = response.headers['Retry-After']

            if 'X-RateLimit-Reset' in response.headers:
                context.metadata['rate_limit_reset'] = int(
                    response.headers['X-RateLimit-Reset']
                )

            return response

    class RateLimitErrorHook(ErrorHookInterface):
        """Log rate limit errors."""

        def on_error(self, exception, context):
            from requestforge import HttpStatusException

            if isinstance(exception, HttpStatusException):
                if exception.status_code == 429:
                    retry_after = context.metadata.get('retry_after', 'unknown')
                    logger.warning(
                        f"Rate limited. Retry after: {retry_after}s"
                    )

    # Configure client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry_strategy(RateLimitRetryStrategy())
        .with_response_hook(RateLimitHook())
        .with_error_hook(RateLimitErrorHook())
        .build()
    )

Timing-Based Retry
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RequestHookInterface, ResponseHookInterface
    import time

    class TimingHooks:
        class Request(RequestHookInterface):
            def before_request(self, request, context):
                context.metadata['request_start'] = time.time()
                return request

        class Response(ResponseHookInterface):
            def after_response(self, response, context):
                start = context.metadata.get('request_start')
                if start:
                    duration = time.time() - start
                    context.metadata['response_time'] = duration
                return response

    # Use with adaptive retry
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry_strategy(AdaptiveRetryStrategy())
        .with_request_hook(TimingHooks.Request())
        .with_response_hook(TimingHooks.Response())
        .build()
    )

Retry with Fallback
-------------------

Fallback to Different Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClient, MaxRetryException

    class FallbackClient:
        """Client with fallback to secondary endpoint."""

        def __init__(self, primary_url, fallback_url):
            # Primary client with retry
            self.primary = HttpClient(
                HttpClientConfigBuilder()
                .with_base_url(primary_url)
                .with_retry(max_retries=3)
                .build()
            )

            # Fallback client (no retry)
            self.fallback = HttpClient(
                HttpClientConfigBuilder()
                .with_base_url(fallback_url)
                .build()
            )

        def get(self, path, **kwargs):
            try:
                # Try primary
                return self.primary.get(path, **kwargs)
            except MaxRetryException:
                # Fall back to secondary
                logger.warning(f"Primary failed, using fallback for {path}")
                return self.fallback.get(path, **kwargs)

    # Usage
    client = FallbackClient(
        primary_url='https://api.example.com',
        fallback_url='https://backup-api.example.com'
    )

    response = client.get('/users')

Circuit Breaker Implementation
-------------------------------

Custom Circuit Breaker
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ErrorHookInterface
    import time

    class CircuitBreaker:
        """Circuit breaker with open/half-open/closed states."""

        def __init__(self, failure_threshold=5, timeout=60, half_open_calls=3):
            self.failure_threshold = failure_threshold
            self.timeout = timeout
            self.half_open_calls = half_open_calls
            self.failures = 0
            self.last_failure_time = None
            self.state = 'closed'  # closed, open, half_open
            self.half_open_successes = 0

        def record_success(self):
            if self.state == 'half_open':
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_calls:
                    # Close circuit
                    self.state = 'closed'
                    self.failures = 0
                    self.half_open_successes = 0
            elif self.state == 'closed':
                # Reset failure count on success
                self.failures = 0

        def record_failure(self):
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                # Open circuit
                self.state = 'open'
                logger.warning(f"Circuit opened after {self.failures} failures")

        def can_attempt(self):
            if self.state == 'closed':
                return True

            if self.state == 'open':
                # Check if timeout passed
                if time.time() - self.last_failure_time >= self.timeout:
                    # Move to half-open
                    self.state = 'half_open'
                    self.half_open_successes = 0
                    return True
                return False

            if self.state == 'half_open':
                return True

            return False

    class CircuitBreakerHook(ErrorHookInterface):
        def __init__(self, circuit_breaker):
            self.cb = circuit_breaker

        def on_error(self, exception, context):
            self.cb.record_failure()

    # Usage
    circuit_breaker = CircuitBreaker()

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_error_hook(CircuitBreakerHook(circuit_breaker))
        .build()
    )

    client = HttpClient(config)

    # Check circuit before request
    if circuit_breaker.can_attempt():
        try:
            response = client.get('/data')
            circuit_breaker.record_success()
        except HttpClientException:
            pass  # Circuit breaker recorded failure
    else:
        print("Circuit is open, request not sent")

Retry Metrics
-------------

Track Retry Statistics
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ErrorHookInterface
    from collections import defaultdict

    class RetryMetricsHook(ErrorHookInterface):
        """Track retry metrics."""

        def __init__(self):
            self.retry_counts = defaultdict(int)
            self.error_types = defaultdict(int)
            self.total_retries = 0

        def on_error(self, exception, context):
            # Track retry attempt
            if context.is_retry:
                self.total_retries += 1
                self.retry_counts[context.attempt] += 1

            # Track error type
            error_type = type(exception).__name__
            self.error_types[error_type] += 1

        def get_stats(self):
            return {
                'total_retries': self.total_retries,
                'retry_distribution': dict(self.retry_counts),
                'error_types': dict(self.error_types)
            }

    # Usage
    metrics = RetryMetricsHook()

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry(max_retries=3)
        .with_error_hook(metrics)
        .build()
    )

    client = HttpClient(config)

    # Make requests
    for i in range(100):
        try:
            client.get(f'/data/{i}')
        except HttpClientException:
            pass

    # Get statistics
    stats = metrics.get_stats()
    print(f"Total retries: {stats['total_retries']}")
    print(f"Retry distribution: {stats['retry_distribution']}")
    print(f"Error types: {stats['error_types']}")

Exponential Backoff with Jitter
--------------------------------

Custom Jitter Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    import random

    class CustomJitterRetryStrategy(RetryStrategyInterface):
        """Exponential backoff with full jitter."""

        def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0):
            self._max_retries = max_retries
            self._base_delay = base_delay
            self._max_delay = max_delay

        @property
        def max_retries(self):
            return self._max_retries

        def should_retry(self, context, exception):
            return context.attempt < self._max_retries

        def get_delay(self, context):
            # Calculate exponential delay
            delay = self._base_delay * (2 ** context.attempt)
            delay = min(delay, self._max_delay)

            # Full jitter: random value between 0 and delay
            return random.uniform(0, delay)

Decorrelated Jitter
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    import random

    class DecorrelatedJitterRetryStrategy(RetryStrategyInterface):
        """Decorrelated jitter algorithm."""

        def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0):
            self._max_retries = max_retries
            self._base_delay = base_delay
            self._max_delay = max_delay
            self._last_delay = base_delay

        @property
        def max_retries(self):
            return self._max_retries

        def should_retry(self, context, exception):
            return context.attempt < self._max_retries

        def get_delay(self, context):
            # Decorrelated jitter
            delay = random.uniform(
                self._base_delay,
                self._last_delay * 3
            )
            delay = min(delay, self._max_delay)
            self._last_delay = delay
            return delay

Testing Retry Logic
-------------------

Test Retry Behavior
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    import responses
    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        ExponentialBackoffRetryStrategy,
        MaxRetryException
    )

    @responses.activate
    def test_retry_on_500():
        # First two calls fail, third succeeds
        responses.add(responses.GET, 'https://api.example.com/data', status=500)
        responses.add(responses.GET, 'https://api.example.com/data', status=500)
        responses.add(
            responses.GET,
            'https://api.example.com/data',
            json={'result': 'success'},
            status=200
        )

        strategy = ExponentialBackoffRetryStrategy(
            max_retries=3,
            base_delay=0.01  # Fast retry for testing
        )

        config = (
            HttpClientConfigBuilder()
            .with_base_url('https://api.example.com')
            .with_retry_strategy(strategy)
            .build()
        )

        client = HttpClient(config)
        response = client.get('/data')

        assert response.status_code == 200
        assert len(responses.calls) == 3  # 2 failures + 1 success

    @responses.activate
    def test_max_retries_exceeded():
        # All calls fail
        for _ in range(10):
            responses.add(
                responses.GET,
                'https://api.example.com/data',
                status=500
            )

        strategy = ExponentialBackoffRetryStrategy(max_retries=3)
        config = (
            HttpClientConfigBuilder()
            .with_base_url('https://api.example.com')
            .with_retry_strategy(strategy)
            .build()
        )

        client = HttpClient(config)

        with pytest.raises(MaxRetryException) as exc_info:
            client.get('/data')

        assert exc_info.value.attempts == 4  # 1 initial + 3 retries

See Also
--------

* :doc:`basic-requests` - Basic request examples
* :doc:`../user-guide/retry-strategies` - Retry strategies guide
* :doc:`../api-reference/retry` - Retry API reference
