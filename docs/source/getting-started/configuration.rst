Configuration
=============

Request Forge uses a builder pattern for flexible, readable configuration.

Basic Configuration
-------------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .build()
    )

Configuration Options
---------------------

Base URL
~~~~~~~~

Set the base URL for all requests:

.. code-block:: python

    builder.with_base_url('https://api.example.com')

Requests to relative URLs will be prefixed with this base URL.

Timeout
~~~~~~~

Configure request timeout in seconds:

.. code-block:: python

    builder.with_timeout(30.0)  # 30 seconds

Default is 30 seconds.

Headers
~~~~~~~

Set default headers for all requests:

.. code-block:: python

    # Multiple headers
    builder.with_headers({
        'User-Agent': 'MyApp/1.0',
        'X-API-Version': 'v2'
    })

    # Single header
    builder.with_header('Authorization', 'Bearer token')

SSL Verification
~~~~~~~~~~~~~~~~

Enable or disable SSL certificate verification:

.. code-block:: python

    builder.with_verify_ssl(True)  # Default
    builder.with_verify_ssl(False)  # Disable (not recommended)

.. warning::
    Disabling SSL verification is not recommended for production use.

Redirects
~~~~~~~~~

Configure redirect behavior:

.. code-block:: python

    builder.with_redirects(
        allow=True,        # Follow redirects
        max_redirects=10   # Maximum redirect hops
    )

Connection Pooling
~~~~~~~~~~~~~~~~~~

Configure connection pool size:

.. code-block:: python

    builder.with_pool_connection(10)   # Pool connections
    builder.with_pool_maxsize(20)      # Maximum pool size

Retry Strategy
~~~~~~~~~~~~~~

Configure retry behavior:

.. code-block:: python

    # Simple configuration
    builder.with_retry(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0
    )

    # Custom strategy
    from requestforge import ExponentialBackoffRetryStrategy

    strategy = ExponentialBackoffRetryStrategy(
        max_retries=5,
        base_delay=2.0,
        max_delay=120.0,
        multiplier=2.0,
        jitter=True
    )
    builder.with_retry_strategy(strategy)

Authentication
~~~~~~~~~~~~~~

Bearer Token
^^^^^^^^^^^^

.. code-block:: python

    builder.with_bearer_token('your-api-token')

API Key
^^^^^^^

.. code-block:: python

    builder.with_api_key('your-api-key', header_name='X-API-Key')

Token Manager
^^^^^^^^^^^^^

For automatic token refresh:

.. code-block:: python

    from requestforge import TokenManager, ClientCredentialsTokenProvider

    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api'
    )

    token_manager = TokenManager(provider)

    builder.with_token_auth(
        token_manager=token_manager,
        excluded_paths={'/health', '/public/*'}
    )

Logging
~~~~~~~

Enable built-in logging:

.. code-block:: python

    builder.with_logging(
        log_headers=True,
        log_body=False,
        sensitive_keys={'authorization', 'x-api-key'}
    )

Complete Example
----------------

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        # Basic settings
        .with_base_url('https://api.example.com')
        .with_timeout(30.0)
        .with_verify_ssl(True)

        # Headers
        .with_header('User-Agent', 'MyApp/1.0')
        .with_header('Accept', 'application/json')

        # Authentication
        .with_bearer_token('your-token')

        # Retry configuration
        .with_retry(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0
        )

        # Connection pooling
        .with_pool_connection(10)
        .with_pool_maxsize(20)

        # Logging
        .with_logging(log_headers=True)

        .build()
    )

    client = HttpClient(config)

Immutability
------------

Configuration objects are **immutable** (frozen dataclasses). Once built, they cannot be modified:

.. code-block:: python

    config = builder.build()

    # This will raise an error:
    # config.base_url = 'new-url'  # ❌ FrozenInstanceError

To change configuration, create a new config object.

Validation
----------

Configuration is validated during creation:

.. code-block:: python

    # This will raise ValueError:
    builder.with_timeout(-1)  # ❌ Timeout must be positive
    builder.with_redirects(max_redirects=-1)  # ❌ Must be non-negative
