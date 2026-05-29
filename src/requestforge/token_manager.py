from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging
from datetime import datetime
import threading

from requestforge.config import TokenData
from requestforge.exceptions import AuthenticationException
from requestforge.interfaces import (
    TokenManagerInterface,
    TokenStorageInterface,
    TokenProviderInterface,
)


if TYPE_CHECKING:
    from requestforge.client import HttpClient


logger = logging.getLogger(__name__)


class TokenRefreshException(AuthenticationException):
    """Raised when token refresh fails."""


# ==================== Storage Implementations ====================


class InMemoryTokenStorage(TokenStorageInterface):
    """
    Thread-safe in-memory token storage.
    Suitable for single-instance deployments.
    """

    def __init__(self) -> None:
        self._tokens: dict[str, TokenData] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> TokenData | None:
        with self._lock:
            return self._tokens.get(key)

    def set(self, key: str, token: TokenData) -> None:
        with self._lock:
            self._tokens[key] = token

    def delete(self, key: str) -> None:
        with self._lock:
            self._tokens.pop(key, None)

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._tokens

    def clear(self) -> None:
        """Clear all tokens."""
        with self._lock:
            self._tokens.clear()


class DjangoCacheTokenStorage(TokenStorageInterface):
    """
    Django cache-based token storage.
    Suitable for multi-instance deployments with shared cache (Redis, Memcached).
    """

    def __init__(
        self, cache_alias: str = "default", key_prefix: str = "token"
    ):
        self._cache_alias = cache_alias
        self._key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"

    def get(self, key: str) -> TokenData | None:
        from django.core.cache import caches

        cache = caches[self._cache_alias]
        data = cache.get(self._make_key(key))

        if data is None:
            return None

        # Reconstruct TokenData from cached dict
        return TokenData(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_at"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            extra=data.get("extra", {}),
        )

    def set(self, key: str, token: TokenData) -> None:
        from django.core.cache import caches

        cache = caches[self._cache_alias]

        # Calculate TTL from expiration
        ttl = None
        if token.expires_at:
            ttl = int((token.expires_at - datetime.now()).total_seconds())
            ttl = max(ttl, 60)  # Minimum 60 seconds

        # Store as dict for serialization
        data = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_at": token.expires_at,
            "refresh_token": token.refresh_token,
            "scope": token.scope,
            "extra": token.extra,
        }

        cache.set(self._make_key(key), data, timeout=ttl)

    def delete(self, key: str) -> None:
        from django.core.cache import caches

        cache = caches[self._cache_alias]
        cache.delete(self._make_key(key))

    def exists(self, key: str) -> bool:
        from django.core.cache import caches

        cache = caches[self._cache_alias]
        return cache.get(self._make_key(key)) is not None


# ==================== Token Provider Base ====================


class BaseOAuth2TokenProvider(TokenProviderInterface):
    """
    Base OAuth2 token provider.
    Subclass and implement _do_fetch_token and _do_refresh_token.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        service_name: str,
        scope: str | None = None,
        extra_params: dict[str, Any] | None = None,
    ):
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._service_name = service_name
        self._scope = scope
        self._extra_params = extra_params or {}

        # Lazy import to avoid circular dependency
        self._http_client: HttpClient | None = None

    @property
    def service_name(self) -> str:
        return self._service_name

    def _get_http_client(self) -> HttpClient:
        """Get HTTP client for token requests (without auth)."""
        if self._http_client is None:
            from requestforge.client import HttpClient
            from requestforge.config import HttpClientConfigBuilder

            config = HttpClientConfigBuilder().with_timeout(30).build()
            self._http_client = HttpClient(config)
        return self._http_client

    def fetch_token(self) -> TokenData:
        """Fetch new token using client credentials."""
        try:
            return self._do_fetch_token()
        except Exception as e:
            logger.error(f"[{self._service_name}] Token fetch failed: {e}")
            raise AuthenticationException(
                message=f"Failed to fetch token for {self._service_name}",
                service_name=self._service_name,
                original_exception=e,
            )

    def refresh_token(self, current_token: TokenData) -> TokenData:
        """Refresh existing token."""
        if current_token.refresh_token:
            try:
                return self._do_refresh_token(current_token)
            except Exception as e:
                logger.warning(
                    f"[{self._service_name}] Token refresh failed, fetching new token: {e}"
                )

        # Fallback to fetching new token
        return self.fetch_token()

    def _do_fetch_token(self) -> TokenData:
        """Override in subclass to implement token fetching."""
        raise NotImplementedError

    def _do_refresh_token(self, current_token: TokenData) -> TokenData:
        """Override in subclass to implement token refresh."""
        raise NotImplementedError


class ClientCredentialsTokenProvider(BaseOAuth2TokenProvider):
    """
    OAuth2 Client Credentials grant type token provider.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        service_name: str,
        scope: str | None = None,
        grant_type: str = "client_credentials",
        extra_params: dict[str, Any] | None = None,
        auth_method: str = "body",  # "body" or "header"
    ):
        super().__init__(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            service_name=service_name,
            scope=scope,
            extra_params=extra_params,
        )
        self._grant_type = grant_type
        self._auth_method = auth_method

    def _do_fetch_token(self) -> TokenData:
        client = self._get_http_client()

        data = {"grant_type": self._grant_type, **self._extra_params}

        if self._scope:
            data["scope"] = self._scope

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth = None

        if self._auth_method == "header":
            import base64

            credentials = f"{self._client_id}:{self._client_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        else:
            data["client_id"] = self._client_id
            data["client_secret"] = self._client_secret

        response = client.post(
            self._token_url, data=data, headers=headers, auth=auth
        )

        if not response.is_success:
            raise AuthenticationException(
                message=f"Token request failed with status {response.status_code}: {response.text}",
                service_name=self._service_name,
            )

        return TokenData.from_response(response.json())

    def _do_refresh_token(self, current_token: TokenData) -> TokenData:
        if not current_token.refresh_token:
            return self.fetch_token()

        client = self._get_http_client()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": current_token.refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        response = client.post(
            self._token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not response.is_success:
            # Fallback to new token
            return self.fetch_token()

        return TokenData.from_response(response.json())


class PasswordGrantTokenProvider(BaseOAuth2TokenProvider):
    """
    OAuth2 Password grant type token provider.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        service_name: str,
        scope: str | None = None,
        extra_params: dict[str, Any] | None = None,
    ):
        super().__init__(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            service_name=service_name,
            scope=scope,
            extra_params=extra_params,
        )
        self._username = username
        self._password = password

    def _do_fetch_token(self) -> TokenData:
        client = self._get_http_client()

        data = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": self._password,
            **self._extra_params,
        }

        if self._scope:
            data["scope"] = self._scope

        response = client.post(
            self._token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if not response.is_success:
            raise AuthenticationException(
                message=f"Token request failed: {response.text}",
                service_name=self._service_name,
            )

        return TokenData.from_response(response.json())

    def _do_refresh_token(self, current_token: TokenData) -> TokenData:
        return self.fetch_token()


# ==================== Token Manager ====================


class TokenManager(TokenManagerInterface):
    """
    Thread-safe token manager with caching.

    Features:
        - Automatic token caching
        - Thread-safe token refresh
        - Prevents concurrent token fetches
        - Automatic expiration handling
    """

    def __init__(
        self,
        provider: TokenProviderInterface,
        storage: TokenStorageInterface | None = None,
    ):
        self._storage: TokenStorageInterface = (
            storage or InMemoryTokenStorage()
        )

        super().__init__(
            provider=provider,
            storage=self._storage,
        )

        self._lock = threading.RLock()
        self._refresh_lock = threading.Lock()

    @property
    def _cache_key(self) -> str:
        return f"auth_token:{self._provider.service_name}"

    def get_token(self) -> TokenData:
        """Get valid token (from cache or fetch new)."""
        # Try to get from cache first
        token = self._storage.get(self._cache_key)

        if token and not token.is_expired:
            logger.debug(f"[{self._provider.service_name}] Using cached token")
            return token

        # Need to fetch/refresh - use lock to prevent concurrent fetches
        with self._refresh_lock:
            # Double-check after acquiring lock
            token = self._storage.get(self._cache_key)
            if token and not token.is_expired:
                return token

            logger.info(f"[{self._provider.service_name}] Fetching new token")

            if token and token.refresh_token:
                new_token = self._provider.refresh_token(token)
            else:
                new_token = self._provider.fetch_token()

            self._storage.set(self._cache_key, new_token)
            return new_token

    def invalidate_token(self) -> None:
        """Invalidate cached token."""
        with self._lock:
            logger.info(f"[{self._provider.service_name}] Invalidating token")
            self._storage.delete(self._cache_key)

    def force_refresh(self) -> TokenData:
        """Force fetch new token."""
        with self._refresh_lock:
            logger.info(
                f"[{self._provider.service_name}] Force refreshing token"
            )
            self.invalidate_token()
            new_token = self._provider.fetch_token()
            self._storage.set(self._cache_key, new_token)
            return new_token
