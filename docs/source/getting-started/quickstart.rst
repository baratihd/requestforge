Quick Start
===========

This guide will help you get started with HTTP Client in 5 minutes.

Simple GET Request
------------------

.. code-block:: python

    from requestforge import create_client

    # Create a client
    client = create_client('https://api.github.com')

    # Make a GET request
    response = client.get('/users/octocat')

    # Check response
    if response.is_success:
        user = response.json()
        print(f"User: {user['name']}")
    else:
        print(f"Error: {response.status_code}")

POST Request with JSON
----------------------

.. code-block:: python

    from requestforge import HttpClient, HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_header('Content-Type', 'application/json')
        .build()
    )

    client = HttpClient(config)

    # POST request with JSON data
    response = client.post(
        '/users',
        json_data={
            'name': 'John Doe',
            'email': 'john@example.com'
        }
    )

    if response.status_code == 201:
        new_user = response.json()
        print(f"Created user ID: {new_user['id']}")

With Authentication
-------------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_bearer_token('your-api-token')
        .build()
    )

    client = HttpClient(config)
    response = client.get('/protected-resource')

With Retry Logic
----------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0
        )
        .build()
    )

    client = HttpClient(config)

    # Automatically retries on failures
    response = client.get('/unstable-endpoint')

Using Context Manager
---------------------

.. code-block:: python

    from requestforge import http_client

    with http_client('https://api.example.com') as client:
        response = client.get('/users')
        users = response.json()

    # Client automatically closed after with block

Error Handling
--------------

.. code-block:: python

    from requestforge import HttpClient, TimeoutException, HttpStatusException

    client = HttpClient(config)

    try:
        response = client.get('/users/1')
        user = response.json()
    except TimeoutException:
        print("Request timed out")
    except HttpStatusException as e:
        print(f"HTTP error {e.status_code}: {e.message}")
    except Exception as e:
        print(f"Unexpected error: {e}")

Next Steps
----------

* Read the :doc:`configuration` guide for advanced setup
* Explore :doc:`../user-guide/authentication` for token management
* Learn about :doc:`../user-guide/retry-strategies` for robust requests
* Check out :doc:`../examples/oauth2-flow` for real-world examples
