Models API Reference
====================

This page documents the data transfer objects (DTOs) used for HTTP operations.

All models are immutable (frozen dataclasses) following the Value Object pattern.

HttpMethod
----------

.. class:: HttpMethod

   Enumeration of HTTP methods.

   **Values:**

   .. attribute:: GET
      :type: str
      :value: 'GET'

   .. attribute:: POST
      :type: str
      :value: 'POST'

   .. attribute:: PUT
      :type: str
      :value: 'PUT'

   .. attribute:: PATCH
      :type: str
      :value: 'PATCH'

   .. attribute:: DELETE
      :type: str
      :value: 'DELETE'

   .. attribute:: HEAD
      :type: str
      :value: 'HEAD'

   .. attribute:: OPTIONS
      :type: str
      :value: 'OPTIONS'

   **Example:**

   .. code-block:: python

       from requestforge import HttpMethod

       method = HttpMethod.GET
       print(method.value)  # 'GET'

       # Can be used in comparisons
       if method == HttpMethod.GET:
           print("It's a GET request")

HttpRequest
-----------

.. class:: HttpRequest(method, url, headers=None, params=None, data=None, json_data=None, files=None, timeout=None, auth=None)

   Immutable HTTP request representation.

   :param HttpMethod method: HTTP method
   :param str url: Request URL (relative or absolute)
   :param dict headers: Request headers (optional)
   :param dict params: URL query parameters (optional)
   :param dict data: Form data (optional)
   :param dict json_data: JSON data (optional)
   :param dict files: Files to upload (optional)
   :param float timeout: Request timeout in seconds (optional)
   :param tuple auth: Authentication tuple (username, password) (optional)

   **Note:** This is a frozen dataclass. Once created, it cannot be modified. Use helper methods to create modified copies.

Attributes
~~~~~~~~~~

.. attribute:: HttpRequest.method
   :type: HttpMethod

   HTTP method for the request.

.. attribute:: HttpRequest.url
   :type: str

   Request URL (can be relative or absolute).

.. attribute:: HttpRequest.headers
   :type: dict[str, str] | None

   Request headers.

.. attribute:: HttpRequest.params
   :type: dict[str, Any] | None

   URL query parameters.

.. attribute:: HttpRequest.data
   :type: dict[str, Any] | None

   Form-encoded data for request body.

.. attribute:: HttpRequest.json_data
   :type: dict[str, Any] | None

   JSON data for request body.

.. attribute:: HttpRequest.files
   :type: dict[str, Any] | None

   Files to upload (multipart/form-data).

.. attribute:: HttpRequest.timeout
   :type: float | None

   Request timeout in seconds.

.. attribute:: HttpRequest.auth
   :type: tuple | None

   Authentication credentials (username, password).

Methods
~~~~~~~

.. method:: HttpRequest.with_headers(headers)

   Create new request with additional headers.

   :param dict headers: Headers to add/override
   :returns: New HttpRequest instance with merged headers
   :rtype: HttpRequest

   **Example:**

   .. code-block:: python

       request = HttpRequest(method=HttpMethod.GET, url='/users')

       # Add headers (returns new instance)
       authenticated = request.with_headers({
           'Authorization': 'Bearer token123',
           'X-Custom': 'value'
       })

       print(request.headers)         # None (original unchanged)
       print(authenticated.headers)   # {'Authorization': '...', 'X-Custom': '...'}

.. method:: HttpRequest.to_dict()

   Convert request to dictionary.

   :returns: Dictionary representation of request
   :rtype: dict[str, Any]

   **Example:**

   .. code-block:: python

       request = HttpRequest(
           method=HttpMethod.POST,
           url='/users',
           json_data={'name': 'John'}
       )

       data = request.to_dict()
       # {
       #     'method': HttpMethod.POST,
       #     'url': '/users',
       #     'headers': None,
       #     'params': None,
       #     'data': None,
       #     'json_data': {'name': 'John'},
       #     'files': None,
       #     'timeout': None,
       #     'auth': None
       # }

.. method:: HttpRequest.to_curl()

   Convert request to cURL command string.

   :returns: cURL command that represents this request
   :rtype: str

   **Example:**

   .. code-block:: python

       request = HttpRequest(
           method=HttpMethod.POST,
           url='https://api.example.com/users',
           headers={'Authorization': 'Bearer token'},
           json_data={'name': 'John'}
       )

       print(request.to_curl())
       # curl -X 'POST' -H 'Authorization: Bearer token' \
       #      -H 'Content-Type: application/json' \
       #      --data '{"name": "John"}' \
       #      'https://api.example.com/users'

Examples
~~~~~~~~

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod

    # Simple GET
    request = HttpRequest(method=HttpMethod.GET, url='/users')

    # GET with parameters
    request = HttpRequest(
        method=HttpMethod.GET,
        url='/users',
        params={'page': 1, 'limit': 10}
    )

    # POST with JSON
    request = HttpRequest(
        method=HttpMethod.POST,
        url='/users',
        json_data={'name': 'John', 'email': 'john@example.com'},
        headers={'Content-Type': 'application/json'}
    )

    # POST with form data
    request = HttpRequest(
        method=HttpMethod.POST,
        url='/login',
        data={'username': 'john', 'password': 'secret'}
    )

    # File upload
    request = HttpRequest(
        method=HttpMethod.POST,
        url='/upload',
        files={'document': open('file.pdf', 'rb')}
    )

    # With timeout
    request = HttpRequest(
        method=HttpMethod.GET,
        url='/slow-endpoint',
        timeout=60.0
    )

    # With basic auth
    request = HttpRequest(
        method=HttpMethod.GET,
        url='/protected',
        auth=('username', 'password')
    )

HttpResponse
------------

.. class:: HttpResponse(status_code, headers, content, elapsed_ms, url, request, encoding=None)

   Immutable HTTP response representation.

   :param int status_code: HTTP status code
   :param dict headers: Response headers
   :param bytes content: Response body content
   :param float elapsed_ms: Request duration in milliseconds
   :param str url: Final URL (after redirects)
   :param HttpRequest request: Original request
   :param str encoding: Response encoding (optional)

Attributes
~~~~~~~~~~

.. attribute:: HttpResponse.status_code
   :type: int

   HTTP status code (e.g., 200, 404, 500).

.. attribute:: HttpResponse.headers
   :type: dict[str, str]

   Response headers.

.. attribute:: HttpResponse.content
   :type: bytes

   Raw response body content.

.. attribute:: HttpResponse.elapsed_ms
   :type: float

   Request duration in milliseconds.

.. attribute:: HttpResponse.url
   :type: str

   Final URL after any redirects.

.. attribute:: HttpResponse.request
   :type: HttpRequest

   Original request that generated this response.

.. attribute:: HttpResponse.encoding
   :type: str | None

   Response encoding (e.g., 'utf-8').

Properties
~~~~~~~~~~

.. attribute:: HttpResponse.text
   :type: str

   Decoded response content as string.

   **Example:**

   .. code-block:: python

       response = client.get('/users')
       print(response.text)  # Decoded string

.. attribute:: HttpResponse.is_success
   :type: bool

   True if status code is 2xx (200-299).

   **Example:**

   .. code-block:: python

       response = client.get('/users')
       if response.is_success:
           print("Request succeeded")

.. attribute:: HttpResponse.is_client_error
   :type: bool

   True if status code is 4xx (400-499).

.. attribute:: HttpResponse.is_server_error
   :type: bool

   True if status code is 5xx (500-599).

Methods
~~~~~~~

.. method:: HttpResponse.json()

   Parse response content as JSON.

   :returns: Parsed JSON data
   :rtype: Any
   :raises ResponseParseException: If content is not valid JSON

   **Example:**

   .. code-block:: python

       response = client.get('/users/1')
       user = response.json()
       print(user['name'])

.. method:: HttpResponse.json_or_none()

   Parse response as JSON, return None on failure.

   :returns: Parsed JSON data or None
   :rtype: Any | None

   **Example:**

   .. code-block:: python

       response = client.get('/data')
       data = response.json_or_none()

       if data is not None:
           process(data)
       else:
           print("Response is not JSON")

Examples
~~~~~~~~

.. code-block:: python

    from requestforge import HttpClient

    client = create_client('https://api.example.com')
    response = client.get('/users/1')

    # Status code
    print(response.status_code)  # 200

    # Check status
    if response.is_success:
        print("Success!")
    elif response.is_client_error:
        print("Client error (4xx)")
    elif response.is_server_error:
        print("Server error (5xx)")

    # Headers
    print(response.headers['Content-Type'])
    print(response.headers.get('X-Rate-Limit'))

    # Body content
    print(response.content)      # bytes
    print(response.text)         # str

    # Parse JSON
    user = response.json()
    print(user['name'])

    # Safe JSON parsing
    data = response.json_or_none()
    if data:
        print(data)

    # Metadata
    print(f"Request took {response.elapsed_ms}ms")
    print(f"Final URL: {response.url}")
    print(f"Encoding: {response.encoding}")

    # Access original request
    print(response.request.url)
    print(response.request.method)

RequestContext
--------------

.. class:: RequestContext(request, attempt=0, max_retries=0, metadata=None)

   Mutable context for request lifecycle.

   :param HttpRequest request: The HTTP request
   :param int attempt: Current attempt number (0-indexed)
   :param int max_retries: Maximum retry attempts
   :param dict metadata: Additional context metadata

   **Note:** Unlike HttpRequest/HttpResponse, RequestContext is mutable to track state during retries.

Attributes
~~~~~~~~~~

.. attribute:: RequestContext.request
   :type: HttpRequest

   The HTTP request being executed.

.. attribute:: RequestContext.attempt
   :type: int

   Current attempt number (0 = first attempt, 1 = first retry, etc.).

.. attribute:: RequestContext.max_retries
   :type: int

   Maximum number of retry attempts allowed.

.. attribute:: RequestContext.metadata
   :type: dict[str, Any]

   Additional context data (e.g., correlation IDs, timing data).

Properties
~~~~~~~~~~

.. attribute:: RequestContext.is_retry
   :type: bool

   True if this is a retry attempt (attempt > 0).

   **Example:**

   .. code-block:: python

       if context.is_retry:
           print(f"Retry attempt {context.attempt}")

Methods
~~~~~~~

.. method:: RequestContext.increment_attempt()

   Increment the attempt counter.

   **Example:**

   .. code-block:: python

       context.increment_attempt()
       print(context.attempt)  # Incremented

Examples
~~~~~~~~

.. code-block:: python

    from requestforge.models import RequestContext, HttpRequest, HttpMethod

    request = HttpRequest(method=HttpMethod.GET, url='/users')
    context = RequestContext(
        request=request,
        attempt=0,
        max_retries=3,
        metadata={}
    )

    # Check if retry
    if context.is_retry:
        print(f"Retry #{context.attempt}")
    else:
        print("First attempt")

    # Store metadata
    context.metadata['request_id'] = 'abc123'
    context.metadata['start_time'] = time.time()

    # Increment attempt
    context.increment_attempt()
    print(f"Attempt: {context.attempt}")  # 1

    # Check retry status
    print(context.is_retry)  # True

FetchContext
------------

.. class:: FetchContext(tokens=None, metadata=None)

   Context passed through the token fetch pipeline.

   :param dict tokens: Tokens fetched by previous steps
   :param dict metadata: Additional metadata

   Used in multi-step authentication pipelines to pass tokens between fetcher steps.

Attributes
~~~~~~~~~~

.. attribute:: FetchContext.tokens
   :type: dict[str, TokenData]

   Dictionary mapping step names to their fetched tokens.

.. attribute:: FetchContext.metadata
   :type: dict[str, Any]

   Additional context metadata.

Methods
~~~~~~~

.. method:: FetchContext.get_token(name)

   Get token by step name.

   :param str name: Step name
   :returns: Token data or None
   :rtype: TokenData | None

.. method:: FetchContext.get_token_value(name)

   Get token access_token value by step name.

   :param str name: Step name
   :returns: Access token string or None
   :rtype: str | None

.. method:: FetchContext.add_token(name, token)

   Add token to context.

   :param str name: Step name
   :param TokenData token: Token data

.. method:: FetchContext.has_token(name)

   Check if token exists in context.

   :param str name: Step name
   :returns: True if token exists
   :rtype: bool

.. method:: FetchContext.has_valid_token(name)

   Check if token exists and is not expired.

   :param str name: Step name
   :returns: True if valid token exists
   :rtype: bool

Examples
~~~~~~~~

.. code-block:: python

    from requestforge.models import FetchContext
    from requestforge.config import TokenData

    context = FetchContext()

    # Add token
    app_token = TokenData(access_token='app-token-123', token_type='Bearer')
    context.add_token('app_token', app_token)

    # Check if token exists
    if context.has_token('app_token'):
        print("App token available")

    # Get token
    token = context.get_token('app_token')
    print(token.access_token)

    # Get just the token value
    token_value = context.get_token_value('app_token')
    print(token_value)  # 'app-token-123'

    # Check validity
    if context.has_valid_token('app_token'):
        print("Token is valid and not expired")

    # Store metadata
    context.metadata['pipeline_start'] = time.time()

Complete Example
----------------

.. code-block:: python

    from requestforge import HttpClient, HttpRequest, HttpMethod

    # Create request
    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/users',
        headers={'Authorization': 'Bearer token'},
        json_data={'name': 'John', 'email': 'john@example.com'},
        timeout=30.0
    )

    # Execute request
    client = HttpClient(config)
    response = client.request(request)

    # Check response
    print(f"Status: {response.status_code}")
    print(f"Success: {response.is_success}")
    print(f"Duration: {response.elapsed_ms}ms")

    # Parse response
    if response.is_success:
        user = response.json()
        print(f"Created user: {user['id']}")
    else:
        print(f"Error: {response.text}")

    # Convert to cURL for debugging
    print(request.to_curl())

See Also
--------

* :doc:`client` - HTTP client API
* :doc:`config` - Configuration models
* :doc:`../user-guide/basic-usage` - Usage guide
