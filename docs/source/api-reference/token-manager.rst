Token Manager API Reference
============================

This page documents the token management system including providers, storage, and managers.

Token Manager
-------------

TokenManager
~~~~~~~~~~~~

.. class:: TokenManager(provider, storage=None)

   Thread-safe token manager with caching.

   :param TokenProviderInterface provider: Token provider
   :param TokenStorageInterface storage: Token storage (default: InMemoryTokenStorage)

   **Features:**

   * Automatic token caching
   * Thread-safe token refresh
   * Prevents concurrent token fetches
   * Automatic expiration handling

   **Thread Safety:** This class is thread-safe. Multiple threads can safely share a single instance.

   **Example:**

   .. code-block:: python

       from requestforge import TokenManager, ClientCredentialsTokenProvider, InMemoryTokenStorage

       provider = ClientCredentialsTokenProvider(
           token_url='https://auth.example.com/oauth/token',
           client_id='your-client-id',
           client_secret='your-client-secret',
           service_name='example-api'
       )

       token_manager = TokenManager(
           provider=provider,
           storage=InMemoryTokenStorage()
       )

Methods
^^^^^^^

.. method:: TokenManager.get_token()

   Get valid token (from cache or fetch new).

   :returns: Valid token data
   :rtype: TokenData
   :raises AuthenticationException: If token fetch fails

   **Behavior:**

   1. Check cache for valid token
   2. If cached and not expired, return cached token
   3. If expired or not cached, fetch new token
   4. Cache new token
   5. Return token

   **Example:**

   .. code-block:: python

       token = token_manager.get_token()
       print(token.access_token)
       print(token.expires_at)

.. method:: TokenManager.invalidate_token()

   Invalidate the current cached token.

   Forces next ``get_token()`` call to fetch a new token.

   **Example:**

   .. code-block:: python

       # Invalidate token (e.g., after logout)
       token_manager.invalidate_token()

.. method:: TokenManager.force_refresh()

   Force fetch a new token regardless of cache.

   :returns: New token data
   :rtype: TokenData
   :raises AuthenticationException: If token fetch fails

   **Example:**

   .. code-block:: python

       # Force refresh token
       new_token = token_manager.force_refresh()

Token Storage
-------------

TokenStorageInterface
~~~~~~~~~~~~~~~~~~~~~

.. class:: TokenStorageInterface

   Abstract interface for token storage.

   **Methods:**

   .. method:: get(key)

      Retrieve token by key.

      :param str key: Storage key
      :returns: Token data or None
      :rtype: TokenData | None

   .. method:: set(key, token)

      Store token with key.

      :param str key: Storage key
      :param TokenData token: Token to store

   .. method:: delete(key)

      Delete token by key.

      :param str key: Storage key

   .. method:: exists(key)

      Check if token exists.

      :param str key: Storage key
      :returns: True if exists
      :rtype: bool

InMemoryTokenStorage
~~~~~~~~~~~~~~~~~~~~

.. class:: InMemoryTokenStorage()

   Thread-safe in-memory token storage.

   **Use Cases:**

   * Single-instance deployments
   * Development/testing
   * Applications without shared cache

   **Limitations:**

   * Tokens not shared across processes
   * Tokens lost on restart

   **Example:**

   .. code-block:: python

       from requestforge import InMemoryTokenStorage

       storage = InMemoryTokenStorage()
       token_manager = TokenManager(provider, storage)

   **Methods:**

   .. method:: get(key)

      Get token from memory.

   .. method:: set(key, token)

      Store token in memory.

   .. method:: delete(key)

      Delete token from memory.

   .. method:: exists(key)

      Check if token exists in memory.

   .. method:: clear()

      Clear all tokens from memory.

      **Example:**

      .. code-block:: python

          storage.clear()  # Remove all cached tokens

DjangoCacheTokenStorage
~~~~~~~~~~~~~~~~~~~~~~~

.. class:: DjangoCacheTokenStorage(cache_alias='default', key_prefix='token')

   Django cache-based token storage.

   :param str cache_alias: Django cache alias
   :param str key_prefix: Prefix for cache keys

   **Use Cases:**

   * Multi-instance deployments
   * Production environments
   * Shared cache backends (Redis, Memcached)

   **Requirements:**

   * Django installed
   * Configured cache backend

   **Example:**

   .. code-block:: python

       from requestforge import DjangoCacheTokenStorage

       storage = DjangoCacheTokenStorage(
           cache_alias='default',
           key_prefix='api_tokens'
       )

       token_manager = TokenManager(provider, storage)

   **Django Settings:**

   .. code-block:: python

       # settings.py
       CACHES = {
           'default': {
               'BACKEND': 'django.core.cache.backends.redis.RedisCache',
               'LOCATION': 'redis://127.0.0.1:6379/1',
           }
       }

   **Methods:**

   .. method:: get(key)

      Get token from Django cache.

   .. method:: set(key, token)

      Store token in Django cache with TTL.

      TTL is calculated from token expiration with minimum of 60 seconds.

   .. method:: delete(key)

      Delete token from Django cache.

   .. method:: exists(key)

      Check if token exists in Django cache.

Custom Storage Example
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import TokenStorageInterface
    from requestforge.config import TokenData
    import redis
    import json
    from datetime import datetime

    class RedisTokenStorage(TokenStorageInterface):
        """Redis-based token storage."""

        def __init__(self, redis_client, key_prefix='token'):
            self.redis = redis_client
            self.prefix = key_prefix

        def _make_key(self, key):
            return f"{self.prefix}:{key}"

        def get(self, key):
            data = self.redis.get(self._make_key(key))
            if data:
                token_dict = json.loads(data)
                # Convert expires_at string to datetime
                if token_dict.get('expires_at'):
                    token_dict['expires_at'] = datetime.fromisoformat(
                        token_dict['expires_at']
                    )
                return TokenData(**token_dict)
            return None

        def set(self, key, token):
            token_dict = {
                'access_token': token.access_token,
                'token_type': token.token_type,
                'expires_at': token.expires_at.isoformat() if token.expires_at else None,
                'refresh_token': token.refresh_token,
                'scope': token.scope,
                'extra': token.extra
            }

            data = json.dumps(token_dict)

            # Calculate TTL
            if token.expires_at:
                ttl = int((token.expires_at - datetime.now()).total_seconds())
                ttl = max(ttl, 60)  # Minimum 60 seconds
                self.redis.setex(self._make_key(key), ttl, data)
            else:
                self.redis.set(self._make_key(key), data)

        def delete(self, key):
            self.redis.delete(self._make_key(key))

        def exists(self, key):
            return self.redis.exists(self._make_key(key))

    # Usage
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    storage = RedisTokenStorage(redis_client)
    token_manager = TokenManager(provider, storage)

Token Providers
---------------

TokenProviderInterface
~~~~~~~~~~~~~~~~~~~~~~

.. class:: TokenProviderInterface

   Abstract interface for token providers.

   **Properties:**

   .. attribute:: service_name
      :type: str

      Unique identifier for this token provider.

   **Methods:**

   .. method:: fetch_token()

      Fetch a new token from the authentication server.

      :returns: Fresh token data
      :rtype: TokenData
      :raises AuthenticationException: If fetch fails

   .. method:: refresh_token(current_token)

      Refresh an existing token.

      :param TokenData current_token: Current token
      :returns: Refreshed token data
      :rtype: TokenData
      :raises AuthenticationException: If refresh fails

BaseOAuth2TokenProvider
~~~~~~~~~~~~~~~~~~~~~~~

.. class:: BaseOAuth2TokenProvider(token_url, client_id, client_secret, service_name, scope=None, extra_params=None)

   Base OAuth2 token provider.

   :param str token_url: Token endpoint URL
   :param str client_id: OAuth2 client ID
   :param str client_secret: OAuth2 client secret
   :param str service_name: Service identifier
   :param str scope: OAuth2 scope (optional)
   :param dict extra_params: Additional parameters (optional)

   **Note:** This is an abstract base class. Use concrete implementations like ``ClientCredentialsTokenProvider``.

   **Properties:**

   .. attribute:: service_name
      :type: str

      Service name for this provider.

   **Methods:**

   .. method:: fetch_token()

      Fetch new token using client credentials.

   .. method:: refresh_token(current_token)

      Refresh existing token or fetch new one.

ClientCredentialsTokenProvider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: ClientCredentialsTokenProvider(token_url, client_id, client_secret, service_name, scope=None, grant_type='client_credentials', extra_params=None, auth_method='body')

   OAuth2 Client Credentials grant type token provider.

   :param str token_url: Token endpoint URL
   :param str client_id: Client ID
   :param str client_secret: Client secret
   :param str service_name: Service name
   :param str scope: OAuth2 scope (optional)
   :param str grant_type: Grant type (default: 'client_credentials')
   :param dict extra_params: Additional parameters (optional)
   :param str auth_method: Authentication method ('body' or 'header')

   **Auth Methods:**

   * **body**: Send credentials in request body
   * **header**: Send credentials in Authorization header (HTTP Basic)

   **Example:**

   .. code-block:: python

       from requestforge import ClientCredentialsTokenProvider

       # Body authentication (default)
       provider = ClientCredentialsTokenProvider(
           token_url='https://auth.example.com/oauth/token',
           client_id='your-client-id',
           client_secret='your-client-secret',
           service_name='example-api',
           scope='read write',
           auth_method='body'
       )

       # Header authentication
       provider = ClientCredentialsTokenProvider(
           token_url='https://auth.example.com/oauth/token',
           client_id='your-client-id',
           client_secret='your-client-secret',
           service_name='example-api',
           auth_method='header'
       )

       token_manager = TokenManager(provider)

PasswordGrantTokenProvider
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: PasswordGrantTokenProvider(token_url, client_id, client_secret, username, password, service_name, scope=None, extra_params=None)

   OAuth2 Password grant type token provider.

   :param str token_url: Token endpoint URL
   :param str client_id: Client ID
   :param str client_secret: Client secret
   :param str username: User username
   :param str password: User password
   :param str service_name: Service name
   :param str scope: OAuth2 scope (optional)
   :param dict extra_params: Additional parameters (optional)

   **Example:**

   .. code-block:: python

       from requestforge import PasswordGrantTokenProvider

       provider = PasswordGrantTokenProvider(
           token_url='https://auth.example.com/oauth/token',
           client_id='your-client-id',
           client_secret='your-client-secret',
           username='user@example.com',
           password='user-password',
           service_name='example-api',
           scope='profile email'
       )

       token_manager = TokenManager(provider)

Custom Provider Example
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import TokenProviderInterface
    from requestforge.config import TokenData
    from datetime import datetime, timedelta
    import requests

    class CustomTokenProvider(TokenProviderInterface):
        """Custom token provider for proprietary API."""

        def __init__(self, api_url, api_key, service_name):
            self._api_url = api_url
            self._api_key = api_key
            self._service_name = service_name

        @property
        def service_name(self):
            return self._service_name

        def fetch_token(self):
            # Custom token fetch logic
            response = requests.post(
                f'{self._api_url}/auth/token',
                headers={'X-API-Key': self._api_key},
                json={'grant_type': 'api_key'}
            )

            if response.status_code != 200:
                raise AuthenticationException(
                    f'Token fetch failed: {response.status_code}',
                    service_name=self._service_name
                )

            data = response.json()

            return TokenData(
                access_token=data['token'],
                token_type='Custom',
                expires_at=datetime.now() + timedelta(seconds=data['ttl']),
                extra={'api_version': data.get('version')}
            )

        def refresh_token(self, current_token):
            # For this API, just fetch a new token
            return self.fetch_token()

    # Usage
    provider = CustomTokenProvider(
        api_url='https://api.example.com',
        api_key='your-api-key',
        service_name='custom-api'
    )
    token_manager = TokenManager(provider)

Complete Examples
-----------------

Basic Token Management
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        TokenManager,
        ClientCredentialsTokenProvider,
        InMemoryTokenStorage
    )

    # Create provider
    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api'
    )

    # Create manager
    token_manager = TokenManager(
        provider=provider,
        storage=InMemoryTokenStorage()
    )

    # Get token (fetched and cached)
    token = token_manager.get_token()
    print(f"Token: {token.access_token}")
    print(f"Expires: {token.expires_at}")

    # Get token again (from cache)
    token = token_manager.get_token()

    # Force refresh
    new_token = token_manager.force_refresh()

With HTTP Client
~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider
    )

    # Setup token manager
    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api'
    )
    token_manager = TokenManager(provider)

    # Configure client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=token_manager)
        .build()
    )

    client = HttpClient(config)

    # Token automatically fetched, cached, and injected
    response = client.get('/users')

    # Token automatically refreshed when expired
    response = client.get('/posts')

Django Integration
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # settings.py
    from requestforge import (
        TokenManager,
        ClientCredentialsTokenProvider,
        DjangoCacheTokenStorage
    )

    # Token provider
    TOKEN_PROVIDER = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id=os.getenv('OAUTH_CLIENT_ID'),
        client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
        service_name='api-service'
    )

    # Token manager with Django cache
    TOKEN_MANAGER = TokenManager(
        provider=TOKEN_PROVIDER,
        storage=DjangoCacheTokenStorage(
            cache_alias='default',
            key_prefix='api_tokens'
        )
    )

    # views.py
    from django.conf import settings
    from requestforge import HttpClient, HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=settings.TOKEN_MANAGER)
        .build()
    )

    client = HttpClient(config)
    response = client.get('/data')

Multi-Service Tokens
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import TokenManager, ClientCredentialsTokenProvider

    # Service A token manager
    service_a_provider = ClientCredentialsTokenProvider(
        token_url='https://auth.service-a.com/token',
        client_id='service-a-client',
        client_secret='service-a-secret',
        service_name='service-a'
    )
    service_a_tokens = TokenManager(service_a_provider)

    # Service B token manager
    service_b_provider = ClientCredentialsTokenProvider(
        token_url='https://auth.service-b.com/token',
        client_id='service-b-client',
        client_secret='service-b-secret',
        service_name='service-b'
    )
    service_b_tokens = TokenManager(service_b_provider)

    # Create clients with different tokens
    client_a = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://api.service-a.com')
        .with_token_auth(token_manager=service_a_tokens)
        .build()
    )

    client_b = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://api.service-b.com')
        .with_token_auth(token_manager=service_b_tokens)
        .build()
    )

Token Refresh Exception
-----------------------

TokenRefreshException
~~~~~~~~~~~~~~~~~~~~~

See :class:`requestforge.exceptions.TokenRefreshException`
for detailed exception documentation.

**Example:**

.. code-block:: python

    from requestforge.token_manager import TokenRefreshException

    try:
        token = token_manager.get_token()
    except TokenRefreshException as e:
        print(f"Token refresh failed: {e}")

See Also
--------

* :doc:`config` - TokenData configuration
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`pipelines` - Multi-step authentication
* :doc:`hooks` - TokenAuthHook
