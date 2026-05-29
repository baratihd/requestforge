Exceptions API Reference
=========================

This page documents the exception hierarchy for HTTP Client errors.

Exception Hierarchy
-------------------

.. code-block:: text

    HttpClientException (base)
    ├── MaxRetryException
    ├── TimeoutException
    ├── ConnectionException
    ├── SSLException
    ├── ResponseParseException
    ├── RequestBuildException
    ├── AuthenticationException
    │   └── TokenRefreshException
    └── HttpStatusException
        ├── BadRequestException (400)
        ├── UnauthorizedException (401)
        ├── ForbiddenException (403)
        ├── NotFoundException (404)
        └── ServerErrorException (5xx)

Base Exception
--------------

HttpClientException
~~~~~~~~~~~~~~~~~~~

.. class:: HttpClientException(message, original_exception=None, context=None)

   Base exception for all HTTP client errors.

   :param str message: Human-readable error message
   :param Exception original_exception: Original underlying exception
   :param dict context: Additional error context

   **Attributes:**

   .. attribute:: message
      :type: str

      Human-readable error message.

   .. attribute:: original_exception
      :type: Exception | None

      Original exception that caused this error.

   .. attribute:: context
      :type: dict[str, Any]

      Additional context about the error.

   **Methods:**

   .. method:: __str__()

      Return string representation with original exception if present.

   **Example:**

   .. code-block:: python

       from requestforge import HttpClientException

       try:
           # Some HTTP operation
           pass
       except HttpClientException as e:
           print(f"Error: {e.message}")
           print(f"Original: {e.original_exception}")
           print(f"Context: {e.context}")

Network Exceptions
------------------

TimeoutException
~~~~~~~~~~~~~~~~

.. class:: TimeoutException(message, original_exception=None, context=None)

   Raised when a request times out.

   Inherits from :class:`HttpClientException`.

   **Causes:**

   * Request exceeds configured timeout
   * Connection timeout
   * Read timeout

   **Example:**

   .. code-block:: python

       from requestforge import TimeoutException

       try:
           response = client.get('/slow-endpoint', timeout=5.0)
       except TimeoutException as e:
           print(f"Request timed out: {e.message}")
           # Retry with longer timeout or handle gracefully

ConnectionException
~~~~~~~~~~~~~~~~~~~

.. class:: ConnectionException(message, original_exception=None, context=None)

   Raised when a connection error occurs.

   **Causes:**

   * Server is down or unreachable
   * DNS resolution failure
   * Network connectivity issues
   * Firewall blocking connection
   * Connection refused

   **Example:**

   .. code-block:: python

       from requestforge import ConnectionException

       try:
           response = client.get('/api/data')
       except ConnectionException as e:
           print(f"Connection failed: {e.message}")
           # Check network, verify server is running

SSLException
~~~~~~~~~~~~

.. class:: SSLException(message, original_exception=None, context=None)

   Raised when SSL/TLS errors occur.

   **Causes:**

   * Invalid SSL certificate
   * Self-signed certificate
   * Certificate expired
   * Hostname mismatch
   * SSL protocol errors

   **Example:**

   .. code-block:: python

       from requestforge import SSLException

       try:
           response = client.get('https://self-signed.example.com')
       except SSLException as e:
           print(f"SSL error: {e.message}")
           # Verify certificate or disable SSL verification (not recommended)

Retry Exceptions
----------------

MaxRetryException
~~~~~~~~~~~~~~~~~

.. class:: MaxRetryException(message, attempts, original_exception=None, context=None)

   Raised when maximum retry attempts are exceeded.

   :param str message: Error message
   :param int attempts: Total number of attempts made
   :param Exception original_exception: Last exception that caused failure
   :param dict context: Request context

   **Attributes:**

   .. attribute:: attempts
      :type: int

      Total number of attempts made (initial + retries).

   **Example:**

   .. code-block:: python

       from requestforge import MaxRetryException

       try:
           response = client.get('/unstable-endpoint')
       except MaxRetryException as e:
           print(f"Failed after {e.attempts} attempts")
           print(f"Last error: {e.original_exception}")
           print(f"Request: {e.context.get('request')}")

Parsing Exceptions
------------------

ResponseParseException
~~~~~~~~~~~~~~~~~~~~~~

.. class:: ResponseParseException(message, original_exception=None, context=None)

   Raised when response parsing (e.g., JSON) fails.

   **Causes:**

   * Server returns invalid JSON
   * Response is not JSON when JSON expected
   * Malformed JSON data
   * Empty response

   **Example:**

   .. code-block:: python

       from requestforge import ResponseParseException

       try:
           response = client.get('/api/data')
           data = response.json()  # May raise ResponseParseException
       except ResponseParseException as e:
           print(f"Parse error: {e.message}")
           print(f"Content: {e.context.get('content_preview')}")
           # Use response.text instead or handle as plain text

Request Exceptions
------------------

RequestBuildException
~~~~~~~~~~~~~~~~~~~~~

.. class:: RequestBuildException(message, original_exception=None, context=None)

   Raised when request building fails.

   **Causes:**

   * Invalid request parameters
   * Request construction errors
   * Serialization failures

   **Example:**

   .. code-block:: python

       from requestforge import RequestBuildException

       try:
           # Invalid request construction
           request = HttpRequest(...)
       except RequestBuildException as e:
           print(f"Request build failed: {e.message}")

HTTP Status Exceptions
----------------------

HttpStatusException
~~~~~~~~~~~~~~~~~~~

.. class:: HttpStatusException(message, status_code, response_body=None, original_exception=None, context=None)

   Base class for HTTP error status codes (4xx, 5xx).

   :param str message: Error message
   :param int status_code: HTTP status code
   :param str response_body: Response body content
   :param Exception original_exception: Original exception
   :param dict context: Additional context

   **Attributes:**

   .. attribute:: status_code
      :type: int

      HTTP status code (e.g., 404, 500).

   .. attribute:: response_body
      :type: str | None

      Response body content (may be truncated).

   **Example:**

   .. code-block:: python

       from requestforge import HttpStatusException

       try:
           response = client.get('/api/data')
       except HttpStatusException as e:
           print(f"HTTP {e.status_code}: {e.message}")
           print(f"Response: {e.response_body}")

BadRequestException (400)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: BadRequestException(message='Bad Request', response_body=None, original_exception=None, context=None)

   Raised for 400 Bad Request responses.

   **Causes:**

   * Invalid request parameters
   * Malformed request data
   * Validation errors

   **Example:**

   .. code-block:: python

       from requestforge import BadRequestException

       try:
           response = client.post('/users', json_data={
               'email': 'invalid-email'  # Invalid format
           })
       except BadRequestException as e:
           print(f"Bad request: {e.response_body}")
           # Parse validation errors from response

UnauthorizedException (401)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: UnauthorizedException(message='Unauthorized', response_body=None, original_exception=None, context=None)

   Raised for 401 Unauthorized responses.

   **Causes:**

   * Missing authentication
   * Invalid credentials
   * Expired token
   * Token refresh needed

   **Note:** When using ``TokenAuthHook``, 401 errors trigger automatic token refresh and retry.

   **Example:**

   .. code-block:: python

       from requestforge import UnauthorizedException

       try:
           response = client.get('/protected-resource')
       except UnauthorizedException:
           print("Authentication required")
           # Redirect to login or refresh token

ForbiddenException (403)
~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: ForbiddenException(message='Forbidden', response_body=None, original_exception=None, context=None)

   Raised for 403 Forbidden responses.

   **Causes:**

   * Insufficient permissions
   * Access denied
   * Resource forbidden

   **Example:**

   .. code-block:: python

       from requestforge import ForbiddenException

       try:
           response = client.delete('/admin/users/1')
       except ForbiddenException:
           print("Insufficient permissions")
           # Show error to user

NotFoundException (404)
~~~~~~~~~~~~~~~~~~~~~~~

.. class:: NotFoundException(message='Not Found', response_body=None, original_exception=None, context=None)

   Raised for 404 Not Found responses.

   **Causes:**

   * Resource does not exist
   * Invalid URL/endpoint
   * Deleted resource

   **Example:**

   .. code-block:: python

       from requestforge import NotFoundException

       try:
           response = client.get('/users/999999')
       except NotFoundException:
           print("User not found")
           return None

ServerErrorException (5xx)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: ServerErrorException(message='Server Error', status_code=500, response_body=None, original_exception=None, context=None)

   Raised for 5xx server error responses.

   :param str message: Error message
   :param int status_code: HTTP status code (500-599)
   :param str response_body: Response body
   :param Exception original_exception: Original exception
   :param dict context: Additional context

   **Causes:**

   * Internal server error (500)
   * Bad gateway (502)
   * Service unavailable (503)
   * Gateway timeout (504)

   **Example:**

   .. code-block:: python

       from requestforge import ServerErrorException

       try:
           response = client.get('/api/data')
       except ServerErrorException as e:
           if e.status_code == 503:
               print("Service temporarily unavailable")
           elif e.status_code == 500:
               print("Internal server error")

Authentication Exceptions
-------------------------

AuthenticationException
~~~~~~~~~~~~~~~~~~~~~~~

.. class:: AuthenticationException(message, original_exception=None, context=None, service_name=None)

   Raised when authentication fails.

   :param str message: Error message
   :param Exception original_exception: Original exception
   :param dict context: Additional context
   :param str service_name: Name of the service that failed

   **Attributes:**

   .. attribute:: service_name
      :type: str | None

      Name of the service/provider that failed authentication.

   **Example:**

   .. code-block:: python

       from requestforge import AuthenticationException

       try:
           response = client.get('/protected')
       except AuthenticationException as e:
           print(f"Auth failed for: {e.service_name}")
           print(f"Reason: {e.message}")

TokenRefreshException
~~~~~~~~~~~~~~~~~~~~~

.. class:: TokenRefreshException

   Raised when token refresh fails.

   Inherits from :class:`AuthenticationException`.

   **Example:**

   .. code-block:: python

       from requestforge.token_manager import TokenRefreshException

       try:
           token = token_manager.get_token()
       except TokenRefreshException as e:
           print(f"Token refresh failed: {e}")
           # Clear session and redirect to login

Error Handling Patterns
-----------------------

Specific to General
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        NotFoundException,
        UnauthorizedException,
        ForbiddenException,
        HttpStatusException,
        TimeoutException,
        ConnectionException,
        HttpClientException
    )

    try:
        response = client.get('/api/resource')
        data = response.json()

    # Most specific first
    except NotFoundException:
        handle_not_found()

    except UnauthorizedException:
        handle_unauthorized()

    except ForbiddenException:
        handle_forbidden()

    # General HTTP errors
    except HttpStatusException as e:
        handle_http_error(e.status_code, e.response_body)

    # Network errors
    except TimeoutException:
        handle_timeout()

    except ConnectionException:
        handle_connection_error()

    # Catch-all
    except HttpClientException as e:
        handle_general_error(e)

By Error Category
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpStatusException,
        TimeoutException,
        ConnectionException,
        SSLException,
        HttpClientException
    )

    try:
        response = client.get('/api/data')

    # HTTP errors (4xx, 5xx)
    except HttpStatusException as e:
        if e.is_client_error:  # 4xx
            log_client_error(e)
        elif e.is_server_error:  # 5xx
            log_server_error(e)

    # Network errors
    except (TimeoutException, ConnectionException, SSLException) as e:
        log_network_error(e)

    # Other errors
    except HttpClientException as e:
        log_unexpected_error(e)

With Retry
~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        MaxRetryException,
        TimeoutException,
        ServerErrorException
    )

    try:
        response = client.get('/api/data')

    except MaxRetryException as e:
        # Check what caused max retries
        if isinstance(e.original_exception, TimeoutException):
            print("Service is too slow")
        elif isinstance(e.original_exception, ServerErrorException):
            print("Service is down")

        print(f"Failed after {e.attempts} attempts")

Context Access
~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientException

    try:
        response = client.post('/api/data', json_data=payload)

    except HttpClientException as e:
        # Access error context
        request = e.context.get('request')
        if request:
            print(f"Failed request: {request.method} {request.url}")
            print(f"Payload: {request.json_data}")

        # Access original exception
        if e.original_exception:
            print(f"Caused by: {type(e.original_exception).__name__}")
            print(f"Details: {e.original_exception}")

Logging Errors
--------------

.. code-block:: python

    import logging
    from requestforge import HttpClientException, HttpStatusException

    logger = logging.getLogger(__name__)

    try:
        response = client.get('/api/data')

    except HttpStatusException as e:
        logger.error(
            f"HTTP {e.status_code} error",
            extra={
                'status_code': e.status_code,
                'url': e.context.get('request', {}).get('url'),
                'response_body': e.response_body[:200]
            },
            exc_info=True
        )

    except HttpClientException as e:
        logger.error(
            f"HTTP client error: {e.message}",
            extra={
                'error_type': type(e).__name__,
                'context': e.context
            },
            exc_info=True
        )

Custom Exception Mapping
------------------------

.. code-block:: python

    from requestforge import HttpStatusException, NotFoundException

    class ResourceNotFoundError(Exception):
        """Custom application exception."""
        pass

    try:
        response = client.get(f'/resources/{resource_id}')
        resource = response.json()

    except NotFoundException:
        raise ResourceNotFoundError(
            f"Resource {resource_id} not found"
        )

    except HttpStatusException as e:
        if e.status_code == 410:  # Gone
            raise ResourceNotFoundError(
                f"Resource {resource_id} was deleted"
            )
        raise

Testing with Exceptions
------------------------

.. code-block:: python

    import pytest
    from requestforge import TimeoutException, NotFoundException

    def test_timeout_handling():
        with pytest.raises(TimeoutException) as exc_info:
            # Code that should timeout
            client.get('/slow-endpoint', timeout=0.001)

        assert "timed out" in str(exc_info.value).lower()

    def test_not_found_handling():
        with pytest.raises(NotFoundException):
            client.get('/nonexistent')

    def test_error_context():
        try:
            client.get('/error')
        except HttpClientException as e:
            assert e.context is not None
            assert 'request' in e.context

Exception Attributes Summary
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Exception
     - Status Code
     - Additional Attributes
   * - HttpClientException
     - N/A
     - message, original_exception, context
   * - MaxRetryException
     - N/A
     - attempts, original_exception
   * - TimeoutException
     - N/A
     - (inherits from base)
   * - ConnectionException
     - N/A
     - (inherits from base)
   * - SSLException
     - N/A
     - (inherits from base)
   * - ResponseParseException
     - N/A
     - (inherits from base)
   * - AuthenticationException
     - N/A
     - service_name
   * - HttpStatusException
     - Any
     - status_code, response_body
   * - BadRequestException
     - 400
     - (inherits from HttpStatusException)
   * - UnauthorizedException
     - 401
     - (inherits from HttpStatusException)
   * - ForbiddenException
     - 403
     - (inherits from HttpStatusException)
   * - NotFoundException
     - 404
     - (inherits from HttpStatusException)
   * - ServerErrorException
     - 5xx
     - (inherits from HttpStatusException)

See Also
--------

* :doc:`../user-guide/error-handling` - Error handling guide
* :doc:`client` - HTTP client API
* :doc:`retry` - Retry strategies
