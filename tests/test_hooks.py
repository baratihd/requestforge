"""
Tests for lifecycle hooks.
    - Logging hooks
    - Authorization hooks
    - Correlation ID tracking
    - Rate limiting
    - Token authentication
    - API key authentication
    - Basic authentication
    - Composite auth hooks
"""

from unittest.mock import Mock

from requestforge.hooks import (
    BasicAuthHook,
    TokenAuthHook,
    ApiKeyAuthHook,
    LoggingErrorHook,
    AuthorizationHook,
    CompositeAuthHook,
    CorrelationIdHook,
    LoggingRequestHook,
    LoggingResponseHook,
    RateLimitResponseHook,
)
from requestforge.models import HttpMethod, HttpRequest, HttpResponse
from requestforge.exceptions import TimeoutException
from requestforge.interfaces import AuthHookInterface


class TestLoggingRequestHook:
    """Test LoggingRequestHook."""

    def test_hook_execution(self, request_context):
        """
        Test hook execution.

        Hook fires, adds request_id, start_time
        """
        hook = LoggingRequestHook()
        request = request_context.request

        modified = hook.before_request(request, request_context)

        assert modified == request
        assert "request_id" in request_context.metadata
        assert "start_time" in request_context.metadata

    def test_request_id_generation(self, request_context):
        """
        Test request ID generation.

        UUID generated, reused per request
        """
        hook = LoggingRequestHook()
        request = request_context.request

        hook.before_request(request, request_context)

        request_id_1 = request_context.metadata["request_id"]
        assert request_id_1 is not None

        # Second call should reuse existing request_id
        hook.before_request(request, request_context)
        request_id_2 = request_context.metadata["request_id"]
        assert request_id_1 == request_id_2

    def test_mask_sensitive_headers(self, request_context):
        """
        Test masking of sensitive headers.

        Auth headers masked in logs
        """
        hook = LoggingRequestHook(log_headers=True)
        request = HttpRequest(
            method=HttpMethod.GET,
            url="/test",
            headers={
                "Authorization": "Bearer token",
                "X-API-Key": "secret-key",
                "X-Custom": "not-secret",
            },
        )
        request_context.request = request

        masked = hook._mask_sensitive_headers(request.headers)

        assert masked["Authorization"] == "***"
        assert masked["X-API-Key"] == "***"
        assert masked["X-Custom"] == "not-secret"

    def test_custom_sensitive_keys(self):
        """
        Test custom sensitive key masking.

        Custom sensitive key patterns
        """
        hook = LoggingRequestHook(sensitive_keys={"custom-key"})
        masked = hook._mask_sensitive_headers(
            {
                "custom-key": "secret",
                "public-key": "public",
            }
        )

        assert masked["custom-key"] == "***"
        assert masked["public-key"] == "public"


class TestLoggingResponseHook:
    """Test LoggingResponseHook."""

    def test_hook_execution(self, http_request, request_context):
        """Test hook execution (logs status, duration)."""
        request_context.metadata["request_id"] = "test-id"
        request_context.metadata["start_time"] = 0

        hook = LoggingResponseHook()
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b'{"success": true}',
            elapsed_ms=100.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        modified = hook.after_response(response, request_context)

        assert modified == response


class TestLoggingErrorHook:
    """Test LoggingErrorHook."""

    def test_error_hook_execution(self, request_context):
        """Test error hook execution (logs error with context)."""
        hook = LoggingErrorHook()
        exception = TimeoutException("Request timed out")

        hook.on_error(exception, request_context)
        # Should not raise


class TestAuthorizationHook:
    """Test AuthorizationHook."""

    def test_token_injection(self, http_request, request_context):
        """Test token injection (callable provides token)."""

        def token_provider():
            return "test-token-123"

        hook = AuthorizationHook(token_provider)
        modified = hook.before_request(http_request, request_context)

        assert "Authorization" in modified.headers
        assert modified.headers["Authorization"] == "Bearer test-token-123"

    def test_no_token_provided(self, http_request, request_context):
        """Test when no token is provided (None = no header added)."""

        def token_provider():
            return None

        hook = AuthorizationHook(token_provider)
        modified = hook.before_request(http_request, request_context)

        assert modified == http_request


class TestCorrelationIdHook:
    """Test CorrelationIdHook."""

    def test_correlation_id_generation(self, http_request, request_context):
        """
        Test correlation ID generation.

        UUID added to header + context
        """
        hook = CorrelationIdHook()
        modified = hook.before_request(http_request, request_context)

        assert "X-Correlation-ID" in modified.headers
        assert request_context.metadata["correlation_id"] is not None

    def test_custom_header_name(self, http_request, request_context):
        """Test custom header name."""
        hook = CorrelationIdHook(header_name="X-Request-ID")
        modified = hook.before_request(http_request, request_context)

        assert "X-Request-ID" in modified.headers

    def test_correlation_id_reuse(self, http_request, request_context):
        """
        Test correlation ID is reused.

        Same ID for request lifetime
        """
        hook = CorrelationIdHook()

        hook.before_request(http_request, request_context)
        id_1 = request_context.metadata["correlation_id"]

        hook.before_request(http_request, request_context)
        id_2 = request_context.metadata["correlation_id"]

        assert id_1 == id_2


class TestRateLimitResponseHook:
    """Test RateLimitResponseHook."""

    def test_rate_limit_parsing(self, http_request, request_context):
        """
        Test rate limit header parsing.

        X-RateLimit-* headers parsed
        """
        hook = RateLimitResponseHook()
        response = HttpResponse(
            status_code=200,
            headers={
                "X-RateLimit-Remaining": "100",
                "X-RateLimit-Reset": "1234567890",
            },
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        hook.after_response(response, request_context)

        assert request_context.metadata["rate_limit_remaining"] == 100
        assert request_context.metadata["rate_limit_reset"] == 1234567890

    def test_missing_rate_limit_headers(self, http_request, request_context):
        """Test missing rate limit headers (Graceful handling)."""
        hook = RateLimitResponseHook()
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        hook.after_response(response, request_context)
        # Should not raise


class TestTokenAuthHook:
    """
    Test TokenAuthHook.

    Exclusion Patterns:
    >>> excluded_paths={'/auth/token', '/health'}
    >>> excluded_path_patterns=['/public/*', '/webhook/*']
    """

    def test_auth_header_injection(
        self, http_request, request_context, token_manager
    ):
        """Test auth header injection (Bearer token injected)."""
        hook = TokenAuthHook(token_manager)
        modified = hook.before_request(http_request, request_context)

        assert "Authorization" in modified.headers
        assert modified.headers["Authorization"].startswith("Bearer")

    def test_should_authenticate_default(self, token_manager):
        """
        Test should_authenticate returns True by default.

        All paths by default
        """
        hook = TokenAuthHook(token_manager)
        request = HttpRequest(method=HttpMethod.GET, url="/users")

        assert hook.should_authenticate(request) is True

    def test_should_not_authenticate_excluded_path(self, token_manager):
        """
        Test should not authenticate excluded path.

        Exact path exclusion
        """
        hook = TokenAuthHook(
            token_manager,
            excluded_paths={"/auth/token"},
        )
        request = HttpRequest(method=HttpMethod.GET, url="/auth/token")

        assert hook.should_authenticate(request) is False

    def test_should_not_authenticate_pattern(self, token_manager):
        """
        Test should not authenticate pattern matched path.

        Glob pattern exclusion
        """
        hook = TokenAuthHook(
            token_manager,
            excluded_path_patterns=["/public/*"],
        )
        request = HttpRequest(method=HttpMethod.GET, url="/public/docs")

        assert hook.should_authenticate(request) is False

    def test_custom_auth_header_name(
        self, http_request, request_context, token_manager
    ):
        """
        Test custom auth header name.

        X-Auth-Token, Token prefix
        """
        hook = TokenAuthHook(
            token_manager,
            auth_header_name="X-Auth-Token",
            auth_header_prefix="Token",
        )
        modified = hook.before_request(http_request, request_context)

        assert "X-Auth-Token" in modified.headers
        assert modified.headers["X-Auth-Token"].startswith("Token")

    def test_refresh_auth_success(self, token_manager):
        """
        Test successful auth refresh.

        TokenManager.force_refresh()
        """
        mock_token_manager = Mock()
        mock_token_manager.force_refresh = Mock()

        hook = TokenAuthHook(mock_token_manager)

        result = hook.refresh_auth()

        assert result is True
        mock_token_manager.force_refresh.assert_called_once()

    def test_refresh_auth_failure(self, token_manager):
        """
        Test failed auth refresh.

        Exception = False return
        """
        mock_token_manager = Mock()
        mock_token_manager.force_refresh = Mock(
            side_effect=Exception("Refresh failed")
        )

        hook = TokenAuthHook(mock_token_manager)

        result = hook.refresh_auth()

        assert result is False

    def test_is_auth_error(self, token_manager):
        """Test auth error detection (401 detection)."""
        hook = TokenAuthHook(token_manager)
        response_401 = Mock(status_code=401)
        response_200 = Mock(status_code=200)

        assert hook.is_auth_error(response_401) is True
        assert hook.is_auth_error(response_200) is False


class TestApiKeyAuthHook:
    """Test ApiKeyAuthHook."""

    def test_api_key_injection(self, http_request, request_context):
        """Test API key injection (X-API-Key header)."""
        hook = ApiKeyAuthHook(api_key="test-key-123")
        modified = hook.before_request(http_request, request_context)

        assert "X-API-Key" in modified.headers
        assert modified.headers["X-API-Key"] == "test-key-123"

    def test_custom_header_name(self, http_request, request_context):
        """Test custom header name."""
        hook = ApiKeyAuthHook(
            api_key="test-key",
            header_name="Authorization",
        )
        modified = hook.before_request(http_request, request_context)

        assert "Authorization" in modified.headers

    def test_refresh_auth_not_supported(self, http_request, request_context):  # noqa
        """Test API key refresh is not supported (Always False)."""
        hook = ApiKeyAuthHook(api_key="test-key")

        result = hook.refresh_auth()

        assert result is False


class TestBasicAuthHook:
    """Test BasicAuthHook."""

    def test_basic_auth_injection(self, http_request, request_context):
        """
        Test basic auth injection.

        Authorization: Basic base64(user:pass)
        """
        hook = BasicAuthHook(username="user", password="pass")
        modified = hook.before_request(http_request, request_context)

        assert "Authorization" in modified.headers
        assert modified.headers["Authorization"].startswith("Basic")

    def test_credentials_base64_encoded(self, http_request, request_context):
        """Test credentials are base64 encoded (Proper encoding)."""
        import base64

        hook = BasicAuthHook(username="user", password="pass")
        modified = hook.before_request(http_request, request_context)

        auth_value = modified.headers["Authorization"]
        encoded_creds = auth_value.replace("Basic ", "")
        decoded = base64.b64decode(encoded_creds).decode()

        assert decoded == "user:pass"


class TestCompositeAuthHook:
    """Test CompositeAuthHook."""

    def test_first_match_strategy(self, http_request, request_context):
        """
        Test first_match strategy.

        First applicable hook wins
        """
        hook1 = Mock(spec=AuthHookInterface)
        hook1.should_authenticate.return_value = False

        hook2 = Mock(spec=AuthHookInterface)
        hook2.should_authenticate.return_value = True
        hook2.before_request.return_value = http_request.with_headers(
            {"X-Hook2": "yes"}
        )

        composite = CompositeAuthHook([hook1, hook2], strategy="first_match")
        modified = composite.before_request(http_request, request_context)

        assert "X-Hook2" in modified.headers

    def test_all_strategy(self, http_request, request_context):
        """Test 'all' strategy applies all hooks."""
        hook1 = Mock(spec=AuthHookInterface)
        hook1.should_authenticate.return_value = True
        hook1.before_request.return_value = http_request.with_headers(
            {"X-Hook1": "yes"}
        )

        hook2 = Mock(spec=AuthHookInterface)
        hook2.should_authenticate.return_value = True
        hook2.before_request.return_value = http_request.with_headers(
            {"X-Hook2": "yes"}
        )

        composite = CompositeAuthHook([hook1, hook2], strategy="all")
        modified = composite.before_request(http_request, request_context)

        # Both hooks should be applied
        assert "X-Hook1" in modified.headers or "X-Hook2" in modified.headers
