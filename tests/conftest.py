"""
Pytest configuration and shared fixtures.
"""

from unittest.mock import Mock

import pytest
import responses

from requestforge.client import HttpClient
from requestforge.config import (
    TokenData,
    HttpClientConfigBuilder,
)
from requestforge.models import (
    HttpMethod,
    HttpRequest,
    RequestContext,
)
from requestforge.token_manager import (
    TokenManager,
    InMemoryTokenStorage,
)


@pytest.fixture()
def mock_response():
    """Create a mock HTTP response."""
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.content = b'{"success": true}'
    response.text = '{"success": true}'
    response.elapsed.total_seconds.return_value = 0.1
    response.url = "https://api.example.com/test"
    response.encoding = "utf-8"
    return response


@pytest.fixture()
def http_request():
    """Create a basic HTTP request."""
    return HttpRequest(
        method=HttpMethod.GET,
        url="/users",
        headers={"X-Test": "test-value"},
        params={"page": 1},
    )


@pytest.fixture()
def request_context(http_request):
    """Create a request context."""
    return RequestContext(
        request=http_request, attempt=0, max_retries=3, metadata={}
    )


@pytest.fixture()
def requestforge_config():
    """Create a basic HTTP client configuration."""
    return (
        HttpClientConfigBuilder()
        .with_base_url("https://api.example.com")
        .with_timeout(30.0)
        .build()
    )


@pytest.fixture()
def requestforge_instance(requestforge_config):
    """Create an HTTP client instance."""
    return HttpClient(requestforge_config)


@pytest.fixture()
def token_storage():
    """Create in-memory token storage."""
    return InMemoryTokenStorage()


@pytest.fixture()
def token_data():
    """Create token data."""
    from datetime import datetime, timedelta

    return TokenData(
        access_token="test-token-123",
        token_type="Bearer",
        expires_at=datetime.now() + timedelta(hours=1),
        refresh_token="refresh-token-123",
    )


@pytest.fixture()
def mock_token_provider():
    """Create a mock token provider."""
    provider = Mock()
    provider.service_name = "test-service"
    provider.fetch_token.return_value = TokenData(
        access_token="test-token",
        token_type="Bearer",
    )
    return provider


@pytest.fixture()
def token_manager(mock_token_provider, token_storage):
    """Create a token manager."""
    return TokenManager(mock_token_provider, token_storage)


@pytest.fixture()
def responses_mock():
    """Responses mock for mocking HTTP requests."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture()
def mock_hook():
    """Create a mock hook."""
    hook = Mock()
    hook.before_request = Mock(side_effect=lambda req, ctx: req)
    hook.after_response = Mock(side_effect=lambda res, ctx: res)
    hook.on_error = Mock()
    return hook


@pytest.fixture(autouse=True)
def reset_logging():  # noqa: PT004
    """Reset logging between tests."""
    import logging

    logger = logging.getLogger("requestforge")
    logger.handlers = []
    yield
    logger.handlers = []
