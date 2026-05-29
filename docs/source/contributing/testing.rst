Testing Guide
=============

This guide covers testing practices and patterns for Request Forge.

Test Structure
--------------

Test Organization
~~~~~~~~~~~~~~~~~

.. code-block:: text

    tests/
    ├── __init__.py
    ├── conftest.py                  # Shared fixtures
    ├── test_client.py               # Client tests
    ├── test_config.py               # Configuration tests
    ├── test_models.py               # Model tests
    ├── test_retry.py                # Retry strategy tests
    ├── test_hooks.py                # Hook tests
    ├── test_token_manager.py        # Token manager tests
    ├── test_pipelines.py            # Pipeline tests
    ├── test_fetcher.py              # Fetcher tests
    ├── test_exceptions.py           # Exception tests
    └── test_utils.py                # Utility tests

Test Markers
~~~~~~~~~~~~

Tests are organized with pytest markers:

.. code-block:: python

    @pytest.mark.unit
    def test_something():
        """Unit test."""
        pass

    @pytest.mark.integration
    def test_integration():
        """Integration test."""
        pass

    @pytest.mark.slow
    def test_slow_operation():
        """Slow test."""
        pass

Run tests by marker:

.. code-block:: bash

    # Run only unit tests
    pytest -m unit

    # Run only integration tests
    pytest -m integration

    # Skip slow tests
    pytest -m "not slow"

Common Fixtures
---------------

Basic Fixtures
~~~~~~~~~~~~~~

.. code-block:: python

    # conftest.py
    import pytest
    from requestforge import HttpClientConfigBuilder, HttpClient

    @pytest.fixture
    def config():
        """Basic HTTP client configuration."""
        return (
            HttpClientConfigBuilder()
            .with_base_url('https://api.example.com')
            .with_timeout(30.0)
            .build()
        )

    @pytest.fixture
    def client(config):
        """HTTP client instance."""
        return HttpClient(config)

    @pytest.fixture
    def mock_token_data():
        """Mock token data."""
        from requestforge.config import TokenData
        from datetime import datetime, timedelta

        return TokenData(
            access_token='test-token-123',
            token_type='Bearer',
            expires_at=datetime.now() + timedelta(hours=1)
        )

responses Fixtures
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    import responses

    @pytest.fixture
    def mock_api():
        """Activate responses mock."""
        with responses.RequestsMock() as rsps:
            yield rsps

    @pytest.fixture
    def mock_success_response(mock_api):
        """Mock successful API response."""
        mock_api.add(
            responses.GET,
            'https://api.example.com/users',
            json={'users': [{'id': 1, 'name': 'John'}]},
            status=200
        )
        return mock_api

Unit Testing
------------

Testing Client
~~~~~~~~~~~~~~

.. code-block:: python

    # tests/test_client.py
    import pytest
    import responses
    from requestforge import HttpClient, HttpClientConfigBuilder

    class TestHttpClient:
        """Test HTTP client functionality."""

        @responses.activate
        def test_get_request(self):
            # Mock response
            responses.add(
                responses.GET,
                'https://api.example.com/users',
                json={'users': [{'id': 1}]},
                status=200
            )

            # Create client
            config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
            client = HttpClient(config)

            # Make request
            response = client.get('/users')

            # Assertions
            assert response.status_code == 200
            assert response.is_success
            assert len(response.json()['users']) == 1

        @responses.activate
        def test_post_request(self):
            responses.add(
                responses.POST,
                'https://api.example.com/users',
                json={'id': 1, 'name': 'John'},
                status=201
            )

            config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
            client = HttpClient(config)

            response = client.post('/users', json_data={'name': 'John'})

            assert response.status_code == 201
            assert response.json()['name'] == 'John'

Testing Retry Logic
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # tests/test_retry.py
    import pytest
    import responses
    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        ExponentialBackoffRetryStrategy,
        MaxRetryException
    )

    class TestRetryStrategies:
        @responses.activate
        def test_retry_on_500(self):
            # First two calls fail, third succeeds
            responses.add(responses.GET, 'https://api.example.com/data', status=500)
            responses.add(responses.GET, 'https://api.example.com/data', status=500)
            responses.add(
                responses.GET,
                'https://api.example.com/data',
                json={'result': 'success'},
                status=200
            )

            strategy = ExponentialBackoffRetryStrategy(
                max_retries=3,
                base_delay=0.01  # Fast for testing
            )

            config = (
                HttpClientConfigBuilder()
                .with_base_url('https://api.example.com')
                .with_retry_strategy(strategy)
                .build()
            )

            client = HttpClient(config)
            response = client.get('/data')

            assert response.status_code == 200
            assert len(responses.calls) == 3

        @responses.activate
        def test_max_retries_exceeded(self):
            # All calls fail
            for _ in range(10):
                responses.add(responses.GET, 'https://api.example.com/data', status=500)

            strategy = ExponentialBackoffRetryStrategy(max_retries=3, base_delay=0.01)
            config = (
                HttpClientConfigBuilder()
                .with_base_url('https://api.example.com')
                .with_retry_strategy(strategy)
                .build()
            )

            client = HttpClient(config)

            with pytest.raises(MaxRetryException) as exc_info:
                client.get('/data')

            assert exc_info.value.attempts == 4  # 1 initial + 3 retries

Testing Hooks
~~~~~~~~~~~~~

.. code-block:: python

    # tests/test_hooks.py
    import pytest
    from unittest.mock import Mock
    from requestforge import HttpClientConfigBuilder, HttpClient
    from requestforge.interfaces import RequestHookInterface

    class TestHooks:
        @responses.activate
        def test_request_hook_called(self):
            # Create mock hook
            mock_hook = Mock(spec=RequestHookInterface)
            mock_hook.before_request = Mock(side_effect=lambda req, ctx: req)

            # Configure client
            responses.add(responses.GET, 'https://api.example.com/test', status=200)

            config = (
                HttpClientConfigBuilder()
                .with_base_url('https://api.example.com')
                .with_request_hook(mock_hook)
                .build()
            )

            client = HttpClient(config)
            client.get('/test')

            # Verify hook was called
            assert mock_hook.before_request.called
            assert mock_hook.before_request.call_count == 1

Testing Token Manager
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # tests/test_token_manager.py
    import pytest
    from unittest.mock import Mock
    from requestforge import TokenManager
    from requestforge.config import TokenData
    from datetime import datetime, timedelta

    class TestTokenManager:
        def test_token_caching(self):
            # Mock provider
            mock_provider = Mock()
            mock_provider.fetch_token.return_value = TokenData(
                access_token='token-123',
                token_type='Bearer',
                expires_at=datetime.now() + timedelta(hours=1)
            )
            mock_provider.service_name = 'test-service'

            # Create manager
            token_manager = TokenManager(mock_provider)

            # First call fetches token
            token1 = token_manager.get_token()
            assert token1.access_token == 'token-123'
            assert mock_provider.fetch_token.call_count == 1

            # Second call uses cache
            token2 = token_manager.get_token()
            assert token2.access_token == 'token-123'
            assert mock_provider.fetch_token.call_count == 1  # Still 1

        def test_force_refresh(self):
            mock_provider = Mock()
            mock_provider.fetch_token.return_value = TokenData(
                access_token='token-123',
                expires_at=datetime.now() + timedelta(hours=1)
            )
            mock_provider.service_name = 'test'

            token_manager = TokenManager(mock_provider)

            # Get token
            token_manager.get_token()

            # Force refresh
            new_token = token_manager.force_refresh()

            # Provider called twice
            assert mock_provider.fetch_token.call_count == 2

Integration Testing
-------------------

Testing with Real Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    from requestforge import create_client

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires live API")
    def test_real_api():
        """Test against real API (skipped by default)."""
        client = create_client('https://api.github.com')
        response = client.get('/users/octocat')

        assert response.is_success
        assert response.json()['login'] == 'octocat'

Testing with Test Server
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    from requestforge import create_client

    class SimpleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

    @pytest.fixture(scope='session')
    def test_server():
        """Start test HTTP server."""
        server = HTTPServer(('localhost', 8888), SimpleHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        yield server
        server.shutdown()

    @pytest.mark.integration
    def test_with_test_server(test_server):
        client = create_client('http://localhost:8888')
        response = client.get('/')

        assert response.status_code == 200
        assert response.json()['status'] == 'ok'

Mocking Strategies
------------------

Using responses
~~~~~~~~~~~~~~~

.. code-block:: python

    import responses
    from requestforge import create_client

    @responses.activate
    def test_api_with_responses():
        # Add mock responses
        responses.add(
            responses.GET,
            'https://api.example.com/users/1',
            json={'id': 1, 'name': 'John'},
            status=200
        )

        responses.add(
            responses.POST,
            'https://api.example.com/users',
            json={'id': 2, 'name': 'Jane'},
            status=201
        )

        # Make requests
        client = create_client('https://api.example.com')

        response1 = client.get('/users/1')
        assert response1.json()['name'] == 'John'

        response2 = client.post('/users', json_data={'name': 'Jane'})
        assert response2.status_code == 201

Using unittest.mock
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from unittest.mock import Mock, patch
    from requestforge import HttpClient, HttpResponse

    def test_with_mock_patch():
        with patch('requestforge.HttpClient.get') as mock_get:
            # Configure mock
            mock_response = Mock(spec=HttpResponse)
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.json.return_value = {'id': 1}
            mock_get.return_value = mock_response

            # Use client
            client = HttpClient(config)
            response = client.get('/users/1')

            # Assertions
            assert response.status_code == 200
            assert response.json()['id'] == 1

Testing Exceptions
------------------

Testing Error Handling
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    import responses
    from requestforge import (
        create_client,
        TimeoutException,
        NotFoundException,
        ServerErrorException
    )

    class TestExceptions:
        @responses.activate
        def test_timeout_exception(self):
            responses.add(
                responses.GET,
                'https://api.example.com/slow',
                body=TimeoutException()
            )

            client = create_client('https://api.example.com')

            with pytest.raises(TimeoutException):
                client.get('/slow', timeout=1.0)

        @responses.activate
        def test_not_found_exception(self):
            responses.add(
                responses.GET,
                'https://api.example.com/users/999',
                status=404
            )

            client = create_client('https://api.example.com')

            with pytest.raises(NotFoundException):
                client.get('/users/999')

        @responses.activate
        def test_server_error_exception(self):
            responses.add(
                responses.GET,
                'https://api.example.com/error',
                status=500
            )

            client = create_client('https://api.example.com')

            with pytest.raises(ServerErrorException) as exc_info:
                client.get('/error')

            assert exc_info.value.status_code == 500

Coverage Requirements
---------------------

Minimum Coverage
~~~~~~~~~~~~~~~~

* Overall coverage: 90%+
* New features: 100% coverage required
* Critical paths: 100% coverage required

Check Coverage
~~~~~~~~~~~~~~

.. code-block:: bash

    # Generate coverage report
    pytest --cov=requestforge --cov-report=term-missing

    # Generate HTML report
    pytest --cov=requestforge --cov-report=html

    # Fail if coverage below threshold
    pytest --cov=requestforge --cov-fail-under=90

Coverage Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: toml

    # pyproject.toml
    [tool.coverage.run]
    source = ["src/requestforge"]
    omit = [
        "*/tests/*",
        "*/__pycache__/*",
    ]

    [tool.coverage.report]
    exclude_lines = [
        "pragma: no cover",
        "def __repr__",
        "raise AssertionError",
        "raise NotImplementedError",
        "if __name__ == .__main__.:",
        "if TYPE_CHECKING:",
        "@abstractmethod",
    ]

Performance Testing
-------------------

Benchmark Tests
~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    import time
    from requestforge import create_client

    @pytest.mark.benchmark
    def test_request_performance():
        """Benchmark request performance."""
        client = create_client('https://httpbin.org')

        start = time.time()
        for _ in range(100):
            client.get('/get')
        duration = time.time() - start

        # Should complete 100 requests in under 10 seconds
        assert duration < 10.0

    @pytest.mark.benchmark
    def test_concurrent_performance():
        """Benchmark concurrent requests."""
        from concurrent.futures import ThreadPoolExecutor

        client = create_client('https://httpbin.org')

        def make_request(i):
            return client.get('/get')

        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(make_request, range(100)))
        duration = time.time() - start

        # Concurrent should be faster
        assert duration < 5.0

Best Practices
--------------

1. **Write Tests First** (TDD)

   .. code-block:: python

       # Write test first
       def test_new_feature():
           result = new_feature()
           assert result == expected

       # Then implement
       def new_feature():
           return expected

2. **Use Descriptive Names**

   .. code-block:: python

       # Good ✅
       def test_retry_strategy_respects_max_retries():
           ...

       # Avoid ❌
       def test_retry():
           ...

3. **Test One Thing**

   .. code-block:: python

       # Good ✅
       def test_get_request_returns_200():
           ...

       def test_get_request_parses_json():
           ...

       # Avoid ❌
       def test_get_request():
           # Tests multiple things
           ...

4. **Use Fixtures**

   .. code-block:: python

       # Good ✅
       @pytest.fixture
       def client():
           return create_client()

       def test_something(client):
           ...

5. **Clean Up Resources**

   .. code-block:: python

       # Good ✅
       @pytest.fixture
       def client():
           client = create_client()
           yield client
           client.close()

See Also
--------

* :doc:`development` - Development guide
* :doc:`code-style` - Code style guide
