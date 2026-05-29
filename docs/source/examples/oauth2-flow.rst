OAuth2 Flow Examples
====================

This page demonstrates various OAuth2 authentication flows using HTTP Client.

Client Credentials Flow
------------------------

Basic Client Credentials
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider,
        InMemoryTokenStorage
    )

    # Create OAuth2 provider
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

    # Configure HTTP client
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

With Django Cache
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        TokenManager,
        ClientCredentialsTokenProvider,
        DjangoCacheTokenStorage
    )

    # Provider
    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api'
    )

    # Django cache storage (shared across processes)
    storage = DjangoCacheTokenStorage(
        cache_alias='default',
        key_prefix='oauth_tokens'
    )

    # Token manager
    token_manager = TokenManager(provider, storage)

    # Django settings.py
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
        }
    }

With Header Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import ClientCredentialsTokenProvider

    # Send credentials in Authorization header (HTTP Basic)
    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api',
        auth_method='header'  # Use HTTP Basic auth
    )

With Extra Parameters
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import ClientCredentialsTokenProvider

    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api',
        scope='read write',
        extra_params={
            'audience': 'https://api.example.com',
            'grant_type': 'client_credentials'
        }
    )

Password Grant Flow
-------------------

User Authentication
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        TokenManager,
        PasswordGrantTokenProvider,
        InMemoryTokenStorage
    )

    # Password grant provider
    provider = PasswordGrantTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        username='user@example.com',
        password='user-password',
        service_name='example-api',
        scope='profile email'
    )

    # Token manager
    token_manager = TokenManager(
        provider=provider,
        storage=InMemoryTokenStorage()
    )

    # Configure client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=token_manager)
        .build()
    )

    client = HttpClient(config)
    response = client.get('/user/profile')

Token Refresh
-------------

Automatic Refresh
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        TokenManager,
        ClientCredentialsTokenProvider
    )

    provider = ClientCredentialsTokenProvider(
        token_url='https://auth.example.com/oauth/token',
        client_id='your-client-id',
        client_secret='your-client-secret',
        service_name='example-api'
    )

    token_manager = TokenManager(provider)

    # First call: fetches token
    token = token_manager.get_token()
    print(f"Token: {token.access_token}")
    print(f"Expires: {token.expires_at}")

    # Subsequent calls: returns cached token
    token = token_manager.get_token()

    # After expiration: automatically refreshes
    token = token_manager.get_token()

Manual Refresh
~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import TokenManager

    token_manager = TokenManager(provider)

    # Force refresh token
    new_token = token_manager.force_refresh()

    # Invalidate token
    token_manager.invalidate_token()

    # Next call will fetch new token
    token = token_manager.get_token()

Auth Retry on 401
-----------------

Automatic Token Refresh on 401
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClientConfigBuilder,
        HttpClient,
        TokenManager,
        SimpleAuthRetryStrategy
    )

    # Token manager
    token_manager = TokenManager(provider)

    # Auth retry strategy
    auth_retry = SimpleAuthRetryStrategy(
        max_retries=1,  # Retry once on 401
        delay=0.5       # Wait 500ms before retry
    )

    # Configure client with auth retry
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=auth_retry
        )
        .build()
    )

    client = HttpClient(config)

    # If 401 error:
    # 1. Token manager refreshes token
    # 2. Request retried with new token
    response = client.get('/protected-resource')

Exponential Auth Retry
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import ExponentialAuthRetryStrategy

    # Exponential backoff for auth retries
    auth_retry = ExponentialAuthRetryStrategy(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        multiplier=2.0,
        jitter=True
    )

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=auth_retry
        )
        .build()
    )

Custom OAuth2 Provider
----------------------

Custom Token Endpoint
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import TokenProviderInterface
    from requestforge.config import TokenData
    from datetime import datetime, timedelta
    import requests

    class CustomOAuth2Provider(TokenProviderInterface):
        """Custom OAuth2 provider for proprietary API."""

        def __init__(self, token_url, client_id, client_secret, service_name):
            self._token_url = token_url
            self._client_id = client_id
            self._client_secret = client_secret
            self._service_name = service_name

        @property
        def service_name(self):
            return self._service_name

        def fetch_token(self):
            # Custom token fetch logic
            response = requests.post(
                self._token_url,
                json={
                    'client_id': self._client_id,
                    'client_secret': self._client_secret,
                    'grant_type': 'custom_grant'
                },
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                raise AuthenticationException(
                    f'Token fetch failed: {response.status_code}',
                    service_name=self._service_name
                )

            data = response.json()

            return TokenData(
                access_token=data['access_token'],
                token_type=data.get('token_type', 'Bearer'),
                expires_at=datetime.now() + timedelta(seconds=data['expires_in']),
                refresh_token=data.get('refresh_token'),
                scope=data.get('scope')
            )

        def refresh_token(self, current_token):
            if current_token.refresh_token:
                # Use refresh token
                response = requests.post(
                    self._token_url,
                    json={
                        'grant_type': 'refresh_token',
                        'refresh_token': current_token.refresh_token,
                        'client_id': self._client_id,
                        'client_secret': self._client_secret
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return TokenData.from_response(data)

            # Fallback to fetching new token
            return self.fetch_token()

    # Usage
    provider = CustomOAuth2Provider(
        token_url='https://auth.example.com/token',
        client_id='client-id',
        client_secret='client-secret',
        service_name='custom-api'
    )

    token_manager = TokenManager(provider)

Multiple Services
-----------------

Different Tokens for Different Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider
    )

    # Service A
    service_a_provider = ClientCredentialsTokenProvider(
        token_url='https://auth-a.example.com/token',
        client_id='service-a-id',
        client_secret='service-a-secret',
        service_name='service-a'
    )
    service_a_manager = TokenManager(service_a_provider)

    # Service B
    service_b_provider = ClientCredentialsTokenProvider(
        token_url='https://auth-b.example.com/token',
        client_id='service-b-id',
        client_secret='service-b-secret',
        service_name='service-b'
    )
    service_b_manager = TokenManager(service_b_provider)

    # Client for Service A
    client_a = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://api-a.example.com')
        .with_token_auth(token_manager=service_a_manager)
        .build()
    )

    # Client for Service B
    client_b = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://api-b.example.com')
        .with_token_auth(token_manager=service_b_manager)
        .build()
    )

    # Each client uses its own token
    response_a = client_a.get('/data')
    response_b = client_b.get('/data')

Path Exclusion
--------------

Exclude Paths from Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientConfigBuilder

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            excluded_paths={
                '/health',      # Health check
                '/status',      # Status endpoint
                '/public/docs'  # Public documentation
            }
        )
        .build()
    )

    client = HttpClient(config)

    # No auth header
    response = client.get('/health')

    # With auth header
    response = client.get('/protected')

Pattern-Based Exclusion
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(
            token_manager=token_manager,
            excluded_paths={'/health'},
            excluded_path_patterns=[
                '/public/*',        # All public paths
                '/docs/*',          # All documentation
                '*/health',         # Health at any level
                '/api/v*/status'    # Status for any version
            ]
        )
        .build()
    )

Token Inspection
----------------

Accessing Token Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import TokenManager

    token_manager = TokenManager(provider)

    # Get current token
    token = token_manager.get_token()

    print(f"Access Token: {token.access_token}")
    print(f"Token Type: {token.token_type}")
    print(f"Expires At: {token.expires_at}")
    print(f"Refresh Token: {token.refresh_token}")
    print(f"Scope: {token.scope}")
    print(f"Is Expired: {token.is_expired}")

    # Get authorization header value
    auth_header = token.authorization_header
    print(f"Authorization: {auth_header}")

Complete OAuth2 Example
------------------------

Full OAuth2 Integration
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider,
        DjangoCacheTokenStorage,
        SimpleAuthRetryStrategy,
        ExponentialBackoffRetryStrategy
    )
    import os

    # OAuth2 provider
    provider = ClientCredentialsTokenProvider(
        token_url=os.getenv('OAUTH_TOKEN_URL'),
        client_id=os.getenv('OAUTH_CLIENT_ID'),
        client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
        service_name='my-api',
        scope='read write delete'
    )

    # Token manager with Django cache
    token_manager = TokenManager(
        provider=provider,
        storage=DjangoCacheTokenStorage(
            cache_alias='default',
            key_prefix='api_oauth_tokens'
        )
    )

    # Auth retry strategy
    auth_retry = SimpleAuthRetryStrategy(
        max_retries=1,
        delay=0.5
    )

    # Request retry strategy
    request_retry = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0
    )

    # Configure client
    config = (
        HttpClientConfigBuilder()
        .with_base_url(os.getenv('API_BASE_URL'))
        .with_timeout(30.0)
        .with_retry_strategy(request_retry)
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=auth_retry,
            excluded_paths={'/health', '/metrics'},
            excluded_path_patterns=['/public/*']
        )
        .with_logging(
            log_headers=True,
            log_body=False,
            sensitive_keys={'authorization'}
        )
        .with_pool_connection(20)
        .with_pool_maxsize(50)
        .build()
    )

    client = HttpClient(config)

    # Usage
    try:
        # Get users (token automatically managed)
        response = client.get('/users')
        users = response.json()

        # Create user
        response = client.post('/users', json_data={
            'name': 'John Doe',
            'email': 'john@example.com'
        })

        # Update user
        response = client.put('/users/123', json_data={
            'name': 'Jane Doe'
        })

        # Delete user
        response = client.delete('/users/123')

    except HttpClientException as e:
        print(f"API error: {e}")

Error Handling
--------------

Handling OAuth2 Errors
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        AuthenticationException,
        UnauthorizedException,
        HttpClientException
    )

    try:
        response = client.get('/protected-resource')

    except AuthenticationException as e:
        print(f"Authentication failed: {e.message}")
        print(f"Service: {e.service_name}")
        # Clear cached credentials or redirect to login

    except UnauthorizedException:
        print("Unauthorized - token may have been revoked")

    except HttpClientException as e:
        print(f"Request failed: {e}")

Token Revocation
~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import TokenManager

    token_manager = TokenManager(provider)

    # Invalidate token (force refresh on next use)
    token_manager.invalidate_token()

    # Next call will fetch new token
    token = token_manager.get_token()

Testing with OAuth2
-------------------

Mocking OAuth2 Tokens
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    from unittest.mock import Mock
    from requestforge import TokenManager, TokenData
    from datetime import datetime, timedelta

    def test_oauth2_request():
        # Mock provider
        mock_provider = Mock()
        mock_provider.fetch_token.return_value = TokenData(
            access_token='test-token',
            token_type='Bearer',
            expires_at=datetime.now() + timedelta(hours=1)
        )
        mock_provider.service_name = 'test-service'

        # Create token manager with mock
        token_manager = TokenManager(mock_provider)

        # Configure client
        config = (
            HttpClientConfigBuilder()
            .with_base_url('https://api.example.com')
            .with_token_auth(token_manager=token_manager)
            .build()
        )

        client = HttpClient(config)

        # Token provider called
        token = token_manager.get_token()
        assert token.access_token == 'test-token'
        mock_provider.fetch_token.assert_called_once()

See Also
--------

* :doc:`multi-step-auth` - Multi-step authentication
* :doc:`basic-requests` - Basic request examples
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`../api-reference/token-manager` - Token manager API
