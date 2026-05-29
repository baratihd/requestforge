Authentication
==============

Request Forge provides comprehensive authentication support with automatic token management, refresh, and retry capabilities.

Authentication Methods
----------------------

Bearer Token
~~~~~~~~~~~~

Simple static bearer token:

.. code-block:: python

    from requestforge import HttpClientConfigBuilder, HttpClient

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_bearer_token('your-api-token-here')
        .build()
    )

    client = HttpClient(config)
    response = client.get('/protected-resource')

    # Authorization header automatically added:
    # Authorization: Bearer your-api-token-here

API Key Authentication
~~~~~~~~~~~~~~~~~~~~~~

API key in custom header:

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_api_key('your-api-key', header_name='X-API-Key')
        .build()
    )

    client = HttpClient(config)
    # All requests include: X-API-Key: your-api-key

Using default header name:

.. code-block:: python

    # Uses X-API-Key by default
    config = builder.with_api_key('your-api-key').build()

Basic Authentication
~~~~~~~~~~~~~~~~~~~~

HTTP Basic authentication:

.. code-block:: python

    from requestforge import HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_basic_auth(username='user', password='pass')
        .build()
    )

    # Authorization: Basic dXNlcjpwYXNz (base64 encoded)

Token Manager
-------------

For dynamic tokens that expire and need refresh, use ``TokenManager``.

Overview
~~~~~~~~

``TokenManager`` provides:

* **Automatic Caching**: Tokens cached until expiration
* **Thread-Safe**: Safe for concurrent requests
* **Auto-Refresh**: Refreshes tokens when expired
* **Retry on 401**: Automatically retries after token refresh

Basic Setup
~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClientConfigBuilder,
        HttpClient,
        TokenManager,
        ClientCredentialsTokenProvider,
        InMemoryTokenStorage
    )

    # Create token provider
    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api',
        scope='read write'
    )

    # Create token manager
    token_manager = TokenManager(
        provider=provider,
        storage=InMemoryTokenStorage()
    )

    # Configure client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            excluded_paths={'/health', '/public'}
        )
        .build()
    )

    client = HttpClient(config)

    # First request: fetches and caches token
    response = client.get('/protected-resource')

    # Subsequent requests: reuses cached token
    response = client.get('/another-resource')

    # When token expires: automatically refreshes
    response = client.get('/resource')

Token Providers
---------------

Client Credentials Flow
~~~~~~~~~~~~~~~~~~~~~~~

OAuth2 client credentials grant:

.. code-block:: python

    from requestforge import ClientCredentialsTokenProvider

    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='my-api',
        scope='read write delete',  # Optional
        grant_type='client_credentials',  # Default
        auth_method='body'  # or 'header'
    )

With header authentication:

.. code-block:: python

    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='my-api',
        auth_method='header'  # Sends credentials in Authorization header
    )

Password Grant Flow
~~~~~~~~~~~~~~~~~~~

OAuth2 password grant (for user authentication):

.. code-block:: python

    from requestforge import PasswordGrantTokenProvider

    provider = PasswordGrantTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        username='user@example.com',
        password='user-password',
        service_name='my-api',
        scope='profile email'
    )

Custom Token Provider
~~~~~~~~~~~~~~~~~~~~~

Implement ``TokenProviderInterface`` for custom logic:

.. code-block:: python

    from requestforge.interfaces import TokenProviderInterface
    from requestforge.config import TokenData
    from datetime import datetime, timedelta

    class CustomTokenProvider(TokenProviderInterface):
        def __init__(self, api_url, api_key):
            self._api_url = api_url
            self._api_key = api_key

        @property
        def service_name(self) -> str:
            return 'custom-api'

        def fetch_token(self) -> TokenData:
            # Custom logic to fetch token
            response = requests.post(
                f'{self._api_url}/auth',
                headers={'X-API-Key': self._api_key}
            )

            data = response.json()
            return TokenData(
                access_token=data['token'],
                token_type='Bearer',
                expires_at=datetime.now() + timedelta(seconds=data['expires_in'])
            )

        def refresh_token(self, current_token: TokenData) -> TokenData:
            # Refresh logic
            return self.fetch_token()

Token Storage
-------------

In-Memory Storage
~~~~~~~~~~~~~~~~~

Default storage (single process):

.. code-block:: python

    from requestforge import InMemoryTokenStorage

    storage = InMemoryTokenStorage()
    token_manager = TokenManager(provider, storage)

Thread-safe for multi-threaded applications, but tokens not shared across processes.

Django Cache Storage
~~~~~~~~~~~~~~~~~~~~

For multi-process deployments (with Redis/Memcached):

.. code-block:: python

    from requestforge import DjangoCacheTokenStorage

    storage = DjangoCacheTokenStorage(
        cache_alias='default',  # Django cache alias
        key_prefix='api_tokens'  # Cache key prefix
    )

    token_manager = TokenManager(provider, storage)

Requires Django and a shared cache backend:

.. code-block:: python

    # settings.py
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
        }
    }

Custom Storage
~~~~~~~~~~~~~~

Implement ``TokenStorageInterface``:

.. code-block:: python

    from requestforge.interfaces import TokenStorageInterface
    from requestforge.config import TokenData
    from typing import Optional

    class RedisTokenStorage(TokenStorageInterface):
        def __init__(self, redis_client):
            self._redis = redis_client

        def get(self, key: str) -> Optional[TokenData]:
            data = self._redis.get(key)
            if data:
                # Deserialize TokenData
                import json
                token_dict = json.loads(data)
                return TokenData(**token_dict)
            return None

        def set(self, key: str, token: TokenData) -> None:
            import json
            data = json.dumps({
                'access_token': token.access_token,
                'token_type': token.token_type,
                # ... other fields
            })
            # Set with TTL
            ttl = (token.expires_at - datetime.now()).total_seconds()
            self._redis.setex(key, int(ttl), data)

        def delete(self, key: str) -> None:
            self._redis.delete(key)

        def exists(self, key: str) -> bool:
            return self._redis.exists(key)

Multi-Step Authentication
--------------------------

For complex authentication flows requiring multiple API calls.

Overview
~~~~~~~~

Multi-step authentication pipeline:

1. **Step 1**: Fetch application token
2. **Step 2**: Use app token to fetch user token
3. **Step 3**: Use user token for API requests

Each step is cached independently with its own TTL.

Basic Pipeline
~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import TokenFetchPipeline, PipelineTokenProvider
    from requestforge.fetcher import BodyTokenFetcher
    from requestforge.token_manager import InMemoryTokenStorage, TokenManager
    from datetime import timedelta

    # Step 1: Application Token
    app_token_fetcher = BodyTokenFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/v1/app/token',
        method='POST',
        request_data={
            'grant_type': 'client_credentials',
            'client_id': 'app-id',
            'client_secret': 'app-secret',
        },
        token_field='access_token',
        expires_in_field='expires_in',
        ttl=timedelta(hours=1)  # Cache for 1 hour
    )

    # Step 2: User Access Token (depends on app_token)
    user_token_fetcher = BodyTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/v1/user/token',
        method='POST',
        request_data={
            'username': 'user@example.com',
            'password': 'password123',
        },
        token_field='access_token',
        ttl=timedelta(minutes=30),
        depends_on=['app_token']  # Requires app_token first
    )

    # Create pipeline
    pipeline = TokenFetchPipeline(
        steps=[app_token_fetcher, user_token_fetcher],
        storage=InMemoryTokenStorage(),
        cache_key_prefix='myapp'
    )

    # Wrap in provider
    provider = PipelineTokenProvider(pipeline, service_name='myapp')

    # Use with TokenManager
    token_manager = TokenManager(provider)

    # Configure client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=token_manager)
        .build()
    )

    client = HttpClient(config)

    # Pipeline automatically:
    # 1. Fetches app_token
    # 2. Uses app_token to fetch user_token
    # 3. Injects user_token into requests
    response = client.get('/user/profile')

Advanced Pipeline
~~~~~~~~~~~~~~~~~

Custom fetcher with token dependency:

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher

    class UserTokenFetcher(BodyTokenFetcher):
        """Custom fetcher that uses app token in headers."""

        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)

            # Inject app token from context
            if context and 'app_token' in context:
                app_token = context['app_token'].access_token
                headers['X-App-Token'] = app_token

            return headers

    user_token_fetcher = UserTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/v1/user/token',
        # ... other config
        depends_on=['app_token']
    )

Authentication Retry
--------------------

Automatic retry on 401 responses.

Simple Retry
~~~~~~~~~~~~

.. code-block:: python

    from requestforge import SimpleAuthRetryStrategy

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=SimpleAuthRetryStrategy(
                max_retries=1,  # Retry once
                delay=0.5  # Wait 500ms before retry
            )
        )
        .build()
    )

Exponential Backoff
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import ExponentialAuthRetryStrategy

    auth_retry = ExponentialAuthRetryStrategy(
        max_retries=3,
        base_delay=0.5,
        max_delay=5.0,
        multiplier=2.0,
        jitter=True
    )

    config = builder.with_token_auth(
        token_manager=token_manager,
        auth_retry_strategy=auth_retry
    ).build()

Custom Retry Logic
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import ConditionalAuthRetryStrategy

    def should_retry(response):
        # Only retry if error is "token_expired"
        if response.status_code == 401:
            data = response.json_or_none()
            return data and data.get('error') == 'token_expired'
        return False

    auth_retry = ConditionalAuthRetryStrategy(
        max_retries=2,
        should_retry_func=should_retry
    )

Path Exclusion
--------------

Exclude paths from authentication:

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            excluded_paths={
                '/health',
                '/status',
                '/public/docs'
            }
        )
        .build()
    )

With glob patterns:

.. code-block:: python

    config = builder.with_token_auth(
        token_manager=token_manager,
        excluded_paths={'/health'},
        excluded_path_patterns=[
            '/public/*',
            '/docs/*',
            '*/health'
        ]
    ).build()

Complete Examples
-----------------

OAuth2 with Django
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # settings.py
    from requestforge import (
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider,
        DjangoCacheTokenStorage
    )

    # Token provider
    oauth_provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id=os.getenv('OAUTH_CLIENT_ID'),
        client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
        service_name='api-service'
    )

    # Token manager with Django cache
    token_manager = TokenManager(
        provider=oauth_provider,
        storage=DjangoCacheTokenStorage()
    )

    # HTTP client config
    API_CLIENT_CONFIG = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=token_manager)
        .with_retry(max_retries=3)
        .with_logging()
        .build()
    )

    # views.py
    from django.conf import settings
    from requestforge import HttpClient

    client = HttpClient(settings.API_CLIENT_CONFIG)
    response = client.get('/users')

Multi-Service Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Different tokens for different services:

.. code-block:: python

    # Service A
    service_a_provider = ClientCredentialsTokenProvider(...)
    service_a_manager = TokenManager(service_a_provider)

    # Service B
    service_b_provider = ClientCredentialsTokenProvider(...)
    service_b_manager = TokenManager(service_b_provider)

    # Client for Service A
    client_a = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://service-a.com')
        .with_token_auth(service_a_manager)
        .build()
    )

    # Client for Service B
    client_b = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://service-b.com')
        .with_token_auth(service_b_manager)
        .build()
    )

Best Practices
--------------

1. **Reuse TokenManager**

   .. code-block:: python

       # Good ✅ - TokenManager shared across requests
       token_manager = TokenManager(provider, storage)

       config = builder.with_token_auth(token_manager).build()
       client = HttpClient(config)

       # All requests use same token manager
       response1 = client.get('/resource1')
       response2 = client.get('/resource2')

2. **Use Shared Storage in Production**

   .. code-block:: python

       # Good ✅ - For multi-process deployments
       storage = DjangoCacheTokenStorage()

       # Avoid ❌ - For multi-process deployments
       storage = InMemoryTokenStorage()  # Not shared across processes

3. **Set Appropriate TTL**

   .. code-block:: python

       # Good ✅ - Cache with shorter TTL than actual expiration
       ttl=timedelta(minutes=55)  # Token expires in 60 minutes

4. **Handle Auth Errors**

   .. code-block:: python

       from requestforge import AuthenticationException

       try:
           response = client.get('/protected')
       except AuthenticationException as e:
           print(f"Auth failed: {e.service_name}")

Next Steps
----------

* Explore :doc:`retry-strategies` for robust requests
* Learn about :doc:`hooks` for custom authentication logic
* Check :doc:`../examples/oauth2-flow` for complete examples
