Pipelines API Reference
=======================

This page documents the multi-step token fetch pipeline system.

TokenFetchPipeline
------------------

.. class:: TokenFetchPipeline(steps, storage, cache_key_prefix='', validate_dependencies=True)

   Pipeline for multi-step token fetching with caching.

   :param list steps: List of TokenFetcherInterface instances
   :param TokenStorageInterface storage: Token storage for caching
   :param str cache_key_prefix: Prefix for all cache keys
   :param bool validate_dependencies: Validate dependencies on initialization

   **Features:**

   * Per-step caching with configurable TTL
   * Automatic dependency resolution
   * Selective cache invalidation
   * Cascading invalidation (invalidating step clears dependents)
   * Thread-safe execution

   **Example:**

   .. code-block:: python

       from requestforge import TokenFetchPipeline
       from requestforge.fetcher import BodyTokenFetcher
       from requestforge.token_manager import InMemoryTokenStorage
       from datetime import timedelta

       # Step 1: App token
       app_token = BodyTokenFetcher(
           name='app_token',
           base_url='https://auth.example.com',
           endpoint='/v1/app/token',
           method='POST',
           request_data={'client_id': 'app-id', 'client_secret': 'app-secret'},
           token_field='access_token',
           ttl=timedelta(hours=1)
       )

       # Step 2: User token (depends on app_token)
       user_token = BodyTokenFetcher(
           name='user_token',
           base_url='https://auth.example.com',
           endpoint='/v1/user/token',
           method='POST',
           request_data={'username': 'user', 'password': 'pass'},
           token_field='access_token',
           ttl=timedelta(minutes=30),
           depends_on=['app_token']
       )

       # Create pipeline
       pipeline = TokenFetchPipeline(
           steps=[app_token, user_token],
           storage=InMemoryTokenStorage(),
           cache_key_prefix='myapp'
       )

Methods
~~~~~~~

.. method:: TokenFetchPipeline.execute(force_refresh=False)

   Execute pipeline and return final token.

   :param bool force_refresh: If True, ignores cache and fetches all steps
   :returns: TokenData from the last step
   :rtype: TokenData
   :raises AuthenticationException: If any step fails
   :raises ValueError: If dependencies cannot be satisfied

   **Behavior:**

   1. Iterate through steps in order
   2. For each step:
      a. Check cache (unless force_refresh)
      b. If cached and valid, use cached token
      c. If not cached, verify dependencies available
      d. Fetch new token
      e. Cache token with step's TTL
      f. Add to context for dependent steps
   3. Return token from last step

   **Example:**

   .. code-block:: python

       # Execute with cache
       token = pipeline.execute()

       # Force refresh all steps
       token = pipeline.execute(force_refresh=True)

.. method:: TokenFetchPipeline.invalidate_step(step_name)

   Invalidate cached token for a specific step.

   :param str step_name: Name of step to invalidate

   Also invalidates all dependent steps (cascading invalidation).

   **Example:**

   .. code-block:: python

       # Invalidate app_token (also invalidates user_token if it depends on it)
       pipeline.invalidate_step('app_token')

.. method:: TokenFetchPipeline.invalidate_all()

   Invalidate all cached tokens.

   **Example:**

   .. code-block:: python

       pipeline.invalidate_all()

.. method:: TokenFetchPipeline.get_step(name)

   Get a step by name.

   :param str name: Step name
   :returns: Step instance or None
   :rtype: TokenFetcherInterface | None

   **Example:**

   .. code-block:: python

       app_step = pipeline.get_step('app_token')
       print(app_step.ttl)

Properties
~~~~~~~~~~

.. attribute:: TokenFetchPipeline.step_names
   :type: list[str]

   Get list of step names in execution order.

   **Example:**

   .. code-block:: python

       print(pipeline.step_names)  # ['app_token', 'user_token']

PipelineTokenProvider
---------------------

.. class:: PipelineTokenProvider(pipeline, service_name, refresh_from_step=None)

   Token provider that wraps a TokenFetchPipeline.

   Implements :class:`TokenProviderInterface` for use with :class:`TokenManager`.

   :param TokenFetchPipeline pipeline: The token fetch pipeline
   :param str service_name: Service name for this provider
   :param str refresh_from_step: Step to invalidate on refresh (optional)

   **Example:**

   .. code-block:: python

       from requestforge import PipelineTokenProvider, TokenManager

       pipeline = TokenFetchPipeline(...)
       provider = PipelineTokenProvider(
           pipeline=pipeline,
           service_name='myapp',
           refresh_from_step='user_token'  # Only refresh user_token on refresh
       )

       token_manager = TokenManager(provider)

Properties
~~~~~~~~~~

.. attribute:: PipelineTokenProvider.service_name
   :type: str

   Service name for this provider.

.. attribute:: PipelineTokenProvider.pipeline
   :type: TokenFetchPipeline

   Get the underlying pipeline.

   **Example:**

   .. code-block:: python

       pipeline = provider.pipeline
       pipeline.invalidate_step('app_token')

Methods
~~~~~~~

.. method:: PipelineTokenProvider.fetch_token()

   Fetch token by executing pipeline.

   :returns: Token from last pipeline step
   :rtype: TokenData

.. method:: PipelineTokenProvider.refresh_token(current_token)

   Refresh token by re-executing pipeline.

   :param TokenData current_token: Current token (ignored)
   :returns: Fresh token from pipeline
   :rtype: TokenData

   **Behavior:**

   * If ``refresh_from_step`` specified, invalidates that step and dependents
   * Otherwise, invalidates all steps
   * Re-executes pipeline

   **Example:**

   .. code-block:: python

       new_token = provider.refresh_token(current_token)

Complete Examples
-----------------

Two-Step Authentication
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import (
        TokenFetchPipeline,
        PipelineTokenProvider,
        TokenManager,
        HttpClient,
        HttpClientConfigBuilder
    )
    from requestforge.fetcher import BodyTokenFetcher
    from requestforge.token_manager import InMemoryTokenStorage
    from datetime import timedelta

    # Step 1: Application token
    app_token_fetcher = BodyTokenFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/v1/app/token',
        method='POST',
        request_data={
            'grant_type': 'client_credentials',
            'client_id': 'app-id',
            'client_secret': 'app-secret'
        },
        token_field='access_token',
        expires_in_field='expires_in',
        ttl=timedelta(hours=1)
    )

    # Step 2: User token (uses app token)
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
        ttl=timedelta(minutes=30),
        depends_on=['app_token']
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

    # Use client (pipeline executes automatically)
    response = client.get('/user/profile')

Three-Step Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher, HeaderTokenFetcher
    from datetime import timedelta

    # Step 1: Device token (from header)
    device_token = HeaderTokenFetcher(
        name='device_token',
        base_url='https://auth.example.com',
        endpoint='/v1/device/register',
        method='POST',
        request_headers={'X-Device-ID': 'device-123'},
        token_header='X-Device-Token',
        token_type='Device',
        ttl=timedelta(days=30)
    )

    # Step 2: App token (using device token)
    class AppTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'device_token' in context:
                headers['X-Device-Token'] = context['device_token'].access_token
            return headers

    app_token = AppTokenFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/v1/app/token',
        method='POST',
        request_data={'client_id': 'app-id'},
        token_field='access_token',
        ttl=timedelta(hours=1),
        depends_on=['device_token']
    )

    # Step 3: User token (using app token)
    class UserTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'app_token' in context:
                headers['X-App-Token'] = context['app_token'].access_token
            return headers

    user_token = UserTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/v1/user/token',
        method='POST',
        request_data={'username': 'user', 'password': 'pass'},
        token_field='access_token',
        ttl=timedelta(minutes=15),
        depends_on=['app_token']
    )

    # Create pipeline with all three steps
    pipeline = TokenFetchPipeline(
        steps=[device_token, app_token, user_token],
        storage=InMemoryTokenStorage(),
        cache_key_prefix='myapp'
    )

    # Use pipeline
    token = pipeline.execute()
    print(f"Final token: {token.access_token}")

Selective Cache Invalidation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Execute pipeline (all steps cached)
    token = pipeline.execute()

    # Later, invalidate just user token
    pipeline.invalidate_step('user_token')

    # Next execution reuses device_token and app_token from cache
    # Only fetches new user_token
    token = pipeline.execute()

    # Invalidate app_token (cascades to user_token)
    pipeline.invalidate_step('app_token')

    # Next execution reuses device_token from cache
    # Fetches new app_token and user_token
    token = pipeline.execute()

    # Force refresh everything
    token = pipeline.execute(force_refresh=True)

With Django Cache
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import DjangoCacheTokenStorage

    pipeline = TokenFetchPipeline(
        steps=[app_token, user_token],
        storage=DjangoCacheTokenStorage(
            cache_alias='default',
            key_prefix='auth_pipeline'
        ),
        cache_key_prefix='myapp'
    )

    # Tokens now shared across Django instances
    provider = PipelineTokenProvider(pipeline, 'myapp')
    token_manager = TokenManager(provider)

Error Handling
~~~~~~~~~~~~~~

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

Dependency Validation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # This will raise ValueError on initialization
    try:
        pipeline = TokenFetchPipeline(
            steps=[
                user_token,   # Depends on 'app_token'
                app_token     # But app_token comes after!
            ],
            storage=InMemoryTokenStorage(),
            validate_dependencies=True  # Default
        )
    except ValueError as e:
        print(f"Invalid dependencies: {e}")

    # Correct order
    pipeline = TokenFetchPipeline(
        steps=[
            app_token,    # No dependencies
            user_token    # Depends on app_token
        ],
        storage=InMemoryTokenStorage()
    )

Pipeline Execution Flow
-----------------------

.. code-block:: text

    Execute Pipeline:

    ┌─────────────────────────────────────┐
    │  Step 1: device_token               │
    │  ├─ Check cache                     │
    │  ├─ Cache miss → Fetch              │
    │  └─ Cache token (TTL: 30 days)      │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │  Step 2: app_token                  │
    │  ├─ Check cache                     │
    │  ├─ Cache miss → Fetch              │
    │  ├─ Use device_token from context   │
    │  └─ Cache token (TTL: 1 hour)       │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │  Step 3: user_token                 │
    │  ├─ Check cache                     │
    │  ├─ Cache miss → Fetch              │
    │  ├─ Use app_token from context      │
    │  └─ Cache token (TTL: 15 min)       │
    └──────────────┬──────────────────────┘
                   ↓
           Return user_token

    Next Execution (within 15 min):

    ┌─────────────────────────────────────┐
    │  Step 1: device_token               │
    │  └─ Cache hit → Use cached          │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │  Step 2: app_token                  │
    │  └─ Cache hit → Use cached          │
    └──────────────┬──────────────────────┘
                   ↓
    ┌─────────────────────────────────────┐
    │  Step 3: user_token                 │
    │  └─ Cache hit → Use cached          │
    └──────────────┬──────────────────────┘
                   ↓
           Return cached user_token

Best Practices
--------------

1. **Order Steps by Dependencies**

   .. code-block:: python

       # Good ✅
       pipeline = TokenFetchPipeline(
           steps=[step_a, step_b, step_c],  # a → b → c
           storage=storage
       )

2. **Set Appropriate TTL**

   .. code-block:: python

       # Good ✅ - Longer TTL for stable tokens
       device_token = HeaderTokenFetcher(..., ttl=timedelta(days=30))
       app_token = BodyTokenFetcher(..., ttl=timedelta(hours=1))
       user_token = BodyTokenFetcher(..., ttl=timedelta(minutes=15))

3. **Use Selective Refresh**

   .. code-block:: python

       # Good ✅ - Only refresh what's needed
       provider = PipelineTokenProvider(
           pipeline=pipeline,
           service_name='myapp',
           refresh_from_step='user_token'  # Don't refresh device/app
       )

4. **Handle Dependencies in Custom Fetchers**

   .. code-block:: python

       # Good ✅ - Access dependencies from context
       class CustomFetcher(BodyTokenFetcher):
           def _build_request_headers(self, context):
               headers = super()._build_request_headers(context)
               if context and 'previous_step' in context:
                   headers['X-Token'] = context['previous_step'].access_token
               return headers

See Also
--------

* :doc:`fetcher` - Token fetcher implementations
* :doc:`token-manager` - Token manager API
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`../examples/multi-step-auth` - Multi-step auth examples
