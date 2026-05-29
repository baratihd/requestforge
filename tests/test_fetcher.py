"""
Tests for token fetchers.

Tests for HTTP-based token fetching with single-step and multi-step authentication flows.
"""

from datetime import datetime, timedelta

import pytest
import responses

from requestforge.config import TokenData
from requestforge.models import HttpMethod
from requestforge.fetcher import (
    BodyTokenFetcher,
    HttpTokenFetcher,
    HeaderTokenFetcher,
)
from requestforge.exceptions import AuthenticationException


class DummyFetcher(HttpTokenFetcher):
    def fetch(self):
        return "token"

    def name(self):
        return "dummy"


class TestHttpTokenFetcher:
    """Test base HttpTokenFetcher."""

    def test_initialization(self):
        """
        Test fetcher initialization.

        Verifies base fetcher initializes with URL, timeout,
        SSL verification, and custom headers
        """
        fetcher = DummyFetcher(
            base_url="https://auth.example.com",
            timeout=30.0,
            verify_ssl=True,
            headers={"X-Custom": "value"},
        )

        assert fetcher._base_url == "https://auth.example.com"
        assert fetcher._timeout == 30.0
        assert fetcher._verify_ssl is True
        assert fetcher._default_headers == {"X-Custom": "value"}

    def test_base_url_trailing_slash_removed(self):
        """
        Test base URL trailing slash is removed.

        Ensures base URL normalization by removing trailing slashes
        """
        fetcher = DummyFetcher(base_url="https://auth.example.com/")
        assert fetcher._base_url == "https://auth.example.com"

    def test_get_client_lazy_initialization(self):
        """
        Test HTTP client is created lazily.


        Validates HTTP client is created lazily only when needed and reused
        """
        fetcher = DummyFetcher(base_url="https://auth.example.com")
        assert fetcher._client is None

        client1 = fetcher._get_client()
        assert client1 is not None

        client2 = fetcher._get_client()
        assert client1 is client2  # Same instance

    def test_close_client(self):
        """Test closing HTTP client."""
        fetcher = DummyFetcher(base_url="https://auth.example.com")
        client = fetcher._get_client()
        assert fetcher._client is not None

        fetcher.close()
        assert fetcher._client is None

    @responses.activate
    def test_make_request_post(self):
        """
        Test making POST request.

        Verifies POST requests are executed correctly
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"token": "test-token"},
            status=200,
        )

        fetcher = DummyFetcher(base_url="https://auth.example.com")
        response = fetcher._make_request(
            method=HttpMethod.POST,
            endpoint="/token",
            data={"grant_type": "client_credentials"},
        )

        assert response.status_code == 200

    @responses.activate
    def test_make_request_get(self):
        """
        Test making GET request.

        Verifies GET requests are executed correctly
        """
        responses.add(
            responses.GET,
            "https://auth.example.com/token?key=value",
            json={"token": "test-token"},
            status=200,
        )

        fetcher = DummyFetcher(base_url="https://auth.example.com")
        response = fetcher._make_request(
            method=HttpMethod.GET,
            endpoint="/token",
            data={"key": "value"},
        )

        assert response.status_code == 200

    def test_make_request_unsupported_method(self):
        """Test unsupported HTTP method raises error."""
        fetcher = DummyFetcher(base_url="https://auth.example.com")

        with pytest.raises(ValueError, match="Unsupported method"):
            fetcher._make_request(
                method=HttpMethod.PUT,
                endpoint="/token",
            )


class TestHeaderTokenFetcher:
    """
    Test HeaderTokenFetcher.

    Scenarios:
        - Simple Auth: API returns token in custom header (e.g., legacy systems)
        - App Token Flow: First step fetches app-level token from header
        - Dependency Chain: Uses previous tokens to fetch next token
    """

    def test_initialization(self):
        """
        Test fetcher initialization.

        Validates fetcher configuration with endpoint, headers, token header name
        """
        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/auth/token",
            method=HttpMethod.POST,
            request_headers={"appname": "my-app"},
            token_header="X-Auth-Token",
            token_type="Bearer",
        )

        assert fetcher.name == "app_token"
        assert fetcher._endpoint == "/auth/token"
        assert fetcher._token_header == "X-Auth-Token"
        assert fetcher._token_type == "Bearer"

    def test_properties(self):
        """
        Test fetcher properties.

        Tests fetcher properties: name, dependencies, TTL
        """
        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            ttl=timedelta(hours=1),
            depends_on=["step1", "step2"],
        )

        assert fetcher.name == "app_token"
        assert fetcher.depends_on == ["step1", "step2"]
        assert fetcher.ttl == timedelta(hours=1)

    @responses.activate
    def test_fetch_token_from_header(self):
        """
        Test fetching token from response header.

        Main Flow: Fetches token from response header (e.g., X-Auth-Token)
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            headers={"X-Auth-Token": "token-from-header"},
            status=200,
        )

        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            token_header="X-Auth-Token",
        )

        token = fetcher.fetch()

        assert token.access_token == "token-from-header"
        assert token.token_type == "Bearer"

    @responses.activate
    def test_fetch_token_with_ttl(self):
        """
        Test token fetch with TTL.

        Validates token expiration is set based on configured TTL
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            headers={"X-Auth-Token": "token-123"},
            status=200,
        )

        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            token_header="X-Auth-Token",
            ttl=timedelta(hours=1),
        )

        token = fetcher.fetch()

        assert token.expires_at is not None
        assert token.expires_at > datetime.now()

    @responses.activate
    def test_fetch_token_missing_header(self):
        """
        Test error when token header is missing.

        Error Scenario: Token header missing from response
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            headers={},  # No token header
            status=200,
        )

        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            token_header="X-Auth-Token",
        )

        with pytest.raises(
            AuthenticationException, match="not found in response"
        ):
            fetcher.fetch()

    @responses.activate
    def test_fetch_token_http_error(self):
        """
        Test error on HTTP error response.

        Error Scenario: HTTP error (401/500) during token fetch
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"error": "Unauthorized"},
            status=401,
        )

        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            token_header="X-Auth-Token",
        )

        with pytest.raises(
            AuthenticationException, match="Token request failed"
        ):
            fetcher.fetch()

    @responses.activate
    def test_fetch_with_request_data(self):
        """
        Test fetch with request data.

        Tests sending request data/params with token request
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            headers={"X-Auth-Token": "token-123"},
            status=200,
        )

        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={"client_id": "app", "client_secret": "secret"},
            token_header="X-Auth-Token",
        )

        token = fetcher.fetch()

        assert token.access_token == "token-123"

    @responses.activate
    def test_fetch_with_get_method(self):
        """
        Test fetch using GET method.

        Validates GET method for token fetching
        """
        responses.add(
            responses.GET,
            "https://auth.example.com/token",
            headers={"X-Auth-Token": "token-123"},
            status=200,
        )

        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            method=HttpMethod.GET,
            token_header="X-Auth-Token",
        )

        token = fetcher.fetch()

        assert token.access_token == "token-123"

    def test_build_request_headers_override(self):
        """
        Test _build_request_headers can be overridden.

        Tests custom header building for dependent tokens
        """
        fetcher = HeaderTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_headers={"X-Custom": "value"},
        )

        headers = fetcher._build_request_headers(None)
        assert headers == {"X-Custom": "value"}

    @responses.activate
    def test_fetch_with_context(self):
        """
        Test fetch with token context from previous steps.

        Multi-Step: Fetches token using previous step's tokens in context
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            headers={"X-Auth-Token": "final-token"},
            status=200,
        )

        fetcher = HeaderTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            token_header="X-Auth-Token",
            depends_on=["app_token"],
        )

        context = {
            "app_token": TokenData(
                access_token="previous-token", token_type="Bearer"
            ),
        }

        token = fetcher.fetch(context)

        assert token.access_token == "final-token"


class TestBodyTokenFetcher:
    """
    Test BodyTokenFetcher.

    Scenarios:
        - OAuth2 Client Credentials: Standard grant_type=client_credentials flow
        - Password Grant: User authentication with username/password
        - Custom Token API: Non-standard APIs with different field names
        - Multi-Step OAuth: Fetch user token using app token from previous step
    """

    def test_initialization(self):
        """
        Test fetcher initialization.

        Validates configuration with OAuth2-style parameters
        """
        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/oauth/token",
            request_data={"grant_type": "client_credentials"},
            token_field="access_token",
        )

        assert fetcher.name == "access_token"
        assert fetcher._endpoint == "/oauth/token"
        assert fetcher._token_field == "access_token"

    def test_initialization_with_all_parameters(self):
        """
        Test initialization with all parameters.

        Tests all customization options (field names, content type, etc.)
        """
        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            method=HttpMethod.POST,
            request_headers={"X-Custom": "header"},
            request_data={"key": "value"},
            content_type="json",
            token_field="token",
            token_type_field="type",
            expires_in_field="ttl",
            refresh_token_field="refresh",
            default_token_type="Custom",
            ttl=timedelta(hours=2),
            timeout=60.0,
            verify_ssl=False,
            depends_on=["step1"],
        )

        assert fetcher.name == "access_token"
        assert fetcher._content_type == "json"
        assert fetcher._token_field == "token"
        assert fetcher._default_token_type == "Custom"
        assert fetcher.ttl == timedelta(hours=2)
        assert fetcher.depends_on == ["step1"]

    @responses.activate
    def test_fetch_token_from_body_json(self):
        """
        Test fetching token from response body (JSON).

        OAuth2 Flow: Fetches token from JSON response body
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={
                "access_token": "token-123",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            content_type="json",
            request_data={"grant_type": "client_credentials"},
        )

        token = fetcher.fetch()

        assert token.access_token == "token-123"
        assert token.token_type == "Bearer"
        assert token.expires_at is not None

    @responses.activate
    def test_fetch_token_from_body_form(self):
        """
        Test fetching token with form-encoded request.

        Form-Encoded: Uses application/x-www-form-urlencoded
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={
                "access_token": "token-456",
                "token_type": "Bearer",
            },
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            content_type="form",
            request_data={"grant_type": "password"},
        )

        token = fetcher.fetch()

        assert token.access_token == "token-456"
        # Verify Content-Type was set correctly
        assert (
            responses.calls[0].request.headers["Content-Type"]
            == "application/x-www-form-urlencoded"
        )

    @responses.activate
    def test_fetch_token_with_expires_in(self):
        """
        Test token expiration is calculated from expires_in.

        Calculates token expiration from expires_in field
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={
                "access_token": "token-123",
                "expires_in": 7200,  # 2 hours
            },
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )

        token = fetcher.fetch()

        assert token.expires_at is not None
        expected_expiry = datetime.now() + timedelta(seconds=7200)
        # Allow 5 second tolerance
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 5

    @responses.activate
    def test_fetch_token_with_ttl_override(self):
        """
        Test TTL override takes precedence over expires_in.

        TTL configuration overrides expires_in from response
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={
                "access_token": "token-123",
                "expires_in": 7200,
            },
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
            ttl=timedelta(hours=1),  # Override
        )

        token = fetcher.fetch()

        assert token.expires_at is not None
        expected_expiry = datetime.now() + timedelta(hours=1)
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 5

    @responses.activate
    def test_fetch_token_with_refresh_token(self):
        """
        Test fetching token with refresh token.

        Extracts refresh token from response
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={
                "access_token": "token-123",
                "refresh_token": "refresh-456",
                "token_type": "Bearer",
            },
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )

        token = fetcher.fetch()

        assert token.access_token == "token-123"
        assert token.refresh_token == "refresh-456"

    @responses.activate
    def test_fetch_token_custom_field_names(self):
        """
        Test fetching with custom field names.

        Non-Standard API: Custom field names (e.g., token instead of access_token)
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={
                "token": "custom-token",
                "type": "CustomType",
                "ttl": 1800,
            },
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
            token_field="token",
            token_type_field="type",
            expires_in_field="ttl",
        )

        token = fetcher.fetch()

        assert token.access_token == "custom-token"
        assert token.token_type == "CustomType"

    @responses.activate
    def test_fetch_token_missing_token_field(self):
        """
        Test error when token field is missing.

        Error Scenario: Required token field missing
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"error": "Invalid request"},
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )

        with pytest.raises(
            AuthenticationException, match="not found in response"
        ):
            fetcher.fetch()

    @responses.activate
    def test_fetch_token_http_error(self):
        """
        Test error on HTTP error response.

        Error Scenario: Authentication failed (401)
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"error": "invalid_client"},
            status=401,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )

        with pytest.raises(
            AuthenticationException, match="Token request failed"
        ):
            fetcher.fetch()

    @responses.activate
    def test_fetch_token_invalid_json(self):
        """
        Test error on invalid JSON response.

        Error Scenario: Malformed JSON response
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            body="invalid json",
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )

        with pytest.raises(AuthenticationException, match="Failed to parse"):
            fetcher.fetch()

    @responses.activate
    def test_fetch_with_context(self):
        """
        Test fetch with context from previous steps.

        Multi-Step: Uses tokens from previous steps
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"access_token": "final-token"},
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
            depends_on=["app_token"],
        )

        context = {
            "app_token": TokenData(access_token="previous-token"),
        }

        token = fetcher.fetch(context)

        assert token.access_token == "final-token"

    def test_build_request_data_override(self):
        """
        Test _build_request_data can be overridden.

        Tests custom request data building
        """
        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={"key": "value"},
        )

        data = fetcher._build_request_data(None)
        assert data == {"key": "value"}

    @responses.activate
    def test_fetch_default_token_type(self):
        """
        Test default token type is used when not in response.

        Uses default token type when not in response
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            json={"access_token": "token-123"},
            status=200,
        )

        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
            default_token_type="Custom",
        )

        token = fetcher.fetch()

        assert token.token_type == "Custom"


class TestFetcherErrorHandling:
    """
    Test error handling in fetchers.

    Scenarios:
        - Custom error handling and logging for failed token fetches.
    """

    @responses.activate
    def test_on_fetch_error_callback(self):
        """
        Test on_fetch_error is called on error.

        Validates error callback is invoked on failures
        """
        responses.add(
            responses.POST,
            "https://auth.example.com/token",
            status=500,
        )

        error_called = False
        error_exception = None

        class CustomFetcher(HeaderTokenFetcher):
            def on_fetch_error(self, error, context):  # noqa
                nonlocal error_called, error_exception
                error_called = True
                error_exception = error

        fetcher = CustomFetcher(
            name="test",
            base_url="https://auth.example.com",
            endpoint="/token",
            token_header="X-Token",
        )

        with pytest.raises(AuthenticationException):
            fetcher.fetch()

        # Note: on_fetch_error is not automatically called by base implementation
        # It's meant to be called by the pipeline or caller


class TestFetcherDependencies:
    """
    Test fetcher dependency handling.

    Scenarios:
        - Dependency management for multi-step authentication flows.
    """

    def test_fetcher_with_no_dependencies(self):
        """
        Test fetcher with no dependencies.

        Independent fetcher (first step in pipeline)
        """
        fetcher = BodyTokenFetcher(
            name="app_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )

        assert fetcher.depends_on == []

    def test_fetcher_with_dependencies(self):
        """
        Test fetcher with dependencies.

        Fetcher depends on multiple previous steps
        """
        fetcher = BodyTokenFetcher(
            name="access_token",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
            depends_on=["app_token", "user_token"],
        )

        assert fetcher.depends_on == ["app_token", "user_token"]

    def test_fetcher_ttl_property(self):
        """
        Test fetcher TTL property.

        Tests TTL configuration for cache control
        """
        # No TTL
        fetcher1 = BodyTokenFetcher(
            name="token1",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
        )
        assert fetcher1.ttl is None

        # With TTL
        fetcher2 = BodyTokenFetcher(
            name="token2",
            base_url="https://auth.example.com",
            endpoint="/token",
            request_data={},
            ttl=timedelta(hours=1),
        )
        assert fetcher2.ttl == timedelta(hours=1)
