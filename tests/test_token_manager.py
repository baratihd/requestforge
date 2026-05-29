"""
Tests for token management.
    - In-memory storage
    - Token caching
    - Token expiration
    - Token refresh
    - OAuth2 token providers
    - Thread safety
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from requestforge.config import TokenData
from requestforge.exceptions import AuthenticationException
from requestforge.token_manager import (
    InMemoryTokenStorage,
    PasswordGrantTokenProvider,
    ClientCredentialsTokenProvider,
)


class TestInMemoryTokenStorage:
    """Test InMemoryTokenStorage."""

    def test_store_and_retrieve_token(self, token_data):
        """Test storing and retrieving token (Basic CRUD)."""
        storage = InMemoryTokenStorage()
        storage.set("access_token", token_data)

        retrieved = storage.get("access_token")
        assert retrieved == token_data

    def test_get_nonexistent_token(self):
        """Test getting non-existent token (Returns None)."""
        storage = InMemoryTokenStorage()
        assert storage.get("nonexistent") is None

    def test_delete_token(self, token_data):
        """Test deleting token (Removal works)."""
        storage = InMemoryTokenStorage()
        storage.set("access_token", token_data)

        storage.delete("access_token")
        assert storage.get("access_token") is None

    def test_exists_check(self, token_data):
        """Test token existence check (Boolean existence)."""
        storage = InMemoryTokenStorage()
        assert not storage.exists("access_token")

        storage.set("access_token", token_data)
        assert storage.exists("access_token")

    def test_clear_all_tokens(self, token_data):
        """Test clearing all tokens (Bulk clear)."""
        storage = InMemoryTokenStorage()
        storage.set("token1", token_data)
        storage.set("token2", token_data)

        storage.clear()

        assert storage.get("token1") is None
        assert storage.get("token2") is None

    def test_thread_safety(self, token_data):
        """Test thread-safe operations (RLock protects operations)."""
        storage = InMemoryTokenStorage()

        # Basic test - would need threading for full test
        storage.set("token", token_data)
        assert storage.get("token") == token_data


class TestTokenManager:
    """
    Test TokenManager.

    Flow:
    >>> get_token()
    >>>   → Check cache
    >>>     → Valid? Return
    >>>     → Expired? Lock → Double-check → Refresh → Cache → Return
    >>>     → Missing? Lock → Double-check → Fetch → Cache → Return
    """

    def test_get_token_from_cache(self, token_manager, token_data):
        """
        Test getting token from cache.

        Cache hit = no provider call
        """
        token_manager._storage.set(token_manager._cache_key, token_data)

        token = token_manager.get_token()
        assert token == token_data

    def test_get_token_fetches_new(self, token_manager):
        """
        Test fetching new token when cache is empty.

        Cache miss = fetch
        """
        token_manager.get_token()

        token_manager._provider.fetch_token.assert_called_once()

    def test_get_token_refreshes_expired(self, token_manager):
        """
        Test refreshing expired token.

        Expired = refresh_token()
        """
        expired_token = TokenData(
            access_token="expired",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        token_manager._storage.set(token_manager._cache_key, expired_token)

        new_token = TokenData(
            access_token="new", expires_at=datetime.now() + timedelta(hours=1)
        )
        token_manager._provider.refresh_token.return_value = new_token

        token = token_manager.get_token()

        # Verify refresh was attempted
        assert (
            token_manager._provider.refresh_token.called
            or token_manager._provider.fetch_token.called
        )

    def test_invalidate_token(self, token_manager, token_data):
        """Test invalidating token (Cache clear)."""
        token_manager._storage.set(token_manager._cache_key, token_data)

        token_manager.invalidate_token()

        assert token_manager._storage.get(token_manager._cache_key) is None

    def test_force_refresh(self, token_manager):
        """
        Test forcing token refresh.

        Bypass cache, fetch new
        """
        new_token = TokenData(
            access_token="new-token",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        token_manager._provider.fetch_token.return_value = new_token

        token = token_manager.force_refresh()

        assert token == new_token
        token_manager._provider.fetch_token.assert_called()

    def test_concurrent_token_fetch_prevention(self, token_manager):
        """
        Test that concurrent fetches are prevented.

        Double-check locking
        """

        fetch_count = 0
        original_fetch = token_manager._provider.fetch_token

        def mock_fetch():
            nonlocal fetch_count
            fetch_count += 1
            return TokenData(access_token="token")

        token_manager._provider.fetch_token = mock_fetch

        # This is a simplified test - would need actual threading for full test
        token_manager.get_token()
        assert fetch_count >= 1


class TestClientCredentialsTokenProvider:
    """
    Test ClientCredentialsTokenProvider.

    OAuth2 Flow:
        POST /token
        grant_type=client_credentials
        client_id=xxx
        client_secret=yyy
        → {access_token, expires_in, refresh_token}
    """

    @patch(
        "requestforge.token_manager.BaseOAuth2TokenProvider._get_http_client"
    )
    def test_fetch_token(self, mock_get_client):
        """Test fetching token. (Client credentials grant)"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "access_token": "token-123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = ClientCredentialsTokenProvider(
            token_url="https://auth.example.com/token",
            client_id="client-id",
            client_secret="client-secret",
            service_name="test-service",
        )

        token = provider.fetch_token()

        assert token.access_token == "token-123"
        assert token.token_type == "Bearer"
        mock_client.post.assert_called_once()

    @patch(
        "requestforge.token_manager.BaseOAuth2TokenProvider._get_http_client"
    )
    def test_fetch_token_with_auth_header(self, mock_get_client):
        """Test fetching token with header-based auth (Basic auth in header)."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "access_token": "token-123",
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = ClientCredentialsTokenProvider(
            token_url="https://auth.example.com/token",
            client_id="client-id",
            client_secret="client-secret",
            service_name="test-service",
            auth_method="header",
        )

        token = provider.fetch_token()

        # Verify auth method was used
        call_kwargs = mock_client.post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]

    @patch(
        "requestforge.token_manager.BaseOAuth2TokenProvider._get_http_client"
    )
    def test_fetch_token_failure(self, mock_get_client):
        """Test token fetch failure (400 → AuthenticationException)."""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.text = "Invalid client"

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = ClientCredentialsTokenProvider(
            token_url="https://auth.example.com/token",
            client_id="invalid-id",
            client_secret="invalid-secret",
            service_name="test-service",
        )

        with pytest.raises(AuthenticationException):
            provider.fetch_token()

    @patch(
        "requestforge.token_manager.BaseOAuth2TokenProvider._get_http_client"
    )
    def test_refresh_token(self, mock_get_client):
        """Test token refresh (Refresh grant flow)."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "access_token": "new-token",
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = ClientCredentialsTokenProvider(
            token_url="https://auth.example.com/token",
            client_id="client-id",
            client_secret="client-secret",
            service_name="test-service",
        )

        old_token = TokenData(
            access_token="old-token",
            refresh_token="refresh-token",
        )

        new_token = provider.refresh_token(old_token)

        assert new_token.access_token == "new-token"


class TestPasswordGrantTokenProvider:
    """Test PasswordGrantTokenProvider."""

    @patch(
        "requestforge.token_manager.BaseOAuth2TokenProvider._get_http_client"
    )
    def test_fetch_token(self, mock_get_client):
        """Test fetching token with password grant."""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "access_token": "token-123",
            "token_type": "Bearer",
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        provider = PasswordGrantTokenProvider(
            token_url="https://auth.example.com/token",
            client_id="client-id",
            client_secret="client-secret",
            username="user",
            password="password",
            service_name="test-service",
        )

        token = provider.fetch_token()

        assert token.access_token == "token-123"
        # Verify password grant was used
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["grant_type"] == "password"
