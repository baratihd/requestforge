Basic Usage
===========

This guide covers the fundamental usage patterns of HTTP Client.

Making Requests
---------------

HTTP Client supports all standard HTTP methods.

GET Requests
~~~~~~~~~~~~

Simple GET request:

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://api.example.com')
    response = client.get('/users')

    print(response.status_code)  # 200
    print(response.json())       # Parsed JSON response

GET with query parameters:

.. code-block:: python

    response = client.get('/users', params={
        'page': 1,
        'limit': 10,
        'active': 'true'
    })

    # Requests: https://api.example.com/users?page=1&limit=10&active=true

GET with custom headers:

.. code-block:: python

    response = client.get('/users', headers={
        'X-API-Version': '2.0',
        'Accept-Language': 'en-US'
    })

POST Requests
~~~~~~~~~~~~~

POST with JSON data:

.. code-block:: python

    response = client.post('/users', json_data={
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': 30
    })

    if response.status_code == 201:
        created_user = response.json()
        print(f"Created user ID: {created_user['id']}")

POST with form data:

.. code-block:: python

    response = client.post('/login', data={
        'username': 'john',
        'password': 'secret123'
    })

POST with file upload:

.. code-block:: python

    response = client.post('/upload', files={
        'file': open('document.pdf', 'rb'),
        'thumbnail': open('thumb.jpg', 'rb')
    })

PUT Requests
~~~~~~~~~~~~

Update a resource:

.. code-block:: python

    response = client.put('/users/123', json_data={
        'name': 'Jane Doe',
        'email': 'jane@example.com'
    })

PATCH Requests
~~~~~~~~~~~~~~

Partial update:

.. code-block:: python

    response = client.patch('/users/123', json_data={
        'email': 'newemail@example.com'
    })

DELETE Requests
~~~~~~~~~~~~~~~

Delete a resource:

.. code-block:: python

    response = client.delete('/users/123')

    if response.status_code == 204:
        print("User deleted successfully")

Working with Responses
----------------------

Response Object
~~~~~~~~~~~~~~~

Every request returns an ``HttpResponse`` object:

.. code-block:: python

    response = client.get('/users/1')

    # Status code
    print(response.status_code)  # 200

    # Headers
    print(response.headers)  # Dict of headers
    print(response.headers['Content-Type'])  # 'application/json'

    # Body content
    print(response.content)  # bytes
    print(response.text)     # str

    # Metadata
    print(response.elapsed_ms)  # Request duration in milliseconds
    print(response.url)         # Final URL after redirects
    print(response.encoding)    # Response encoding

Status Checks
~~~~~~~~~~~~~

Convenient properties for checking response status:

.. code-block:: python

    response = client.get('/users/1')

    # Status categories
    if response.is_success:        # 2xx
        print("Success!")

    if response.is_client_error:   # 4xx
        print("Client error")

    if response.is_server_error:   # 5xx
        print("Server error")

    # Specific status codes
    if response.status_code == 200:
        print("OK")
    elif response.status_code == 404:
        print("Not found")

Parsing JSON
~~~~~~~~~~~~

.. code-block:: python

    response = client.get('/users/1')

    # Parse JSON (raises ResponseParseException on invalid JSON)
    user = response.json()
    print(user['name'])

    # Safe JSON parsing (returns None on error)
    data = response.json_or_none()
    if data:
        print(data['name'])
    else:
        print("Invalid JSON response")

Request Configuration
---------------------

Per-Request Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Override client defaults for specific requests:

.. code-block:: python

    from requestforge import HttpClient, HttpClientConfigBuilder

    # Client with default timeout of 30s
    config = HttpClientConfigBuilder().with_timeout(30.0).build()
    client = HttpClient(config)

    # Override timeout for this request only
    response = client.get('/slow-endpoint', timeout=60.0)

    # Override headers
    response = client.get('/users', headers={
        'X-Custom-Header': 'special-value'
    })

Base URL Handling
~~~~~~~~~~~~~~~~~

Absolute vs. Relative URLs:

.. code-block:: python

    # With base URL
    client = create_client('https://api.example.com')

    # Relative URL (uses base URL)
    response = client.get('/users')
    # Requests: https://api.example.com/users

    # Absolute URL (ignores base URL)
    response = client.get('https://other-api.com/data')
    # Requests: https://other-api.com/data

URL Construction:

.. code-block:: python

    # Leading/trailing slashes are handled automatically
    client = create_client('https://api.example.com/')

    # All of these work the same:
    client.get('/users')
    client.get('users')
    client.get('/users/')
    # All request: https://api.example.com/users

Using HttpRequest Objects
--------------------------

For more control, create ``HttpRequest`` objects explicitly:

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod

    request = HttpRequest(
        method=HttpMethod.POST,
        url='/users',
        headers={'X-Custom': 'value'},
        params={'notify': 'true'},
        json_data={'name': 'John'},
        timeout=60.0
    )

    response = client.request(request)

Modifying Requests:

.. code-block:: python

    # Create base request
    request = HttpRequest(method=HttpMethod.GET, url='/users')

    # Add headers (returns new request object)
    authenticated_request = request.with_headers({
        'Authorization': 'Bearer token123'
    })

    # Original request is unchanged (immutable)
    print(request.headers)              # None
    print(authenticated_request.headers)  # {'Authorization': 'Bearer token123'}

Converting to cURL:

.. code-block:: python

    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/users',
        headers={'Authorization': 'Bearer token'},
        json_data={'name': 'John'}
    )

    # Generate cURL command for debugging
    curl_command = request.to_curl()
    print(curl_command)
    # Output: curl -X 'POST' -H 'Authorization: Bearer token' --data '{"name": "John"}' 'https://api.example.com/users'

Resource Management
-------------------

Using Context Managers
~~~~~~~~~~~~~~~~~~~~~~

Always close clients to release resources:

.. code-block:: python

    # Automatic cleanup with context manager (recommended)
    with create_client('https://api.example.com') as client:
        response = client.get('/users')
        users = response.json()
    # Client automatically closed here

Manual Cleanup:

.. code-block:: python

    client = create_client('https://api.example.com')
    try:
        response = client.get('/users')
    finally:
        client.close()

Session Lifecycle
~~~~~~~~~~~~~~~~~

Understanding session lifecycle:

.. code-block:: python

    from requestforge import HttpClient, HttpClientConfigBuilder

    config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
    client = HttpClient(config)

    # Sessions are created lazily per thread
    response1 = client.get('/users')  # Creates session
    response2 = client.get('/posts')  # Reuses same session

    # Connection pooling is automatic
    # Multiple requests reuse connections

    # Close to release all connections
    client.close()

Best Practices
--------------

1. **Use Context Managers**

   .. code-block:: python

       # Good ✅
       with create_client('https://api.example.com') as client:
           response = client.get('/users')

       # Avoid ❌
       client = create_client('https://api.example.com')
       response = client.get('/users')
       # Forgot to close!

2. **Reuse Client Instances**

   .. code-block:: python

       # Good ✅ - Connection pooling benefits
       client = create_client('https://api.example.com')
       for user_id in range(1, 100):
           response = client.get(f'/users/{user_id}')
       client.close()

       # Avoid ❌ - Creates new connection for each request
       for user_id in range(1, 100):
           client = create_client('https://api.example.com')
           response = client.get(f'/users/{user_id}')
           client.close()

3. **Check Response Status**

   .. code-block:: python

       # Good ✅
       response = client.get('/users/1')
       if response.is_success:
           user = response.json()
       else:
           print(f"Error: {response.status_code}")

       # Avoid ❌ - Assumes success
       response = client.get('/users/1')
       user = response.json()  # May fail if status is 404/500

4. **Handle Exceptions**

   .. code-block:: python

       # Good ✅
       from requestforge import TimeoutException, HttpClientException

       try:
           response = client.get('/users/1')
       except TimeoutException:
           print("Request timed out")
       except HttpClientException as e:
           print(f"Request failed: {e}")

5. **Use Appropriate Timeouts**

   .. code-block:: python

       # Good ✅ - Different timeouts for different endpoints
       fast_response = client.get('/health', timeout=5.0)
       slow_response = client.get('/reports/generate', timeout=120.0)

Common Patterns
---------------

Pagination
~~~~~~~~~~

.. code-block:: python

    def fetch_all_users(client):
        page = 1
        all_users = []

        while True:
            response = client.get('/users', params={'page': page, 'limit': 100})

            if not response.is_success:
                break

            users = response.json()
            if not users:
                break

            all_users.extend(users)
            page += 1

        return all_users

Batch Operations
~~~~~~~~~~~~~~~~

.. code-block:: python

    def create_users_batch(client, users_data):
        results = []

        for user_data in users_data:
            response = client.post('/users', json_data=user_data)
            results.append({
                'data': user_data,
                'success': response.is_success,
                'response': response.json() if response.is_success else None
            })

        return results

Download Files
~~~~~~~~~~~~~~

.. code-block:: python

    def download_file(client, url, output_path):
        response = client.get(url)

        if response.is_success:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        return False

Next Steps
----------

* Learn about :doc:`authentication` for token management
* Explore :doc:`retry-strategies` for robust requests
* Read :doc:`error-handling` for exception handling
* Check :doc:`concurrent-requests` for parallel execution
