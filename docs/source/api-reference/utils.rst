Utilities API Reference
=======================

This page documents utility functions for Request Forge.

to_curl
-------

.. function:: to_curl(request)

   Convert HttpRequest to cURL command string.

   :param HttpRequest request: The HTTP request to convert
   :returns: cURL command string
   :rtype: str

   This utility function converts an :class:`HttpRequest` object into an equivalent
   cURL command that can be executed in a shell. Useful for debugging and sharing
   request details.

   **Features:**

   * Handles all HTTP methods
   * Includes headers
   * Handles query parameters
   * Includes request body (JSON and form data)
   * Handles file uploads
   * Includes authentication
   * Includes timeout
   * Properly quotes and escapes values

   **Example:**

   .. code-block:: python

       from requestforge import HttpRequest, HttpMethod
       from requestforge.utils import to_curl

       request = HttpRequest(
           method=HttpMethod.POST,
           url='https://api.example.com/users',
           headers={'Authorization': 'Bearer token123'},
           json_data={'name': 'John Doe', 'email': 'john@example.com'}
       )

       curl_command = to_curl(request)
       print(curl_command)

   **Output:**

   .. code-block:: bash

       curl -X 'POST' \
            -H 'Authorization: Bearer token123' \
            -H 'Content-Type: application/json' \
            --data '{"name": "John Doe", "email": "john@example.com"}' \
            'https://api.example.com/users'

GET Request
~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod
    from requestforge.utils import to_curl

    request = HttpRequest(
        method=HttpMethod.GET,
        url='https://api.example.com/users',
        params={'page': 1, 'limit': 10},
        headers={'Accept': 'application/json'}
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'GET' \
         -H 'Accept: application/json' \
         'https://api.example.com/users?page=1&limit=10'

POST with JSON
~~~~~~~~~~~~~~

.. code-block:: python

    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/users',
        headers={'Authorization': 'Bearer token'},
        json_data={'name': 'John', 'age': 30}
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'POST' \
         -H 'Authorization: Bearer token' \
         -H 'Content-Type: application/json' \
         --data '{"name": "John", "age": 30}' \
         'https://api.example.com/users'

POST with Form Data
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/login',
        data={'username': 'john', 'password': 'secret123'}
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'POST' \
         --data 'username=john&password=secret123' \
         'https://api.example.com/login'

With Authentication
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Bearer token
    request = HttpRequest(
        method=HttpMethod.GET,
        url='https://api.example.com/protected',
        headers={'Authorization': 'Bearer abc123'}
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'GET' \
         -H 'Authorization: Bearer abc123' \
         'https://api.example.com/protected'

.. code-block:: python

    # Basic auth
    request = HttpRequest(
        method=HttpMethod.GET,
        url='https://api.example.com/protected',
        auth=('username', 'password')
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'GET' \
         -u 'username:password' \
         'https://api.example.com/protected'

File Upload
~~~~~~~~~~~

.. code-block:: python

    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/upload',
        files={'document': 'path/to/file.pdf'}
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'POST' \
         -F 'document=@path/to/file.pdf' \
         'https://api.example.com/upload'

With Timeout
~~~~~~~~~~~~

.. code-block:: python

    request = HttpRequest(
        method=HttpMethod.GET,
        url='https://api.example.com/slow',
        timeout=30.0
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'GET' \
         --max-time 30.0 \
         'https://api.example.com/slow'

Complex Example
~~~~~~~~~~~~~~~

.. code-block:: python

    request = HttpRequest(
        method=HttpMethod.PUT,
        url='https://api.example.com/users/123',
        params={'notify': 'true'},
        headers={
            'Authorization': 'Bearer token',
            'Content-Type': 'application/json',
            'X-Request-ID': 'abc-123'
        },
        json_data={
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'tags': ['admin', 'premium']
        },
        timeout=60.0
    )

    print(to_curl(request))

**Output:**

.. code-block:: bash

    curl -X 'PUT' \
         -H 'Authorization: Bearer token' \
         -H 'Content-Type: application/json' \
         -H 'X-Request-ID: abc-123' \
         --data '{"name": "Jane Doe", "email": "jane@example.com", "tags": ["admin", "premium"]}' \
         --max-time 60.0 \
         'https://api.example.com/users/123?notify=true'

Usage in Debugging
------------------

Logging Requests
~~~~~~~~~~~~~~~~

.. code-block:: python

    import logging
    from requestforge import HttpClient, HttpRequest, HttpMethod
    from requestforge.utils import to_curl

    logger = logging.getLogger(__name__)

    def debug_request(request: HttpRequest):
        """Log request as cURL command."""
        curl = to_curl(request)
        logger.debug(f"Request: {curl}")

    # Usage
    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/users',
        json_data={'name': 'John'}
    )

    debug_request(request)
    response = client.request(request)

Custom Hook
~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RequestHookInterface
    from requestforge.utils import to_curl

    class CurlLoggingHook(RequestHookInterface):
        """Hook that logs all requests as cURL commands."""

        def before_request(self, request, context):
            curl = to_curl(request)
            print(f"[CURL] {curl}")
            return request

    # Usage
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_request_hook(CurlLoggingHook())
        .build()
    )

    client = HttpClient(config)
    response = client.get('/users')  # Prints cURL command

Error Reporting
~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientException
    from requestforge.utils import to_curl

    try:
        response = client.request(request)
    except HttpClientException as e:
        # Include cURL command in error report
        curl = to_curl(request)
        logger.error(
            f"Request failed: {e.message}",
            extra={
                'curl_command': curl,
                'error': str(e)
            }
        )

Testing Support
~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    from requestforge.utils import to_curl

    def test_request_format():
        """Test that request is formatted correctly."""
        request = HttpRequest(
            method=HttpMethod.POST,
            url='https://api.example.com/users',
            json_data={'name': 'Test'}
        )

        curl = to_curl(request)

        # Verify command structure
        assert curl.startswith("curl -X 'POST'")
        assert 'https://api.example.com/users' in curl
        assert '--data' in curl
        assert 'name' in curl

Sharing Requests
~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.utils import to_curl

    def share_request(request):
        """Generate shareable cURL command for request."""
        curl = to_curl(request)

        print("Copy and paste this command to reproduce the request:")
        print()
        print(curl)
        print()
        print("You can save it to a file and execute:")
        print("$ bash request.sh")

        # Optionally save to file
        with open('request.sh', 'w') as f:
            f.write('#!/bin/bash\n')
            f.write(curl)
            f.write('\n')

    # Usage
    request = HttpRequest(...)
    share_request(request)

HttpRequest Extension
---------------------

The ``to_curl()`` utility is also available as a method on :class:`HttpRequest`:

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod

    request = HttpRequest(
        method=HttpMethod.GET,
        url='https://api.example.com/users'
    )

    # Call directly on request object
    curl = request.to_curl()
    print(curl)

This is equivalent to:

.. code-block:: python

    from requestforge.utils import to_curl

    curl = to_curl(request)
    print(curl)

Implementation Notes
--------------------

**Quoting:**

The function uses ``shlex.quote()`` to properly escape and quote values for shell safety.

**Headers:**

All headers are included with ``-H`` flag. Content-Type is automatically added for JSON requests.

**Query Parameters:**

Parameters are URL-encoded and appended to the URL.

**Request Body:**

* JSON data uses ``--data`` with JSON-encoded string
* Form data uses ``--data`` with URL-encoded string
* Files use ``-F`` for multipart uploads

**Authentication:**

* Bearer tokens included in Authorization header
* Basic auth uses ``-u`` flag
* Custom auth headers included as regular headers

**Special Characters:**

All special characters are properly escaped for shell execution.

Limitations
-----------

1. **File Content:** File uploads show file path, not actual content
2. **Binary Data:** Binary request bodies may not be representable in cURL
3. **Session Cookies:** Does not include session cookies from client
4. **SSL Options:** Does not include custom SSL/TLS settings

See Also
--------

* :doc:`models` - HttpRequest and HttpResponse
* :doc:`../user-guide/basic-usage` - Basic usage guide
* :doc:`client` - HTTP client API
