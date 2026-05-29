Retry Strategies API Reference
===============================

This page documents retry strategy implementations and interfaces.

RetryStrategyInterface
----------------------

.. class:: RetryStrategyInterface

   Abstract interface for retry strategies.

   All retry strategies must implement this interface.

Methods
~~~~~~~

.. py:method:: RetryStrategyInterface.should_retry(context, exception)

   Determine if request should be retried.

   :param RequestContext context: Request context with attempt count
   :param Exception exception: Exception that caused failure
   :returns: True if should retry, False otherwise
   :rtype: bool

.. py:method:: RetryStrategyInterface.get_delay(context)

   Get delay in seconds before next retry.

   :param RequestContext context: Request context
   :returns: Delay in seconds
   :rtype: float

Properties
~~~~~~~~~~

.. attribute:: max_retries
   :type: int

   Maximum number of retry attempts.

NoRetryStrategy
---------------

.. class:: NoRetryStrategy()

   No retry strategy - fail immediately on error.

   :returns: NoRetryStrategy instance
   :rtype: NoRetryStrategy

   **Use Cases:**

   * Unit tests requiring immediate failures
   * Non-critical requests where retry overhead isn't justified
   * Operations that should never be retried

   **Example:**

   .. code-block:: python

       from requestforge import NoRetryStrategy

       strategy = NoRetryStrategy()

       print(strategy.max_retries)  # 0
       print(strategy.should_retry(context, exception))  # Always False
       print(strategy.get_delay(context))  # 0.0

SimpleRetryStrategy
-------------------

.. class:: SimpleRetryStrategy(max_retries=3, delay=1.0, retryable_exceptions=None)

   Simple retry strategy with fixed delay.

   :param int max_retries: Maximum retry attempts
   :param float delay: Fixed delay between retries in seconds
   :param frozenset retryable_exceptions: Exception types to retry (optional)

Attributes
~~~~~~~~~~

.. attribute:: SimpleRetryStrategy.max_retries
   :type: int

   Maximum number of retry attempts.

Methods
~~~~~~~

.. py:method:: SimpleRetryStrategy.should_retry(context, exception)

   Check if should retry based on attempt count and exception type.

   :param RequestContext context: Request context
   :param Exception exception: Exception that occurred
   :returns: True if should retry
   :rtype: bool

.. py:method:: SimpleRetryStrategy.get_delay(context)

   Get fixed delay.

   :param RequestContext context: Request context
   :returns: Fixed delay in seconds
   :rtype: float

Examples
~~~~~~~~

.. code-block:: python

    from requestforge import SimpleRetryStrategy, TimeoutException, ConnectionException

    # Basic usage
    strategy = SimpleRetryStrategy(max_retries=3, delay=2.0)

    # Only retry specific exceptions
    strategy = SimpleRetryStrategy(
        max_retries=3,
        delay=1.0,
        retryable_exceptions=frozenset({
            TimeoutException,
            ConnectionException
        })
    )

    # Configure client
    config = builder.with_retry_strategy(strategy).build()

ExponentialBackoffRetryStrategy
--------------------------------

.. class:: ExponentialBackoffRetryStrategy(max_retries=3, base_delay=1.0, max_delay=60.0, multiplier=2.0, jitter=True, retryable_exceptions=None, retryable_status_codes=None)

   Exponential backoff retry strategy with jitter.

   **Recommended for production use.**

   :param int max_retries: Maximum retry attempts
   :param float base_delay: Initial delay in seconds
   :param float max_delay: Maximum delay cap in seconds
   :param float multiplier: Exponential multiplier
   :param bool jitter: Add random jitter (±25%)
   :param frozenset retryable_exceptions: Exception types to retry
   :param frozenset retryable_status_codes: HTTP status codes to retry

Attributes
~~~~~~~~~~

.. attribute:: ExponentialBackoffRetryStrategy.max_retries
   :type: int

   Maximum number of retry attempts.

Methods
~~~~~~~

.. py:method:: ExponentialBackoffRetryStrategy.should_retry(context, exception)

   Check if should retry based on attempt count, exception type, and status code.

   :param RequestContext context: Request context
   :param Exception exception: Exception that occurred
   :returns: True if should retry
   :rtype: bool

.. py:method:: ExponentialBackoffRetryStrategy.get_delay(context)

   Calculate exponential backoff delay with optional jitter.

   :param RequestContext context: Request context
   :returns: Delay in seconds
   :rtype: float

   **Delay Formula:**

   .. code-block:: python

       delay = min(base_delay * (multiplier ** attempt), max_delay)

       if jitter:
           jitter_range = delay * 0.25
           delay += random(-jitter_range, jitter_range)

.. method:: is_retryable_status(status_code)

   Check if HTTP status code is retryable.

   :param int status_code: HTTP status code
   :returns: True if status code is retryable
   :rtype: bool

.. method:: is_max_retry(context)

   Check if maximum retries reached.

   :param RequestContext context: Request context
   :returns: True if max retries reached
   :rtype: bool

Examples
~~~~~~~~

.. code-block:: python

    from requestforge import ExponentialBackoffRetryStrategy

    # Recommended production configuration
    strategy = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        multiplier=2.0,
        jitter=True
    )

    # Custom retryable status codes
    strategy = ExponentialBackoffRetryStrategy(
        max_retries=5,
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

    # Aggressive retry (fast)
    strategy = ExponentialBackoffRetryStrategy(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0,
        multiplier=2.0,
        jitter=True
    )

    # Conservative retry (slow)
    strategy = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=5.0,
        max_delay=300.0,
        multiplier=3.0,
        jitter=True
    )

**Retry Timeline Example:**

.. code-block:: text

    Attempt 1: Immediate
    Attempt 2: ~1s delay    (1.0 * 2^0 ± jitter)
    Attempt 3: ~2s delay    (1.0 * 2^1 ± jitter)
    Attempt 4: ~4s delay    (1.0 * 2^2 ± jitter)
    Attempt 5: ~8s delay    (1.0 * 2^3 ± jitter)

CircuitBreakerRetryStrategy
----------------------------

.. class:: CircuitBreakerRetryStrategy(max_retries=3, failure_threshold=5, recovery_timeout=30.0, half_open_max_calls=3, base_delay=1.0)

   Circuit breaker pattern implementation.

   :param int max_retries: Retries per request
   :param int failure_threshold: Failures before opening circuit
   :param float recovery_timeout: Seconds before testing recovery
   :param int half_open_max_calls: Test calls in half-open state
   :param float base_delay: Base delay between retries

States
~~~~~~

The circuit breaker has three states:

* **CLOSED**: Normal operation, requests pass through
* **OPEN**: Too many failures, reject requests immediately
* **HALF_OPEN**: Testing if service recovered

Attributes
~~~~~~~~~~

.. attribute:: CircuitBreakerRetryStrategy.max_retries
   :type: int

   Maximum retry attempts per request.

.. attribute:: CircuitBreakerRetryStrategy.state
   :type: str

   Current circuit state: 'closed', 'open', or 'half_open'.

Methods
~~~~~~~

.. py:method:: CircuitBreakerRetryStrategy.should_retry(context, exception)

   Check if should retry considering circuit state.

   :param RequestContext context: Request context
   :param Exception exception: Exception that occurred
   :returns: True if should retry
   :rtype: bool

.. py:method:: CircuitBreakerRetryStrategy.get_delay(context)

   Get delay based on attempt number.

   :param RequestContext context: Request context
   :returns: Delay in seconds
   :rtype: float

.. method:: record_success()

   Record a successful request (may close circuit).

.. method:: reset()

   Reset circuit breaker to CLOSED state.

Examples
~~~~~~~~

.. code-block:: python

    from requestforge import CircuitBreakerRetryStrategy

    strategy = CircuitBreakerRetryStrategy(
        max_retries=3,
        failure_threshold=5,     # Open after 5 failures
        recovery_timeout=30.0,   # Try recovery after 30s
        half_open_max_calls=3    # Test with 3 calls
    )

    config = builder.with_retry_strategy(strategy).build()
    client = HttpClient(config)

    # Check circuit state
    print(strategy.state)  # 'closed', 'open', or 'half_open'

    # Reset circuit manually
    strategy.reset()

**State Transitions:**

.. code-block:: text

    CLOSED ──(5 failures)──> OPEN ──(30s timeout)──> HALF_OPEN
       ↑                                                  |
       └────────────(3 successful calls)─────────────────┘

Auth Retry Strategies
---------------------

NoAuthRetryStrategy
~~~~~~~~~~~~~~~~~~~

.. class:: NoAuthRetryStrategy(auth_error_codes=None)

   No authentication retry - fail immediately on auth error.

   :param frozenset auth_error_codes: HTTP codes considered auth errors (default: {401})

SimpleAuthRetryStrategy
~~~~~~~~~~~~~~~~~~~~~~~

.. class:: SimpleAuthRetryStrategy(max_retries=1, delay=0.0, auth_error_codes=None)

   Simple auth retry with fixed delay.

   :param int max_retries: Maximum auth retry attempts
   :param float delay: Delay between retries
   :param frozenset auth_error_codes: Auth error codes (default: {401})

ExponentialAuthRetryStrategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: ExponentialAuthRetryStrategy(max_retries=2, base_delay=0.5, max_delay=5.0, multiplier=2.0, jitter=True, auth_error_codes=None)

   Exponential backoff for auth retries.

   :param int max_retries: Maximum retry attempts
   :param float base_delay: Initial delay
   :param float max_delay: Maximum delay cap
   :param float multiplier: Exponential multiplier
   :param bool jitter: Add random jitter
   :param frozenset auth_error_codes: Auth error codes

ConditionalAuthRetryStrategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: ConditionalAuthRetryStrategy(max_retries=1, delay=0.0, should_retry_func=None, is_auth_error_func=None, auth_error_codes=None)

   Conditional auth retry based on custom logic.

   :param int max_retries: Maximum retry attempts
   :param float delay: Delay between retries
   :param callable should_retry_func: Custom function to determine if should retry
   :param callable is_auth_error_func: Custom function to identify auth errors
   :param frozenset auth_error_codes: Auth error codes

   **Example:**

   .. code-block:: python

       def should_retry(response):
           # Only retry if error is "token_expired"
           if response.status_code == 401:
               data = response.json_or_none()
               return data and data.get('error') == 'token_expired'
           return False

       strategy = ConditionalAuthRetryStrategy(
           max_retries=2,
           should_retry_func=should_retry
       )

Custom Retry Strategy
---------------------

Implementing a custom retry strategy:

.. code-block:: python

    from requestforge.interfaces import RetryStrategyInterface
    from requestforge.models import RequestContext

    class CustomRetryStrategy(RetryStrategyInterface):
        """Custom retry strategy with business logic."""

        def __init__(self, max_retries=3):
            self._max_retries = max_retries

        @property
        def max_retries(self) -> int:
            return self._max_retries

        def should_retry(self, context: RequestContext, exception: Exception) -> bool:
            # Custom logic
            if context.attempt >= self._max_retries:
                return False

            # Only retry on specific days
            import datetime
            if datetime.datetime.now().weekday() >= 5:  # Weekend
                return False

            # Only retry timeout errors
            from requestforge import TimeoutException
            return isinstance(exception, TimeoutException)

        def get_delay(self, context: RequestContext) -> float:
            # Custom delay based on time of day
            import datetime
            hour = datetime.datetime.now().hour

            if 9 <= hour <= 17:  # Business hours
                return 1.0
            else:
                return 5.0  # Off-hours, longer delay

    # Use custom strategy
    config = builder.with_retry_strategy(CustomRetryStrategy()).build()

See Also
--------

* :doc:`../user-guide/retry-strategies` - Retry strategies user guide
* :doc:`client` - HTTP client API
* :doc:`exceptions` - Exception types
