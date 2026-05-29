Code Style Guide
================

This guide covers coding standards and style conventions for Request Forge.

Code Formatting
---------------

We use **Ruff** for code formatting and linting.

Ruff Configuration
~~~~~~~~~~~~~~~~~~

.. code-block:: toml

    # .ruff.toml
    target-version = "py310"
    fix = true
    line-length = 79
    indent-width = 4

    [lint]
    select = [
        "E",        # pycodestyle errors
        "W",        # pycodestyle warnings
        "F",        # pyflakes
        "I",        # isort
        "B",        # flake8-bugbear
        "C4",       # flake8-comprehensions list/set/dict
        "UP",       # pyupgrade
        "ARG",      # flake8-unused-arguments
        "SIM",      # flake8-simplify
        'S',        # security
        'F',        # flake8
        'PIE',      # improving code quality and readability
        'A',        # builtin names used
        'E',        # errors
        'W',        # warnings
        'TID',      # tidier imports
        'TCH',      # imports for type checking
        'N',        # naming
        'D419',     # doc style
        'DJ',       # django
        'ICN',      # import conventions
        'ASYNC',    # async
        'T20',      # found print
        'PT',       # pytest style
        'RSE',      # Unnecessary parentheses on raised exception
        'RET',      # checks returns
        'TD',       # todos comments
        'FIX',      # fix me comments
    ]
    extend-ignore = [
        'A003',
        'UP031',    # Use format specifiers instead of percent format
        'S101',     # Use of `assert` detected
        'W293',     # Blank line contains whitespace
        'S105',     # Possible hardcoded password assigned
        'S106',     # Possible hardcoded password assigned
        'S107',     # Possible hardcoded password assigned
        'F841',     # Remove assignment to unused variable
        'N818',     # Check exception names
        'ARG002',   # Unused method argument
        'ARG005',   # Unused lambda argument
        'SIM117',   # Use a single with statement
    ]
    ignore = [
        "E501",  # line too long (handled by formatter)
        "B008",  # do not perform function calls in argument defaults
        "B904",  # raise from
    ]

    [lint.per-file-ignores]
    "__init__.py" = ["F401", "F403"]
    "tests/*" = ["B011", "ARG001"]

    [format]
    quote-style = "single"
    indent-style = "space"
    skip-magic-trailing-comma = false
    line-ending = "auto"

    [lint.isort]
    known-first-party = ["requestforge"]
    from-first = true
    length-sort = true
    order-by-type = true
    case-sensitive = true
    force-wrap-aliases = true
    combine-as-imports = true
    detect-same-package = true
    length-sort-straight = true
    split-on-trailing-comma = true
    force-sort-within-sections = true
    lines-after-imports = 2
    no-lines-before = ['future', ]
    known-third-party = ['pytest']
    section-order = ['future', 'standard-library', 'third-party', 'local-folder']

Running Ruff
~~~~~~~~~~~~

.. code-block:: bash

    # Check code
    ruff check src/ tests/

    # Fix auto-fixable issues
    ruff check --fix src/ tests/

    # Format code
    ruff format src/ tests/

    # Check formatting
    ruff format --check src/ tests/

Python Style
------------

PEP 8 Compliance
~~~~~~~~~~~~~~~~

Follow PEP 8 with these exceptions:

* Line length: 120 characters (instead of 79)
* String quotes: Single quotes preferred (``'text'`` instead of ``"text"``)

Imports
~~~~~~~

Order imports using isort style:

.. code-block:: python

    # Standard library
    import os
    import sys
    from typing import Any

    # Third-party
    import requests
    from requests.adapters import HTTPAdapter

    # Local
    from requestforge.config import HttpClientConfig
    from requestforge.exceptions import HttpClientException

**Rules:**

* Group imports: stdlib, third-party, local
* Sort alphabetically within groups
* Use absolute imports
* Avoid wildcard imports (``from module import *``)

Type Hints
~~~~~~~~~~

Use type hints for all public APIs:

.. code-block:: python

    # Good ✅
    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Execute a GET request."""
        ...

    # Avoid ❌
    def get(self, url, params=None, headers=None):
        ...

**Type Hint Guidelines:**

* Use built-in generic types (``list[str]``, not ``List[str]``)
* Use ``|`` for unions (``str | None``, not ``Optional[str]``)
* Use ``from __future__ import annotations`` for forward references
* Use ``TYPE_CHECKING`` for import-only types

.. code-block:: python

    from __future__ import annotations

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from collections.abc import Iterator

Naming Conventions
------------------

Classes
~~~~~~~

* Use ``PascalCase``
* Descriptive names
* Interfaces end with ``Interface``

.. code-block:: python

    # Good ✅
    class HttpClient:
        ...

    class RetryStrategyInterface:
        ...

    class ExponentialBackoffRetryStrategy:
        ...

Functions and Methods
~~~~~~~~~~~~~~~~~~~~~

* Use ``snake_case``
* Descriptive verb-based names
* Private methods start with ``_``

.. code-block:: python

    # Good ✅
    def get_token(self):
        ...

    def _build_request_headers(self, context):
        ...

    # Avoid ❌
    def getTok(self):
        ...

Variables
~~~~~~~~~

* Use ``snake_case``
* Descriptive names
* Private variables start with ``_``
* Constants use ``UPPER_CASE``

.. code-block:: python

    # Good ✅
    user_token = 'abc123'
    _cache_key = 'tokens:user'
    MAX_RETRIES = 3

    # Avoid ❌
    ut = 'abc123'
    maxRetries = 3

Documentation
-------------

Docstrings
~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

    def fetch_token(self, context: dict | None = None) -> TokenData:
        """
        Fetch token for this step.

        Args:
            context: Dictionary mapping step names to TokenData from
                     previous steps. None if this is the first step.

        Returns:
            TokenData containing the fetched token.

        Raises:
            AuthenticationException: If token fetch fails.

        Example:
            >>> fetcher = BodyTokenFetcher(...)
            >>> token = fetcher.fetch()
            >>> print(token.access_token)
        """
        ...

**Docstring Sections:**

* Short summary (one line)
* Detailed description (optional)
* ``Args``: Parameter descriptions
* ``Returns``: Return value description
* ``Raises``: Exceptions that can be raised
* ``Example``: Usage examples (optional)
* ``Note``: Additional notes (optional)

Module Docstrings
~~~~~~~~~~~~~~~~~

.. code-block:: python

    """
    Retry strategy implementations with different patterns.

    This module provides various retry strategies including:
    - NoRetryStrategy: No retries
    - ExponentialBackoffRetryStrategy: Exponential backoff with jitter
    - CircuitBreakerRetryStrategy: Circuit breaker pattern
    """

Comments
~~~~~~~~

.. code-block:: python

    # Good ✅ - Explain why, not what
    # Jitter prevents thundering herd when many clients retry simultaneously
    delay += random.uniform(-jitter_range, jitter_range)

    # Avoid ❌ - Obvious comments
    # Add jitter to delay
    delay += random.uniform(-jitter_range, jitter_range)

Code Organization
-----------------

Class Structure
~~~~~~~~~~~~~~~

Organize class members in this order:

1. Class variables
2. ``__init__``
3. Properties
4. Public methods
5. Private methods
6. Magic methods (``__str__``, ``__repr__``, etc.)

.. code-block:: python

    class HttpClient:
        # Class variables
        DEFAULT_TIMEOUT = 30.0

        # Initialization
        def __init__(self, config):
            self._config = config

        # Properties
        @property
        def session(self):
            return self._session

        # Public methods
        def get(self, url):
            ...

        def post(self, url, data):
            ...

        # Private methods
        def _build_url(self, url):
            ...

        def _execute_request(self, request):
            ...

        # Magic methods
        def __enter__(self):
            ...

        def __exit__(self, exc_type, exc_val, exc_tb):
            ...

Function Length
~~~~~~~~~~~~~~~

* Keep functions focused and short
* Aim for < 50 lines
* Extract complex logic to separate functions

.. code-block:: python

    # Good ✅ - Focused function
    def should_retry(self, context, exception):
        if context.attempt >= self._max_retries:
            return False
        return self._is_retryable_exception(exception)

    def _is_retryable_exception(self, exception):
        return isinstance(exception, (TimeoutException, ConnectionException))

    # Avoid ❌ - Too long, doing too much
    def should_retry(self, context, exception):
        # 100 lines of logic...

Best Practices
--------------

Immutability
~~~~~~~~~~~~

Prefer immutable objects:

.. code-block:: python

    # Good ✅ - Immutable dataclass
    @dataclass(frozen=True)
    class HttpRequest:
        method: HttpMethod
        url: str

        def with_headers(self, headers: dict) -> HttpRequest:
            """Return new instance with headers."""
            return HttpRequest(
                method=self.method,
                url=self.url,
                headers={**self.headers, **headers}
            )

SOLID Principles
~~~~~~~~~~~~~~~~

Follow SOLID principles:

.. code-block:: python

    # Good ✅ - Interface segregation
    class RequestHookInterface:
        def before_request(self, request, context):
            ...

    class ResponseHookInterface:
        def after_response(self, response, context):
            ...

    # Avoid ❌ - Fat interface
    class HookInterface:
        def before_request(self, request, context):
            ...
        def after_response(self, response, context):
            ...
        def on_error(self, exception, context):
            ...

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

    # Good ✅ - Specific exceptions
    if token.is_expired:
        raise AuthenticationException('Token expired')

    # Avoid ❌ - Generic exceptions
    if token.is_expired:
        raise Exception('Error')

**Rules:**

* Use specific exception types
* Include meaningful error messages
* Provide context in exceptions
* Don't catch exceptions you can't handle

Resource Management
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Good ✅ - Context manager
    with HttpClient('https://api.example.com') as client:
        response = client.get('/users')

    # Good ✅ - Explicit cleanup
    client = HttpClient(config)
    try:
        response = client.get('/users')
    finally:
        client.close()

Constants
~~~~~~~~~

.. code-block:: python

    # Good ✅ - Named constants
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

    if status_code in RETRY_STATUS_CODES:
        ...

    # Avoid ❌ - Magic numbers
    if status_code in {408, 429, 500, 502, 503, 504}:
        ...

Example Code
------------

Well-Styled Module
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    """
    Request Forge retry strategies.

    This module provides retry strategy implementations following
    the Strategy pattern.
    """

    from __future__ import annotations

    from abc import ABC, abstractmethod
    from typing import TYPE_CHECKING
    import secrets

    from requestforge.exceptions import TimeoutException, ConnectionException

    if TYPE_CHECKING:
        from requestforge.models import RequestContext

    # Constants
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BASE_DELAY = 1.0
    DEFAULT_MAX_DELAY = 60.0


    class RetryStrategyInterface(ABC):
        """Abstract interface for retry strategies."""

        @property
        @abstractmethod
        def max_retries(self) -> int:
            """Maximum number of retry attempts."""

        @abstractmethod
        def should_retry(self, context: RequestContext, exception: Exception) -> bool:
            """
            Determine if request should be retried.

            Args:
                context: Request context with attempt count
                exception: Exception that caused failure

            Returns:
                True if should retry, False otherwise
            """

        @abstractmethod
        def get_delay(self, context: RequestContext) -> float:
            """
            Get delay in seconds before next retry.

            Args:
                context: Request context

            Returns:
                Delay in seconds
            """


    class ExponentialBackoffRetryStrategy(RetryStrategyInterface):
        """
        Exponential backoff retry strategy with jitter.

        Delay formula: min(base_delay * (multiplier ^ attempt) + jitter, max_delay)

        Example:
            >>> strategy = ExponentialBackoffRetryStrategy(
            ...     max_retries=3,
            ...     base_delay=1.0,
            ...     max_delay=60.0,
            ...     multiplier=2.0,
            ...     jitter=True
            ... )
        """

        def __init__(
            self,
            max_retries: int = DEFAULT_MAX_RETRIES,
            base_delay: float = DEFAULT_BASE_DELAY,
            max_delay: float = DEFAULT_MAX_DELAY,
            multiplier: float = 2.0,
            jitter: bool = True,
        ):
            self._max_retries = max_retries
            self._base_delay = base_delay
            self._max_delay = max_delay
            self._multiplier = multiplier
            self._jitter = jitter

        @property
        def max_retries(self) -> int:
            return self._max_retries

        def should_retry(self, context: RequestContext, exception: Exception) -> bool:
            if context.attempt >= self._max_retries:
                return False

            return isinstance(exception, (TimeoutException, ConnectionException))

        def get_delay(self, context: RequestContext) -> float:
            # Calculate exponential delay
            delay = self._base_delay * (self._multiplier ** context.attempt)

            # Add jitter if enabled
            if self._jitter:
                jitter_range = delay * 0.25
                delay += (
                    secrets.randbelow(int(jitter_range * 2 * 1_000_000)) / 1_000_000
                    - jitter_range
                )

            # Cap at max_delay
            return min(max(delay, 0), self._max_delay)

Pre-commit Configuration
-------------------------

.. code-block:: yaml

    # .pre-commit-config.yaml
    repos:
      - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.1.9
        hooks:
          - id: ruff
            args: [--fix, --exit-non-zero-on-fix]
          - id: ruff-format

      - repo: https://github.com/pre-commit/pre-commit-hooks
        rev: v4.5.0
        hooks:
          - id: trailing-whitespace
          - id: end-of-file-fixer
          - id: check-yaml
          - id: check-added-large-files
          - id: check-merge-conflict

See Also
--------

* :doc:`development` - Development guide
* :doc:`testing` - Testing guide
* :doc:`../architecture/design-principles` - Design principles
