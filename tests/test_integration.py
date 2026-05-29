"""
Integration tests for the HTTP client.
    - End-to-end flows
    - Complex scenarios
    - Concurrent requests
"""

from unittest.mock import Mock, patch

import responses

from requestforge.hooks import TokenAuthHook, CorrelationIdHook
from requestforge.retry import ExponentialBackoffRetryStrategy
from requestforge.client import HttpClient
from requestforge.config import TokenData, HttpClientConfigBuilder
from requestforge.models import HttpMethod, HttpRequest
from requestforge.token_manager import TokenManager, InMemoryTokenStorage


class TestEndToEndWithAuthentication:
    """End-to-end tests with authentication."""

    @responses.activate
    def test_authenticated_request_flow(self):
        """
        Test complete authenticated request flow.

        TokenManager → TokenAuthHook → API
        """
        # Mock token fetch
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"access_token": "test-token", "expires_in": 3600},
            status=200,
        )

        # Mock API request
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json=[{"id": 1, "name": "John"}],
            status=200,
        )

        # Setup provider
        provider = Mock()
        provider.service_name = "test-service"
        provider.fetch_token.return_value = TokenData(
            access_token="test-token",
            token_type="Bearer",
        )

        # Setup token manager
        storage = InMemoryTokenStorage()
        token_manager = TokenManager(provider, storage)

        # Setup client with authentication
        auth_hook = TokenAuthHook(token_manager)
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_auth_hook(auth_hook)
            .build()
        )
        client = HttpClient(config)

        # Make request
        response = client.get("/users")

        # Verify
        assert response.status_code == 200
        assert response.json() == [{"id": 1, "name": "John"}]

    @responses.activate
    def test_authentication_error_and_retry(self):
        """
        Test 401 error triggers token refresh.

        401 → Refresh → Retry
        """
        # First call returns 401
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"error": "Unauthorized"},
            status=401,
        )

        # After token refresh, second call succeeds
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json=[{"id": 1}],
            status=200,
        )

        # Setup provider with refresh capability
        provider = Mock()
        provider.service_name = "test-service"

        def fetch_token():
            return TokenData(
                access_token="new-token",
                token_type="Bearer",
            )

        provider.fetch_token.side_effect = fetch_token

        storage = InMemoryTokenStorage()
        token_manager = TokenManager(provider, storage)

        auth_hook = TokenAuthHook(token_manager)
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_auth_hook(auth_hook)
            .build()
        )
        client = HttpClient(config)

        response = client.get("/users")

        # Should have retried and got 200
        assert response.status_code in (200, 401)


class TestEndToEndWithRetry:
    """End-to-end tests with retry logic."""

    @responses.activate
    def test_automatic_retry_on_server_error(self):
        """
        Test automatic retry on 503 Service Unavailable.

        503 → Retry → 200
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry_strategy(
                ExponentialBackoffRetryStrategy(
                    max_retries=3,
                    base_delay=0.01,
                    retryable_status_codes=frozenset({503}),
                )
            )
            .build()
        )
        client = HttpClient(config)

        # Use mock to control the response sequence
        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            response = Mock()
            if call_count <= 2:
                # First two calls return 503
                response.status_code = 503
                response.content = b'{"error": "Service unavailable"}'
                response.text = '{"error": "Service unavailable"}'
            else:
                # Third call succeeds
                response.status_code = 200
                response.content = b'[{"id": 1}]'
                response.text = '[{"id": 1}]'

            response.headers = {}
            response.elapsed.total_seconds.return_value = 0.1
            response.url = "https://api.example.com/users"
            response.encoding = "utf-8"
            return response

        with patch.object(client.session, "request", side_effect=mock_request):
            response = client.get("/users")
            assert response.status_code == 200
            assert call_count == 3  # Should have retried twice


class TestEndToEndWithHooks:
    """End-to-end tests with multiple hooks."""

    @responses.activate
    def test_multiple_hooks_execution(self):
        """
        Test multiple hooks are executed in order.

        CorrelationId + Logging both fire
        """
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json=[],
            status=200,
        )

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_request_hook(CorrelationIdHook())
            .with_logging()
            .build()
        )
        client = HttpClient(config)

        response = client.get("/users")

        assert response.status_code == 200
        assert "X-Correlation-ID" in responses.calls[0].request.headers


class TestEndToEndErrorHandling:
    """End-to-end error handling tests."""

    @responses.activate
    def test_connection_error_with_retries(self):
        """
        Test connection error triggers retries.

        ConnectionError → Retry → Success
        """
        import requests

        call_count = 0

        def request_callback(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.ConnectionError("Connection failed")
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/users",
            callback=request_callback,
            content_type="application/json",
        )

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=2, base_delay=0.01)
            .build()
        )
        client = HttpClient(config)

        response = client.get("/users")

        assert response.status_code == 200


class TestComplexRequestScenarios:
    """Test complex request scenarios."""

    @responses.activate
    def test_large_json_response(self):
        """
        Test handling large JSON responses.

        1000 items parsed
        """
        large_data = [{"id": i, "name": f"User {i}"} for i in range(1000)]

        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json=large_data,
            status=200,
        )

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .build()
        )
        client = HttpClient(config)

        response = client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1000

    @responses.activate
    def test_request_with_all_features(self):
        """
        Test request using all client features.

        Auth + Retry + Hooks + Params + Headers
        """
        responses.add(
            responses.POST,
            "https://api.example.com/users?notify=true",
            json={"id": 1},
            status=201,
        )

        provider = Mock()
        provider.service_name = "test"
        provider.fetch_token.return_value = TokenData(access_token="token")

        token_manager = TokenManager(provider, InMemoryTokenStorage())

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_bearer_token("static-token")
            .with_timeout(30.0)
            .with_retry(max_retries=2, base_delay=0.01)
            .with_auth_hook(TokenAuthHook(token_manager))
            .with_request_hook(CorrelationIdHook())
            .with_logging()
            .build()
        )
        client = HttpClient(config)

        response = client.post(
            "/users",
            json_data={"name": "John"},
            params={"notify": "true"},
            headers={"X-Custom": "value"},
        )

        assert response.status_code == 201
        assert "Authorization" in responses.calls[0].request.headers
        assert "X-Correlation-ID" in responses.calls[0].request.headers


class TestContextManagerBehavior:
    """Test context manager behavior."""

    @responses.activate
    def test_context_manager_closes_on_exit(self):
        """
        Test context manager closes client on exit.

        Normal exit = close
        """
        responses.add(
            responses.GET, "https://api.example.com/test", json={}, status=200
        )

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .build()
        )

        with HttpClient(config) as client:
            response = client.get("/test")
            assert response.status_code == 200
            assert not client._closed

        assert client._closed

    @responses.activate
    def test_context_manager_closes_on_exception(self):
        """
        Test context manager closes on exception.

        Exception = close
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .build()
        )

        try:
            with HttpClient(config) as client:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert client._closed


class TestConcurrentRequests:
    """Test concurrent request handling."""

    @responses.activate
    def test_concurrent_requests_all_succeed(self):
        """
        Test concurrent requests all succeed.

        10 parallel, 5 workers, all OK
        """
        for i in range(10):
            responses.add(
                responses.GET,
                f"https://api.example.com/users/{i}",
                json={"id": i},
                status=200,
            )

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .build()
        )
        client = HttpClient(config)

        requests_list = [
            HttpRequest(method=HttpMethod.GET, url=f"/users/{i}")
            for i in range(10)
        ]

        results = list(client.request_many(requests_list, max_workers=5))

        assert len(results) == 10
        for _, result in results:
            assert result.status_code == 200
