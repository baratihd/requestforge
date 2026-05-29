Multi-Step Authentication Examples
===================================

This page demonstrates complex multi-step authentication flows using token pipelines.

Two-Step Authentication
-----------------------

App Token → User Token
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        TokenFetchPipeline,
        PipelineTokenProvider,
        InMemoryTokenStorage
    )
    from requestforge.fetcher import BodyTokenFetcher
    from datetime import timedelta

    # Step 1: Fetch application token
    app_token_fetcher = BodyTokenFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/v1/app/token',
        method='POST',
        request_data={
            'grant_type': 'client_credentials',
            'client_id': 'your-app-id',
            'client_secret': 'your-app-secret'
        },
        token_field='access_token',
        expires_in_field='expires_in',
        ttl=timedelta(hours=1)  # Cache for 1 hour
    )

    # Step 2: Fetch user token using app token
    class UserTokenFetcher(BodyTokenFetcher):
        """Custom fetcher that uses app token in headers."""

        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            # Inject app token from previous step
            if context and 'app_token' in context:
                headers['X-App-Token'] = context['app_token'].access_token
            return headers

    user_token_fetcher = UserTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/v1/user/token',
        method='POST',
        request_data={
            'username': 'user@example.com',
            'password': 'password123'
        },
        token_field='access_token',
        ttl=timedelta(minutes=30),  # Cache for 30 minutes
        depends_on=['app_token']    # Requires app_token first
    )

    # Create pipeline
    pipeline = TokenFetchPipeline(
        steps=[app_token_fetcher, user_token_fetcher],
        storage=InMemoryTokenStorage(),
        cache_key_prefix='myapp'
    )

    # Wrap in provider
    provider = PipelineTokenProvider(
        pipeline=pipeline,
        service_name='myapp',
        refresh_from_step='user_token'  # Only refresh user token
    )

    # Use with TokenManager
    token_manager = TokenManager(provider)

    # Configure HTTP client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=token_manager)
        .build()
    )

    client = HttpClient(config)

    # Pipeline executes automatically:
    # 1. Fetches app_token
    # 2. Uses app_token to fetch user_token
    # 3. Injects user_token into requests
    response = client.get('/user/profile')

Three-Step Authentication
--------------------------

Device → App → User Tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HeaderTokenFetcher, BodyTokenFetcher
    from datetime import timedelta

    # Step 1: Device registration token (from header)
    device_token_fetcher = HeaderTokenFetcher(
        name='device_token',
        base_url='https://auth.example.com',
        endpoint='/v1/device/register',
        method='POST',
        request_headers={
            'X-Device-ID': 'unique-device-id',
            'X-Device-Type': 'mobile'
        },
        token_header='X-Device-Token',
        token_type='Device',
        ttl=timedelta(days=30)  # Device token valid for 30 days
    )

    # Step 2: App token using device token
    class AppTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'device_token' in context:
                headers['X-Device-Token'] = context['device_token'].access_token
            return headers

    app_token_fetcher = AppTokenFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/v1/app/token',
        method='POST',
        request_data={
            'client_id': 'app-id',
            'client_secret': 'app-secret'
        },
        token_field='access_token',
        ttl=timedelta(hours=1),
        depends_on=['device_token']
    )

    # Step 3: User token using app token
    class UserTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'app_token' in context:
                headers['X-App-Token'] = context['app_token'].access_token
            return headers

    user_token_fetcher = UserTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/v1/user/token',
        method='POST',
        request_data={
            'username': 'user@example.com',
            'password': 'password123'
        },
        token_field='access_token',
        ttl=timedelta(minutes=15),
        depends_on=['app_token']
    )

    # Create three-step pipeline
    pipeline = TokenFetchPipeline(
        steps=[device_token_fetcher, app_token_fetcher, user_token_fetcher],
        storage=InMemoryTokenStorage(),
        cache_key_prefix='myapp'
    )

    # Execute pipeline
    token = pipeline.execute()
    print(f"Final token: {token.access_token}")

Header-Based Authentication Chain
----------------------------------

Session → API Key → Access Token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HeaderTokenFetcher, BodyTokenFetcher
    from datetime import timedelta

    # Step 1: Session token from login
    session_token_fetcher = HeaderTokenFetcher(
        name='session_token',
        base_url='https://auth.example.com',
        endpoint='/v1/login',
        method='POST',
        request_data={
            'username': 'user',
            'password': 'pass'
        },
        token_header='X-Session-Token',
        token_type='Session',
        ttl=timedelta(hours=24)
    )

    # Step 2: API key using session
    class ApiKeyFetcher(HeaderTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'session_token' in context:
                headers['X-Session-Token'] = context['session_token'].access_token
            return headers

    api_key_fetcher = ApiKeyFetcher(
        name='api_key',
        base_url='https://auth.example.com',
        endpoint='/v1/apikey/generate',
        method='POST',
        token_header='X-API-Key',
        token_type='ApiKey',
        ttl=timedelta(hours=12),
        depends_on=['session_token']
    )

    # Step 3: Access token using API key
    class AccessTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'api_key' in context:
                headers['X-API-Key'] = context['api_key'].access_token
            return headers

    access_token_fetcher = AccessTokenFetcher(
        name='access_token',
        base_url='https://auth.example.com',
        endpoint='/v1/token',
        method='POST',
        request_data={'grant_type': 'api_key'},
        token_field='access_token',
        ttl=timedelta(minutes=30),
        depends_on=['api_key']
    )

    pipeline = TokenFetchPipeline(
        steps=[session_token_fetcher, api_key_fetcher, access_token_fetcher],
        storage=InMemoryTokenStorage(),
        cache_key_prefix='complex_auth'
    )

Mixed Authentication Flow
--------------------------

Token in Header and Body
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HeaderTokenFetcher, BodyTokenFetcher
    from datetime import timedelta

    # Step 1: Device token from header
    device_token = HeaderTokenFetcher(
        name='device_token',
        base_url='https://auth.example.com',
        endpoint='/device/register',
        method='POST',
        request_headers={'X-Device-ID': 'device-123'},
        token_header='X-Device-Token',
        ttl=timedelta(days=30)
    )

    # Step 2: Access token from body (using device token)
    class MixedTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            """Put device token in header."""
            headers = super()._build_request_headers(context)
            if context and 'device_token' in context:
                headers['X-Device-Token'] = context['device_token'].access_token
            return headers

        def _build_request_data(self, context):
            """Put additional data in body."""
            data = super()._build_request_data(context)
            data['device_validated'] = True
            return data

    access_token = MixedTokenFetcher(
        name='access_token',
        base_url='https://auth.example.com',
        endpoint='/token',
        method='POST',
        request_data={
            'username': 'user',
            'password': 'pass'
        },
        token_field='access_token',
        ttl=timedelta(minutes=30),
        depends_on=['device_token']
    )

    pipeline = TokenFetchPipeline(
        steps=[device_token, access_token],
        storage=InMemoryTokenStorage()
    )

Selective Cache Invalidation
-----------------------------

Invalidate Specific Steps
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import TokenFetchPipeline

    # Create pipeline with three steps
    pipeline = TokenFetchPipeline(
        steps=[device_token, app_token, user_token],
        storage=InMemoryTokenStorage()
    )

    # Execute pipeline (all steps cached)
    token = pipeline.execute()

    # Later, invalidate just user token
    pipeline.invalidate_step('user_token')

    # Next execution reuses device_token and app_token from cache
    # Only fetches new user_token
    token = pipeline.execute()

    # Invalidate app_token (cascades to user_token)
    pipeline.invalidate_step('app_token')

    # Next execution reuses device_token
    # Fetches new app_token and user_token
    token = pipeline.execute()

    # Force refresh everything
    token = pipeline.execute(force_refresh=True)

Cascade Invalidation Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Given: device_token → app_token → user_token

    pipeline = TokenFetchPipeline(
        steps=[device_token, app_token, user_token],
        storage=storage
    )

    # Invalidate device_token
    pipeline.invalidate_step('device_token')

    # This invalidates:
    # - device_token (directly)
    # - app_token (depends on device_token)
    # - user_token (depends on app_token)

    # Next execution fetches all three tokens

With Django Cache
-----------------

Multi-Process Token Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        TokenFetchPipeline,
        PipelineTokenProvider,
        TokenManager,
        DjangoCacheTokenStorage
    )

    # Django cache storage (shared across processes)
    storage = DjangoCacheTokenStorage(
        cache_alias='default',
        key_prefix='auth_pipeline'
    )

    # Create pipeline
    pipeline = TokenFetchPipeline(
        steps=[app_token_fetcher, user_token_fetcher],
        storage=storage,
        cache_key_prefix='myapp'
    )

    # Tokens shared across Django workers/processes
    provider = PipelineTokenProvider(pipeline, 'myapp')
    token_manager = TokenManager(provider)

    # settings.py
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
        }
    }

Custom Token Fetcher
--------------------

Complex Custom Logic
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HttpTokenFetcher
    from requestforge.config import TokenData
    from requestforge.models import HttpMethod
    from datetime import datetime, timedelta
    import hashlib

    class SignedTokenFetcher(HttpTokenFetcher):
        """Custom fetcher with request signing."""

        def __init__(self, name, secret_key, **kwargs):
            super().__init__(**kwargs)
            self._name = name
            self._secret_key = secret_key
            self._depends_on = []

        @property
        def name(self):
            return self._name

        @property
        def depends_on(self):
            return self._depends_on

        @property
        def ttl(self):
            return timedelta(hours=1)

        def fetch(self, context=None):
            import time
            timestamp = str(int(time.time()))

            # Create signature
            signature_string = f"{self._secret_key}{timestamp}"
            signature = hashlib.sha256(signature_string.encode()).hexdigest()

            # Make request with signature
            response = self._make_request(
                method=HttpMethod.POST,
                endpoint='/auth/token',
                headers={
                    'X-Timestamp': timestamp,
                    'X-Signature': signature
                },
                json_data={'grant_type': 'signed'}
            )

            if not response.is_success:
                raise AuthenticationException(
                    f'Signed auth failed: {response.status_code}',
                    service_name=self._name
                )

            data = response.json()

            return TokenData(
                access_token=data['token'],
                token_type='Signed',
                expires_at=datetime.now() + timedelta(seconds=data['ttl']),
                extra={'signature': signature}
            )

    # Usage
    fetcher = SignedTokenFetcher(
        name='signed_token',
        secret_key='my-secret-key',
        base_url='https://auth.example.com',
        timeout=30.0
    )

    token = fetcher.fetch()

Error Handling
--------------

Pipeline Error Handling
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import AuthenticationException

    try:
        token = pipeline.execute()
    except AuthenticationException as e:
        print(f"Auth failed at step: {e.service_name}")
        print(f"Error: {e.message}")

        # Invalidate failed step
        if e.service_name:
            pipeline.invalidate_step(e.service_name)

        # Handle error (redirect to login, etc.)

Custom Error Handling in Fetcher
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher

    class RobustTokenFetcher(BodyTokenFetcher):
        """Fetcher with custom error handling."""

        def on_fetch_error(self, error, context=None):
            # Custom error logging
            logger.error(
                f"Token fetch failed for {self.name}",
                extra={
                    'error': str(error),
                    'context': context,
                    'endpoint': self._endpoint
                }
            )

            # Send alert
            send_alert(f"Token fetch failed: {error}")

            # Don't raise, let caller handle

    fetcher = RobustTokenFetcher(
        name='robust_token',
        base_url='https://auth.example.com',
        endpoint='/token',
        request_data={'client_id': 'id'}
    )

Testing Pipeline
----------------

Unit Testing Pipeline
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    import responses
    from requestforge import TokenFetchPipeline
    from requestforge.fetcher import BodyTokenFetcher
    from requestforge.token_manager import InMemoryTokenStorage
    from datetime import timedelta

    @responses.activate
    def test_two_step_pipeline():
        # Mock app token endpoint
        responses.add(
            responses.POST,
            'https://auth.example.com/app/token',
            json={'access_token': 'app-token-123', 'expires_in': 3600},
            status=200
        )

        # Mock user token endpoint
        responses.add(
            responses.POST,
            'https://auth.example.com/user/token',
            json={'access_token': 'user-token-456', 'expires_in': 1800},
            status=200
        )

        # Create pipeline
        app_token = BodyTokenFetcher(
            name='app_token',
            base_url='https://auth.example.com',
            endpoint='/app/token',
            request_data={'client_id': 'test'},
            token_field='access_token'
        )

        user_token = BodyTokenFetcher(
            name='user_token',
            base_url='https://auth.example.com',
            endpoint='/user/token',
            request_data={'username': 'test'},
            token_field='access_token',
            depends_on=['app_token']
        )

        pipeline = TokenFetchPipeline(
            steps=[app_token, user_token],
            storage=InMemoryTokenStorage()
        )

        # Execute pipeline
        token = pipeline.execute()

        assert token.access_token == 'user-token-456'
        assert len(responses.calls) == 2

Complete Example
----------------

Production Multi-Step Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        TokenFetchPipeline,
        PipelineTokenProvider,
        DjangoCacheTokenStorage,
        ExponentialBackoffRetryStrategy,
        SimpleAuthRetryStrategy
    )
    from requestforge.fetcher import BodyTokenFetcher
    from datetime import timedelta
    import os

    # Step 1: App token
    app_token = BodyTokenFetcher(
        name='app_token',
        base_url=os.getenv('AUTH_URL'),
        endpoint='/v1/app/token',
        method='POST',
        request_data={
            'client_id': os.getenv('CLIENT_ID'),
            'client_secret': os.getenv('CLIENT_SECRET')
        },
        token_field='access_token',
        expires_in_field='expires_in',
        ttl=timedelta(hours=1)
    )

    # Step 2: User token
    class UserTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'app_token' in context:
                headers['X-App-Token'] = context['app_token'].access_token
            return headers

    user_token = UserTokenFetcher(
        name='user_token',
        base_url=os.getenv('AUTH_URL'),
        endpoint='/v1/user/token',
        method='POST',
        request_data={
            'username': os.getenv('USERNAME'),
            'password': os.getenv('PASSWORD')
        },
        token_field='access_token',
        ttl=timedelta(minutes=30),
        depends_on=['app_token']
    )

    # Pipeline
    pipeline = TokenFetchPipeline(
        steps=[app_token, user_token],
        storage=DjangoCacheTokenStorage(
            cache_alias='default',
            key_prefix='production_auth'
        ),
        cache_key_prefix='myapp'
    )

    # Provider
    provider = PipelineTokenProvider(
        pipeline=pipeline,
        service_name='myapp',
        refresh_from_step='user_token'
    )

    # Token manager
    token_manager = TokenManager(provider)

    # Retry strategies
    request_retry = ExponentialBackoffRetryStrategy(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0
    )

    auth_retry = SimpleAuthRetryStrategy(
        max_retries=1,
        delay=0.5
    )

    # HTTP client
    config = (
        HttpClientConfigBuilder()
        .with_base_url(os.getenv('API_URL'))
        .with_timeout(30.0)
        .with_retry_strategy(request_retry)
        .with_token_auth(
            token_manager=token_manager,
            auth_retry_strategy=auth_retry,
            excluded_paths={'/health'}
        )
        .with_logging(log_headers=True)
        .build()
    )

    client = HttpClient(config)

    # Usage
    response = client.get('/user/profile')

See Also
--------

* :doc:`oauth2-flow` - OAuth2 examples
* :doc:`basic-requests` - Basic requests
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`../api-reference/pipelines` - Pipeline API reference
* :doc:`../api-reference/fetcher` - Fetcher API reference
