"""
Tests for HTTP client configuration.
    - TokenData model
    - HttpClientConfig immutability
    - HttpClientConfigBuilder fluent interface
    - Configuration validation
    - Header management
    - Retry strategies
    - Auth hooks
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from requestforge.hooks import (
    LoggingRequestHook,
    LoggingResponseHook,
)
from requestforge.retry import ExponentialBackoffRetryStrategy
from requestforge.config import (
    TokenData,
    HttpClientConfig,
    HttpClientConfigBuilder,
)
from requestforge.interfaces import AuthHookInterface


class TestTokenData:
    """
    Test TokenData model.

    Expiry Logic:
        expires_at = now + 1 hour     → NOT expired
        expires_at = now - 1 hour     → EXPIRED
        expires_at = now + 20 seconds → EXPIRED (30s buffer)
    """

    def test_create_token_minimal(self):
        """
        Test creating token with minimal parameters.

        Token with just access_token
        """
        token = TokenData(access_token="test-token")
        assert token.access_token == "test-token"
        assert token.token_type == "Bearer"
        assert token.expires_at is None
        assert token.refresh_token is None

    def test_create_token_full(self):
        """
        Test creating token with all parameters.

        All fields: token, type, expiry, refresh, scope, extra
        """
        expires_at = datetime.now() + timedelta(hours=1)
        token = TokenData(
            access_token="test-token",
            token_type="Bearer",
            expires_at=expires_at,
            refresh_token="refresh-token",
            scope="read write",
            extra={"custom": "value"},
        )

        assert token.access_token == "test-token"
        assert token.token_type == "Bearer"
        assert token.expires_at == expires_at
        assert token.refresh_token == "refresh-token"
        assert token.scope == "read write"
        assert token.extra["custom"] == "value"

    def test_token_is_not_expired(self):
        """
        Test token expiration check.

        Future expiry = valid
        """
        token = TokenData(
            access_token="test",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert not token.is_expired

    def test_token_is_expired(self):
        """
        Test expired token detection.

        Past expiry = expired
        """
        token = TokenData(
            access_token="test",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert token.is_expired

    def test_token_expires_soon(self):
        """
        Test token expiration buffer (30 seconds).

        30-second buffer: expires in 20s = expired
        """
        token = TokenData(
            access_token="test",
            expires_at=datetime.now() + timedelta(seconds=20),
        )
        assert token.is_expired  # Within 30 second buffer

    def test_authorization_header(self):
        """
        Test authorization_header property.

        "Bearer token" format
        """
        token = TokenData(
            access_token="test-token",
            token_type="Bearer",
        )
        assert token.authorization_header == "Bearer test-token"

    def test_authorization_header_without_type(self):
        """
        Test authorization_header without type.

        Just token when no type
        """
        token = TokenData(
            access_token="test-token",
            token_type="",
        )
        assert token.authorization_header == "test-token"

    def test_from_response(self):
        """
        Test creating token from API response.

        Parse standard OAuth2 response
        """
        response_data = {
            "access_token": "token-123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh-123",
            "scope": "read",
        }

        token = TokenData.from_response(response_data)

        assert token.access_token == "token-123"
        assert token.token_type == "Bearer"
        assert token.refresh_token == "refresh-123"
        assert token.scope == "read"
        assert token.expires_at is not None

    def test_from_response_custom_keys(self):
        """
        Test creating token from response with custom keys.

        Parse non-standard field names
        """
        response_data = {
            "token": "custom-token",
            "ttl": 7200,
        }

        token = TokenData.from_response(
            response_data,
            access_token_key="token",
            expires_in_key="ttl",
        )

        assert token.access_token == "custom-token"
        assert token.expires_at is not None

    def test_token_extra_fields(self):
        """
        Test extra fields are preserved.

        Unknown fields stored in extra
        """
        response_data = {
            "access_token": "token",
            "custom_field": "value",
            "another_field": 123,
        }

        token = TokenData.from_response(response_data)
        assert token.extra["custom_field"] == "value"
        assert token.extra["another_field"] == 123


class TestHttpClientConfig:
    """Test HttpClientConfig immutable configuration."""

    def test_create_config_default(self):
        """
        Test creating config with defaults.

        Default values applied
        """
        config = HttpClientConfig()
        assert config.base_url == ""
        assert config.default_timeout == 30.0
        assert config.verify_ssl is True
        assert config.allow_redirects is True

    def test_create_config_custom(self):
        """
        Test creating config with custom values.

        All custom values accepted
        """
        config = HttpClientConfig(
            base_url="https://api.example.com",
            default_timeout=60.0,
            verify_ssl=False,
            allow_redirects=False,
        )

        assert config.base_url == "https://api.example.com"
        assert config.default_timeout == 60.0
        assert config.verify_ssl is False
        assert config.allow_redirects is False

    def test_config_is_immutable(self):
        """
        Test that config is immutable (frozen).

        Frozen dataclass - cannot modify
        """
        config = HttpClientConfig()
        with pytest.raises(Exception):  # noqa FrozenInstanceError
            config.base_url = "new-url"

    def test_config_validation_timeout(self):
        """
        Test config validation for timeout.

        timeout <= 0 raises ValueError
        """
        with pytest.raises(
            ValueError, match="default_timeout must be positive"
        ):
            HttpClientConfig(default_timeout=-1)

        with pytest.raises(
            ValueError, match="default_timeout must be positive"
        ):
            HttpClientConfig(default_timeout=0)

    def test_config_validation_redirects(self):
        """
        Test config validation for max_redirects.

        max_redirects < 0 raises ValueError
        """
        with pytest.raises(
            ValueError, match="max_redirects must be non-negative"
        ):
            HttpClientConfig(max_redirects=-1)


class TestHttpClientConfigBuilder:
    """
    Test fluent builder for configuration.

    Fluent API:
    >>> config = (Builder()
    ... .with_base_url(url)
    ... .with_timeout(30)
    ... .with_retry(3)
    ... .with_logging()
    ... .build())
    """

    def test_builder_default(self):
        """
        Test builder creates default config.

        Build with no config = defaults
        """
        config = HttpClientConfigBuilder().build()
        assert config.base_url == ""
        assert config.default_timeout == 30.0

    def test_builder_with_base_url(self):
        """
        Test builder with base URL.

        Trailing slash stripped
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com/")
            .build()
        )
        assert (
            config.base_url == "https://api.example.com"
        )  # Trailing slash removed

    def test_builder_with_timeout(self):
        """
        Test builder with timeout.

        Custom timeout
        """
        config = HttpClientConfigBuilder().with_timeout(60.0).build()
        assert config.default_timeout == 60.0

    def test_builder_with_headers(self):
        """
        Test builder with headers.

        Multiple headers at once
        """
        headers = {"X-Custom": "value"}
        config = HttpClientConfigBuilder().with_headers(headers).build()
        assert config.default_headers["X-Custom"] == "value"

    def test_builder_with_header(self):
        """
        Test builder with single header.

        Single header addition
        """
        config = (
            HttpClientConfigBuilder()
            .with_header("X-Custom", "value")
            .with_header("X-Other", "other")
            .build()
        )
        assert config.default_headers["X-Custom"] == "value"
        assert config.default_headers["X-Other"] == "other"

    def test_builder_with_bearer_token(self):
        """
        Test builder with bearer token.

        Sets Authorization header
        """
        config = (
            HttpClientConfigBuilder().with_bearer_token("test-token").build()
        )
        assert config.default_headers["Authorization"] == "Bearer test-token"

    def test_builder_with_api_key(self):
        """
        Test builder with API key.

        Sets X-API-Key header
        """
        config = HttpClientConfigBuilder().with_api_key("test-key").build()
        assert config.default_headers["X-API-Key"] == "test-key"

    def test_builder_with_api_key_custom_header(self):
        """Test builder with custom API key header."""
        config = (
            HttpClientConfigBuilder()
            .with_api_key("test-key", header_name="Authorization")
            .build()
        )
        assert config.default_headers["Authorization"] == "test-key"

    def test_builder_with_verify_ssl(self):
        """
        Test builder with SSL verification.

        SSL verification toggle
        """
        config = HttpClientConfigBuilder().with_verify_ssl(False).build()
        assert config.verify_ssl is False

    def test_builder_with_redirects(self):
        """
        Test builder with redirect configuration.

        Redirect configuration
        """
        config = (
            HttpClientConfigBuilder()
            .with_redirects(allow=False, max_redirects=5)
            .build()
        )
        assert config.allow_redirects is False
        assert config.max_redirects == 5

    def test_builder_with_retry_strategy(self):
        """
        Test builder with retry strategy.

        Custom retry strategy
        """
        strategy = ExponentialBackoffRetryStrategy(max_retries=5)
        config = (
            HttpClientConfigBuilder().with_retry_strategy(strategy).build()
        )
        assert config.retry_strategy == strategy

    def test_builder_with_retry(self):
        """
        Test builder with exponential backoff.

        Exponential backoff shortcut
        """
        config = (
            HttpClientConfigBuilder()
            .with_retry(max_retries=5, base_delay=2.0)
            .build()
        )
        assert isinstance(
            config.retry_strategy, ExponentialBackoffRetryStrategy
        )
        assert config.retry_strategy.max_retries == 5

    def test_builder_with_pool_configuration(self):
        """
        Test builder with connection pool configuration.

        Connection pool sizing
        """
        config = (
            HttpClientConfigBuilder()
            .with_pool_connection(20)
            .with_pool_maxsize(50)
            .build()
        )
        assert config.pool_connection == 20
        assert config.pool_maxsize == 50

    def test_builder_with_logging(self):
        """
        Test builder with logging hooks.

        Adds 3 logging hooks
        """
        config = HttpClientConfigBuilder().with_logging().build()
        assert len(config.request_hooks) > 0
        assert len(config.response_hooks) > 0
        assert len(config.error_hooks) > 0

    def test_builder_fluent_chaining(self):
        """
        Test builder method chaining.

        All methods chainable
        """
        config = (
            HttpClientConfigBuilder()
            .with_base_url("https://api.example.com")
            .with_timeout(60.0)
            .with_bearer_token("token")
            .with_retry(max_retries=3)
            .with_logging()
            .build()
        )

        assert config.base_url == "https://api.example.com"
        assert config.default_timeout == 60.0
        assert config.default_headers["Authorization"] == "Bearer token"
        assert config.retry_strategy.max_retries == 3
        assert len(config.request_hooks) > 0

    def test_builder_with_auth_hook(self):
        """
        Test builder with auth hook.

        Auth hook attachment
        """
        mock_hook = Mock(spec=AuthHookInterface)
        config = HttpClientConfigBuilder().with_auth_hook(mock_hook).build()
        assert config.auth_hook == mock_hook

    def test_builder_with_request_hook(self):
        """
        Test builder with request hook.

        Request hook registration
        """
        hook = LoggingRequestHook()
        config = HttpClientConfigBuilder().with_request_hook(hook).build()
        assert hook in config.request_hooks

    def test_builder_with_response_hook(self):
        """
        Test builder with response hook.

        Response hook registration
        """
        hook = LoggingResponseHook()
        config = HttpClientConfigBuilder().with_response_hook(hook).build()
        assert hook in config.response_hooks

    def test_builder_multiple_calls_accumulate_hooks(self):
        """
        Test that multiple hook additions accumulate.

        Multiple hooks accumulate
        """
        hook1 = LoggingRequestHook()
        hook2 = LoggingRequestHook()

        config = (
            HttpClientConfigBuilder()
            .with_request_hook(hook1)
            .with_request_hook(hook2)
            .build()
        )

        assert len(config.request_hooks) == 2

    def test_builder_reuse_builder_instance(self):
        """
        Test reusing builder instance.

        Builder reusable (new config each build)
        """
        builder = HttpClientConfigBuilder()
        config1 = builder.with_timeout(30.0).build()
        builder2 = HttpClientConfigBuilder()
        config2 = builder2.with_timeout(60.0).build()

        # Builders should not interfere
        assert config1.default_timeout == 30.0
        assert config2.default_timeout == 60.0
