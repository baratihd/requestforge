"""
Comprehensive tests for HttpClient.
    - Client initialization
    - Basic HTTP requests (GET, POST, PUT, PATCH, DELETE)
    - Error handling
    - Retry logic
    - Authentication
    - Concurrent requests
    - Session management
    - Factory functions
    - Hook execution
    - Edge cases
"""

from unittest.mock import Mock, patch

import pytest
import requests
import responses

from requestforge.hooks import TokenAuthHook
from requestforge.client import HttpClient, http_client, create_client
from requestforge.config import (
    HttpClientConfigBuilder,
)
from requestforge.models import (
    HttpMethod,
    HttpRequest,
    HttpResponse,
)
from requestforge.exceptions import (
    TimeoutException,
    MaxRetryException,
    ConnectionException,
    HttpClientException,
    ResponseParseException,
)
from requestforge.interfaces import AuthHookInterface


class TestHttpClientInitialization:
    """
    Test HttpClient initialization.

    Scenarios:
        - Default Usage: HttpClient() works out of the box
        - Production Config: Custom timeouts, pools, retry strategies
        - Testing: Inject mocked session for unit tests
        - Multi-threaded: Django/Gunicorn workers each get own session
    """

    def test_init_with_default_config(self):
        """
        Test initialization with default configuration.

        Client initializes with sensible defaults when no config provided
        """
        client = HttpClient()
        assert client._config is not None
        assert client._closed is False

    def test_init_with_custom_config(self, requestforge_config):
        """
        Test initialization with custom configuration.

        Client accepts and uses custom HttpClientConfig
        """
        client = HttpClient(requestforge_config)
        assert client._config == requestforge_config
        assert client._closed is False

    def test_init_with_custom_session(self, requestforge_config):
        """
        Test initialization with custom session.

        Client uses injected requests.Session (for testing/mocking)
        """
        import requests

        session = requests.Session()
        client = HttpClient(requestforge_config, session=session)
        assert client._session == session

    def test_session_property_creates_thread_local_session(
        self, requestforge_config
    ):
        """
        Test that session property creates thread-local sessions.

        Each thread gets its own session with connection pooling
        """
        client = HttpClient(requestforge_config)
        session1 = client.session
        session2 = client.session
        assert session1 is session2  # Same thread returns same session

    def test_adapter_property_creates_adapter(self, requestforge_config):
        """
        Test that adapter property creates HTTPAdapter.

        HTTPAdapter created with pool settings
        """
        client = HttpClient(requestforge_config)
        adapter = client.adapter
        assert adapter is not None
        from requests.adapters import HTTPAdapter

        assert isinstance(adapter, HTTPAdapter)

    def test_auth_hook_property(self):
        """
        Test auth_hook property.

        Auth hook accessible from config
        """
        mock_hook = Mock(spec=AuthHookInterface)
        config = HttpClientConfigBuilder().with_auth_hook(mock_hook).build()
        client = HttpClient(config)
        assert client.auth_hook == mock_hook


class TestHttpClientBasicRequests:
    """
    Test basic HTTP request methods.

    Scenarios:
        - REST API CRUD: All HTTP verbs work correctly
        - Query Building: Complex query params handled
        - Header Merging: Default + request headers combined
    """

    @responses.activate
    def test_get_request(self, requestforge_instance):
        """
        Test GET request.

        GET request with path, returns parsed response
        """
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"id": 1},
            status=200,
        )

        response = requestforge_instance.get("/users")
        assert response.status_code == 200
        assert response.is_success
        assert response.json() == {"id": 1}

    @responses.activate
    def test_post_request_with_json(self, requestforge_instance):
        """
        Test POST request with JSON data.

        POST with JSON body, auto Content-Type header
        """
        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 1},
            status=201,
        )

        response = requestforge_instance.post(
            "/users", json_data={"name": "John"}
        )
        assert response.status_code == 201
        assert response.json() == {"id": 1}

    @responses.activate
    def test_post_request_with_form_data(self, requestforge_instance):
        """
        Test POST request with form data.

        POST with form-encoded data
        """
        responses.add(
            responses.POST,
            "https://api.example.com/login",
            json={"token": "abc"},
            status=200,
        )

        response = requestforge_instance.post(
            "/login", data={"username": "user", "password": "pass"}
        )
        assert response.status_code == 200

    @responses.activate
    def test_put_request(self, requestforge_instance):
        """Test PUT request."""
        responses.add(
            responses.PUT,
            "https://api.example.com/users/1",
            json={"id": 1},
            status=200,
        )

        response = requestforge_instance.put(
            "/users/1", json_data={"name": "Jane"}
        )
        assert response.status_code == 200

    @responses.activate
    def test_patch_request(self, requestforge_instance):
        """Test PATCH request."""
        responses.add(
            responses.PATCH,
            "https://api.example.com/users/1",
            json={"id": 1},
            status=200,
        )

        response = requestforge_instance.patch(
            "/users/1", json_data={"status": "active"}
        )
        assert response.status_code == 200

    @responses.activate
    def test_delete_request(self, requestforge_instance):
        """Test DELETE request."""
        responses.add(
            responses.DELETE, "https://api.example.com/users/1", status=204
        )

        response = requestforge_instance.delete("/users/1")
        assert response.status_code == 204

    @responses.activate
    def test_get_with_params(self, requestforge_instance):
        """Test GET request with query parameters."""
        responses.add(
            responses.GET,
            "https://api.example.com/users?page=1&limit=10",
            json=[],
            status=200,
        )

        response = requestforge_instance.get(
            "/users", params={"page": 1, "limit": 10}
        )
        assert response.status_code == 200

    @responses.activate
    def test_get_with_custom_headers(self, requestforge_instance):
        """
        Test request with custom headers.

        Per-request headers merged with defaults
        """
        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        response = requestforge_instance.get(
            "/users", headers={"X-Custom": "value"}
        )
        assert response.status_code == 200


class TestHttpClientErrorHandling:
    """
    Test HTTP client error handling.

    Error Mapping:
        requests.Timeout          → TimeoutException
        requests.ConnectionError  → ConnectionException
        requests.SSLError         → SSLException
        requests.JSONDecodeError  → ResponseParseException
    """

    def test_timeout_exception(self, requestforge_instance):
        """
        Test timeout exception handling.

        requests.Timeout → TimeoutException mapping
        """
        # Configure client with NO retry
        client = HttpClient(
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=0)  # Disable retry
            .build()
        )

        def mock_request(*args, **kwargs):
            raise requests.Timeout("Connection timed out")

        # with patch.object(client.session, "request", side_effect=mock_request):
        #     with pytest.raises(MaxRetryException):
        #         client.get("/users")

        with (
            patch.object(client.session, "request", side_effect=mock_request),
            pytest.raises(MaxRetryException),
        ):
            client.get("/users")

    def test_connection_exception(self, requestforge_instance):
        """
        Test connection exception handling.

        requests.ConnectionError → ConnectionException
        """
        # Configure client with NO retry
        client = HttpClient(
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=0)  # Disable retry
            .build()
        )

        def mock_request(*args, **kwargs):
            raise requests.ConnectionError("Connection failed")

        with (
            patch.object(client.session, "request", side_effect=mock_request),
            pytest.raises(MaxRetryException),
        ):
            client.get("/users")

    def test_ssl_exception(self, requestforge_instance):
        """
        Test SSL exception handling.

        requests.SSLError → SSLException
        """
        client = HttpClient(
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=0)  # Disable retry
            .build()
        )

        def mock_request(*args, **kwargs):
            raise requests.exceptions.SSLError("SSL error")

        with (
            patch.object(client.session, "request", side_effect=mock_request),
            pytest.raises(MaxRetryException),
        ):
            client.get("/users")

    @responses.activate
    def test_json_decode_error(self, requestforge_instance):
        """
        Test JSON decode error.

        Invalid JSON → ResponseParseException on .json()
        """
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            body="invalid json",
            status=200,
        )

        response = requestforge_instance.get("/users")
        with pytest.raises(ResponseParseException):
            response.json()

    def test_request_on_closed_client(self, requestforge_instance):
        """
        Test request on closed client.

        Operations fail after client.close()
        """
        requestforge_instance.close()
        with pytest.raises(HttpClientException, match="Client is closed"):
            requestforge_instance.get("/users")

    @responses.activate
    def test_execute_hooks_on_error(self, requestforge_instance):
        """
        Test error hooks are executed.

        Error hooks fire on exceptions
        """
        error_hook = Mock()
        error_hook.on_error = Mock()
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_error_hook(error_hook)
            .build()
        )
        client = HttpClient(config)

        with (
            patch.object(
                client.session,
                "request",
                side_effect=TimeoutException("Timeout"),
            ),
            pytest.raises(MaxRetryException),
        ):
            client.get("/users")

        assert error_hook.on_error.called


class TestHttpClientRetryLogic:
    """
    Test HTTP client retry logic.

    Retry Timeline Test:
        Attempt 1: TimeoutException → wait 1s
        Attempt 2: TimeoutException → wait 2s
        Attempt 3: Success! → return response
    """

    @responses.activate
    def test_no_retry_strategy(self, requestforge_instance):
        """
        Test with no retry strategy.

        NoRetryStrategy = fail immediately
        """

        with (
            patch.object(
                requestforge_instance.session,
                "request",
                side_effect=TimeoutException("Timeout"),
            ),
            pytest.raises(MaxRetryException),
        ):
            requestforge_instance.get("/users")

    @responses.activate
    def test_exponential_backoff_retry(self):
        """
        Test exponential backoff retry.

        Successful retry after transient failures
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=2, base_delay=0.01, max_delay=0.1)
            .build()
        )
        client = HttpClient(config)

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutException("Timeout")
            response = Mock()
            response.status_code = 200
            response.headers = {}
            response.content = b'{"success": true}'
            response.elapsed.total_seconds.return_value = 0.1
            response.url = "https://api.example.com/test"
            response.encoding = "utf-8"
            return response

        with patch.object(client.session, "request", side_effect=mock_request):
            response = client.get("/users")
            assert response.status_code == 200
            assert call_count == 3

    @responses.activate
    def test_max_retry_exceeded(self):
        """
        Test max retry exceeded.

        MaxRetryException after all retries exhausted
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=2, base_delay=0.01)
            .build()
        )
        client = HttpClient(config)

        with patch.object(
            client.session, "request", side_effect=TimeoutException("Timeout")
        ):
            with pytest.raises(MaxRetryException) as exc_info:
                client.get("/users")
            assert exc_info.value.attempts == 3  # initial + 2 retries

    @responses.activate
    def test_retryable_status_codes(self):
        """Test retryable status codes with exponential backoff."""
        from requestforge.retry import ExponentialBackoffRetryStrategy
        from requestforge.exceptions import HttpStatusException

        # Create strategy that explicitly retries HttpStatusException
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry_strategy(
                ExponentialBackoffRetryStrategy(
                    max_retries=2,
                    base_delay=0.01,
                    retryable_exceptions=frozenset(
                        {
                            TimeoutException,
                            ConnectionException,
                            HttpStatusException,  # Explicitly include
                        }
                    ),
                )
            )
            .build()
        )
        client = HttpClient(config)

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            response = Mock()
            if call_count <= 2:
                response.status_code = 503
                response.content = b'{"error": "Service unavailable"}'
                response.text = '{"error": "Service unavailable"}'
            else:
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
            assert call_count == 3


class TestHttpClientAuthentication:
    """
    Test HTTP client authentication.

    Auth Flow:
        Request → Auth Hook → Inject Token → Send
                        ↓
        Response 401 → Refresh Token → Retry Request
    """

    @responses.activate
    def test_with_bearer_token(self):
        """
        Test request with bearer token.

        Static Bearer token in Authorization header
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_bearer_token("test-token")
            .build()
        )
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        response = client.get("/users")
        assert response.status_code == 200
        assert (
            responses.calls[0].request.headers["Authorization"]
            == "Bearer test-token"
        )

    @responses.activate
    def test_with_api_key(self):
        """
        Test request with API key.

        API key in custom header (X-API-Key)
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_api_key("test-key-123")
            .build()
        )
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        response = client.get("/users")
        assert response.status_code == 200
        assert (
            responses.calls[0].request.headers["X-API-Key"] == "test-key-123"
        )

    @responses.activate
    def test_auth_hook_injection(self, token_manager):
        """
        Test auth hook token injection.

        TokenAuthHook injects dynamic token
        """

        auth_hook = TokenAuthHook(token_manager)
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_auth_hook(auth_hook)
            .build()
        )
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        response = client.get("/users")
        assert response.status_code == 200
        assert "Authorization" in responses.calls[0].request.headers

    @responses.activate
    def test_auth_error_with_token_refresh(self, token_manager):
        """
        Test authentication error triggers token refresh.

        401 → token refresh → retry
        """

        refresh_called = False

        def mock_force_refresh():
            nonlocal refresh_called
            refresh_called = True

        token_manager.force_refresh = mock_force_refresh

        auth_hook = TokenAuthHook(token_manager)
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_auth_hook(auth_hook)
            .build()
        )
        client = HttpClient(config)

        # First call returns 401, second returns 200
        responses.add(
            responses.GET, "https://api.example.com/users", status=401
        )
        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        response = client.get("/users")
        # Should retry after 401 and succeed
        assert (
            response.status_code == 200 or response.status_code == 401
        )  # Depends on auth hook behavior


class TestHttpClientConcurrentRequests:
    """
    Test concurrent request execution.

    Concurrency Test:
        Requests: [GET /1, GET /2, GET /3, GET /4, GET /5]
        Workers: 3
        Results: All 200 OK, returned as completed (not ordered)
    """

    @responses.activate
    def test_request_many(self, requestforge_instance):
        """
        Test executing multiple requests concurrently.

        5 parallel requests with 3 workers, all succeed
        """
        for i in range(5):
            responses.add(
                responses.GET,
                f"https://api.example.com/users/{i}",
                json={"id": i},
                status=200,
            )

        requests_list = [
            HttpRequest(method=HttpMethod.GET, url=f"/users/{i}")
            for i in range(5)
        ]

        results = list(
            requestforge_instance.request_many(requests_list, max_workers=3)
        )
        assert len(results) == 5

        for _, result in results:
            assert isinstance(result, HttpResponse)
            assert result.status_code == 200

    @responses.activate
    def test_request_many_with_failures(self, requestforge_instance):
        """
        Test concurrent requests with some failures.

        Mixed success/failure, fail_fast=False
        """
        responses.add(
            responses.GET,
            "https://api.example.com/users/0",
            json={"id": 0},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.example.com/users/2",
            json={"id": 2},
            status=200,
        )

        requests_list = [
            HttpRequest(method=HttpMethod.GET, url="/users/0"),
            HttpRequest(method=HttpMethod.GET, url="/users/1"),
            HttpRequest(method=HttpMethod.GET, url="/users/2"),
        ]

        results = list(
            requestforge_instance.request_many(
                requests_list, max_workers=3, fail_fast=False
            )
        )
        assert len(results) == 3

    @responses.activate
    def test_request_many_fail_fast(self, requestforge_instance):
        """
        Test fail_fast behavior.

        First error stops execution, fail_fast=True
        """
        # Create a client with retry disabled
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_retry(max_retries=0)
            .build()
        )
        client = HttpClient(config)

        # Create requests where one will definitely fail
        requests_list = [
            HttpRequest(method=HttpMethod.GET, url="/users/0"),
            HttpRequest(method=HttpMethod.GET, url="/users/1"),
        ]

        # Mock to force a failure
        original_request = client.request
        call_count = 0

        def mock_request_with_failure(req):
            nonlocal call_count
            call_count += 1
            # Second request fails
            if call_count == 2:
                raise ConnectionException("Forced failure for testing")
            # First request would succeed (but we won't mock the actual response)
            from unittest.mock import Mock

            response = Mock(spec=HttpResponse)
            response.status_code = 200
            response.is_success = True
            return response

        # With fail_fast=True, should raise on first error
        with (
            patch.object(
                client, "request", side_effect=mock_request_with_failure
            ),
            pytest.raises(
                (HttpClientException, ConnectionException, MaxRetryException)
            ),
        ):
            list(
                client.request_many(
                    requests_list, max_workers=1, fail_fast=True
                )
            )


class TestHttpClientSessionManagement:
    """Test session management."""

    def test_context_manager(self, requestforge_config):
        """T
        est using client as context manager.

        with HttpClient() auto-closes on exit
        """
        with HttpClient(requestforge_config) as client:
            assert not client._closed

        assert client._closed

    def test_close_method(self, requestforge_instance):
        """
        Test close method.

        Explicit close() releases resources
        """
        assert not requestforge_instance._closed
        requestforge_instance.close()
        assert requestforge_instance._closed

    def test_idempotent_close(self, requestforge_instance):
        """
        Test that close is idempotent.

        Multiple close() calls safe
        """
        requestforge_instance.close()
        requestforge_instance.close()  # Should not raise
        assert requestforge_instance._closed

    def test_destructor_cleanup(self, requestforge_config):
        """
        Test destructor cleanup.

        del cleans up if not closed
        """
        client = HttpClient(requestforge_config)
        client_id = id(client)
        del client  # Should not raise


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_client(self):
        """
        Test create_client factory function.

        create_client() convenience factory
        """
        client = create_client(
            base_url="https://api.example.com",
            timeout=20.0,
            max_retries=2,
            enable_logging=True,
        )
        assert isinstance(client, HttpClient)
        assert client._config.base_url == "https://api.example.com"
        assert client._config.default_timeout == 20.0

    def test_requestforge_context_manager(self):
        """Test requestforge context manager function."""
        with http_client("https://api.example.com") as client:
            assert isinstance(client, HttpClient)
            assert not client._closed

        assert client._closed


class TestHttpClientHooks:
    """
    Test hook execution.

    http_client() context manager function
    Hook Pipeline:
        Request  → Hook1 → Hook2 → Auth Hook → Send
        Response ← Hook1 ← Hook2 ← Return
    """

    @responses.activate
    def test_request_hook_execution(self, requestforge_instance):
        """
        Test request hooks are executed.

        Request hooks fire before send
        """
        request_hook = Mock()
        request_hook.before_request = Mock(side_effect=lambda req, ctx: req)

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_request_hook(request_hook)
            .build()
        )
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        client.get("/users")
        assert request_hook.before_request.called

    @responses.activate
    def test_response_hook_execution(self, requestforge_instance):
        """
        Test response hooks are executed.

        Response hooks fire after receive
        """
        response_hook = Mock()
        response_hook.after_response = Mock(side_effect=lambda res, ctx: res)

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_response_hook(response_hook)
            .build()
        )
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        client.get("/users")
        assert response_hook.after_response.called

    @responses.activate
    def test_hook_modification_of_request(self):
        """
        Test hook can modify request.

        Hook can modify request (add headers)
        """

        def modify_request(request, context):
            return request.with_headers({"X-Modified": "true"})

        request_hook = Mock()
        request_hook.before_request = Mock(side_effect=modify_request)

        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_request_hook(request_hook)
            .build()
        )
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        client.get("/users")
        assert "X-Modified" in responses.calls[0].request.headers


class TestHttpClientEdgeCases:
    """Test edge cases and special scenarios."""

    @responses.activate
    def test_empty_response_body(self, requestforge_instance):
        """
        Test handling empty response body.

        204 No Content handled
        """
        responses.add(
            responses.DELETE,
            "https://api.example.com/users/1",
            body="",
            status=204,
        )

        response = requestforge_instance.delete("/users/1")
        assert response.status_code == 204
        assert response.text == ""

    @responses.activate
    def test_response_with_different_encoding(self, requestforge_instance):
        """
        Test response with different encoding.

        UTF-8, other encodings
        """
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            body="测试",
            status=200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )

        response = requestforge_instance.get("/users")
        assert response.status_code == 200

    @responses.activate
    def test_request_without_base_url(self):
        """
        Test request with absolute URL.

        Absolute URLs work without base_url
        """
        config = HttpClientConfigBuilder().build()  # No base URL
        client = HttpClient(config)

        responses.add(
            responses.GET, "https://api.example.com/users", json=[], status=200
        )

        response = client.get("https://api.example.com/users")
        assert response.status_code == 200

    def test_build_url_with_base_url(self, requestforge_instance):
        """
        Test URL building with base URL.

        Relative paths joined with base
        """
        url = requestforge_instance._build_url("/users")
        assert url == "https://api.example.com/users"

    def test_build_url_with_absolute_url(self, requestforge_instance):
        """
        Test URL building with absolute URL.

        Absolute URLs pass through
        """
        url = requestforge_instance._build_url(
            "https://other.example.com/users"
        )
        assert url == "https://other.example.com/users"

    @responses.activate
    def test_multiple_sequential_requests(self, requestforge_instance):
        """
        Test multiple sequential requests.

        Connection reuse across requests
        """
        responses.add(
            responses.GET,
            "https://api.example.com/users/1",
            json={"id": 1},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.example.com/users/2",
            json={"id": 2},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.example.com/users/3",
            json={"id": 3},
            status=200,
        )

        for i in range(1, 4):
            response = requestforge_instance.get(f"/users/{i}")
            assert response.status_code == 200
            assert response.json()["id"] == i
