from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any
import logging
from datetime import datetime, timedelta

from requestforge.config import TokenData
from requestforge.models import HttpMethod
from requestforge.exceptions import AuthenticationException
from requestforge.interfaces import TokenFetcherInterface


if TYPE_CHECKING:
    from requestforge.client import HttpClient
    from requestforge.models import HttpResponse


logger = logging.getLogger(__name__)


class HttpTokenFetcher(TokenFetcherInterface):
    """
    Base class for HTTP-based token fetchers.

    Provides common HTTP client setup and configuration.
    Subclasses implement the specific fetch logic.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        headers: dict[str, str] | None = None,
    ):
        """
        Initialize HTTP token fetcher.

        Args:
            base_url: Base URL for token endpoint.
            timeout: Request timeout in seconds.
            verify_ssl: Whether to verify SSL certificates.
            headers: Default headers for requests.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._default_headers = headers or {}
        self._client: HttpClient | None = None

    def _get_client(self) -> HttpClient:
        """Get or create HTTP client."""
        if self._client is None:
            from requestforge.client import HttpClient
            from requestforge.config import HttpClientConfigBuilder

            self._client = HttpClient(
                HttpClientConfigBuilder()
                .with_base_url(self._base_url)
                .with_timeout(self._timeout)
                .with_verify_ssl(self._verify_ssl)
                .with_headers(self._default_headers)
                .build()
            )
        return self._client

    def _make_request(
        self,
        method: HttpMethod,
        endpoint: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """Make HTTP request."""
        client = self._get_client()

        if method.upper() == HttpMethod.POST:
            return client.post(
                endpoint, headers=headers, data=data, json_data=json_data
            )
        if method.upper() == HttpMethod.GET:
            return client.get(endpoint, headers=headers, params=data)
        raise ValueError(f"Unsupported method: {method}")

    @abstractmethod
    def fetch(self, context: dict[str, TokenData] | None = None) -> TokenData:
        """
        Fetch token for this step.

        Args:
            context: Dict containing tokens from previous steps.
                     Keys are step names, values are TokenData.
                     None if this is the first step.

        Returns:
            TokenData containing the fetched token.

        Raises:
            AuthenticationException: If token fetch fails.
        """

    def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


class HeaderTokenFetcher(HttpTokenFetcher):
    """
    Token fetcher that extracts token from response headers.

    Useful for APIs that return tokens in headers rather than body.

    Example:
        >>> fetcher = HeaderTokenFetcher(
        ...     name='app_token',
        ...     base_url='https://api.example.com',
        ...     endpoint='/auth/token',
        ...     method=HttpMethod.POST,
        ...     request_headers={'appname': 'my-app', 'secret': 'secret'},
        ...     token_header='X-Auth-Token',
        ... )
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        endpoint: str,
        method: HttpMethod = HttpMethod.POST,
        request_headers: dict[str, str] | None = None,
        request_data: dict[str, Any] | None = None,
        token_header: str = "Authorization",
        token_type: str = "Bearer",
        ttl: timedelta | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        depends_on: list[str] | None = None,
    ):
        """
        Initialize header token fetcher.

        Args:
            name: Step name.
            base_url: Base URL for API.
            endpoint: Token endpoint path.
            method: HTTP method (GET or POST).
            request_headers: Headers to send with request.
            request_data: Data/params to send with request.
            token_header: Response header containing token.
            token_type: Token type for TokenData.
            ttl: Time-to-live for cached token.
            timeout: Request timeout.
            verify_ssl: Whether to verify SSL.
            depends_on: List of dependency step names.
        """
        super().__init__(base_url, timeout, verify_ssl)
        self._name = name
        self._endpoint = endpoint
        self._method = method
        self._request_headers = request_headers or {}
        self._request_data = request_data or {}
        self._token_header = token_header
        self._token_type = token_type
        self._ttl = ttl
        self._depends_on = depends_on or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return self._depends_on

    @property
    def ttl(self) -> timedelta | None:
        return self._ttl

    def _build_request_headers(
        self, context: dict[str, TokenData] | None
    ) -> dict[str, str]:
        """Build request headers, potentially using tokens from context."""
        return dict(self._request_headers)

    def fetch(self, context: dict[str, TokenData] | None = None) -> TokenData:
        headers = self._build_request_headers(context)

        response = self._make_request(
            method=self._method,
            endpoint=self._endpoint,
            headers=headers,
            data=self._request_data
            if self._method.upper() == HttpMethod.POST
            else None,
        )

        if not response.is_success:
            raise AuthenticationException(
                message=f"Token request failed with status {response.status_code}: {response.text[:500]}",
                service_name=self._name,
            )

        token_value = response.headers.get(self._token_header)
        if not token_value:
            raise AuthenticationException(
                message=f"Token header '{self._token_header}' not found in response",
                service_name=self._name,
            )

        expires_at = None
        if self._ttl:
            expires_at = datetime.now() + self._ttl

        return TokenData(
            access_token=token_value,
            token_type=self._token_type,
            expires_at=expires_at,
        )


class BodyTokenFetcher(HttpTokenFetcher):
    """
    Token fetcher that extracts token from response body (JSON).

    Useful for standard OAuth2 and similar token endpoints.

    Example:
        >>> fetcher = BodyTokenFetcher(
        ...     name='access_token',
        ...     base_url='https://auth.example.com',
        ...     endpoint='/oauth/token',
        ...     method=HttpMethod.POST,
        ...     request_data={
        ...         'grant_type': 'client_credentials',
        ...         'client_id': 'my-client',
        ...         'client_secret': 'my-secret',
        ...     },
        ...     token_field='access_token',
        ...     expires_in_field='expires_in',
        ... )
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        endpoint: str,
        method: HttpMethod = HttpMethod.POST,
        request_headers: dict[str, str] | None = None,
        request_data: dict[str, Any] | None = None,
        content_type: str = "form",  # 'form' or 'json'
        token_field: str = "access_token",
        token_type_field: str = "token_type",
        expires_in_field: str = "expires_in",
        refresh_token_field: str = "refresh_token",
        default_token_type: str = "Bearer",
        ttl: timedelta | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        depends_on: list[str] | None = None,
    ):
        """
        Initialize body token fetcher.

        Args:
            name: Step name.
            base_url: Base URL for API.
            endpoint: Token endpoint path.
            method: HTTP method.
            request_headers: Headers to send.
            request_data: Request body data.
            content_type: 'form' for form-encoded, 'json' for JSON.
            token_field: JSON field containing access token.
            token_type_field: JSON field containing token type.
            expires_in_field: JSON field containing expires_in seconds.
            refresh_token_field: JSON field containing refresh token.
            default_token_type: Default token type if not in response.
            ttl: Override TTL for cached token.
            timeout: Request timeout.
            verify_ssl: Whether to verify SSL.
            depends_on: List of dependency step names.
        """
        super().__init__(base_url, timeout, verify_ssl)
        self._name = name
        self._endpoint = endpoint
        self._method = method
        self._request_headers = request_headers or {}
        self._request_data = request_data or {}
        self._content_type = content_type
        self._token_field = token_field
        self._token_type_field = token_type_field
        self._expires_in_field = expires_in_field
        self._refresh_token_field = refresh_token_field
        self._default_token_type = default_token_type
        self._ttl = ttl
        self._depends_on = depends_on or []

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return self._depends_on

    @property
    def ttl(self) -> timedelta | None:
        return self._ttl

    def _build_request_data(
        self, context: dict[str, TokenData] | None
    ) -> dict[str, Any]:
        """Build request data, potentially using tokens from context."""
        return dict(self._request_data)

    def fetch(self, context: dict[str, TokenData] | None = None) -> TokenData:
        headers = dict(self._request_headers)
        data = self._build_request_data(context)

        if self._content_type == "form":
            headers.setdefault(
                "Content-Type", "application/x-www-form-urlencoded"
            )
            response = self._make_request(
                method=self._method,
                endpoint=self._endpoint,
                headers=headers,
                data=data,
            )
        else:
            headers.setdefault("Content-Type", "application/json")
            response = self._make_request(
                method=self._method,
                endpoint=self._endpoint,
                headers=headers,
                json_data=data,
            )

        if not response.is_success:
            raise AuthenticationException(
                message=f"Token request failed with status {response.status_code}: {response.text[:500]}",
                service_name=self._name,
            )

        try:
            body = response.json()
        except Exception as e:
            raise AuthenticationException(
                message=f"Failed to parse token response: {e}",
                service_name=self._name,
                original_exception=e,
            )

        token_value = body.get(self._token_field)
        if not token_value:
            raise AuthenticationException(
                message=f"Token field '{self._token_field}' not found in response",
                service_name=self._name,
            )

        # Parse expiration
        expires_at = None
        if self._ttl:
            expires_at = datetime.now() + self._ttl
        elif self._expires_in_field in body:
            expires_in = int(body[self._expires_in_field])
            expires_at = datetime.now() + timedelta(seconds=expires_in)

        return TokenData(
            access_token=token_value,
            token_type=body.get(
                self._token_type_field, self._default_token_type
            ),
            expires_at=expires_at,
            refresh_token=body.get(self._refresh_token_field),
        )
