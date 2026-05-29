from __future__ import annotations

from typing import TYPE_CHECKING
import logging
from datetime import datetime

from requestforge.config import TokenData
from requestforge.models import FetchContext
from requestforge.exceptions import AuthenticationException
from requestforge.interfaces import TokenProviderInterface


if TYPE_CHECKING:
    from requestforge.interfaces import (
        TokenFetcherInterface,
        TokenStorageInterface,
    )

logger = logging.getLogger(__name__)


class TokenFetchPipeline:
    """
    Pipeline for multi-step token fetching with caching.

    Executes token fetchers in order, caching results at each step.
    Handles dependencies between steps automatically.

    Features:
        - Per-step caching with configurable TTL
        - Dependency resolution between steps
        - Selective cache invalidation
        - Thread-safe execution

    Example:
        >>> from requestforge.token_manager import InMemoryTokenStorage
        >>>
        >>> pipeline = TokenFetchPipeline(
        ...     steps=[
        ...         AppTokenFetcher(...),
        ...         AuthTokenFetcher(...),
        ...     ],
        ...     storage=InMemoryTokenStorage(),
        ...     cache_key_prefix='myservice',
        ... )
        >>>
        >>> # Execute pipeline
        >>> token = pipeline.execute()
        >>>
        >>> # Invalidate specific step
        >>> pipeline.invalidate_step('app_token')
        >>>
        >>> # Invalidate all steps
        >>> pipeline.invalidate_all()
    """

    def __init__(
        self,
        steps: list[TokenFetcherInterface],
        storage: TokenStorageInterface,
        cache_key_prefix: str = "",
        validate_dependencies: bool = True,
    ):
        """
        Initialize pipeline.

        Args:
            steps: List of token fetchers in execution order.
            storage: Token storage for caching.
            cache_key_prefix: Prefix for all cache keys.
            validate_dependencies: If True, validates dependencies on init.

        Raises:
            ValueError: If dependencies are invalid.
        """
        self._steps = steps
        self._storage = storage
        self._cache_key_prefix = cache_key_prefix
        self._step_map = {step.name: step for step in steps}

        if validate_dependencies:
            self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """Validate that all dependencies can be satisfied."""
        available = set()
        for step in self._steps:
            for dep in step.depends_on:
                if dep not in available:
                    raise ValueError(
                        f"Step '{step.name}' depends on '{dep}' which is not "
                        f"available. Ensure dependencies are ordered before "
                        f"dependent steps."
                    )
            available.add(step.name)

    def _cache_key(self, step_name: str) -> str:
        """Generate cache key for a step."""
        if self._cache_key_prefix:
            return f"{self._cache_key_prefix}:{step_name}"
        return step_name

    def _get_cached_token(
        self, step: TokenFetcherInterface
    ) -> TokenData | None:
        """Get cached token for step if valid."""
        cache_key = self._cache_key(step.name)
        cached = self._storage.get(cache_key)

        if cached is None:
            return None

        # Check expiration
        if cached.is_expired:
            logger.debug(f"Cached token for {step.name} is expired")
            return None

        return cached

    def _cache_token(
        self, step: TokenFetcherInterface, token: TokenData
    ) -> None:
        """Cache token for step."""
        cache_key = self._cache_key(step.name)

        # Apply step TTL if specified
        if step.ttl and not token.expires_at:
            token = TokenData(
                access_token=token.access_token,
                token_type=token.token_type,
                expires_at=datetime.now() + step.ttl,
                refresh_token=token.refresh_token,
                scope=token.scope,
                extra=token.extra,
            )

        self._storage.set(cache_key, token)

    def execute(self, force_refresh: bool = False) -> TokenData:
        """
        Execute pipeline and return final token.

        Args:
            force_refresh: If True, ignores cache and fetches all steps.

        Returns:
            TokenData from the last step.

        Raises:
            AuthenticationException: If any step fails.
        """
        context = FetchContext()
        final_token: TokenData | None = None

        for step in self._steps:
            logger.debug(f"Processing step: {step.name}")

            # Check cache unless force refresh
            if not force_refresh:
                cached = self._get_cached_token(step)
                if cached:
                    logger.debug(f"Using cached token for {step.name}")
                    context.add_token(step.name, cached)
                    final_token = cached
                    continue

            # Verify dependencies are available
            for dep in step.depends_on:
                if not context.has_valid_token(dep):
                    raise AuthenticationException(
                        message=f"Dependency '{dep}' not available for step '{step.name}'",
                        service_name=step.name,
                    )

            # Fetch new token
            try:
                logger.info(f"Fetching token for step: {step.name}")
                token = step.fetch(context.tokens if context.tokens else None)

                # Cache the token
                self._cache_token(step, token)

                # Add to context
                context.add_token(step.name, token)
                final_token = token

                logger.info(f"Successfully fetched token for {step.name}")

            except Exception as e:
                step.on_fetch_error(e, context.tokens)
                raise AuthenticationException(
                    message=f"Token fetch failed for step '{step.name}': {e}",
                    service_name=step.name,
                    original_exception=e,
                )

        if final_token is None:
            raise AuthenticationException(
                message="No tokens fetched from pipeline",
                service_name="pipeline",
            )

        return final_token

    def invalidate_step(self, step_name: str) -> None:
        """
        Invalidate cached token for a specific step.

        Also invalidates all dependent steps.
        """
        logger.info(f"Invalidating token for step: {step_name}")
        self._storage.delete(self._cache_key(step_name))

        # Invalidate dependent steps
        for step in self._steps:
            if step_name in step.depends_on:
                self.invalidate_step(step.name)

    def invalidate_all(self) -> None:
        """Invalidate all cached tokens."""
        logger.info("Invalidating all tokens in pipeline")
        for step in self._steps:
            self._storage.delete(self._cache_key(step.name))

    def get_step(self, name: str) -> TokenFetcherInterface | None:
        """Get a step by name."""
        return self._step_map.get(name)

    @property
    def step_names(self) -> list[str]:
        """Get list of step names in order."""
        return [step.name for step in self._steps]


class PipelineTokenProvider(TokenProviderInterface):
    """
    Token provider that wraps a TokenFetchPipeline.

    Implements TokenProviderInterface for use with TokenManager.

    Example:
        >>> from requestforge.token_manager import TokenManager
        >>>
        >>> pipeline = TokenFetchPipeline(...)
        >>> provider = PipelineTokenProvider(pipeline, 'my-service')
        >>> token_manager = TokenManager(provider)
    """

    def __init__(
        self,
        pipeline: TokenFetchPipeline,
        service_name: str,
        refresh_from_step: str | None = None,
    ):
        """
        Initialize provider.

        Args:
            pipeline: The token fetch pipeline.
            service_name: Name for this service.
            refresh_from_step: If specified, only invalidates from this step
                               on refresh. If None, invalidates all steps.
        """
        self._pipeline = pipeline
        self._service_name = service_name
        self._refresh_from_step = refresh_from_step

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def pipeline(self) -> TokenFetchPipeline:
        """Get the underlying pipeline."""
        return self._pipeline

    def fetch_token(self) -> TokenData:
        """Fetch token by executing pipeline."""
        return self.pipeline.execute(force_refresh=False)

    def refresh_token(self, current_token: TokenData) -> TokenData:
        """Refresh token by re-executing pipeline."""
        if self._refresh_from_step:
            self.pipeline.invalidate_step(self._refresh_from_step)
        else:
            self.pipeline.invalidate_all()

        return self.pipeline.execute(force_refresh=True)
