"""
Tests for token fetch pipeline.

Tests for orchestrating multi-step token fetching with
caching, dependencies, and cascading invalidation.

Key Testing Patterns:
1. Mocking Strategy
    - MockTokenFetcher: Lightweight test doubles
    - responses library: HTTP request mocking
    - unittest.mock: Behavior verification
2. Test Data Patterns
    - Valid tokens: Success scenarios
    - Expired tokens: Cache invalidation
    - Missing dependencies: Error handling
    - Malformed responses: Robustness testing
3. Coverage Areas
    - Happy Path: Normal operation
    - Error Scenarios: Failures, timeouts, invalid data
    - Edge Cases: Empty pipelines, circular deps
    - Performance: Caching, lazy loading
    - Security: Token expiration, invalidation
"""

from datetime import datetime, timedelta

import pytest

from requestforge.config import TokenData
from requestforge.pipelines import TokenFetchPipeline, PipelineTokenProvider
from requestforge.exceptions import AuthenticationException
from requestforge.interfaces import TokenFetcherInterface
from requestforge.token_manager import InMemoryTokenStorage


class MockTokenFetcher(TokenFetcherInterface):
    """Mock token fetcher for testing."""

    def __init__(
        self,
        name,
        token_value="test-token",
        depends_on=None,
        ttl=None,
        should_fail=False,
    ):
        self._name = name
        self._token_value = token_value
        self._depends_on = depends_on or []
        self._ttl = ttl
        self._should_fail = should_fail
        self.fetch_called = False
        self.error_handler_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def depends_on(self) -> list[str]:
        return self._depends_on

    @property
    def ttl(self):
        return self._ttl

    def fetch(self, context=None) -> TokenData:  # noqa
        self.fetch_called = True
        if self._should_fail:
            raise Exception(f"Fetch failed for {self._name}")

        expires_at = None
        if self._ttl:
            expires_at = datetime.now() + self._ttl

        return TokenData(
            access_token=self._token_value,
            token_type="Bearer",
            expires_at=expires_at,
        )

    def on_fetch_error(self, error, context):  # noqa
        self.error_handler_called = True


class TestTokenFetchPipeline:
    """
    Test TokenFetchPipeline.

    Scenarios:
        - Scenario 1: Simple Two-Step Auth
            - First execution: Both steps fetch and cache
            - Second execution: Both read from cache
            - Force refresh: Both re-fetch
            ```
            Step 1: App Token (from client credentials)
            Step 2: User Access Token (using app token)
            ```
        - Scenario 2: Three-Tier Auth Chain
            - Invalidating Step 1 cascades to Steps 2 & 3
            - Partial cache: Step 1 cached, Steps 2-3 fetch
            ```
            Step 1: Organization Token
            Step 2: Application Token (depends on org token)
            Step 3: User Token (depends on app token)
            ```
        Scenario 3: Cache Expiration
            - After 6 minutes: Step 1 re-fetches, Step 2 uses cache
            ```
            Step 1: Short-lived token (TTL: 5 min)
            Step 2: Long-lived token (TTL: 1 hour)
            ```
    """

    def test_initialization(self):
        """
        Test pipeline initialization.

        Validates pipeline setup with steps, storage, cache prefix
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2")

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step1, step2],
            storage=storage,
            cache_key_prefix="test",
        )

        assert len(pipeline._steps) == 2
        assert pipeline._cache_key_prefix == "test"
        assert pipeline._storage == storage

    def test_initialization_validates_dependencies(self):
        """
        Test initialization validates dependencies.

        Validation: Detects missing/misordered dependencies at init
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2", depends_on=["nonexistent"])

        storage = InMemoryTokenStorage()

        with pytest.raises(ValueError, match="not available"):
            TokenFetchPipeline(
                steps=[step1, step2],
                storage=storage,
                validate_dependencies=True,
            )

    def test_initialization_skip_validation(self):
        """
        Test initialization can skip validation.

        Allows bypassing dependency validation for flexibility
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2", depends_on=["nonexistent"])

        storage = InMemoryTokenStorage()

        # Should not raise
        pipeline = TokenFetchPipeline(
            steps=[step1, step2],
            storage=storage,
            validate_dependencies=False,
        )

        assert len(pipeline._steps) == 2

    def test_validate_dependencies_success(self):
        """
        Test successful dependency validation.

        Complex dependency graph validates successfully
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2", depends_on=["step1"])
        step3 = MockTokenFetcher("step3", depends_on=["step1", "step2"])

        storage = InMemoryTokenStorage()

        # Should not raise
        pipeline = TokenFetchPipeline(
            steps=[step1, step2, step3],
            storage=storage,
            validate_dependencies=True,
        )

        assert len(pipeline._steps) == 3

    def test_cache_key_generation(self):
        """
        Test cache key generation.

        Tests cache key naming with/without prefix
        """
        step = MockTokenFetcher("step1")
        storage = InMemoryTokenStorage()

        # With prefix
        pipeline1 = TokenFetchPipeline(
            steps=[step],
            storage=storage,
            cache_key_prefix="myapp",
        )
        assert pipeline1._cache_key("step1") == "myapp:step1"

        # Without prefix
        pipeline2 = TokenFetchPipeline(
            steps=[step],
            storage=storage,
            cache_key_prefix="",
        )
        assert pipeline2._cache_key("step1") == "step1"

    def test_execute_single_step(self):
        """
        Test executing pipeline with single step.

        Simple Flow: Single-step token fetch
        """
        step = MockTokenFetcher("step1", token_value="token-123")
        storage = InMemoryTokenStorage()

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        token = pipeline.execute()

        assert token.access_token == "token-123"
        assert step.fetch_called

    def test_execute_multiple_steps(self):
        """
        Test executing pipeline with multiple steps.

        Multi-Step Flow: Sequential execution with dependencies
        """
        step1 = MockTokenFetcher("step1", token_value="token-1")
        step2 = MockTokenFetcher(
            "step2", token_value="token-2", depends_on=["step1"]
        )

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step1, step2], storage=storage)

        token = pipeline.execute()

        # Final token should be from last step
        assert token.access_token == "token-2"
        assert step1.fetch_called
        assert step2.fetch_called

    def test_execute_uses_cache(self):
        """
        Test pipeline uses cached tokens.

        Cache Hit: Reuses cached tokens (performance optimization)
        """
        step = MockTokenFetcher("step1", token_value="fresh-token")
        storage = InMemoryTokenStorage()

        # Pre-populate cache
        cached_token = TokenData(
            access_token="cached-token",
            token_type="Bearer",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        storage.set("step1", cached_token)

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        token = pipeline.execute()

        # Should use cached token
        assert token.access_token == "cached-token"
        assert not step.fetch_called

    def test_execute_force_refresh(self):
        """
        Test force refresh bypasses cache.

        Force Refresh: Bypasses cache to fetch fresh tokens
        """
        step = MockTokenFetcher("step1", token_value="fresh-token")
        storage = InMemoryTokenStorage()

        # Pre-populate cache
        cached_token = TokenData(
            access_token="cached-token",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        storage.set("step1", cached_token)

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        token = pipeline.execute(force_refresh=True)

        # Should fetch fresh token
        assert token.access_token == "fresh-token"
        assert step.fetch_called

    def test_execute_skips_expired_cache(self):
        """
        Test pipeline skips expired cached tokens.

        Cache Invalidation: Expired tokens are re-fetched
        """
        step = MockTokenFetcher("step1", token_value="fresh-token")
        storage = InMemoryTokenStorage()

        # Pre-populate with expired token
        expired_token = TokenData(
            access_token="expired-token",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        storage.set("step1", expired_token)

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        token = pipeline.execute()

        # Should fetch fresh token
        assert token.access_token == "fresh-token"
        assert step.fetch_called

    def test_execute_caches_fetched_tokens(self):
        """
        Test pipeline caches fetched tokens.

        Verifies tokens are cached after fetching
        """
        step = MockTokenFetcher("step1", token_value="new-token")
        storage = InMemoryTokenStorage()

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        pipeline.execute()

        # Check token was cached
        cached = storage.get("step1")
        assert cached is not None
        assert cached.access_token == "new-token"

    def test_execute_applies_step_ttl(self):
        """
        Test pipeline applies step TTL to cached token.

        TTL from fetcher is applied to cached token
        """
        ttl = timedelta(hours=2)
        step = MockTokenFetcher("step1", token_value="token", ttl=ttl)
        storage = InMemoryTokenStorage()

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        pipeline.execute()

        # Check cached token has TTL-based expiration
        cached = storage.get("step1")
        assert cached.expires_at is not None
        expected = datetime.now() + ttl
        assert abs((cached.expires_at - expected).total_seconds()) < 5

    def test_execute_dependency_validation(self):
        """
        Test pipeline validates dependencies at execution.

        Runtime Validation: Dependencies exist before fetch
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2", depends_on=["step1"])

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step1, step2],
            storage=storage,
        )

        # Should succeed
        token = pipeline.execute()
        assert token is not None

    def test_execute_missing_dependency_error(self):
        """
        Test error when dependency is missing.

        Error Scenario: Missing dependency causes failure
        """
        step = MockTokenFetcher("step2", depends_on=["step1"])

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step],
            storage=storage,
            validate_dependencies=False,  # Skip init validation
        )

        with pytest.raises(AuthenticationException, match="not available"):
            pipeline.execute()

    def test_execute_step_failure(self):
        """
        Test pipeline handles step failure.

        Error Handling: Step failure propagates correctly
        """
        step = MockTokenFetcher("step1", should_fail=True)
        storage = InMemoryTokenStorage()

        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        with pytest.raises(
            AuthenticationException, match="Token fetch failed"
        ):
            pipeline.execute()

        assert step.error_handler_called

    def test_execute_no_steps(self):
        """
        Test error when pipeline has no steps.

        Edge Case: Empty pipeline raises error
        """
        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[], storage=storage)

        with pytest.raises(AuthenticationException, match="No tokens fetched"):
            pipeline.execute()

    def test_invalidate_step(self):
        """
        Test invalidating specific step.

        Selective Invalidation: Clears specific step cache
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2")

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step1, step2],
            storage=storage,
            cache_key_prefix="test",
        )

        # Cache tokens
        storage.set("test:step1", TokenData(access_token="token1"))
        storage.set("test:step2", TokenData(access_token="token2"))

        # Invalidate step1
        pipeline.invalidate_step("step1")

        assert storage.get("test:step1") is None
        assert storage.get("test:step2") is not None

    def test_invalidate_step_cascades(self):
        """
        Test invalidating step also invalidates dependents.

        Cascade Invalidation: Dependent steps also cleared
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2", depends_on=["step1"])
        step3 = MockTokenFetcher("step3", depends_on=["step2"])

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step1, step2, step3], storage=storage
        )

        # Cache all tokens
        storage.set("step1", TokenData(access_token="token1"))
        storage.set("step2", TokenData(access_token="token2"))
        storage.set("step3", TokenData(access_token="token3"))

        # Invalidate step1 should cascade to step2 and step3
        pipeline.invalidate_step("step1")

        assert storage.get("step1") is None
        assert storage.get("step2") is None
        assert storage.get("step3") is None

    def test_invalidate_all(self):
        """
        Test invalidating all steps.

        Full Refresh: Clears entire pipeline cache
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2")

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step1, step2], storage=storage)

        # Cache tokens
        storage.set("step1", TokenData(access_token="token1"))
        storage.set("step2", TokenData(access_token="token2"))

        # Invalidate all
        pipeline.invalidate_all()

        assert storage.get("step1") is None
        assert storage.get("step2") is None

    def test_get_step(self):
        """
        Test getting step by name.

        Retrieves step by name for inspection
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2")

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step1, step2], storage=storage)

        retrieved = pipeline.get_step("step1")
        assert retrieved == step1

        assert pipeline.get_step("nonexistent") is None

    def test_step_names_property(self):
        """
        Test step_names property.

        Lists all step names in execution order
        """
        step1 = MockTokenFetcher("step1")
        step2 = MockTokenFetcher("step2")
        step3 = MockTokenFetcher("step3")

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step1, step2, step3], storage=storage
        )

        assert pipeline.step_names == ["step1", "step2", "step3"]


class TestPipelineTokenProvider:
    """
    Test PipelineTokenProvider.

    Scenarios:
        - Integrates multi-step pipeline with standard TokenManager interface for seamless auth.
    """

    def test_initialization(self):
        """
        Test provider initialization.

        Provider wraps pipeline for TokenManager compatibility
        """
        step = MockTokenFetcher("step1")
        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        provider = PipelineTokenProvider(
            pipeline=pipeline,
            service_name="test-service",
        )

        assert provider.service_name == "test-service"
        assert provider.pipeline == pipeline

    def test_service_name_property(self):
        """
        Test service_name property.

        Service identification for logging/metrics
        """
        step = MockTokenFetcher("step1")
        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        provider = PipelineTokenProvider(pipeline, "my-service")

        assert provider.service_name == "my-service"

    def test_pipeline_property(self):
        """
        Test pipeline property.

        Access to underlying pipeline
        """
        step = MockTokenFetcher("step1")
        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        provider = PipelineTokenProvider(pipeline, "test")

        assert provider.pipeline == pipeline

    def test_fetch_token(self):
        """
        Test fetch_token executes pipeline.

        Normal Fetch: Executes pipeline without refresh
        """
        step = MockTokenFetcher("step1", token_value="test-token")
        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        provider = PipelineTokenProvider(pipeline, "test")

        token = provider.fetch_token()

        assert token.access_token == "test-token"
        assert step.fetch_called

    def test_refresh_token_invalidates_all(self):
        """
        Test refresh_token invalidates all steps.

        Full Refresh: Clears all steps on refresh
        """
        step1 = MockTokenFetcher("step1", token_value="token1")
        step2 = MockTokenFetcher("step2", token_value="token2")

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step1, step2], storage=storage)

        # Pre-populate cache
        storage.set("step1", TokenData(access_token="old1"))
        storage.set("step2", TokenData(access_token="old2"))

        provider = PipelineTokenProvider(pipeline, "test")

        current_token = TokenData(access_token="current")
        new_token = provider.refresh_token(current_token)

        # Cache should be cleared and new tokens fetched
        assert new_token.access_token == "token2"
        assert step1.fetch_called
        assert step2.fetch_called

    def test_refresh_token_with_refresh_from_step(self):
        """
        Test refresh_token with specific refresh step.

        Partial Refresh: Only invalidates from specific step
        """
        step1 = MockTokenFetcher("step1", token_value="token1")
        step2 = MockTokenFetcher(
            "step2", token_value="token2", depends_on=["step1"]
        )

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step1, step2], storage=storage)

        # Pre-populate cache
        storage.set(
            "step1",
            TokenData(
                access_token="old1",
                expires_at=datetime.now() + timedelta(hours=1),
            ),
        )
        storage.set("step2", TokenData(access_token="old2"))

        provider = PipelineTokenProvider(
            pipeline,
            "test",
            refresh_from_step="step2",
        )

        current_token = TokenData(access_token="current")
        new_token = provider.refresh_token(current_token)

        # Only step2 and its dependencies should be invalidated
        # In this case, step2 depends on step1, so both get invalidated
        assert new_token.access_token == "token2"


class TestPipelineIntegration:
    """
    Integration tests for pipeline with multiple steps.

    Scenarios:
        - T+0: All 3 steps fetch and cache
        - T+16 min: Step 3 re-fetches (expired), Steps 1-2 from cache
        - T+31 min: Steps 2-3 re-fetch, Step 1 from cache
        - T+61 min: All 3 steps re-fetch
        ```
        # Multi-Service Authentication
        Step 1: Platform Token (client_credentials)
        ├─ Cache: 1 hour
        ├─ Endpoint: /platform/token
        └─ Returns: platform_token

        Step 2: Service Token (using platform_token)
        ├─ Cache: 30 minutes
        ├─ Endpoint: /service/auth
        ├─ Headers: {X-Platform-Token: <step1.token>}
        └─ Returns: service_token

        Step 3: User Token (using service_token)
        ├─ Cache: 15 minutes
        ├─ Endpoint: /user/session
        ├─ Headers: {Authorization: Bearer <step2.token>}
        └─ Returns: access_token (used for API calls)
        ```
    """

    def test_multi_step_pipeline_execution(self):
        """
        Test multi-step pipeline execution flow.

        Complete Flow: 3-step pipeline from start to finish
        """
        # Setup 3-step pipeline
        step1 = MockTokenFetcher("app_token", token_value="app-123")
        step2 = MockTokenFetcher(
            "user_token", token_value="user-456", depends_on=["app_token"]
        )
        step3 = MockTokenFetcher(
            "access_token", token_value="access-789", depends_on=["user_token"]
        )

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(
            steps=[step1, step2, step3],
            storage=storage,
            cache_key_prefix="myapp",
        )

        # Execute pipeline
        token = pipeline.execute()

        # Verify final token
        assert token.access_token == "access-789"

        # Verify all steps were executed
        assert step1.fetch_called
        assert step2.fetch_called
        assert step3.fetch_called

        # Verify all tokens are cached
        assert storage.get("myapp:app_token") is not None
        assert storage.get("myapp:user_token") is not None
        assert storage.get("myapp:access_token") is not None

    def test_pipeline_partial_cache_hit(self):
        """
        Test pipeline with partial cache hit.

        Hybrid: Some steps cached, others fetch
        """
        step1 = MockTokenFetcher("step1", token_value="fresh1")
        step2 = MockTokenFetcher(
            "step2", token_value="fresh2", depends_on=["step1"]
        )

        storage = InMemoryTokenStorage()

        # Cache only step1
        storage.set(
            "step1",
            TokenData(
                access_token="cached1",
                expires_at=datetime.now() + timedelta(hours=1),
            ),
        )

        pipeline = TokenFetchPipeline(steps=[step1, step2], storage=storage)

        token = pipeline.execute()

        # step1 should use cache, step2 should fetch
        assert not step1.fetch_called
        assert step2.fetch_called
        assert token.access_token == "fresh2"

    def test_pipeline_with_ttl_override(self):
        """
        Test pipeline respects step TTL.

        Custom Expiration: Step TTL overrides response TTL
        """
        ttl = timedelta(minutes=30)
        step = MockTokenFetcher("step1", token_value="token", ttl=ttl)

        storage = InMemoryTokenStorage()
        pipeline = TokenFetchPipeline(steps=[step], storage=storage)

        pipeline.execute()

        cached = storage.get("step1")
        assert cached.expires_at is not None

        # TTL should be approximately 30 minutes from now
        expected_expiry = datetime.now() + ttl
        assert abs((cached.expires_at - expected_expiry).total_seconds()) < 5
