"""
Tests for retry strategies.
    - No retry strategy
    - Simple retry strategy
    - Exponential backoff calculations
    - Circuit breaker pattern
    - Auth-specific retry strategies
    - Conditional retry logic
"""

import time
from unittest.mock import Mock

import pytest

from requestforge.retry import (
    NoRetryStrategy,
    NoAuthRetryStrategy,
    SimpleRetryStrategy,
    SimpleAuthRetryStrategy,
    CircuitBreakerRetryStrategy,
    ConditionalAuthRetryStrategy,
    ExponentialAuthRetryStrategy,
    ExponentialBackoffRetryStrategy,
)
from requestforge.exceptions import TimeoutException, ConnectionException


class TestNoRetryStrategy:
    """Test NoRetryStrategy."""

    def test_max_retries(self):
        """Test max retries is zero."""
        strategy = NoRetryStrategy()
        assert strategy.max_retries == 0

    def test_should_not_retry(self, request_context):
        """Test that no retry strategy never retries."""
        strategy = NoRetryStrategy()
        assert not strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )

    def test_delay_is_zero(self, request_context):
        """Test delay is zero."""
        strategy = NoRetryStrategy()
        assert strategy.get_delay(request_context) == 0.0


class TestSimpleRetryStrategy:
    """Test SimpleRetryStrategy."""

    def test_max_retries(self):
        """Test max retries setting."""
        strategy = SimpleRetryStrategy(max_retries=5)
        assert strategy.max_retries == 5

    def test_fixed_delay(self, request_context):
        """Test fixed delay."""
        strategy = SimpleRetryStrategy(delay=2.0)
        assert strategy.get_delay(request_context) == 2.0

    def test_should_retry_within_limit(self, request_context):
        """Test retry within limit (Retries until max)."""
        strategy = SimpleRetryStrategy(max_retries=3)
        request_context.attempt = 0
        assert strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )

        request_context.attempt = 2
        assert strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )

    def test_should_not_retry_at_limit(self, request_context):
        """Test no retry at limit (Stops at max)."""
        strategy = SimpleRetryStrategy(max_retries=3)
        request_context.attempt = 3
        assert not strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )

    def test_retryable_exceptions_filter(self, request_context):
        """Test filtering by retryable exceptions."""
        retryable = frozenset({TimeoutException})
        strategy = SimpleRetryStrategy(retryable_exceptions=retryable)

        request_context.attempt = 0
        assert strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )
        assert not strategy.should_retry(
            request_context, ConnectionException("Connection")
        )


class TestExponentialBackoffRetryStrategy:
    """
    Test ExponentialBackoffRetryStrategy.

    Delay Formula:
    >>> delay = min(base_delay * multiplier^attempt + jitter, max_delay)
    """

    def test_max_retries(self):
        """Test configurable max retries."""
        strategy = ExponentialBackoffRetryStrategy(max_retries=5)
        assert strategy.max_retries == 5

    def test_exponential_delay_calculation(self, request_context):
        """Test exponential delay calculation (1s, 2s, 4s, 8s...)."""
        strategy = ExponentialBackoffRetryStrategy(
            max_retries=5,
            base_delay=1.0,
            multiplier=2.0,
            jitter=False,
        )

        request_context.attempt = 0
        delay_0 = strategy.get_delay(request_context)
        assert delay_0 == pytest.approx(1.0, abs=0.1)

        request_context.attempt = 1
        delay_1 = strategy.get_delay(request_context)
        assert delay_1 == pytest.approx(2.0, abs=0.1)

        request_context.attempt = 2
        delay_2 = strategy.get_delay(request_context)
        assert delay_2 == pytest.approx(4.0, abs=0.1)

    def test_max_delay_cap(self, request_context):
        """Test maximum delay cap."""
        strategy = ExponentialBackoffRetryStrategy(
            max_retries=10,
            base_delay=1.0,
            max_delay=10.0,
            jitter=False,
        )

        request_context.attempt = 10
        delay = strategy.get_delay(request_context)
        assert delay <= 10.0

    def test_jitter_randomization(self, request_context):
        """
        Test jitter adds randomization.

        Randomization prevents thundering herd
        """
        strategy = ExponentialBackoffRetryStrategy(
            max_retries=5,
            base_delay=10.0,
            jitter=True,
        )

        delays = []
        for attempt in range(5):
            request_context.attempt = attempt
            delays.append(strategy.get_delay(request_context))

        # All delays should be different (with high probability)
        assert len(set(delays)) >= 3

    def test_should_retry_with_retryable_exception(self, request_context):
        """
        Test should retry with retryable exception.

        Timeout/Connection retry
        """
        strategy = ExponentialBackoffRetryStrategy(max_retries=3)
        request_context.attempt = 0

        assert strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )
        assert strategy.should_retry(
            request_context, ConnectionException("Connection")
        )

    def test_should_not_retry_at_max(self, request_context):
        """Test should not retry at max (stops at max)."""
        strategy = ExponentialBackoffRetryStrategy(max_retries=3)
        request_context.attempt = 3

        assert not strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )

    def test_retryable_status_codes(self):
        """
        Test retryable status codes.

        408, 429, 500, 502, 503, 504
        """
        strategy = ExponentialBackoffRetryStrategy()

        assert strategy.is_retryable_status(500)
        assert strategy.is_retryable_status(502)
        assert strategy.is_retryable_status(503)
        assert strategy.is_retryable_status(429)
        assert not strategy.is_retryable_status(404)
        assert not strategy.is_retryable_status(200)

    def test_is_max_retry(self, request_context):
        """Test is_max_retry check."""
        strategy = ExponentialBackoffRetryStrategy(max_retries=3)

        request_context.attempt = 2
        assert not strategy.is_max_retry(request_context)

        request_context.attempt = 3
        assert strategy.is_max_retry(request_context)


class TestCircuitBreakerRetryStrategy:
    """
    Test CircuitBreakerRetryStrategy.

    State Machine:
    CLOSED → (5 failures) → OPEN → (30s) → HALF_OPEN → (3 successes) → CLOSED
                ↑_____________________________________________|
    """

    def test_initial_state_closed(self):
        """Test initial state is CLOSED."""
        strategy = CircuitBreakerRetryStrategy()
        assert strategy.state == CircuitBreakerRetryStrategy.State.CLOSED

    def test_circuit_opens_on_failure_threshold(self, request_context):
        """
        Test circuit opens after failure threshold.

        Opens after N failures
        """
        strategy = CircuitBreakerRetryStrategy(
            failure_threshold=2, max_retries=1
        )

        # First failure
        request_context.attempt = 0
        strategy.should_retry(request_context, TimeoutException("Timeout"))
        strategy._record_failure()
        assert strategy.state == CircuitBreakerRetryStrategy.State.CLOSED

        # Second failure
        strategy.should_retry(request_context, TimeoutException("Timeout"))
        strategy._record_failure()
        assert strategy.state == CircuitBreakerRetryStrategy.State.OPEN

    def test_circuit_prevents_requests_when_open(self, request_context):
        """Test circuit prevents requests when open."""
        strategy = CircuitBreakerRetryStrategy()
        strategy._state = CircuitBreakerRetryStrategy.State.OPEN
        strategy._last_failure_time = time.time()

        request_context.attempt = 0
        assert not strategy.should_retry(
            request_context, TimeoutException("Timeout")
        )

    def test_circuit_half_open_after_timeout(self, request_context):
        """Test circuit transitions to HALF_OPEN after timeout."""
        strategy = CircuitBreakerRetryStrategy(recovery_timeout=0.1)
        strategy._state = CircuitBreakerRetryStrategy.State.OPEN
        strategy._last_failure_time = (
            time.time() - 0.2
        )  # Past recovery timeout

        request_context.attempt = 0
        strategy.should_retry(request_context, TimeoutException("Timeout"))
        assert strategy.state == CircuitBreakerRetryStrategy.State.HALF_OPEN

    def test_reset_circuit(self):
        """Test resetting circuit breaker (manual reset to CLOSED)."""
        strategy = CircuitBreakerRetryStrategy()
        strategy._state = CircuitBreakerRetryStrategy.State.OPEN
        strategy._failure_count = 5

        strategy.reset()

        assert strategy.state == CircuitBreakerRetryStrategy.State.CLOSED
        assert strategy._failure_count == 0


class TestNoAuthRetryStrategy:
    """Test NoAuthRetryStrategy."""

    def test_no_retry_on_auth_error(self):
        """Test no retry on 401."""
        strategy = NoAuthRetryStrategy()
        assert strategy.max_retries == 0
        assert not strategy.should_retry(Mock(), attempt=0)

    def test_is_auth_error_401(self):
        """Test 401 is auth error."""
        strategy = NoAuthRetryStrategy()
        response = Mock(status_code=401)
        assert strategy.is_auth_error(response)

    def test_is_auth_error_other_codes(self):
        """Test other status codes are not auth errors."""
        strategy = NoAuthRetryStrategy()
        assert not strategy.is_auth_error(Mock(status_code=200))
        assert not strategy.is_auth_error(Mock(status_code=500))


class TestSimpleAuthRetryStrategy:
    """Test SimpleAuthRetryStrategy."""

    def test_max_retries(self):
        """Test max retries setting."""
        strategy = SimpleAuthRetryStrategy(max_retries=2)
        assert strategy.max_retries == 2

    def test_fixed_delay(self):
        """Test fixed delay."""
        strategy = SimpleAuthRetryStrategy(delay=1.5)
        assert strategy.get_delay(attempt=0) == 1.5
        assert strategy.get_delay(attempt=1) == 1.5

    def test_should_retry_within_limit(self):
        """Test retry within limit."""
        strategy = SimpleAuthRetryStrategy(max_retries=2)
        response = Mock(status_code=401)

        assert strategy.should_retry(response, attempt=0)
        assert strategy.should_retry(response, attempt=1)

    def test_should_not_retry_at_limit(self):
        """Test no retry at limit."""
        strategy = SimpleAuthRetryStrategy(max_retries=2)
        response = Mock(status_code=401)

        assert not strategy.should_retry(response, attempt=2)

    def test_custom_auth_error_codes(self):
        """Test custom auth error codes."""
        strategy = SimpleAuthRetryStrategy(
            auth_error_codes=frozenset({401, 403})
        )

        assert strategy.is_auth_error(Mock(status_code=401))
        assert strategy.is_auth_error(Mock(status_code=403))
        assert not strategy.is_auth_error(Mock(status_code=200))


class TestExponentialAuthRetryStrategy:
    """Test ExponentialAuthRetryStrategy."""

    def test_exponential_delay(self):
        """Test exponential delay (0.5s, 1s, 2s...)."""
        strategy = ExponentialAuthRetryStrategy(
            max_retries=3,
            base_delay=1.0,
            multiplier=2.0,
            jitter=False,
        )

        assert strategy.get_delay(0) == pytest.approx(1.0)
        assert strategy.get_delay(1) == pytest.approx(2.0)
        assert strategy.get_delay(2) == pytest.approx(4.0)

    def test_max_delay_cap(self):
        """Test max delay cap."""
        strategy = ExponentialAuthRetryStrategy(
            max_retries=5,
            base_delay=1.0,
            max_delay=5.0,
            jitter=False,
        )

        delay = strategy.get_delay(5)
        assert delay <= 5.0


class TestConditionalAuthRetryStrategy:
    """
    Test ConditionalAuthRetryStrategy.

    Custom Logic:
    >>> strategy = ConditionalAuthRetryStrategy(
    ...     should_retry_func=lambda r: r.json().get('error') == 'token_expired',
    ...     is_auth_error_func=lambda r: r.status_code in {401, 403}
    ... )
    """

    def test_with_custom_should_retry(self):
        """Test with custom should_retry function (function decides retry)."""

        def should_retry_func(response):
            data = response.json_or_none()
            return data and data.get("error") == "token_expired"

        strategy = ConditionalAuthRetryStrategy(
            max_retries=2,
            should_retry_func=should_retry_func,
        )

        response_expired = Mock()
        response_expired.json_or_none.return_value = {"error": "token_expired"}
        response_expired.status_code = 401

        assert strategy.should_retry(response_expired, attempt=0)

    def test_with_custom_is_auth_error(self):
        """Test with custom is_auth_error function (function detects auth error)."""

        def is_auth_error_func(response):
            return response.status_code in {401, 403}

        strategy = ConditionalAuthRetryStrategy(
            is_auth_error_func=is_auth_error_func
        )

        assert strategy.is_auth_error(Mock(status_code=401))
        assert strategy.is_auth_error(Mock(status_code=403))
        assert not strategy.is_auth_error(Mock(status_code=200))
