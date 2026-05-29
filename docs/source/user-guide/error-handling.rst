Error Handling
==============

Request Forge provides a comprehensive exception hierarchy for robust error handling.

Exception Hierarchy
-------------------

All HTTP Client exceptions inherit from ``HttpClientException``:

.. code-block:: text

    HttpClientException (base)
    ├── MaxRetryException          # Maximum retries exceeded
    ├── TimeoutException           # Request timeout
    ├── ConnectionException        # Network/connection errors
    ├── SSLException               # SSL/TLS errors
    ├── ResponseParseException     # JSON/response parsing errors
    ├── AuthenticationException    # Authentication failures
    │   └── TokenRefreshException  # Token refresh failures
    └── HttpStatusException        # HTTP error status codes
        ├── BadRequestException      # 400 Bad Request
        ├── UnauthorizedException    # 401 Unauthorized
        ├── ForbiddenException       # 403 Forbidden
        ├── NotFoundException        # 404 Not Found
        └── ServerErrorException     # 5xx Server Errors

Base Exception
--------------

HttpClientException
~~~~~~~~~~~~~~~~~~~

All exceptions inherit from this base class:

.. code-block:: python

    from requestforge import HttpClientException

    try:
        response = client.get('/users/1')
    except HttpClientException as e:
        print(f"Error: {e.message}")
        print(f"Original exception: {e.original_exception}")
        print(f"Context: {e.context}")

**Attributes:**

* ``message`` (str): Human-readable error message
* ``original_exception`` (Exception | None): Original underlying exception
* ``context`` (dict): Additional context about the error

Network Errors
--------------

TimeoutException
~~~~~~~~~~~~~~~~

Raised when a request times out:

.. code-block:: python

    from requestforge import TimeoutException

    try:
        response = client.get('/slow-endpoint', timeout=5.0)
    except TimeoutException as e:
        print(f"Request timed out after 5 seconds")
        print(f"URL: {e.context.get('request').url}")

**When raised:**

* Request exceeds configured timeout
* Connection timeout
* Read timeout

**Best practices:**

.. code-block:: python

    # Handle timeout with retry
    from requestforge import TimeoutException
    import time

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = client.get('/data', timeout=10.0)
            break
        except TimeoutException:
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise

ConnectionException
~~~~~~~~~~~~~~~~~~~

Raised on network connection failures:

.. code-block:: python

    from requestforge import ConnectionException

    try:
        response = client.get('/users')
    except ConnectionException as e:
        print(f"Network error: {e.message}")
        # Check if server is unreachable
        if "Connection refused" in str(e.original_exception):
            print("Server is not running")

**Common causes:**

* Server is down or unreachable
* DNS resolution failure
* Network connectivity issues
* Firewall blocking connection

**Handling:**

.. code-block:: python

    from requestforge import ConnectionException
    import logging

    try:
        response = client.get('/api/data')
    except ConnectionException as e:
        logging.error(f"Cannot connect to API: {e}")
        # Fallback to cached data or show error to user
        return get_cached_data()

SSLException
~~~~~~~~~~~~

Raised on SSL/TLS errors:

.. code-block:: python

    from requestforge import SSLException

    try:
        response = client.get('https://self-signed.badssl.com')
    except SSLException as e:
        print(f"SSL error: {e.message}")
        print(f"Original: {e.original_exception}")

**Common causes:**

* Invalid SSL certificate
* Self-signed certificate
* Certificate expired
* Hostname mismatch

**Disabling SSL verification (not recommended for production):**

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_verify_ssl(False)  # ⚠️ Security risk!
        .build()
    )

HTTP Status Errors
------------------

HttpStatusException
~~~~~~~~~~~~~~~~~~~

Base class for HTTP status code errors:

.. code-block:: python

    from requestforge import HttpStatusException

    try:
        response = client.get('/users/999')
    except HttpStatusException as e:
        print(f"HTTP {e.status_code}: {e.message}")
        print(f"Response body: {e.response_body}")

**Attributes:**

* ``status_code`` (int): HTTP status code
* ``response_body`` (str | None): Response body content
* ``message`` (str): Error message
* ``original_exception`` (Exception | None): Original exception
* ``context`` (dict): Request context

BadRequestException (400)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Raised for 400 Bad Request responses:

.. code-block:: python

    from requestforge import BadRequestException

    try:
        response = client.post('/users', json_data={
            'email': 'invalid-email'  # Invalid data
        })
    except BadRequestException as e:
        print(f"Invalid request: {e.response_body}")
        # Parse error details
        error_data = json.loads(e.response_body)
        for field, errors in error_data.get('errors', {}).items():
            print(f"{field}: {errors}")

UnauthorizedException (401)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Raised for 401 Unauthorized responses:

.. code-block:: python

    from requestforge import UnauthorizedException

    try:
        response = client.get('/protected-resource')
    except UnauthorizedException:
        print("Authentication required or token expired")
        # Redirect to login or refresh token

**Note:** When using ``TokenAuthHook``, 401 errors trigger automatic token refresh and retry.

ForbiddenException (403)
~~~~~~~~~~~~~~~~~~~~~~~~

Raised for 403 Forbidden responses:

.. code-block:: python

    from requestforge import ForbiddenException

    try:
        response = client.delete('/admin/users/1')
    except ForbiddenException:
        print("Insufficient permissions")
        # Show error to user or request elevated access

NotFoundException (404)
~~~~~~~~~~~~~~~~~~~~~~~

Raised for 404 Not Found responses:

.. code-block:: python

    from requestforge import NotFoundException

    try:
        response = client.get('/users/nonexistent')
    except NotFoundException:
        print("Resource not found")
        return None  # Or show 404 page

ServerErrorException (5xx)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Raised for 5xx server errors:

.. code-block:: python

    from requestforge import ServerErrorException

    try:
        response = client.get('/api/data')
    except ServerErrorException as e:
        print(f"Server error {e.status_code}")
        if e.status_code == 503:
            print("Service temporarily unavailable")
        elif e.status_code == 500:
            print("Internal server error")

Retry Errors
------------

MaxRetryException
~~~~~~~~~~~~~~~~~

Raised when maximum retry attempts are exceeded:

.. code-block:: python

    from requestforge import MaxRetryException

    try:
        response = client.get('/unstable-endpoint')
    except MaxRetryException as e:
        print(f"Failed after {e.attempts} attempts")
        print(f"Last error: {e.original_exception}")
        print(f"Request: {e.context.get('request')}")

**Attributes:**

* ``attempts`` (int): Total number of attempts made
* ``original_exception`` (Exception | None): Last exception that caused failure
* ``message`` (str): Error message
* ``context`` (dict): Request context

**Example with custom handling:**

.. code-block:: python

    from requestforge import MaxRetryException, TimeoutException

    try:
        response = client.get('/api/data')
    except MaxRetryException as e:
        if isinstance(e.original_exception, TimeoutException):
            print("Service is responding too slowly")
            # Maybe increase timeout or reduce load
        else:
            print(f"Service failed: {e.original_exception}")
            # Log to monitoring system

Authentication Errors
---------------------

AuthenticationException
~~~~~~~~~~~~~~~~~~~~~~~

Raised on authentication failures:

.. code-block:: python

    from requestforge import AuthenticationException

    try:
        response = client.get('/protected')
    except AuthenticationException as e:
        print(f"Auth failed for service: {e.service_name}")
        print(f"Reason: {e.message}")
        # Clear cached credentials or redirect to login

**Attributes:**

* ``service_name`` (str | None): Name of the service that failed
* ``message`` (str): Error message
* ``original_exception`` (Exception | None): Original exception
* ``context`` (dict): Additional context

TokenRefreshException
~~~~~~~~~~~~~~~~~~~~~

Raised when token refresh fails:

.. code-block:: python

    from requestforge.token_manager import TokenRefreshException

    try:
        token = token_manager.get_token()
    except TokenRefreshException as e:
        print(f"Failed to refresh token: {e}")
        # Clear session and redirect to login

Parsing Errors
--------------

ResponseParseException
~~~~~~~~~~~~~~~~~~~~~~

Raised when response parsing fails:

.. code-block:: python

    from requestforge import ResponseParseException

    try:
        response = client.get('/data')
        data = response.json()  # Expects JSON
    except ResponseParseException as e:
        print(f"Invalid JSON response: {e.message}")
        print(f"Content preview: {e.context.get('content_preview')}")
        # Use response.text instead or handle as plain text

**Common causes:**

* Server returns HTML instead of JSON
* Malformed JSON
* Empty response when JSON expected

**Safe parsing:**

.. code-block:: python

    response = client.get('/data')

    # Option 1: Use json_or_none()
    data = response.json_or_none()
    if data is None:
        print("Response is not JSON")

    # Option 2: Try-except
    try:
        data = response.json()
    except ResponseParseException:
        # Fallback to text
        data = response.text

Error Handling Patterns
-----------------------

Specific to General
~~~~~~~~~~~~~~~~~~~

Handle specific exceptions first, then general:

.. code-block:: python

    from requestforge import (
        NotFoundException,
        UnauthorizedException,
        HttpStatusException,
        TimeoutException,
        HttpClientException
    )

    try:
        response = client.get('/users/1')
        user = response.json()

    # Most specific first
    except NotFoundException:
        print("User not found")
        return None

    except UnauthorizedException:
        print("Please login")
        redirect_to_login()

    # More general HTTP errors
    except HttpStatusException as e:
        print(f"HTTP error {e.status_code}")

    # Network errors
    except TimeoutException:
        print("Request timed out")

    # Catch-all for HTTP client errors
    except HttpClientException as e:
        print(f"Request failed: {e}")
        logger.error(f"Error details: {e.context}")

Retry Pattern
~~~~~~~~~~~~~

Implement custom retry with specific error handling:

.. code-block:: python

    from requestforge import TimeoutException, ServerErrorException
    import time

    def fetch_with_retry(url, max_retries=3):
        last_error = None

        for attempt in range(max_retries):
            try:
                response = client.get(url)
                return response.json()

            except TimeoutException as e:
                print(f"Timeout on attempt {attempt + 1}")
                last_error = e
                time.sleep(2 ** attempt)  # Exponential backoff

            except ServerErrorException as e:
                if e.status_code == 503:  # Service Unavailable
                    print(f"Service unavailable, attempt {attempt + 1}")
                    last_error = e
                    time.sleep(5)
                else:
                    raise  # Don't retry other server errors

            except HttpClientException as e:
                # Don't retry other errors
                raise

        # Max retries exceeded
        raise MaxRetryException(
            message=f"Failed after {max_retries} attempts",
            attempts=max_retries,
            original_exception=last_error
        )

Fallback Pattern
~~~~~~~~~~~~~~~~

Provide fallback data on errors:

.. code-block:: python

    from requestforge import HttpClientException

    def get_user_data(user_id):
        try:
            response = client.get(f'/users/{user_id}')
            return response.json()

        except NotFoundException:
            return None

        except HttpClientException as e:
            logger.error(f"Failed to fetch user {user_id}: {e}")
            # Return cached data if available
            return get_cached_user_data(user_id)

Circuit Breaker Pattern
~~~~~~~~~~~~~~~~~~~~~~~~

Stop making requests after consecutive failures:

.. code-block:: python

    from requestforge import HttpClientException
    import time

    class CircuitBreaker:
        def __init__(self, failure_threshold=5, timeout=60):
            self.failure_count = 0
            self.failure_threshold = failure_threshold
            self.timeout = timeout
            self.last_failure_time = None
            self.state = 'closed'  # closed, open, half_open

        def call(self, func):
            if self.state == 'open':
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = 'half_open'
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func()
                self.on_success()
                return result
            except HttpClientException as e:
                self.on_failure()
                raise

        def on_success(self):
            self.failure_count = 0
            self.state = 'closed'

        def on_failure(self):
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'open'

    # Usage
    breaker = CircuitBreaker()

    try:
        response = breaker.call(lambda: client.get('/api/data'))
    except Exception as e:
        print(f"Request failed or circuit open: {e}")

Context Managers
~~~~~~~~~~~~~~~~

Ensure cleanup even on errors:

.. code-block:: python

    from requestforge import http_client, HttpClientException

    try:
        with http_client('https://api.example.com') as client:
            response = client.get('/users')
            users = response.json()
            # Process users
    except HttpClientException as e:
        print(f"API error: {e}")
    # Client automatically closed

Logging Errors
--------------

Basic Logging
~~~~~~~~~~~~~

.. code-block:: python

    import logging
    from requestforge import HttpClientException

    logger = logging.getLogger(__name__)

    try:
        response = client.get('/api/data')
    except HttpClientException as e:
        logger.error(
            f"API request failed: {e.message}",
            exc_info=True,  # Include stack trace
            extra={
                'url': e.context.get('request', {}).get('url'),
                'exception_type': type(e).__name__
            }
        )

Structured Logging
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import structlog
    from requestforge import HttpClientException, HttpStatusException

    logger = structlog.get_logger()

    try:
        response = client.get('/users/1')
    except HttpStatusException as e:
        logger.error(
            "http_request_failed",
            status_code=e.status_code,
            url=e.context.get('request', {}).get('url'),
            response_body=e.response_body[:200],
            exception_type=type(e).__name__
        )
    except HttpClientException as e:
        logger.error(
            "http_request_error",
            error=str(e),
            exception_type=type(e).__name__,
            context=e.context
        )

Error Hooks
~~~~~~~~~~~

Use error hooks for centralized logging:

.. code-block:: python

    from requestforge.interfaces import ErrorHookInterface
    import logging

    class ErrorLoggingHook(ErrorHookInterface):
        def __init__(self):
            self.logger = logging.getLogger('requestforge')

        def on_error(self, exception, context):
            self.logger.error(
                f"Request failed: {type(exception).__name__}",
                extra={
                    'exception': str(exception),
                    'url': context.request.url,
                    'method': context.request.method.value,
                    'attempt': context.attempt,
                    'max_retries': context.max_retries
                }
            )

    config = builder.with_error_hook(ErrorLoggingHook()).build()

Error Monitoring
----------------

Sentry Integration
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import sentry_sdk
    from requestforge import HttpClientException
    from requestforge.interfaces import ErrorHookInterface

    class SentryErrorHook(ErrorHookInterface):
        def on_error(self, exception, context):
            with sentry_sdk.push_scope() as scope:
                # Add tags
                scope.set_tag("http_method", context.request.method.value)
                scope.set_tag("http_url", context.request.url)

                # Add context
                scope.set_context("request", {
                    "url": context.request.url,
                    "method": context.request.method.value,
                    "attempt": context.attempt,
                    "max_retries": context.max_retries
                })

                # Capture exception
                sentry_sdk.capture_exception(exception)

    config = builder.with_error_hook(SentryErrorHook()).build()

Datadog Integration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from datadog import statsd
    from requestforge.interfaces import ErrorHookInterface

    class DatadogErrorHook(ErrorHookInterface):
        def on_error(self, exception, context):
            # Increment error counter
            statsd.increment(
                'requestforge.error',
                tags=[
                    f'exception_type:{type(exception).__name__}',
                    f'url:{context.request.url}',
                    f'method:{context.request.method.value}'
                ]
            )

Best Practices
--------------

1. **Handle Specific Exceptions**

   .. code-block:: python

       # Good ✅ - Specific handling
       try:
           response = client.get('/users/1')
       except NotFoundException:
           return None
       except UnauthorizedException:
           redirect_to_login()

       # Avoid ❌ - Too broad
       try:
           response = client.get('/users/1')
       except Exception:
           print("Something went wrong")

2. **Don't Silence Errors**

   .. code-block:: python

       # Good ✅ - Log and re-raise or handle
       try:
           response = client.get('/data')
       except HttpClientException as e:
           logger.error(f"Request failed: {e}")
           raise

       # Avoid ❌ - Silent failure
       try:
           response = client.get('/data')
       except:
           pass

3. **Provide Context**

   .. code-block:: python

       # Good ✅ - Rich error information
       try:
           response = client.get(f'/users/{user_id}')
       except HttpClientException as e:
           raise ValueError(
               f"Failed to fetch user {user_id}: {e.message}"
           ) from e

4. **Use Appropriate Retry**

   .. code-block:: python

       # Good ✅ - Retry on transient errors
       config = builder.with_retry(max_retries=3).build()

       # Transient errors automatically retried:
       # - TimeoutException
       # - ConnectionException
       # - 5xx ServerErrorException

5. **Clean Up Resources**

   .. code-block:: python

       # Good ✅ - Context manager ensures cleanup
       with http_client('https://api.example.com') as client:
           response = client.get('/data')

       # Or explicit cleanup
       client = create_client('https://api.example.com')
       try:
           response = client.get('/data')
       finally:
           client.close()

Testing Error Handling
-----------------------

Mock Exceptions
~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    from unittest.mock import patch, Mock
    from requestforge import TimeoutException, NotFoundException

    def test_timeout_handling():
        with patch('requestforge.HttpClient.get') as mock_get:
            mock_get.side_effect = TimeoutException("Timeout")

            # Your code that handles timeout
            result = fetch_user_with_timeout_handling(1)

            assert result is None

    def test_not_found_handling():
        with patch('requestforge.HttpClient.get') as mock_get:
            mock_get.side_effect = NotFoundException("Not found")

            result = get_user(999)

            assert result is None

Mock HTTP Responses
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import responses
    from requestforge import HttpClient, NotFoundException

    @responses.activate
    def test_404_handling():
        responses.add(
            responses.GET,
            'https://api.example.com/users/999',
            status=404,
            json={'error': 'User not found'}
        )

        client = create_client('https://api.example.com')

        with pytest.raises(NotFoundException):
            client.get('/users/999')

Common Scenarios
----------------

API Rate Limiting
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpStatusException
    import time

    def api_call_with_rate_limit(url):
        while True:
            try:
                response = client.get(url)
                return response.json()

            except HttpStatusException as e:
                if e.status_code == 429:  # Too Many Requests
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    print(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                else:
                    raise

Partial Failures
~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientException

    def fetch_multiple_users(user_ids):
        results = []
        errors = []

        for user_id in user_ids:
            try:
                response = client.get(f'/users/{user_id}')
                results.append(response.json())
            except HttpClientException as e:
                errors.append({
                    'user_id': user_id,
                    'error': str(e)
                })

        return results, errors

Graceful Degradation
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientException

    def get_recommendations(user_id):
        try:
            # Try personalized recommendations
            response = client.get(f'/recommendations/{user_id}')
            return response.json()

        except HttpClientException:
            # Fall back to popular items
            try:
                response = client.get('/recommendations/popular')
                return response.json()
            except HttpClientException:
                # Final fallback to cached data
                return get_default_recommendations()

Next Steps
----------

* Learn about :doc:`concurrent-requests` for parallel error handling
* Explore :doc:`hooks` for centralized error handling
* Check :doc:`../examples/custom-retry` for advanced error recovery
