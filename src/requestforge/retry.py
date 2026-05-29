from __future__ import annotations

import time
from typing import TYPE_CHECKING
import secrets

from requestforge.interfaces import (
    RetryStrategyInterface,
    AuthRetryStrategyInterface,
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from requestforge.models import HttpResponse, RequestContext


class NoRetryStrategy(RetryStrategyInterface):
    """No retry - fail immediately on error."""

    @property
    def max_retries(self) -> int:
        return 0

    def should_retry(
        self, context: RequestContext, exception: Exception
    ) -> bool:
        return False

    def get_delay(self, context: RequestContext) -> float:
        return 0.0


class SimpleRetryStrategy(RetryStrategyInterface):
    """Simple retry with fixed delay."""

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        retryable_exceptions: frozenset[type[Exception]] | None = None,
    ):
        self._max_retries = max_retries
        self._delay = delay
        self._retryable_exceptions = retryable_exceptions

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(
        self, context: RequestContext, exception: Exception
    ) -> bool:
        if context.attempt >= self._max_retries:
            return False

        if self._retryable_exceptions:
            return any(
                isinstance(exception, exc_type)
                for exc_type in self._retryable_exceptions
            )
        return True

    def get_delay(self, context: RequestContext) -> float:
        return self._delay


class ExponentialBackoffRetryStrategy(RetryStrategyInterface):
    """
    Exponential backoff retry strategy with jitter.

    Delay formula: min(base_delay * (multiplier ^ attempt) + jitter, max_delay)

    Attributes:
        `max_retries`: Maximum retry attempts
        `base_delay`: Initial delay in seconds
        `max_delay`: Maximum delay cap in seconds
        `multiplier`: Exponential multiplier
        `jitter`: Whether to add random jitter
        `retryable_exceptions`: Set of exception types to retry
        `retryable_status_codes`: Set of HTTP status codes to retry
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: frozenset[type[Exception]] | None = None,
        retryable_status_codes: frozenset[int] | None = None,
    ):
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._multiplier = multiplier
        self._jitter = jitter
        self._retryable_exceptions = retryable_exceptions
        self._retryable_status_codes = retryable_status_codes or frozenset(
            {
                408,  # Request Timeout
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            }
        )

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def is_max_retry(self, context: RequestContext) -> bool:
        return bool(context.attempt >= self._max_retries)

    def should_retry(
        self, context: RequestContext, exception: Exception
    ) -> bool:
        if self.is_max_retry(context):
            return False

        # Check retryable exception types
        if self._retryable_exceptions:
            return any(
                isinstance(exception, exc_type)
                for exc_type in self._retryable_exceptions
            )

        # By default, retry on common transient errors
        from requestforge.exceptions import (
            TimeoutException,
            ConnectionException,
            HttpStatusException,
        )

        # For HttpStatusException, it's already been checked by is_retryable_status
        # so we accept it here
        if isinstance(exception, HttpStatusException):
            return True

        return isinstance(exception, TimeoutException | ConnectionException)

    def get_delay(self, context: RequestContext) -> float:
        # Calculate exponential delay
        delay = self._base_delay * (self._multiplier**context.attempt)

        # Add jitter (±25% randomization)
        if self._jitter:
            jitter_range = delay * 0.25
            delay += (
                secrets.randbelow(int(jitter_range * 2 * 1_000_000))
                / 1_000_000
                - jitter_range
            )

        # Cap at max_delay
        return min(max(delay, 0), self._max_delay)

    def is_retryable_status(self, status_code: int) -> bool:
        """Check if HTTP status code is retryable."""
        return status_code in self._retryable_status_codes


class CircuitBreakerRetryStrategy(RetryStrategyInterface):
    """Circuit breaker pattern implementation."""

    class State:
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(
        self,
        max_retries: int = 3,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        base_delay: float = 1.0,
    ):
        self._max_retries = max_retries
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._base_delay = base_delay

        self._state = self.State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def state(self) -> str:
        return self._state

    def should_retry(
        self, context: RequestContext, exception: Exception
    ) -> bool:
        current_time = time.time()

        if self._state == self.State.OPEN:
            # Check if recovery timeout passed
            if (
                self._last_failure_time
                and current_time - self._last_failure_time
                >= self._recovery_timeout
            ):
                self._state = self.State.HALF_OPEN
                self._half_open_calls = 0
            else:
                return False

        if context.attempt >= self._max_retries:
            self._record_failure()
            return False

        return True

    def get_delay(self, context: RequestContext) -> float:
        return self._base_delay * (context.attempt + 1)

    def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._failure_threshold:
            self._state = self.State.OPEN

    def record_success(self) -> None:
        """Record a success and potentially close the circuit."""
        if self._state == self.State.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self._half_open_max_calls:
                self._state = self.State.CLOSED
                self._failure_count = 0
        elif self._state == self.State.CLOSED:
            self._failure_count = 0

    def reset(self) -> None:
        """Reset circuit breaker state."""
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0


class NoAuthRetryStrategy(AuthRetryStrategyInterface):
    """No auth retry - fail immediately on auth error."""

    def __init__(self, auth_error_codes: frozenset[int] | None = None):
        self._auth_error_codes = auth_error_codes or frozenset({401})

    @property
    def max_retries(self) -> int:
        return 0

    def should_retry(self, response: HttpResponse, attempt: int) -> bool:
        return False

    def get_delay(self, attempt: int) -> float:
        return 0.0

    def is_auth_error(self, response: HttpResponse) -> bool:
        return response.status_code in self._auth_error_codes


class SimpleAuthRetryStrategy(AuthRetryStrategyInterface):
    """Simple auth retry with fixed delay."""

    def __init__(
        self,
        max_retries: int = 1,
        delay: float = 0.0,
        auth_error_codes: frozenset[int] | None = None,
    ):
        self._max_retries = max_retries
        self._delay = delay
        self._auth_error_codes = auth_error_codes or frozenset({401})

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(self, response: HttpResponse, attempt: int) -> bool:
        if attempt >= self._max_retries:
            return False
        return self.is_auth_error(response)

    def get_delay(self, attempt: int) -> float:
        return self._delay

    def is_auth_error(self, response: HttpResponse) -> bool:
        return response.status_code in self._auth_error_codes


class ExponentialAuthRetryStrategy(AuthRetryStrategyInterface):
    """Exponential backoff for auth retries."""

    def __init__(
        self,
        max_retries: int = 2,
        base_delay: float = 0.5,
        max_delay: float = 5.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        auth_error_codes: frozenset[int] | None = None,
    ):
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._multiplier = multiplier
        self._jitter = jitter
        self._auth_error_codes = auth_error_codes or frozenset({401})

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(self, response: HttpResponse, attempt: int) -> bool:
        if attempt >= self._max_retries:
            return False
        return self.is_auth_error(response)

    def get_delay(self, attempt: int) -> float:
        delay = self._base_delay * (self._multiplier**attempt)

        if self._jitter:
            jitter_range = delay * 0.25
            jitter_value = (
                secrets.randbelow(int(jitter_range * 2 * 1_000_000))
                / 1_000_000
            ) - jitter_range
            delay += jitter_value

        return min(max(delay, 0), self._max_delay)

    def is_auth_error(self, response: HttpResponse) -> bool:
        return response.status_code in self._auth_error_codes


class ConditionalAuthRetryStrategy(AuthRetryStrategyInterface):
    """Conditional auth retry based on response content."""

    def __init__(
        self,
        max_retries: int = 1,
        delay: float = 0.0,
        should_retry_func: Callable[[HttpResponse], bool] | None = None,
        is_auth_error_func: Callable[[HttpResponse], bool] | None = None,
        auth_error_codes: frozenset[int] | None = None,
    ):
        self._max_retries = max_retries
        self._delay = delay
        self._should_retry_func = should_retry_func
        self._is_auth_error_func = is_auth_error_func
        self._auth_error_codes = auth_error_codes or frozenset({401})

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(self, response: HttpResponse, attempt: int) -> bool:
        if attempt >= self._max_retries:
            return False

        if not self.is_auth_error(response):
            return False

        if self._should_retry_func:
            return self._should_retry_func(response)

        return True

    def get_delay(self, attempt: int) -> float:
        return self._delay

    def is_auth_error(self, response: HttpResponse) -> bool:
        if self._is_auth_error_func:
            return self._is_auth_error_func(response)
        return response.status_code in self._auth_error_codes
