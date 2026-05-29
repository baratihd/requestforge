from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING
import fnmatch
import logging
import threading

from requestforge.retry import SimpleAuthRetryStrategy
from requestforge.interfaces import (
    AuthHookInterface,
    ErrorHookInterface,
    RequestHookInterface,
    ResponseHookInterface,
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from requestforge.config import TokenData
    from requestforge.models import HttpRequest, HttpResponse, RequestContext
    from requestforge.interfaces import (
        TokenManagerInterface,
        AuthRetryStrategyInterface,
    )

logger = logging.getLogger(__name__)


class LoggingRequestHook(RequestHookInterface):
    """Hook for logging outgoing requests."""

    def __init__(
        self,
        log_headers: bool = False,
        log_body: bool = False,
        sensitive_keys: set[str] | None = None,
    ):
        self._log_headers = log_headers
        self._log_body = log_body
        self._sensitive_keys = sensitive_keys

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        request_id = (
            context.metadata.get("request_id") or str(uuid.uuid4())[:8]
        )
        context.metadata["request_id"] = request_id
        context.metadata["start_time"] = time.time()

        log_parts = [
            f"[{request_id}] HTTP {request.method.value} {request.url}"
        ]

        if context.is_retry:
            log_parts.append(f"(retry #{context.attempt})")

        logger.info(" ".join(log_parts))

        if self._log_headers and request.headers:
            safe_headers = self._mask_sensitive_headers(request.headers)
            logger.debug(f"[{request_id}] Headers: {safe_headers}")

        if self._log_body and request.json_data:
            logger.debug(f"[{request_id}] Body: {request.json_data}")

        return request

    def _mask_sensitive_headers(
        self, headers: dict[str, str]
    ) -> dict[str, str]:
        """Mask sensitive header values."""
        sensitive_keys = self._sensitive_keys or {
            "authorization",
            "x-api-key",
            "api-key",
            "cookie",
            "set-cookie",
        }
        return {
            k: "***" if k.lower() in sensitive_keys else v
            for k, v in headers.items()
        }


class LoggingResponseHook(ResponseHookInterface):
    """Hook for logging responses."""

    def __init__(self, log_headers: bool = False, log_body: bool = False):
        self._log_headers = log_headers
        self._log_body = log_body

    def after_response(
        self, response: HttpResponse, context: RequestContext
    ) -> HttpResponse:
        request_id = context.metadata.get("request_id", "unknown")
        start_time = context.metadata.get("start_time", 0)
        duration = (
            (time.time() - start_time) * 1000
            if start_time
            else response.elapsed_ms
        )

        log_level = logging.INFO if response.is_success else logging.WARNING

        logger.log(
            log_level,
            f"[{request_id}] Response: {response.status_code} ({duration:.2f}ms)",
        )

        if self._log_headers:
            logger.debug(
                f"[{request_id}] Response Headers: {dict(response.headers)}"
            )

        if self._log_body and not response.is_success:
            logger.debug(
                f"[{request_id}] Response Body: {response.text[:500]}"
            )

        return response


class LoggingErrorHook(ErrorHookInterface):
    """Hook for logging errors."""

    def on_error(self, exception: Exception, context: RequestContext) -> None:
        request_id = context.metadata.get("request_id", "unknown")
        logger.error(
            f"[{request_id}] Request failed, (request: {context.request.to_dict()}) (attempt {context.attempt + 1}/"
            f"{context.max_retries + 1}): {type(exception).__name__}: {exception}"
        )


class AuthorizationHook(RequestHookInterface):
    """Hook for adding authorization headers."""

    def __init__(self, token_provider: Callable):
        self._token_provider = token_provider

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        token = self._token_provider()
        if token:
            return request.with_headers({"Authorization": f"Bearer {token}"})
        return request


class CorrelationIdHook(RequestHookInterface):
    """Hook for adding correlation ID to requests."""

    def __init__(self, header_name: str = "X-Correlation-ID"):
        self._header_name = header_name

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        correlation_id = context.metadata.get("correlation_id") or str(
            uuid.uuid4()
        )
        context.metadata["correlation_id"] = correlation_id
        return request.with_headers({self._header_name: correlation_id})


class RateLimitResponseHook(ResponseHookInterface):
    """Hook for handling rate limit headers."""

    def after_response(
        self, response: HttpResponse, context: RequestContext
    ) -> HttpResponse:
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
        rate_limit_reset = response.headers.get("X-RateLimit-Reset")

        if rate_limit_remaining:
            context.metadata["rate_limit_remaining"] = int(
                rate_limit_remaining
            )
        if rate_limit_reset:
            context.metadata["rate_limit_reset"] = int(rate_limit_reset)

        return response


class TokenAuthHook(AuthHookInterface):
    """Token-based authentication hook."""

    def __init__(
        self,
        token_manager: TokenManagerInterface,
        retry_strategy: AuthRetryStrategyInterface | None = None,
        auth_header_name: str = "Authorization",
        auth_header_prefix: str = "Bearer",
        excluded_paths: set[str] | None = None,
        excluded_path_patterns: list[str] | None = None,
    ):
        self._token_manager = token_manager
        self._retry_strategy = retry_strategy or SimpleAuthRetryStrategy(
            max_retries=1
        )
        self._auth_header_name = auth_header_name
        self._auth_header_prefix = auth_header_prefix
        self._excluded_paths = excluded_paths or set()
        self._excluded_patterns = excluded_path_patterns or []
        self._lock = threading.RLock()

    @property
    def retry_strategy(self) -> AuthRetryStrategyInterface:
        return self._retry_strategy

    @property
    def token_manager(self) -> TokenManagerInterface:
        """Get the token manager for direct access if needed."""
        return self._token_manager

    def should_authenticate(self, request: HttpRequest) -> bool:
        url = request.url

        if url.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            url = urlparse(url).path

        if url in self._excluded_paths:
            logger.debug(f"Path {url} excluded from auth (exact match)")
            return False

        for pattern in self._excluded_patterns:
            if fnmatch.fnmatch(url, pattern):
                logger.debug(
                    f"Path {url} excluded from auth (pattern: {pattern})"
                )
                return False

        return True

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        if not self.should_authenticate(request):
            return request

        token = self.get_token()

        if self._auth_header_prefix:
            auth_value = f"{self._auth_header_prefix} {token.access_token}"
        else:
            auth_value = token.access_token

        return request.with_headers({self._auth_header_name: auth_value})

    def is_auth_error(self, response: HttpResponse) -> bool:
        return self._retry_strategy.is_auth_error(response)

    def refresh_auth(self) -> bool:
        with self._lock:
            try:
                logger.info("Refreshing authentication token")
                self._token_manager.force_refresh()
                logger.info("Token refresh successful")
                return True
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                return False

    def invalidate_auth(self) -> None:
        with self._lock:
            logger.info("Invalidating authentication token")
            self._token_manager.invalidate_token()

    def get_token(self) -> TokenData:
        return self._token_manager.get_token()


class ApiKeyAuthHook(AuthHookInterface):
    """API Key authentication hook."""

    def __init__(
        self,
        api_key: str,
        header_name: str = "X-API-Key",
        retry_strategy: AuthRetryStrategyInterface | None = None,
        excluded_paths: set[str] | None = None,
    ):
        from requestforge.retry import NoAuthRetryStrategy

        self._api_key = api_key
        self._header_name = header_name
        self._retry_strategy = retry_strategy or NoAuthRetryStrategy()
        self._excluded_paths = excluded_paths or set()

    @property
    def retry_strategy(self) -> AuthRetryStrategyInterface:
        return self._retry_strategy

    def should_authenticate(self, request: HttpRequest) -> bool:
        url = request.url
        if url.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            url = urlparse(url).path
        return url not in self._excluded_paths

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        if not self.should_authenticate(request):
            return request
        return request.with_headers({self._header_name: self._api_key})

    def is_auth_error(self, response: HttpResponse) -> bool:
        return self._retry_strategy.is_auth_error(response)

    def refresh_auth(self) -> bool:
        return False

    def invalidate_auth(self) -> None:
        pass

    def get_token(self) -> TokenData:
        from requestforge.config import TokenData

        return TokenData(access_token=self._api_key, token_type="ApiKey")


class BasicAuthHook(AuthHookInterface):
    """HTTP Basic Authentication hook."""

    def __init__(
        self,
        username: str,
        password: str,
        retry_strategy: AuthRetryStrategyInterface | None = None,
        excluded_paths: set[str] | None = None,
    ):
        import base64

        from requestforge.retry import NoAuthRetryStrategy

        self._credentials = base64.b64encode(
            f"{username}:{password}".encode()
        ).decode()
        self._retry_strategy = retry_strategy or NoAuthRetryStrategy()
        self._excluded_paths = excluded_paths or set()

    @property
    def retry_strategy(self) -> AuthRetryStrategyInterface:
        return self._retry_strategy

    def should_authenticate(self, request: HttpRequest) -> bool:
        url = request.url
        if url.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            url = urlparse(url).path
        return url not in self._excluded_paths

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        if not self.should_authenticate(request):
            return request
        return request.with_headers(
            {"Authorization": f"Basic {self._credentials}"}
        )

    def is_auth_error(self, response: HttpResponse) -> bool:
        return self._retry_strategy.is_auth_error(response)

    def refresh_auth(self) -> bool:
        return False

    def invalidate_auth(self) -> None:
        pass

    def get_token(self) -> TokenData:
        from requestforge.config import TokenData

        return TokenData(access_token=self._credentials, token_type="Basic")


class CompositeAuthHook(AuthHookInterface):
    """Composite auth hook that combines multiple authentication methods."""

    def __init__(
        self,
        hooks: list[AuthHookInterface],
        strategy: str = "first_match",
        retry_strategy: AuthRetryStrategyInterface | None = None,
    ):
        self._hooks = hooks
        self._strategy = strategy
        self._retry_strategy = retry_strategy or (
            hooks[0].retry_strategy if hooks else SimpleAuthRetryStrategy()
        )

    @property
    def retry_strategy(self) -> AuthRetryStrategyInterface:
        return self._retry_strategy

    def _find_applicable_hook(
        self, request: HttpRequest
    ) -> AuthHookInterface | None:
        for hook in self._hooks:
            if hook.should_authenticate(request):
                return hook
        return None

    def should_authenticate(self, request: HttpRequest) -> bool:
        return self._find_applicable_hook(request) is not None

    def before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        if self._strategy == "first_match":
            hook = self._find_applicable_hook(request)
            if hook:
                return hook.before_request(request, context)
        elif self._strategy == "all":
            for hook in self._hooks:
                if hook.should_authenticate(request):
                    request = hook.before_request(request, context)
        return request

    def is_auth_error(self, response: HttpResponse) -> bool:
        return any(hook.is_auth_error(response) for hook in self._hooks)

    def refresh_auth(self) -> bool:
        return any(hook.refresh_auth() for hook in self._hooks)

    def invalidate_auth(self) -> None:
        for hook in self._hooks:
            hook.invalidate_auth()

    def get_token(self) -> TokenData:
        if self._hooks:
            return self._hooks[0].get_token()
        from requestforge.config import TokenData

        return TokenData(access_token="", token_type="")
