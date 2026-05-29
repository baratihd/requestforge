"""
Tests for HTTP models (request, response, context).
    - HttpMethod enum
    - HttpRequest creation and immutability
    - HttpResponse parsing and status checks
    - RequestContext state management
    - FetchContext token management
"""

from datetime import datetime, timedelta

import pytest

from requestforge.config import TokenData
from requestforge.models import (
    HttpMethod,
    HttpRequest,
    FetchContext,
    HttpResponse,
    RequestContext,
)
from requestforge.exceptions import ResponseParseException


class TestHttpMethod:
    """Test HttpMethod enum."""

    def test_http_methods_exist(self):
        """Test all 7 HTTP methods are defined."""
        assert HttpMethod.GET.value == "GET"
        assert HttpMethod.POST.value == "POST"
        assert HttpMethod.PUT.value == "PUT"
        assert HttpMethod.PATCH.value == "PATCH"
        assert HttpMethod.DELETE.value == "DELETE"
        assert HttpMethod.HEAD.value == "HEAD"
        assert HttpMethod.OPTIONS.value == "OPTIONS"

    def test_http_method_is_string_enum(self):
        """
        Test HttpMethod is string enum.

        Methods are strings (GET == 'GET')
        """
        assert isinstance(HttpMethod.GET, str)
        assert HttpMethod.GET == "GET"


class TestHttpRequest:
    """
    Test HttpRequest model.

    Immutability:
    >>> req = HttpRequest.GET('/users')
    >>> req.url = '/other'  # AttributeError!
    >>> new_req = req.with_headers({'X-New': 'value'})  # New instance
    """

    def test_create_request_minimal(self):
        """
        Test creating request with minimal parameters.

        Method + URL only
        """
        request = HttpRequest(method=HttpMethod.GET, url="/users")
        assert request.method == HttpMethod.GET
        assert request.url == "/users"
        assert request.headers is None
        assert request.params is None

    def test_create_request_with_all_parameters(self):
        """
        Test creating request with all parameters.

        All fields populated
        """
        headers = {"Authorization": "Bearer token"}
        params = {"page": 1}
        data = {"name": "John"}
        json_data = {"email": "john@example.com"}
        timeout = 30.0
        auth = ("user", "pass")

        request = HttpRequest(
            method=HttpMethod.POST,
            url="/users",
            headers=headers,
            params=params,
            data=data,
            json_data=json_data,
            timeout=timeout,
            auth=auth,
        )

        assert request.method == HttpMethod.POST
        assert request.url == "/users"
        assert request.headers == headers
        assert request.params == params
        assert request.data == data
        assert request.json_data == json_data
        assert request.timeout == timeout
        assert request.auth == auth

    def test_request_is_immutable(self):
        """
        Test that HttpRequest is immutable (frozen dataclass).

        Frozen dataclass
        """
        request = HttpRequest(method=HttpMethod.GET, url="/users")
        with pytest.raises(AttributeError):
            request.url = "/other"

    def test_request_with_headers(self):
        """
        Test with_headers method.

        with_headers() merges headers
        """
        original = HttpRequest(
            method=HttpMethod.GET,
            url="/users",
            headers={"X-Original": "value"},
        )

        modified = original.with_headers({"X-New": "header"})

        # Original unchanged
        assert original.headers == {"X-Original": "value"}
        # New request has both headers
        assert "X-Original" in modified.headers
        assert "X-New" in modified.headers
        assert modified.headers["X-New"] == "header"

    def test_request_with_headers_override(self):
        """
        Test with_headers overrides existing headers.

        with_headers() overrides existing
        """
        original = HttpRequest(
            method=HttpMethod.GET,
            url="/users",
            headers={"X-Original": "value"},
        )

        modified = original.with_headers({"X-Original": "new-value"})

        assert modified.headers["X-Original"] == "new-value"

    def test_request_to_dict(self):
        """
        Test to_dict method.

        Serialization to dict
        """
        request = HttpRequest(
            method=HttpMethod.GET,
            url="/users",
            headers={"X-Test": "value"},
        )

        request_dict = request.to_dict()
        assert request_dict["method"] == HttpMethod.GET
        assert request_dict["url"] == "/users"
        assert request_dict["headers"] == {"X-Test": "value"}

    def test_request_to_curl(self):
        """
        Test to_curl method.

        Generate cURL command
        """
        request = HttpRequest(
            method=HttpMethod.POST,
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer token"},
            json_data={"name": "John"},
        )

        curl_cmd = request.to_curl()
        assert "curl" in curl_cmd
        assert "POST" in curl_cmd
        assert "api.example.com/users" in curl_cmd


class TestHttpResponse:
    """
    Test HttpResponse model.

    Status Checks:
    >>> response.is_success        # 200-299
    >>> response.is_client_error   # 400-499
    >>> response.is_server_error   # 500-599
    """

    def test_create_response(self, http_request):
        """
        Test creating response.

        All response fields
        """
        response = HttpResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"id": 1}',
            elapsed_ms=150.5,
            url="https://api.example.com/users/1",
            request=http_request,
        )

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.elapsed_ms == 150.5
        assert response.request == http_request

    def test_response_text_property(self, http_request):
        """
        Test text property.

        Content decoded to string
        """
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b"Hello World",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        assert response.text == "Hello World"

    def test_response_text_with_encoding(self, http_request):
        """
        Test text property with different encoding.

        Custom encoding support
        """
        response = HttpResponse(
            status_code=200,
            headers={},
            content="测试".encode(),
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
            encoding="utf-8",
        )

        assert response.text == "测试"

    def test_response_is_success(self, http_request):
        """
        Test is_success property.

        2xx = success
        """
        assert HttpResponse(
            status_code=200,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_success

        assert HttpResponse(
            status_code=201,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_success

        assert not HttpResponse(
            status_code=400,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_success

    def test_response_is_client_error(self, http_request):
        """
        Test is_client_error property.

        4xx = client error
        """
        assert not HttpResponse(
            status_code=200,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_client_error

        assert HttpResponse(
            status_code=400,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_client_error

        assert HttpResponse(
            status_code=404,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_client_error

    def test_response_is_server_error(self, http_request):
        """
        Test is_server_error property.

        5xx = server error
        """
        assert not HttpResponse(
            status_code=400,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_server_error

        assert HttpResponse(
            status_code=500,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_server_error

        assert HttpResponse(
            status_code=503,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        ).is_server_error

    def test_response_json_parsing(self, http_request):
        """Test valid JSON parsing."""
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b'{"id": 1, "name": "John"}',
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "John"

    def test_response_json_parsing_invalid(self, http_request):
        """
        Test JSON parsing with invalid JSON.

        Invalid JSON → ResponseParseException
        """
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b"invalid json",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        with pytest.raises(ResponseParseException):
            response.json()

    def test_response_json_or_none(self, http_request):
        """
        Test json_or_none method.

        Safe parsing returns None on error
        """
        # Valid JSON
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b'{"id": 1}',
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )
        assert response.json_or_none() == {"id": 1}

        # Invalid JSON
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b"invalid",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )
        assert response.json_or_none() is None

    def test_response_is_immutable(self, http_request):
        """Test that HttpResponse is immutable (Frozen dataclass)."""
        response = HttpResponse(
            status_code=200,
            headers={},
            content=b"",
            elapsed_ms=10.0,
            url="https://api.example.com/test",
            request=http_request,
        )

        with pytest.raises(AttributeError):
            response.status_code = 404


class TestRequestContext:
    """Test RequestContext model."""

    def test_create_context(self, http_request):
        """
        Test creating request context.

        Context with request, attempt, max_retries
        """
        context = RequestContext(
            request=http_request,
            attempt=0,
            max_retries=3,
        )

        assert context.request == http_request
        assert context.attempt == 0
        assert context.max_retries == 3
        assert context.metadata == {}

    def test_context_increment_attempt(self, http_request):
        """Test incrementing attempt counter."""
        context = RequestContext(
            request=http_request, attempt=0, max_retries=3
        )

        context.increment_attempt()
        assert context.attempt == 1

        context.increment_attempt()
        assert context.attempt == 2

    def test_context_is_retry(self, http_request):
        """
        Test is_retry property.

        attempt > 0 = is_retry
        """
        context = RequestContext(
            request=http_request, attempt=0, max_retries=3
        )
        assert not context.is_retry

        context.increment_attempt()
        assert context.is_retry

    def test_context_metadata(self, http_request):
        """
        Test metadata dictionary.

        Custom metadata storage
        """
        context = RequestContext(
            request=http_request, attempt=0, max_retries=3
        )

        context.metadata["request_id"] = "123"
        context.metadata["custom"] = "value"

        assert context.metadata["request_id"] == "123"
        assert context.metadata["custom"] == "value"


class TestFetchContext:
    """Test FetchContext model."""

    def test_create_fetch_context(self):
        """
        Test creating fetch context.

        Empty token/context dicts
        """
        context = FetchContext()
        assert context.tokens == {}
        assert context.metadata == {}

    def test_add_token(self, token_data):
        """
        Test adding token to context.

        Store token by step name
        """
        context = FetchContext()
        context.add_token("access_token", token_data)

        assert context.get_token("access_token") == token_data

    def test_get_token_value(self, token_data):
        """
        Test getting token value.

        Get access_token string
        """
        context = FetchContext()
        context.add_token("access_token", token_data)

        assert (
            context.get_token_value("access_token") == token_data.access_token
        )

    def test_has_token(self, token_data):
        """Test checking token existence."""
        context = FetchContext()
        assert not context.has_token("access_token")

        context.add_token("access_token", token_data)
        assert context.has_token("access_token")

    def test_has_valid_token(self, token_data):
        """Test checking valid token existence."""
        context = FetchContext()
        assert not context.has_valid_token("access_token")

        context.add_token("access_token", token_data)
        assert context.has_valid_token("access_token")

    def test_has_valid_token_expired(self):
        """Test has_valid_token with expired token."""
        expired_token = TokenData(
            access_token="expired-token",
            token_type="Bearer",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        context = FetchContext()
        context.add_token("access_token", expired_token)
        assert not context.has_valid_token("access_token")
