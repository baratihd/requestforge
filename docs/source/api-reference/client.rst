Client API Reference
====================

This page documents the main ``HttpClient`` class and related factory functions.

HttpClient
----------

.. class:: HttpClient(config=None, session=None)

   Production-ready HTTP client implementation following SOLID principles.

   :param config: Client configuration object
   :type config: HttpClientConfig | None
   :param session: Optional requests Session to use
   :type session: requests.Session | None

   **Thread Safety:** This class is thread-safe. Multiple threads can safely share a single client instance.

   **Example:**

   .. code-block:: python

       from requestforge import HttpClient, HttpClientConfigBuilder

       config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
       client = HttpClient(config)

       response = client.get('/users')

Properties
~~~~~~~~~~

.. attribute:: HttpClient.adapter

   HTTP adapter for connection pooling.

   :type: HTTPAdapter
   :returns: Configured HTTPAdapter instance

   .. code-block:: python

       adapter = client.adapter
       print(f"Pool connections: {adapter._pool_connections}")

.. attribute:: HttpClient.session

   Thread-safe requests session.

   :type: requests.Session
   :returns: Session instance for current thread

   **Note:** Sessions are created lazily per thread and managed automatically.

   .. code-block:: python

       session = client.session
       print(session.headers)

.. attribute:: HttpClient.auth_hook

   Get the configured authentication hook.

   :type: AuthHookInterface | None
   :returns: Authentication hook if configured, None otherwise

   .. code-block:: python

       if client.auth_hook:
           token = client.auth_hook.get_token()

HTTP Methods
~~~~~~~~~~~~

.. method:: HttpClient.get(url, params=None, headers=None, timeout=None, **kwargs)

   Execute a GET request.

   :param str url: URL path (relative or absolute)
   :param dict params: URL query parameters
   :param dict headers: Request headers
   :param float timeout: Request timeout in seconds
   :param kwargs: Additional request parameters
   :returns: HTTP response object
   :rtype: HttpResponse
   :raises HttpClientException: On request failure

   **Example:**

   .. code-block:: python

       # Simple GET
       response = client.get('/users')

       # With parameters
       response = client.get('/users', params={'page': 1, 'limit': 10})

       # With custom headers
       response = client.get('/users', headers={'X-Custom': 'value'})

       # With timeout
       response = client.get('/slow-endpoint', timeout=60.0)

.. method:: HttpClient.post(url, json_data=None, data=None, params=None, headers=None, timeout=None, **kwargs)

   Execute a POST request.

   :param str url: URL path
   :param dict json_data: JSON data to send in request body
   :param dict data: Form data to send in request body
   :param dict params: URL query parameters
   :param dict headers: Request headers
   :param float timeout: Request timeout in seconds
   :param kwargs: Additional request parameters
   :returns: HTTP response object
   :rtype: HttpResponse
   :raises HttpClientException: On request failure

   **Example:**

   .. code-block:: python

       # JSON POST
       response = client.post('/users', json_data={
           'name': 'John Doe',
           'email': 'john@example.com'
       })

       # Form POST
       response = client.post('/login', data={
           'username': 'john',
           'password': 'secret'
       })

       # With query parameters
       response = client.post('/users', json_data={...}, params={'notify': 'true'})

.. method:: HttpClient.put(url, json_data=None, data=None, params=None, headers=None, timeout=None, **kwargs)

   Execute a PUT request.

   :param str url: URL path
   :param dict json_data: JSON data to send
   :param dict data: Form data to send
   :param dict params: URL query parameters
   :param dict headers: Request headers
   :param float timeout: Request timeout in seconds
   :returns: HTTP response object
   :rtype: HttpResponse

   **Example:**

   .. code-block:: python

       response = client.put('/users/123', json_data={
           'name': 'Jane Doe',
           'email': 'jane@example.com'
       })

.. method:: HttpClient.patch(url, json_data=None, data=None, params=None, headers=None, timeout=None, **kwargs)

   Execute a PATCH request.

   :param str url: URL path
   :param dict json_data: JSON data to send
   :param dict data: Form data to send
   :param dict params: URL query parameters
   :param dict headers: Request headers
   :param float timeout: Request timeout in seconds
   :returns: HTTP response object
   :rtype: HttpResponse

   **Example:**

   .. code-block:: python

       # Partial update
       response = client.patch('/users/123', json_data={
           'email': 'newemail@example.com'
       })

.. method:: HttpClient.delete(url, json_data=None, data=None, params=None, headers=None, timeout=None, **kwargs)

   Execute a DELETE request.

   :param str url: URL path
   :param dict json_data: Optional JSON data
   :param dict data: Optional form data
   :param dict params: URL query parameters
   :param dict headers: Request headers
   :param float timeout: Request timeout in seconds
   :returns: HTTP response object
   :rtype: HttpResponse

   **Example:**

   .. code-block:: python

       # Simple delete
       response = client.delete('/users/123')

       # Delete with reason
       response = client.delete('/users/123', json_data={
           'reason': 'User requested account deletion'
       })

Core Request Method
~~~~~~~~~~~~~~~~~~~

.. method:: HttpClient.request(request)

   Execute an HTTP request with comprehensive retry logic and lifecycle hooks.

   :param HttpRequest request: HTTP request object
   :returns: HTTP response object
   :rtype: HttpResponse
   :raises MaxRetryException: If max retries exceeded
   :raises TimeoutException: On request timeout
   :raises ConnectionException: On connection failure
   :raises HttpStatusException: On HTTP error status
   :raises AuthenticationException: On authentication failure

   This is the core method that all other HTTP methods delegate to. It handles:

   * Request hook execution
   * Authentication injection
   * Request execution
   * Response hook execution
   * Error handling and retry logic
   * Authentication retry on 401

   **Example:**

   .. code-block:: python

       from requestforge import HttpRequest, HttpMethod

       request = HttpRequest(
           method=HttpMethod.POST,
           url='/users',
           json_data={'name': 'John'},
           headers={'X-Custom': 'value'},
           timeout=30.0
       )

       response = client.request(request)

   **Request Flow:**

   .. code-block:: text

       1. Execute request hooks (before_request)
       2. Execute auth hook (inject token)
       3. Execute HTTP request
       4. Check for auth error (401)
          ├─ Yes → Refresh token & retry
          └─ No → Continue
       5. Check for retryable error
          ├─ Yes → Retry with backoff
          └─ No → Continue
       6. Execute response hooks (after_response)
       7. Return response

Concurrent Requests
~~~~~~~~~~~~~~~~~~~

.. method:: HttpClient.request_many(requests_list, max_workers=5, fail_fast=False)

   Execute multiple HTTP requests concurrently.

   :param list requests_list: List of HttpRequest objects
   :param int max_workers: Maximum number of concurrent worker threads
   :param bool fail_fast: If True, stop on first error
   :returns: Generator yielding (index, result) tuples
   :rtype: Generator[tuple[int, HttpResponse | HttpClientException], None, None]
   :raises HttpClientException: If fail_fast=True and request fails

   Results are yielded as they complete (not in order). Each result is a tuple of:

   * **index** (int): Index of request in original list
   * **result** (HttpResponse | HttpClientException): Response or exception

   **Example:**

   .. code-block:: python

       from requestforge import HttpRequest, HttpMethod

       requests = [
           HttpRequest(method=HttpMethod.GET, url=f'/users/{i}')
           for i in range(1, 11)
       ]

       # Execute with 5 workers
       for index, result in client.request_many(requests, max_workers=5):
           if isinstance(result, HttpResponse):
               print(f"Request {index}: Success")
           else:
               print(f"Request {index}: Failed - {result}")

   **Fail-Fast Example:**

   .. code-block:: python

       try:
           results = client.request_many(requests, max_workers=10, fail_fast=True)
           for index, response in results:
               process(response)
       except HttpClientException as e:
           print(f"Batch failed: {e}")

Resource Management
~~~~~~~~~~~~~~~~~~~

.. method:: HttpClient.close()

   Close the client and release all resources.

   This method:

   * Closes thread-local sessions
   * Closes shared session (if provided)
   * Releases connection pool resources
   * Marks client as closed

   .. code-block:: python

       client = HttpClient(config)
       try:
           response = client.get('/users')
       finally:
           client.close()

.. method:: HttpClient.__enter__()

   Enter context manager.

   :returns: Self
   :rtype: HttpClient

.. method:: HttpClient.__exit__(exc_type, exc_val, exc_tb)

   Exit context manager and cleanup resources.

   **Example:**

   .. code-block:: python

       with HttpClient(config) as client:
           response = client.get('/users')
       # Client automatically closed

Factory Functions
-----------------

create_client
~~~~~~~~~~~~~

.. function:: create_client(base_url='', timeout=30.0, max_retries=3, headers=None, enable_logging=True, auth_hook=None)

   Factory function to create a configured HTTP client.

   :param str base_url: Base URL for all requests
   :param float timeout: Default timeout in seconds
   :param int max_retries: Maximum retry attempts
   :param dict headers: Default headers
   :param bool enable_logging: Enable logging hooks
   :param AuthHookInterface auth_hook: Authentication hook
   :returns: Configured HTTP client
   :rtype: HttpClient

   **Example:**

   .. code-block:: python

       from requestforge import create_client

       # Simple client
       client = create_client('https://api.example.com')

       # With custom configuration
       client = create_client(
           base_url='https://api.example.com',
           timeout=60.0,
           max_retries=5,
           headers={'User-Agent': 'MyApp/1.0'},
           enable_logging=True
       )

       # With authentication
       from requestforge import TokenManager

       client = create_client(
           base_url='https://api.example.com',
           auth_hook=TokenAuthHook(token_manager)
       )

requestforge (Context Manager)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. function:: http_client(base_url='', **kwargs)

   Context manager factory for HTTP client.

   :param str base_url: Base URL for requests
   :param kwargs: Additional configuration (same as create_client)
   :returns: Context manager yielding HttpClient
   :rtype: ContextManager[HttpClient]

   **Example:**

   .. code-block:: python

       from requestforge import http_client

       with http_client('https://api.example.com') as client:
           response = client.get('/users')
           users = response.json()
       # Client automatically closed

   **With Configuration:**

   .. code-block:: python

       with http_client(
           base_url='https://api.example.com',
           timeout=60.0,
           max_retries=5
       ) as client:
           response = client.get('/data')

Complete Example
----------------

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        HttpRequest,
        HttpMethod,
        create_client,
        requestforge
    )

    # Method 1: Using builder pattern
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .with_retry(max_retries=3)
        .with_bearer_token('your-token')
        .with_logging()
        .build()
    )

    client = HttpClient(config)

    # Simple requests
    response = client.get('/users')
    response = client.post('/users', json_data={'name': 'John'})
    response = client.put('/users/1', json_data={'name': 'Jane'})
    response = client.patch('/users/1', json_data={'email': 'new@email.com'})
    response = client.delete('/users/1')

    # Advanced request
    request = HttpRequest(
        method=HttpMethod.POST,
        url='/users',
        headers={'X-Custom': 'value'},
        json_data={'name': 'John'},
        timeout=60.0
    )
    response = client.request(request)

    # Concurrent requests
    requests = [
        HttpRequest(method=HttpMethod.GET, url=f'/users/{i}')
        for i in range(1, 11)
    ]
    for index, result in client.request_many(requests, max_workers=5):
        print(f"Request {index}: {result.status_code}")

    client.close()

    # Method 2: Using factory function
    client = create_client(
        base_url='https://api.example.com',
        timeout=30.0,
        max_retries=3
    )

    response = client.get('/users')
    client.close()

    # Method 3: Using context manager
    with http_client('https://api.example.com') as client:
        response = client.get('/users')

See Also
--------

* :doc:`config` - Configuration API reference
* :doc:`models` - Request and response models
* :doc:`exceptions` - Exception types
* :doc:`../user-guide/basic-usage` - Basic usage guide
