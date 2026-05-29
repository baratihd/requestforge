Token Fetcher API Reference
============================

This page documents token fetcher implementations for multi-step authentication.

TokenFetcherInterface
---------------------

.. class:: TokenFetcherInterface

   Abstract interface for a single token fetch operation.

   Token fetchers are used in multi-step authentication pipelines where multiple tokens
   must be obtained in sequence, with later steps potentially depending on earlier ones.

Properties
~~~~~~~~~~

.. attribute:: name
   :type: str

   Unique name for this fetcher/step.

.. attribute:: depends_on
   :type: list[str]

   Names of fetcher steps this depends on.

   Default: Empty list (no dependencies)

.. attribute:: ttl
   :type: timedelta | None

   Time-to-live for cached token.

   Default: None (use token's expires_at)

Methods
~~~~~~~

.. py:method:: TokenFetcherInterface.fetch(context=None)

   Fetch token for this step.

   :param dict context: Dictionary mapping step names to TokenData from previous steps
   :returns: Fetched token data
   :rtype: TokenData
   :raises AuthenticationException: If token fetch fails

   **Example:**

   .. code-block:: python

       # No dependencies
       token = fetcher.fetch()

       # With dependencies
       context = {'app_token': app_token_data}
       user_token = fetcher.fetch(context)

.. method:: on_fetch_error(error, context=None)

   Called when fetch fails.

   :param Exception error: The exception that occurred
   :param dict context: Token context (optional)

   Default implementation logs the error.

HttpTokenFetcher
----------------

.. class:: HttpTokenFetcher(base_url, timeout=30.0, verify_ssl=True, headers=None)

   Base class for HTTP-based token fetchers.

   Provides common HTTP client setup and configuration.
   Subclasses implement the specific fetch logic.

   :param str base_url: Base URL for token endpoint
   :param float timeout: Request timeout in seconds
   :param bool verify_ssl: Whether to verify SSL certificates
   :param dict headers: Default headers for requests

   **Note:** This is an abstract base class. Use concrete implementations like
   :class:`BodyTokenFetcher` or :class:`HeaderTokenFetcher`.

Methods
~~~~~~~

.. method:: close()

   Close HTTP client and release resources.

   **Example:**

   .. code-block:: python

       fetcher = BodyTokenFetcher(...)
       try:
           token = fetcher.fetch()
       finally:
           fetcher.close()

HeaderTokenFetcher
------------------

.. class:: HeaderTokenFetcher(name, base_url, endpoint, method='POST', request_headers=None, request_data=None, token_header='Authorization', token_type='Bearer', ttl=None, timeout=30.0, verify_ssl=True, depends_on=None)

   Token fetcher that extracts token from response headers.

   Useful for APIs that return tokens in headers rather than body.

   :param str name: Step name
   :param str base_url: Base URL for API
   :param str endpoint: Token endpoint path
   :param str method: HTTP method (GET or POST)
   :param dict request_headers: Headers to send with request
   :param dict request_data: Data/params to send with request
   :param str token_header: Response header containing token
   :param str token_type: Token type for TokenData
   :param timedelta ttl: Time-to-live for cached token
   :param float timeout: Request timeout
   :param bool verify_ssl: Whether to verify SSL
   :param list depends_on: List of dependency step names

   **Example:**

   .. code-block:: python

       from requestforge.fetcher import HeaderTokenFetcher
       from datetime import timedelta

       fetcher = HeaderTokenFetcher(
           name='app_token',
           base_url='https://auth.example.com',
           endpoint='/auth/token',
           method='POST',
           request_headers={
               'X-App-Name': 'my-app',
               'X-App-Secret': 'secret123'
           },
           token_header='X-Auth-Token',
           token_type='Bearer',
           ttl=timedelta(hours=1)
       )

       token = fetcher.fetch()
       print(token.access_token)

Properties
~~~~~~~~~~

.. attribute:: HeaderTokenFetcher.name
   :type: str

   Step name.

.. attribute:: HeaderTokenFetcher.depends_on
   :type: list[str]

   Dependency step names.

.. attribute:: HeaderTokenFetcher.ttl
   :type: timedelta | None

   Cache TTL.

Methods
~~~~~~~

.. py:method:: HeaderTokenFetcher.fetch(context=None)

   Fetch token from response header.

   :param dict context: Token context from previous steps
   :returns: Token data
   :rtype: TokenData
   :raises AuthenticationException: If request fails or header not found

Custom Headers Example
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HeaderTokenFetcher

    class CustomHeaderFetcher(HeaderTokenFetcher):
        """Custom fetcher with dynamic headers."""

        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)

            # Add token from previous step
            if context and 'device_token' in context:
                headers['X-Device-Token'] = context['device_token'].access_token

            return headers

    fetcher = CustomHeaderFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/app/token',
        method='POST',
        token_header='X-App-Token',
        depends_on=['device_token']
    )

BodyTokenFetcher
----------------

.. class:: BodyTokenFetcher(name, base_url, endpoint, method='POST', request_headers=None, request_data=None, content_type='form', token_field='access_token', token_type_field='token_type', expires_in_field='expires_in', refresh_token_field='refresh_token', default_token_type='Bearer', ttl=None, timeout=30.0, verify_ssl=True, depends_on=None)

   Token fetcher that extracts token from response body (JSON).

   Useful for standard OAuth2 and similar token endpoints.

   :param str name: Step name
   :param str base_url: Base URL for API
   :param str endpoint: Token endpoint path
   :param str method: HTTP method
   :param dict request_headers: Headers to send
   :param dict request_data: Request body data
   :param str content_type: 'form' for form-encoded, 'json' for JSON
   :param str token_field: JSON field containing access token
   :param str token_type_field: JSON field containing token type
   :param str expires_in_field: JSON field containing expires_in seconds
   :param str refresh_token_field: JSON field containing refresh token
   :param str default_token_type: Default token type if not in response
   :param timedelta ttl: Override TTL for cached token
   :param float timeout: Request timeout
   :param bool verify_ssl: Whether to verify SSL
   :param list depends_on: List of dependency step names

   **Example:**

   .. code-block:: python

       from requestforge.fetcher import BodyTokenFetcher
       from datetime import timedelta

       fetcher = BodyTokenFetcher(
           name='access_token',
           base_url='https://auth.example.com',
           endpoint='/oauth/token',
           method='POST',
           request_data={
               'grant_type': 'client_credentials',
               'client_id': 'my-client',
               'client_secret': 'my-secret',
           },
           content_type='form',  # or 'json'
           token_field='access_token',
           expires_in_field='expires_in',
           ttl=timedelta(minutes=30)
       )

       token = fetcher.fetch()

Properties
~~~~~~~~~~

.. attribute:: BodyTokenFetcher.name
   :type: str

   Step name.

.. attribute:: BodyTokenFetcher.depends_on
   :type: list[str]

   Dependency step names.

.. attribute:: BodyTokenFetcher.ttl
   :type: timedelta | None

   Cache TTL.

Methods
~~~~~~~

.. py:method:: BodyTokenFetcher.fetch(context=None)

   Fetch token from response body.

   :param dict context: Token context from previous steps
   :returns: Token data
   :rtype: TokenData
   :raises AuthenticationException: If request fails or field not found

Content Types
~~~~~~~~~~~~~

**Form-encoded (default):**

.. code-block:: python

    fetcher = BodyTokenFetcher(
        name='token',
        base_url='https://auth.example.com',
        endpoint='/oauth/token',
        content_type='form',  # application/x-www-form-urlencoded
        request_data={
            'grant_type': 'client_credentials',
            'client_id': 'id',
            'client_secret': 'secret'
        }
    )

**JSON:**

.. code-block:: python

    fetcher = BodyTokenFetcher(
        name='token',
        base_url='https://auth.example.com',
        endpoint='/api/token',
        content_type='json',  # application/json
        request_data={
            'username': 'user',
            'password': 'pass'
        }
    )

Custom Field Names
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # API returns non-standard field names
    fetcher = BodyTokenFetcher(
        name='token',
        base_url='https://auth.example.com',
        endpoint='/auth',
        token_field='auth_token',        # Instead of 'access_token'
        token_type_field='type',          # Instead of 'token_type'
        expires_in_field='ttl',           # Instead of 'expires_in'
        refresh_token_field='refresh',    # Instead of 'refresh_token'
        default_token_type='Custom'
    )

Custom Data Building
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher

    class UserTokenFetcher(BodyTokenFetcher):
        """Custom fetcher that uses app token in request."""

        def _build_request_data(self, context):
            data = super()._build_request_data(context)

            # Add app token to request data
            if context and 'app_token' in context:
                data['app_token'] = context['app_token'].access_token

            return data

    fetcher = UserTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/user/token',
        request_data={
            'username': 'user',
            'password': 'pass'
        },
        depends_on=['app_token']
    )

Complete Examples
-----------------

Simple OAuth2 Flow
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher
    from datetime import timedelta

    # Single-step OAuth2
    fetcher = BodyTokenFetcher(
        name='oauth_token',
        base_url='https://auth.example.com',
        endpoint='/oauth/token',
        method='POST',
        request_data={
            'grant_type': 'client_credentials',
            'client_id': 'your-client-id',
            'client_secret': 'your-client-secret',
            'scope': 'read write'
        },
        content_type='form',
        token_field='access_token',
        expires_in_field='expires_in',
        refresh_token_field='refresh_token'
    )

    # Fetch token
    token = fetcher.fetch()
    print(f"Token: {token.access_token}")
    print(f"Expires: {token.expires_at}")
    print(f"Refresh: {token.refresh_token}")

Two-Step Flow
~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher
    from datetime import timedelta

    # Step 1: App token
    app_token_fetcher = BodyTokenFetcher(
        name='app_token',
        base_url='https://auth.example.com',
        endpoint='/v1/app/token',
        method='POST',
        request_data={
            'client_id': 'app-id',
            'client_secret': 'app-secret'
        },
        token_field='token',
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

    # Execute steps
    app_token = app_token_fetcher.fetch()

    context = {'app_token': app_token}
    user_token = user_token_fetcher.fetch(context)

Header-Based Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HeaderTokenFetcher
    from datetime import timedelta

    fetcher = HeaderTokenFetcher(
        name='session_token',
        base_url='https://api.example.com',
        endpoint='/auth/session',
        method='POST',
        request_headers={
            'X-API-Key': 'your-api-key',
            'X-Device-ID': 'device-123'
        },
        request_data={
            'username': 'user',
            'password': 'pass'
        },
        token_header='X-Session-Token',
        token_type='Session',
        ttl=timedelta(hours=24)
    )

    token = fetcher.fetch()

Mixed Header and Body Tokens
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    # Step 2: User token from body (using device token)
    class UserTokenFetcher(BodyTokenFetcher):
        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)
            if context and 'device_token' in context:
                headers['X-Device-Token'] = context['device_token'].access_token
            return headers

    user_token = UserTokenFetcher(
        name='user_token',
        base_url='https://auth.example.com',
        endpoint='/user/auth',
        method='POST',
        request_data={'username': 'user', 'password': 'pass'},
        token_field='access_token',
        ttl=timedelta(minutes=15),
        depends_on=['device_token']
    )

Custom Token Fetcher
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.fetcher import HttpTokenFetcher
    from requestforge.config import TokenData
    from requestforge.models import HttpMethod
    from datetime import datetime, timedelta

    class CustomTokenFetcher(HttpTokenFetcher):
        """Custom token fetcher with proprietary logic."""

        def __init__(self, name, api_key, **kwargs):
            super().__init__(**kwargs)
            self._name = name
            self._api_key = api_key
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
            # Custom fetch logic
            response = self._make_request(
                method=HttpMethod.POST,
                endpoint='/custom/auth',
                headers={'X-API-Key': self._api_key},
                json_data={'action': 'authenticate'}
            )

            if not response.is_success:
                raise AuthenticationException(
                    f'Custom auth failed: {response.status_code}',
                    service_name=self._name
                )

            data = response.json()

            # Build TokenData with custom logic
            return TokenData(
                access_token=data['custom_token'],
                token_type='Custom',
                expires_at=datetime.now() + timedelta(seconds=data['ttl']),
                extra={'session_id': data['session']}
            )

    # Usage
    fetcher = CustomTokenFetcher(
        name='custom_token',
        api_key='your-key',
        base_url='https://api.example.com',
        timeout=30.0
    )

Error Handling
--------------

.. code-block:: python

    from requestforge import AuthenticationException
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

    fetcher = RobustTokenFetcher(
        name='robust_token',
        base_url='https://auth.example.com',
        endpoint='/token',
        request_data={'client_id': 'id'}
    )

    try:
        token = fetcher.fetch()
    except AuthenticationException as e:
        print(f"Fetch failed: {e.message}")
        print(f"Service: {e.service_name}")

Dependency Injection
--------------------

.. code-block:: python

    from requestforge.fetcher import BodyTokenFetcher

    class DependentTokenFetcher(BodyTokenFetcher):
        """Fetcher that injects dependencies."""

        def _build_request_headers(self, context):
            headers = super()._build_request_headers(context)

            # Inject multiple dependencies
            if context:
                if 'device_token' in context:
                    headers['X-Device'] = context['device_token'].access_token

                if 'app_token' in context:
                    headers['X-App'] = context['app_token'].access_token

            return headers

        def _build_request_data(self, context):
            data = super()._build_request_data(context)

            # Add token to request body
            if context and 'session_token' in context:
                data['session'] = context['session_token'].access_token

            return data

    fetcher = DependentTokenFetcher(
        name='final_token',
        base_url='https://auth.example.com',
        endpoint='/final/token',
        request_data={'username': 'user'},
        depends_on=['device_token', 'app_token', 'session_token']
    )

Testing Fetchers
----------------

.. code-block:: python

    import pytest
    import responses
    from requestforge.fetcher import BodyTokenFetcher
    from requestforge import AuthenticationException

    @responses.activate
    def test_token_fetch_success():
        # Mock token endpoint
        responses.add(
            responses.POST,
            'https://auth.example.com/oauth/token',
            json={
                'access_token': 'test-token-123',
                'token_type': 'Bearer',
                'expires_in': 3600
            },
            status=200
        )

        fetcher = BodyTokenFetcher(
            name='test_token',
            base_url='https://auth.example.com',
            endpoint='/oauth/token',
            request_data={'client_id': 'test'}
        )

        token = fetcher.fetch()

        assert token.access_token == 'test-token-123'
        assert token.token_type == 'Bearer'
        assert token.expires_at is not None

    @responses.activate
    def test_token_fetch_failure():
        # Mock failed response
        responses.add(
            responses.POST,
            'https://auth.example.com/oauth/token',
            json={'error': 'invalid_client'},
            status=401
        )

        fetcher = BodyTokenFetcher(
            name='test_token',
            base_url='https://auth.example.com',
            endpoint='/oauth/token',
            request_data={'client_id': 'test'}
        )

        with pytest.raises(AuthenticationException) as exc_info:
            fetcher.fetch()

        assert 'Token request failed' in str(exc_info.value)

Best Practices
--------------

1. **Set Appropriate TTL**

   .. code-block:: python

       # Good ✅ - Matches token lifetime
       fetcher = BodyTokenFetcher(
           name='token',
           base_url='...',
           endpoint='...',
           ttl=timedelta(hours=1)  # Matches actual token expiry
       )

2. **Handle Dependencies in Headers**

   .. code-block:: python

       # Good ✅ - Override _build_request_headers
       class MyFetcher(BodyTokenFetcher):
           def _build_request_headers(self, context):
               headers = super()._build_request_headers(context)
               if context and 'prev_token' in context:
                   headers['Authorization'] = f"Bearer {context['prev_token'].access_token}"
               return headers

3. **Validate Context**

   .. code-block:: python

       # Good ✅ - Check dependencies exist
       def fetch(self, context=None):
           if self.depends_on and not context:
               raise ValueError(f"{self.name} requires context")

           for dep in self.depends_on:
               if not context or dep not in context:
                   raise ValueError(f"Missing dependency: {dep}")

           return super().fetch(context)

4. **Clean Up Resources**

   .. code-block:: python

       # Good ✅ - Close fetcher when done
       fetcher = BodyTokenFetcher(...)
       try:
           token = fetcher.fetch()
       finally:
           fetcher.close()

See Also
--------

* :doc:`pipelines` - Token fetch pipelines
* :doc:`token-manager` - Token management
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`../examples/multi-step-auth` - Multi-step examples
