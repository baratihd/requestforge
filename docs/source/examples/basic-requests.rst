Basic Requests Examples
=======================

This page provides practical examples of basic HTTP operations using HTTP Client.

Simple GET Request
------------------

.. code-block:: python

    from requestforge import create_client

    # Create client
    client = create_client('https://api.github.com')

    # Simple GET request
    response = client.get('/users/octocat')

    if response.is_success:
        user = response.json()
        print(f"Name: {user['name']}")
        print(f"Bio: {user['bio']}")
        print(f"Public repos: {user['public_repos']}")
    else:
        print(f"Error: {response.status_code}")

GET with Query Parameters
--------------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://api.github.com')

    # GET with query parameters
    response = client.get('/search/repositories', params={
        'q': 'requestforge',
        'sort': 'stars',
        'order': 'desc',
        'per_page': 5
    })

    if response.is_success:
        data = response.json()
        print(f"Total results: {data['total_count']}")

        for repo in data['items']:
            print(f"- {repo['full_name']}: {repo['stargazers_count']} stars")

POST Request with JSON
----------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://jsonplaceholder.typicode.com')

    # POST request with JSON data
    response = client.post('/posts', json_data={
        'title': 'My New Post',
        'body': 'This is the content of my post',
        'userId': 1
    })

    if response.status_code == 201:
        created_post = response.json()
        print(f"Created post with ID: {created_post['id']}")
    else:
        print(f"Failed to create post: {response.status_code}")

POST with Form Data
-------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://httpbin.org')

    # POST with form data
    response = client.post('/post', data={
        'username': 'john_doe',
        'email': 'john@example.com',
        'age': '30'
    })

    if response.is_success:
        result = response.json()
        print(f"Form data received: {result['form']}")

PUT Request (Update Resource)
------------------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://jsonplaceholder.typicode.com')

    # PUT request to update resource
    response = client.put('/posts/1', json_data={
        'id': 1,
        'title': 'Updated Title',
        'body': 'Updated content',
        'userId': 1
    })

    if response.is_success:
        updated_post = response.json()
        print(f"Updated post: {updated_post['title']}")

PATCH Request (Partial Update)
-------------------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://jsonplaceholder.typicode.com')

    # PATCH request for partial update
    response = client.patch('/posts/1', json_data={
        'title': 'New Title Only'
    })

    if response.is_success:
        updated_post = response.json()
        print(f"Updated title: {updated_post['title']}")

DELETE Request
--------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://jsonplaceholder.typicode.com')

    # DELETE request
    response = client.delete('/posts/1')

    if response.status_code == 200:
        print("Post deleted successfully")
    elif response.status_code == 204:
        print("Post deleted (no content)")

Custom Headers
--------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_header('User-Agent', 'MyApp/1.0')
        .with_header('Accept', 'application/json')
        .with_header('X-Custom-Header', 'custom-value')
        .build()
    )

    client = HttpClient(config)
    response = client.get('/data')

Per-Request Headers
-------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://api.example.com')

    # Headers for specific request
    response = client.get('/users', headers={
        'X-Request-ID': 'abc123',
        'X-Client-Version': '2.0'
    })

Request Timeout
---------------

.. code-block:: python

    from requestforge import create_client, TimeoutException

    client = create_client('https://httpbin.org')

    try:
        # Request with 5 second timeout
        response = client.get('/delay/10', timeout=5.0)
    except TimeoutException:
        print("Request timed out after 5 seconds")

Handling Different Status Codes
--------------------------------

.. code-block:: python

    from requestforge import (
        create_client,
        NotFoundException,
        UnauthorizedException,
        ServerErrorException
    )

    client = create_client('https://api.example.com')

    try:
        response = client.get('/users/123')

        if response.status_code == 200:
            user = response.json()
            print(f"User found: {user['name']}")
        elif response.status_code == 201:
            print("Resource created")
        elif response.status_code == 204:
            print("No content")

    except NotFoundException:
        print("User not found (404)")
    except UnauthorizedException:
        print("Unauthorized (401)")
    except ServerErrorException as e:
        print(f"Server error ({e.status_code})")

File Upload
-----------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://httpbin.org')

    # Upload single file
    with open('document.pdf', 'rb') as f:
        response = client.post('/post', files={
            'file': f
        })

    if response.is_success:
        print("File uploaded successfully")

Multiple File Upload
--------------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://httpbin.org')

    # Upload multiple files
    files = {
        'document': open('document.pdf', 'rb'),
        'image': open('photo.jpg', 'rb'),
        'data': open('data.csv', 'rb')
    }

    try:
        response = client.post('/post', files=files)
        if response.is_success:
            print("Files uploaded successfully")
    finally:
        # Close all files
        for f in files.values():
            f.close()

Basic Authentication
--------------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_basic_auth(username='user', password='password')
        .build()
    )

    client = HttpClient(config)
    response = client.get('/protected')

API Key Authentication
----------------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_api_key('your-api-key-here', header_name='X-API-Key')
        .build()
    )

    client = HttpClient(config)
    response = client.get('/data')

Bearer Token Authentication
----------------------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_bearer_token('your-access-token')
        .build()
    )

    client = HttpClient(config)
    response = client.get('/protected-resource')

Response Parsing
----------------

JSON Response
~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import create_client, ResponseParseException

    client = create_client('https://api.github.com')
    response = client.get('/users/octocat')

    try:
        data = response.json()
        print(f"User: {data['login']}")
    except ResponseParseException:
        print("Response is not valid JSON")

Safe JSON Parsing
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://api.example.com')
    response = client.get('/data')

    # Returns None if parsing fails
    data = response.json_or_none()

    if data is not None:
        print(f"Data: {data}")
    else:
        print(f"Plain text response: {response.text}")

Text Response
~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://httpbin.org')
    response = client.get('/html')

    # Get response as text
    html_content = response.text
    print(html_content)

Binary Response
~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://httpbin.org')
    response = client.get('/image/png')

    # Save binary content
    with open('image.png', 'wb') as f:
        f.write(response.content)

Using Context Manager
---------------------

.. code-block:: python

    from requestforge import http_client

    # Automatically closes client
    with http_client('https://api.github.com') as client:
        response = client.get('/users/octocat')
        user = response.json()
        print(f"User: {user['name']}")

    # Client is automatically closed here

Request Metadata
----------------

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://httpbin.org')
    response = client.get('/get')

    # Response metadata
    print(f"Status: {response.status_code}")
    print(f"Duration: {response.elapsed_ms}ms")
    print(f"URL: {response.url}")
    print(f"Encoding: {response.encoding}")

    # Response headers
    print(f"Content-Type: {response.headers['Content-Type']}")
    print(f"Content-Length: {response.headers.get('Content-Length')}")

Converting to cURL
------------------

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod

    request = HttpRequest(
        method=HttpMethod.POST,
        url='https://api.example.com/users',
        headers={'Authorization': 'Bearer token'},
        json_data={'name': 'John Doe'}
    )

    # Convert to cURL command for debugging
    curl_command = request.to_curl()
    print(curl_command)
    # Output: curl -X 'POST' -H 'Authorization: Bearer token' ...

Error Handling
--------------

Comprehensive Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        create_client,
        TimeoutException,
        ConnectionException,
        NotFoundException,
        HttpStatusException,
        HttpClientException
    )

    client = create_client('https://api.example.com')

    try:
        response = client.get('/users/123')
        user = response.json()
        print(f"User: {user['name']}")

    except TimeoutException:
        print("Request timed out - server too slow")

    except ConnectionException:
        print("Cannot connect to server")

    except NotFoundException:
        print("User not found")

    except HttpStatusException as e:
        print(f"HTTP error {e.status_code}: {e.message}")

    except HttpClientException as e:
        print(f"Request failed: {e}")

Batch Requests
--------------

Sequential Requests
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://jsonplaceholder.typicode.com')

    user_ids = [1, 2, 3, 4, 5]
    users = []

    for user_id in user_ids:
        response = client.get(f'/users/{user_id}')
        if response.is_success:
            users.append(response.json())

    print(f"Fetched {len(users)} users")

Pagination
~~~~~~~~~~

.. code-block:: python

    from requestforge import create_client

    client = create_client('https://api.github.com')

    all_repos = []
    page = 1

    while True:
        response = client.get('/user/repos', params={
            'page': page,
            'per_page': 100
        })

        if not response.is_success:
            break

        repos = response.json()
        if not repos:
            break

        all_repos.extend(repos)
        page += 1

    print(f"Total repositories: {len(all_repos)}")

Rate Limiting Handling
----------------------

.. code-block:: python

    from requestforge import create_client, HttpStatusException
    import time

    client = create_client('https://api.github.com')

    def fetch_with_rate_limit(url):
        while True:
            try:
                response = client.get(url)
                return response
            except HttpStatusException as e:
                if e.status_code == 429:  # Too Many Requests
                    # Get retry-after header
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after}s")
                    time.sleep(retry_after)
                else:
                    raise

    response = fetch_with_rate_limit('/users/octocat')

Complete Example: REST API Client
----------------------------------

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        NotFoundException,
        HttpClientException
    )

    class GitHubClient:
        """Simple GitHub API client."""

        def __init__(self, token=None):
            builder = (
                HttpClientConfigBuilder()
                .with_base_url('https://api.github.com')
                .with_timeout(30.0)
                .with_header('Accept', 'application/vnd.github.v3+json')
            )

            if token:
                builder.with_bearer_token(token)

            self.client = HttpClient(builder.build())

        def get_user(self, username):
            """Get user information."""
            try:
                response = self.client.get(f'/users/{username}')
                return response.json()
            except NotFoundException:
                return None
            except HttpClientException as e:
                print(f"Error fetching user: {e}")
                return None

        def get_repos(self, username):
            """Get user repositories."""
            response = self.client.get(f'/users/{username}/repos')
            if response.is_success:
                return response.json()
            return []

        def search_repos(self, query, language=None):
            """Search repositories."""
            params = {'q': query}
            if language:
                params['q'] += f' language:{language}'

            response = self.client.get('/search/repositories', params=params)
            if response.is_success:
                return response.json()['items']
            return []

    # Usage
    github = GitHubClient(token='your-github-token')

    # Get user
    user = github.get_user('octocat')
    if user:
        print(f"User: {user['name']}")

    # Get repositories
    repos = github.get_repos('octocat')
    print(f"Repositories: {len(repos)}")

    # Search
    python_repos = github.search_repos('requestforge', language='python')
    for repo in python_repos[:5]:
        print(f"- {repo['full_name']}: {repo['stargazers_count']} stars")

See Also
--------

* :doc:`oauth2-flow` - OAuth2 authentication examples
* :doc:`multi-step-auth` - Multi-step authentication
* :doc:`custom-retry` - Custom retry strategies
* :doc:`../user-guide/basic-usage` - Basic usage guide
* :doc:`../api-reference/client` - Client API reference
