"""
Tests for exception hierarchy.
    - Exception hierarchy
    - Exception message formatting
    - Original exception wrapping
    - Context information
"""

from requestforge.exceptions import (
    SSLException,
    TimeoutException,
    MaxRetryException,
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    ConnectionException,
    HttpClientException,
    HttpStatusException,
    ServerErrorException,
    RequestBuildException,
    UnauthorizedException,
    ResponseParseException,
    AuthenticationException,
)


class TestHttpClientException:
    """Test base HttpClientException."""

    def test_create_exception(self):
        """
        Test creating exception.

        Message, no original, empty context
        """
        exc = HttpClientException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.original_exception is None
        assert exc.context == {}

    def test_exception_with_original(self):
        """
        Test exception with original exception.

        Wraps original exception
        """
        original = ValueError("Original error")
        exc = HttpClientException("Wrapped error", original_exception=original)
        assert exc.original_exception == original
        assert "ValueError" in str(exc)
        assert "Original error" in str(exc)

    def test_exception_with_context(self):
        """
        Test exception with context.

        Context dict attached
        """
        context = {"request": "GET /users", "retry_count": 2}
        exc = HttpClientException("Error", context=context)
        assert exc.context == context


class TestMaxRetryException:
    """Test MaxRetryException."""

    def test_create_max_retry_exception(self):
        """
        Test creating MaxRetryException.

        Attempts count tracked
        """
        exc = MaxRetryException("Max retries exceeded", attempts=3)
        assert exc.message == "Max retries exceeded"
        assert exc.attempts == 3

    def test_max_retry_with_original(self):
        """
        Test MaxRetryException with original exception.

        Original exception preserved
        """
        original = TimeoutException("Timeout")
        exc = MaxRetryException(
            "Max retries exceeded", attempts=3, original_exception=original
        )
        assert exc.original_exception == original


class TestTimeoutException:
    """Test TimeoutException."""

    def test_create_timeout_exception(self):
        """Test creating TimeoutException."""
        exc = TimeoutException("Request timed out")
        assert isinstance(exc, HttpClientException)
        assert exc.message == "Request timed out"


class TestConnectionException:
    """Test ConnectionException."""

    def test_create_connection_exception(self):
        """Test creating ConnectionException."""
        exc = ConnectionException("Connection failed")
        assert isinstance(exc, HttpClientException)
        assert exc.message == "Connection failed"


class TestResponseParseException:
    """Test ResponseParseException."""

    def test_create_response_parse_exception(self):
        """Test creating ResponseParseException."""
        exc = ResponseParseException("Failed to parse JSON")
        assert isinstance(exc, HttpClientException)
        assert exc.message == "Failed to parse JSON"


class TestHttpStatusException:
    """Test HttpStatusException."""

    def test_create_status_exception(self):
        """
        Test creating status exception.

        Status code + response body
        """
        exc = HttpStatusException(
            "Bad request", status_code=400, response_body="Invalid input"
        )
        assert exc.status_code == 400
        assert exc.response_body == "Invalid input"

    def test_status_exception_string(self):
        """Test status exception string representation."""
        exc = HttpStatusException("Error", status_code=500)
        assert "Error" in str(exc)


class TestRequestBuildException:
    """Test RequestBuildException."""

    def test_create_request_build_exception(self):
        """Test creating RequestBuildException."""
        exc = RequestBuildException("Invalid request")
        assert isinstance(exc, HttpClientException)


class TestSSLException:
    """Test SSLException."""

    def test_create_ssl_exception(self):
        """Test creating SSLException."""
        exc = SSLException("SSL certificate error")
        assert isinstance(exc, HttpClientException)


class TestAuthenticationException:
    """Test AuthenticationException."""

    def test_create_auth_exception(self):
        """Test creating AuthenticationException."""
        exc = AuthenticationException("Auth failed", service_name="oauth2")
        assert exc.message == "Auth failed"
        assert exc.service_name == "oauth2"

    def test_auth_exception_without_service(self):
        """Test AuthenticationException without service name."""
        exc = AuthenticationException("Auth failed")
        assert exc.service_name is None


class TestStatusSpecificExceptions:
    """Test status code specific exceptions."""

    def test_unauthorized_exception(self):
        """Test UnauthorizedException."""
        exc = UnauthorizedException(response_body="Unauthorized")
        assert exc.status_code == 401
        assert exc.response_body == "Unauthorized"

    def test_forbidden_exception(self):
        """Test ForbiddenException."""
        exc = ForbiddenException(response_body="Forbidden")
        assert exc.status_code == 403

    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException(response_body="Resource not found")
        assert exc.status_code == 404

    def test_bad_request_exception(self):
        """Test BadRequestException."""
        exc = BadRequestException(response_body="Bad request")
        assert exc.status_code == 400

    def test_server_error_exception(self):
        """Test ServerErrorException."""
        exc = ServerErrorException(
            status_code=502, response_body="Bad gateway"
        )
        assert exc.status_code == 502


class TestExceptionHierarchy:
    """
    Test exception inheritance hierarchy.

    Catch Pattern:
    >>> try:
    >>>     client.get('/api')
    >>> except UnauthorizedException:      # Specific
    >>>     handle_401()
    >>> except HttpStatusException:        # Any 4xx/5xx
    >>>     handle_http_error()
    >>> except HttpClientException:        # Any client error
    >>>     handle_generic()
    """

    def test_all_exceptions_inherit_from_base(self):
        """Test all exceptions inherit from HttpClientException."""
        exceptions = [
            MaxRetryException("msg", 1),
            TimeoutException("msg"),
            ConnectionException("msg"),
            ResponseParseException("msg"),
            HttpStatusException("msg", 400),
            RequestBuildException("msg"),
            SSLException("msg"),
            AuthenticationException("msg"),
            UnauthorizedException(),
            ForbiddenException(),
            NotFoundException(),
            BadRequestException(),
            ServerErrorException(),
        ]

        for exc in exceptions:
            assert isinstance(exc, HttpClientException)

    def test_status_exceptions_inherit_from_status_exception(self):
        """Test status-specific exceptions inherit from HttpStatusException."""
        exceptions = [
            UnauthorizedException(),
            ForbiddenException(),
            NotFoundException(),
            BadRequestException(),
            ServerErrorException(),
        ]

        for exc in exceptions:
            assert isinstance(exc, HttpStatusException)
