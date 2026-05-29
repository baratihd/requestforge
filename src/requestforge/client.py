from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, TypeVar
import logging
import threading
import contextlib
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

from requestforge.retry import NoRetryStrategy, ExponentialBackoffRetryStrategy
from requestforge.config import HttpClientConfig, HttpClientConfigBuilder
from requestforge.models import (
    HttpMethod,
    HttpRequest,
    HttpResponse,
    RequestContext,
)
from requestforge.exceptions import (
    SSLException,
    TimeoutException,
    MaxRetryException,
    ConnectionException,
    HttpClientException,
    HttpStatusException,
    ResponseParseException,
    AuthenticationException,
)
from requestforge.interfaces import (
    AuthHookInterface,
    HttpClientInterface,
    HttpSessionInterface,
)


if TYPE_CHECKING:
    from types import TracebackType
    from collections.abc import Iterator, Generator


logger = logging.getLogger(__name__)

T = TypeVar("T")


class HttpClient(HttpClientInterface, HttpSessionInterface):
    """Production-ready HTTP client implementation following SOLID principles."""

    def __init__(
        self,
        config: HttpClientConfig | None = None,
        session: requests.Session | None = None,
    ):
        self._config = config or HttpClientConfig()
        self._session = session
        self._session_lock = threading.Lock()
        self._local = threading.local()
        self._closed = False
        self._adapter: HTTPAdapter | None = None

    @property
    def adapter(self) -> HTTPAdapter:
        if self._adapter:
            return self._adapter

        self._adapter = HTTPAdapter(
            pool_connections=self._config.pool_connection,
            pool_maxsize=self._config.pool_maxsize,
            max_retries=0,
        )
        return self._adapter

    @property
    def session(self) -> requests.Session:
        """Get or create thread-safe session."""
        if self._session:
            return self._session

        if not hasattr(self._local, "session") or self._local.session is None:
            with self._session_lock:
                self._local.session = self._create_session()

        return self._local.session

    @property
    def auth_hook(self) -> AuthHookInterface | None:
        """Get the configured auth hook."""
        return self._config.auth_hook

    def _create_session(self) -> requests.Session:
        """Create and configure a new session."""
        session = requests.Session()

        session.headers.update(self._config.default_headers)
        session.headers.setdefault("Content-Type", "application/json")
        session.headers.setdefault("Accept", "application/json")

        session.mount("http://", self.adapter)
        session.mount("https://", self.adapter)

        return session

    def _build_url(self, url: str) -> str:
        """Build full URL from base URL and path."""
        if url.startswith(("http://", "https://")):
            return url

        base = self._config.base_url.rstrip("/")
        path = url.lstrip("/")

        if base:
            return f"{base}/{path}"
        return path

    def _map_exception(
        self, exception: Exception, context: RequestContext | None = None
    ) -> HttpClientException:
        """Map requests exceptions to our custom exceptions."""
        ctx = {"request": context.request if context else None}

        if isinstance(exception, requests.Timeout):
            return TimeoutException(
                message="Request timed out",
                original_exception=exception,
                context=ctx,
            )

        if isinstance(exception, requests.ConnectionError):
            return ConnectionException(
                message="Connection failed",
                original_exception=exception,
                context=ctx,
            )

        if isinstance(exception, requests.exceptions.SSLError):
            return SSLException(
                message="SSL/TLS error occurred",
                original_exception=exception,
                context=ctx,
            )

        if isinstance(exception, requests.JSONDecodeError):
            return ResponseParseException(
                message="Failed to parse JSON response",
                original_exception=exception,
                context=ctx,
            )

        if isinstance(exception, HttpClientException):
            return exception

        return HttpClientException(
            message=f"HTTP request failed: {exception}",
            original_exception=exception,
            context=ctx,
        )

    def _execute_hooks_before_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        """Execute all request hooks."""
        for hook in self._config.request_hooks:
            try:
                request = hook.before_request(request, context)
            except Exception as e:
                logger.warning(f"Request hook failed: {e}")
        return request

    def _execute_auth_hook(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpRequest:
        """Execute auth hook if configured."""
        auth_hook = self._config.auth_hook
        if auth_hook and auth_hook.should_authenticate(request):
            try:
                request = auth_hook.before_request(request, context)
            except Exception as e:
                logger.warning(f"Auth hook failed: {e}")
                raise AuthenticationException(
                    message=f"Authentication hook failed: {e}",
                    original_exception=e,
                )
        return request

    def _execute_hooks_after_response(
        self, response: HttpResponse, context: RequestContext
    ) -> HttpResponse:
        """Execute all response hooks."""
        for hook in self._config.response_hooks:
            try:
                response = hook.after_response(response, context)
            except Exception as e:
                logger.warning(f"Response hook failed: {e}")
        return response

    def _execute_hooks_on_error(
        self, exception: Exception, context: RequestContext
    ) -> None:
        """Execute all error hooks."""
        for hook in self._config.error_hooks:
            try:
                hook.on_error(exception, context)
            except Exception as e:
                logger.warning(f"Error hook failed: {e}")

    @staticmethod
    def _build_response(
        response: requests.Response, request: HttpRequest
    ) -> HttpResponse:
        """Convert requests.Response to our HttpResponse."""
        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            elapsed_ms=response.elapsed.total_seconds() * 1000,
            url=str(response.url),
            encoding=response.encoding,
            request=request,
        )

    def _execute_single_request(
        self, request: HttpRequest, context: RequestContext
    ) -> HttpResponse:
        """Execute a single HTTP request without retry logic."""
        url = self._build_url(request.url)
        headers = {**self._config.default_headers, **(request.headers or {})}
        timeout = request.timeout or self._config.default_timeout

        try:
            raw_response = self.session.request(
                method=request.method.value,
                url=url,
                headers=headers,
                params=request.params,
                data=request.data,
                json=request.json_data,
                files=request.files,
                timeout=timeout,
                auth=request.auth,
                verify=self._config.verify_ssl,
                allow_redirects=self._config.allow_redirects,
            )
        except Exception as e:
            raise self._map_exception(e, context)
        else:
            return self._build_response(raw_response, request)

    def request(self, request: HttpRequest) -> HttpResponse:
        """Execute an HTTP request with comprehensive retry logic and lifecycle hooks."""
        if self._closed:
            raise HttpClientException("Client is closed")

        retry_strategy = self._config.retry_strategy or NoRetryStrategy()
        auth_hook = self._config.auth_hook

        context = RequestContext(
            request=request,
            attempt=0,
            max_retries=retry_strategy.max_retries,
            metadata={},
        )

        auth_attempt = 0
        max_auth_retries = (
            auth_hook.retry_strategy.max_retries if auth_hook else 0
        )

        last_exception: Exception | None = None

        while True:
            try:
                modified_request = self._execute_hooks_before_request(
                    request, context
                )

                if auth_hook and auth_hook.should_authenticate(
                    modified_request
                ):
                    modified_request = self._execute_auth_hook(
                        modified_request, context
                    )

                response = self._execute_single_request(
                    modified_request, context
                )

                if auth_hook and auth_hook.is_auth_error(response):
                    auth_retry_strategy = auth_hook.retry_strategy

                    if auth_retry_strategy.should_retry(
                        response, auth_attempt
                    ):
                        delay = auth_retry_strategy.get_delay(auth_attempt)
                        logger.warning(
                            f"Auth error {response.status_code} (attempt {auth_attempt + 1}/"
                            f"{max_auth_retries + 1}), refreshing token"
                        )

                        if delay > 0:
                            time.sleep(delay)

                        if auth_hook.refresh_auth():
                            auth_attempt += 1
                            context.metadata["auth_retry"] = auth_attempt
                            continue

                        logger.error(
                            "Token refresh failed, returning auth error response"
                        )

                response = self._execute_hooks_after_response(
                    response, context
                )

                if isinstance(
                    retry_strategy, ExponentialBackoffRetryStrategy
                ) and retry_strategy.is_retryable_status(response.status_code):
                    status_exception = HttpStatusException(
                        message=f"HTTP {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text[:1000],
                    )

                    if retry_strategy.should_retry(context, status_exception):
                        delay = retry_strategy.get_delay(context)
                        logger.warning(
                            f"Retryable status {response.status_code}, retrying in {delay:.2f}s"
                        )
                        time.sleep(delay)
                        context.increment_attempt()

                        continue
                    # Max retries reached, return the error response
                    return response

                return response

            except HttpClientException as e:
                last_exception = e
                self._execute_hooks_on_error(e, context)

                if retry_strategy.should_retry(context, e):
                    delay = retry_strategy.get_delay(context)
                    logger.warning(
                        f"Request failed (attempt {context.attempt + 1}), retrying in {delay:.2f}s: {e}"
                    )

                    time.sleep(delay)
                    context.increment_attempt()
                else:
                    break

        raise MaxRetryException(
            message=f"Max retries ({retry_strategy.max_retries}) exceeded",
            attempts=context.attempt + 1,
            original_exception=last_exception,
            context={"request": request},
        )

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """Execute a GET request."""
        return self.request(
            HttpRequest(
                method=HttpMethod.GET,
                url=url,
                params=params,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
        )

    def post(
        self,
        url: str,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """Execute a POST request."""
        return self.request(
            HttpRequest(
                method=HttpMethod.POST,
                url=url,
                json_data=json_data,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
        )

    def put(
        self,
        url: str,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """Execute PUT request."""
        return self.request(
            HttpRequest(
                method=HttpMethod.PUT,
                url=url,
                json_data=json_data,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
        )

    def patch(
        self,
        url: str,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """Execute PATCH request."""
        return self.request(
            HttpRequest(
                method=HttpMethod.PATCH,
                url=url,
                json_data=json_data,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
        )

    def delete(
        self,
        url: str,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """Execute DELETE request."""
        return self.request(
            HttpRequest(
                method=HttpMethod.DELETE,
                url=url,
                json_data=json_data,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
        )

    def request_many(
        self,
        requests_list: list[HttpRequest],
        max_workers: int = 5,
        fail_fast: bool = False,
    ) -> Generator[tuple[int, HttpResponse | HttpClientException], None, None]:
        """Execute multiple HTTP requests concurrently."""

        def execute_with_index(
            _index: int, req: HttpRequest
        ) -> tuple[int, HttpResponse | HttpClientException]:
            try:
                return _index, self.request(req)
            except HttpClientException as exec_error:
                if fail_fast:
                    raise exec_error
                return _index, exec_error
            except Exception as unexpected_error:
                if fail_fast:
                    raise HttpClientException(
                        f"Unexpected error: {unexpected_error}"
                    ) from unexpected_error
                return _index, HttpClientException(
                    f"Unexpected error: {unexpected_error}"
                )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(execute_with_index, i, req): i
                for i, req in enumerate(requests_list)
            }

            for future in as_completed(futures):
                try:
                    index, result = future.result()
                    yield index, result
                except Exception as e:
                    if fail_fast:
                        raise e
                    yield (
                        futures[future],
                        HttpClientException(f"Execution failed: {e}"),
                    )

    def close(self) -> None:
        """Close the client and release all resources."""
        self._closed = True

        if hasattr(self._local, "session") and self._local.session:
            self._local.session.close()
            self._local.session = None

        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        with contextlib.suppress(Exception):
            if not self._closed:
                self.close()


def create_client(
    base_url: str = "",
    timeout: float = 30.0,
    max_retries: int = 3,
    headers: dict[str, str] | None = None,
    enable_logging: bool = True,
    auth_hook: AuthHookInterface | None = None,
) -> HttpClient:
    """Factory function to create a configured HTTP client."""
    builder = (
        HttpClientConfigBuilder()
        .with_base_url(base_url)
        .with_timeout(timeout)
        .with_retry(max_retries=max_retries)
    )

    if headers:
        builder.with_headers(headers)

    if enable_logging:
        builder.with_logging()

    if auth_hook:
        builder.with_auth_hook(auth_hook)

    return HttpClient(builder.build())


@contextmanager
def http_client(base_url: str = "", **kwargs: Any) -> Iterator[HttpClient]:
    """Context manager for HTTP client."""
    client = create_client(base_url=base_url, **kwargs)
    try:
        yield client
    finally:
        client.close()
