# Request Forge

[![PyPI version](https://badge.fury.io/py/requestforge.svg)](https://badge.fury.io/py/requestforge)
[![Python Versions](https://img.shields.io/pypi/pyversions/requestforge.svg)](https://pypi.org/project/requestforge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/baratihd/requestforge/workflows/Tests/badge.svg)](https://github.com/baratihd/requestforge/actions)
[![Code Coverage](https://codecov.io/gh/baratihd/requestforge/branch/main/graph/badge.svg)](https://codecov.io/gh/baratihd/requestforge)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A **production-ready**, **thread-safe** Request Forge library for Python with advanced features like automatic retries, authentication management, request/response hooks, and multi-step token fetching pipelines.

Built following **SOLID principles** with comprehensive error handling, this library is designed for enterprise applications requiring robust HTTP communication with complex authentication flows.

---

## 🚀 Features

### Core Features
- ✅ **Clean API**: Intuitive interface for GET, POST, PUT, PATCH, DELETE requests
- ✅ **Thread-Safe**: Safe for use in multi-threaded environments (Django, Flask, FastAPI)
- ✅ **Connection Pooling**: Automatic connection pooling for optimal performance
- ✅ **Retry Strategies**: Exponential backoff, circuit breaker, custom strategies
- ✅ **Error Handling**: Comprehensive exception hierarchy with detailed context
- ✅ **Request/Response Hooks**: Extensible lifecycle hooks for cross-cutting concerns
- ✅ **Concurrent Requests**: Built-in support for parallel request execution

### Authentication Features
- 🔐 **Token Management**: Automatic token caching, refresh, and expiration handling
- 🔐 **Multi-Step Auth**: Pipeline-based authentication for complex OAuth flows
- 🔐 **Auto-Retry on 401**: Automatic token refresh and request retry
- 🔐 **Multiple Auth Types**: Bearer tokens, API keys, Basic auth, custom schemes
- 🔐 **Token Storage**: In-memory and Django cache backends

### Developer Experience
- 📝 **Type Hints**: Full type annotations for IDE autocomplete
- 📝 **Comprehensive Tests**: 500+ test cases with 95%+ coverage
- 📝 **Detailed Logging**: Built-in logging hooks for debugging
- 📝 **Context Managers**: Clean resource management with `with` statements
- 📝 **Builder Pattern**: Fluent configuration interface

---

## 📦 Installation

### Basic Installation

```bash
pip install requestforge
```

### With Django Support

```bash
pip install requestforge[django]
```

### Development Installation

```bash
git clone https://github.com/baratihd/requestforge.git
cd requestforge
pip install -e ".[dev]"
```

## 🎯 Quick Start

```python
from requestforge import HttpClient, HttpClientConfigBuilder

# Create client with basic configuration
config = (
    HttpClientConfigBuilder()
    .with_base_url('https://api.example.com')
    .with_timeout(30.0)
    .build()
)

client = HttpClient(config)

# Make GET request
response = client.get('/users/1')

if response.is_success:
    user = response.json()
    print(f"User: {user['name']}")
```

### POST Request with JSON

```python
response = client.post(
    '/users',
    json_data={
        'name': 'John Doe',
        'email': 'john@example.com',
    }
)

if response.status_code == 201:
    print(f"User created: {response.json()}")
```

### Using Context Manager

```python
from requestforge import http_client

with http_client('https://api.example.com') as client:
    response = client.get('/users')
    users = response.json()
```

## 🔧 Configuration

Builder Pattern Configuration

```python
from requestforge import HttpClientConfigBuilder

config = (
    HttpClientConfigBuilder()
    # Base configuration
    .with_base_url('https://api.example.com')
    .with_timeout(30.0)
    .with_verify_ssl(True)

    # Headers
    .with_header('User-Agent', 'MyApp/1.0')
    .with_header('X-API-Version', 'v2')

    # Authentication
    .with_bearer_token('your-token-here')
    # or
    .with_api_key('your-api-key', header_name='X-API-Key')

    # Retry configuration
    .with_retry(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0
    )

    # Connection pooling
    .with_pool_connection(10)
    .with_pool_maxsize(20)

    # Logging
    .with_logging(
        log_headers=True,
        log_body=False,
        sensitive_keys={'authorization', 'x-api-key'}
    )

    .build()
)
```

### All Configuration Options


Option  |   Type    |   Default	Description
base_url    |   str	''  |   Base URL for all requests
default_timeout	float	30.0	Default timeout in seconds
default_headers	dict	{}	Headers included in all requests
verify_ssl	bool	True	SSL certificate verification
allow_redirects	bool	True	Follow HTTP redirects
max_redirects	int	10	Maximum redirect hops
pool_connection	int	10	Connection pool size
pool_maxsize	int	20	Maximum pool size
retry_strategy	RetryStrategyInterface	None	Retry strategy implementation


## 🔄 Retry Strategies

### Exponential Backoff (Recommended)

```python
from requestforge import HttpClientConfigBuilder, ExponentialBackoffRetryStrategy

strategy = ExponentialBackoffRetryStrategy(
    max_retries=3,
    base_delay=1.0,      # Start with 1 second
    max_delay=60.0,      # Cap at 60 seconds
    multiplier=2.0,      # Double delay each retry
    jitter=True,         # Add randomization
    retryable_status_codes={408, 429, 500, 502, 503, 504}
)

config = (
    HttpClientConfigBuilder()
    .with_base_url('https://api.example.com')
    .with_retry_strategy(strategy)
    .build()
)
```

Retry Timeline:
- Attempt 1: Immediate
- Attempt 2: ~1 second delay (+ jitter)
- Attempt 3: ~2 second delay (+ jitter)
- Attempt 4: ~4 second delay (+ jitter)

### Simple Retry

```python
from requestforge import SimpleRetryStrategy

strategy = SimpleRetryStrategy(
    max_retries=3,
    delay=2.0  # Fixed 2-second delay
)
```

### Circuit Breaker

```python
from requestforge import CircuitBreakerRetryStrategy

strategy = CircuitBreakerRetryStrategy(
    max_retries=3,
    failure_threshold=5,    # Open circuit after 5 failures
    recovery_timeout=30.0,  # Try again after 30 seconds
    half_open_max_calls=3   # Test with 3 calls before fully closing
)
```

Circuit States:
- CLOSED: Normal operation
- OPEN: Too many failures, reject requests immediately
- HALF_OPEN: Testing if service recovered

### Custom Retry Strategy

```python
from requestforge import RetryStrategyInterface
from requestforge.models import RequestContext

class CustomRetryStrategy(RetryStrategyInterface):
    def __init__(self, max_retries=3):
        self._max_retries = max_retries

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(self, context: RequestContext, exception: Exception) -> bool:
        # Custom logic: only retry on specific errors
        if context.attempt >= self._max_retries:
            return False
        return isinstance(exception, TimeoutException)

    def get_delay(self, context: RequestContext) -> float:
        # Custom delay logic
        return 2.0 ** context.attempt
```

## 🔐 Authentication

### Simple Bearer Token

```python
config = (
    HttpClientConfigBuilder()
    .with_base_url('https://api.example.com')
    .with_bearer_token('your-static-token')
    .build()
)
```

### API Key Authentication

```python
config = (
    HttpClientConfigBuilder()
    .with_api_key('your-api-key', header_name='X-API-Key')
    .build()
)
```

### Token Manager with Auto-Refresh

```python
from requestforge import (
    HttpClientConfigBuilder,
    TokenManager,
    ClientCredentialsTokenProvider,
    InMemoryTokenStorage
)

# Setup token provider (OAuth2 client credentials)
provider = ClientCredentialsTokenProvider(
    token_url='https://auth.example.com/oauth/token',
    client_id='your-client-id',
    client_secret='your-client-secret',
    service_name='example-api',
    scope='read write'
)

# Create token manager with caching
token_manager = TokenManager(
    provider=provider,
    storage=InMemoryTokenStorage()
)

# Configure client with auto-refresh
config = (
    HttpClientConfigBuilder()
    .with_base_url('https://api.example.com')
    .with_token_auth(
        token_manager=token_manager,
        excluded_paths={'/health', '/public/*'}  # Don't auth these
    )
    .build()
)

client = HttpClient(config)

# Token is automatically:
# 1. Fetched on first request
# 2. Cached for subsequent requests
# 3. Refreshed when expired
# 4. Refreshed and retried on 401 errors
response = client.get('/protected-resource')
```

### Multi-Step Authentication Pipeline

For complex authentication flows (e.g., get app token → get user token → access API):
```python
from requestforge import TokenFetchPipeline, PipelineTokenProvider
from requestforge.fetcher import BodyTokenFetcher
from requestforge.token_manager import InMemoryTokenStorage, TokenManager
from datetime import timedelta

# Step 1: Fetch application token
app_token_fetcher = BodyTokenFetcher(
    name='app_token',
    base_url='https://auth.example.com',
    endpoint='/v1/app/token',
    method='POST',
    request_data={
        'grant_type': 'client_credentials',
        'client_id': 'your-app-id',
        'client_secret': 'your-app-secret',
    },
    token_field='access_token',
    expires_in_field='expires_in',
    ttl=timedelta(hours=1)  # Cache for 1 hour
)

# Step 2: Fetch user access token (using app token)
class UserTokenFetcher(BodyTokenFetcher):
    def _build_request_headers(self, context):
        # Inject app token from previous step
        headers = super()._build_request_headers(context)
        if context and 'app_token' in context:
            headers['X-App-Token'] = context['app_token'].access_token
        return headers

user_token_fetcher = UserTokenFetcher(
    name='user_token',
    base_url='https://auth.example.com',
    endpoint='/v1/user/token',
    method='POST',
    request_data={
        'username': 'user@example.com',
        'password': 'password123',
    },
    token_field='access_token',
    ttl=timedelta(minutes=30),
    depends_on=['app_token']  # Requires app_token
)

# Create pipeline
pipeline = TokenFetchPipeline(
    steps=[app_token_fetcher, user_token_fetcher],
    storage=InMemoryTokenStorage(),
    cache_key_prefix='myapp'
)

# Wrap in provider
provider = PipelineTokenProvider(pipeline, service_name='myapp')

# Use with TokenManager
token_manager = TokenManager(provider)

# Configure client
config = (
    HttpClientConfigBuilder()
    .with_base_url('https://api.example.com')
    .with_token_auth(token_manager=token_manager)
    .build()
)

client = HttpClient(config)

# Pipeline automatically:
# 1. Fetches app_token (step 1)
# 2. Fetches user_token using app_token (step 2)
# 3. Caches both tokens
# 4. Uses user_token for API requests
# 5. Refreshes tokens when expired
response = client.get('/user/profile')
```

Pipeline Benefits:

✅ Automatic Dependency Resolution: Steps execute in correct order
✅ Per-Step Caching: Each token cached with its own TTL
✅ Cascading Invalidation: Invalidating step 1 clears dependent steps
✅ Partial Cache Hits: Reuse cached tokens when possible

## 🪝 Hooks & Lifecycle

### Built-in Hooks

```python
from requestforge import (
    LoggingRequestHook,
    LoggingResponseHook,
    LoggingErrorHook,
    CorrelationIdHook
)

config = (
    HttpClientConfigBuilder()
    .with_request_hook(LoggingRequestHook(log_headers=True))
    .with_request_hook(CorrelationIdHook(header_name='X-Request-ID'))
    .with_response_hook(LoggingResponseHook(log_body=True))
    .with_error_hook(LoggingErrorHook())
    .build()
)
```

### Custom Request Hook

```python
from requestforge.interfaces import RequestHookInterface
from requestforge.models import HttpRequest, RequestContext

class CustomHeaderHook(RequestHookInterface):
    def before_request(self, request: HttpRequest, context: RequestContext) -> HttpRequest:
        # Add custom logic before request
        custom_header = f"request-{context.attempt}-{time.time()}"
        return request.with_headers({
            'X-Custom-Header': custom_header,
            'X-Timestamp': str(time.time())
        })

config = (
    HttpClientConfigBuilder()
    .with_request_hook(CustomHeaderHook())
    .build()
)
```

### Custom Response Hook

```python
from requestforge.interfaces import ResponseHookInterface

class MetricsHook(ResponseHookInterface):
    def after_response(self, response: HttpResponse, context: RequestContext) -> HttpResponse:
        # Send metrics to monitoring system
        metrics.timing('api.request.duration', response.elapsed_ms)
        metrics.increment(f'api.status.{response.status_code}')

        if not response.is_success:
            metrics.increment('api.errors')

        return response
```

### Hook Execution Order

Request Flow:
  1. Request Hooks (in registration order)
  2. Auth Hook (token injection)
  3. → HTTP Request →
  4. Response Hooks (in registration order)

Error Flow:
  1. Error Hooks (in registration order)
  2. → Exception Raised →


## 🚦 Error Handling

### Exception Hierarchy

```text
HttpClientException (base)
├── MaxRetryException          # Retries exhausted
├── TimeoutException          # Request timeout
├── ConnectionException       # Network error
├── SSLException             # SSL/TLS error
├── ResponseParseException   # JSON parse error
├── AuthenticationException  # Auth failure
└── HttpStatusException      # HTTP error status
    ├── BadRequestException       (400)
    ├── UnauthorizedException     (401)
    ├── ForbiddenException        (403)
    ├── NotFoundException         (404)
    └── ServerErrorException      (5xx)
```

### Error Handling Examples

```python
from requestforge import (
    HttpClient,
    TimeoutException,
    ConnectionException,
    UnauthorizedException,
    HttpStatusException
)

try:
    response = client.get('/users/1')
    user = response.json()

except UnauthorizedException:
    # Handle authentication errors
    print("Authentication failed - please login")

except NotFoundException:
    # Handle 404 specifically
    print("User not found")

except HttpStatusException as e:
    # Handle other HTTP errors
    print(f"HTTP error {e.status_code}: {e.response_body}")

except TimeoutException:
    # Handle timeouts
    print("Request timed out")

except ConnectionException:
    # Handle connection errors
    print("Network connection failed")

except HttpClientException as e:
    # Catch-all for HTTP client errors
    print(f"Request failed: {e}")
    if e.original_exception:
        print(f"Original error: {e.original_exception}")
```

### Accessing Error Context

```python
try:
    response = client.get('/users/1')
except MaxRetryException as e:
    print(f"Failed after {e.attempts} attempts")
    print(f"Original error: {e.original_exception}")
    print(f"Context: {e.context}")
```

## 🔀 Concurrent Requests

### Parallel Request Execution

```python
from requestforge import HttpRequest, HttpMethod

# Prepare multiple requests
requests = [
    HttpRequest(method=HttpMethod.GET, url='/users/1'),
    HttpRequest(method=HttpMethod.GET, url='/users/2'),
    HttpRequest(method=HttpMethod.GET, url='/users/3'),
    HttpRequest(method=HttpMethod.POST, url='/users', json_data={'name': 'John'}),
]

# Execute concurrently with 5 workers
results = client.request_many(requests, max_workers=5, fail_fast=False)

# Process results
for index, result in results:
    if isinstance(result, HttpResponse):
        print(f"Request {index}: {result.status_code}")
    else:
        print(f"Request {index} failed: {result}")
```

### Fail-Fast Mode

```python
# Stop on first error
try:
    results = client.request_many(requests, max_workers=5, fail_fast=True)
    # All requests succeeded
except HttpClientException as e:
    # First error occurred
    print(f"Request failed: {e}")
```

## 🧪 Testing

### Mocking HTTP Requests

```python
import responses
from requestforge import HttpClient, HttpClientConfigBuilder

@responses.activate
def test_get_user():
    # Mock the HTTP response
    responses.add(
        responses.GET,
        'https://api.example.com/users/1',
        json={'id': 1, 'name': 'John Doe'},
        status=200
    )

    # Create client and make request
    config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
    client = HttpClient(config)

    response = client.get('/users/1')

    assert response.status_code == 200
    assert response.json()['name'] == 'John Doe'
```

### Testing with Custom Hooks

```python
from unittest.mock import Mock

def test_custom_hook():
    # Create mock hook
    mock_hook = Mock()
    mock_hook.before_request = Mock(side_effect=lambda req, ctx: req)

    # Configure client with hook
    config = (
        HttpClientConfigBuilder()
        .with_request_hook(mock_hook)
        .build()
    )
    client = HttpClient(config)

    # Make request (with responses mock)
    response = client.get('/test')

    # Verify hook was called
    assert mock_hook.before_request.called
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=requestforge --cov-report=html

# Run specific test file
pytest tests/test_client.py -v

# Run specific test class
pytest tests/test_client.py::TestHttpClientBasicRequests -v

# Run with markers
pytest -m unit
pytest -m integration
```

## 📊 Logging

### Enable Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable HTTP client logging
config = (
    HttpClientConfigBuilder()
    .with_logging(
        log_headers=True,
        log_body=True,
        sensitive_keys={'authorization', 'x-api-key', 'cookie'}
    )
    .build()
)
```

### Log Output Example

```text
2026-05-25 10:30:45,123 - requestforge.hooks - INFO - [a3f2c1b4] HTTP GET /users
2026-05-25 10:30:45,124 - requestforge.hooks - DEBUG - [a3f2c1b4] Headers: {'User-Agent': 'MyApp/1.0', 'Authorization': '***'}
2026-05-25 10:30:45,325 - requestforge.hooks - INFO - [a3f2c1b4] Response: 200 (201.23ms)
```

## 🎨 Advanced Usage

### Custom Retry Logic per Request

```python
from requestforge import SimpleRetryStrategy

# Configure client with default retry
config = (
    HttpClientConfigBuilder()
    .with_retry(max_retries=3)
    .build()
)
client = HttpClient(config)

# Override retry for specific request
custom_strategy = SimpleRetryStrategy(max_retries=5, delay=2.0)
request = HttpRequest(
    method=HttpMethod.GET,
    url='/critical-endpoint',
    timeout=60.0
)

# Set custom retry in context (requires modification to support per-request retry)
response = client.request(request)
```

### Converting Request to cURL

```python
request = HttpRequest(
    method=HttpMethod.POST,
    url='https://api.example.com/users',
    headers={'Authorization': 'Bearer token'},
    json_data={'name': 'John'},
    params={'notify': 'true'}
)

curl_command = request.to_curl()
print(curl_command)
# Output: curl -X 'POST' -H 'Authorization: Bearer token' -H 'Content-Type: application/json' --data '{"name": "John"}' 'https://api.example.com/users?notify=true'
```

### Session Sharing (Advanced)

```python
import requests

# Create shared session
session = requests.Session()
session.headers.update({'User-Agent': 'CustomAgent/1.0'})

# Share session across multiple clients
client1 = HttpClient(config, session=session)
client2 = HttpClient(config, session=session)

# Both clients use the same connection pool
```

## 🏗️ Architecture

### Design Principles

- SOLID Principles
    - Single Responsibility: Each class has one clear purpose
    - Open/Closed: Extensible via hooks and strategies
    - Liskov Substitution: Interfaces are interchangeable
    - Interface Segregation: Small, focused interfaces
    - Dependency Inversion: Depend on abstractions

- Design Patterns
    - Builder Pattern: Fluent configuration
    - Strategy Pattern: Pluggable retry strategies
    - Chain of Responsibility: Hook pipeline
    - Factory Pattern: Client creation
    - Template Method: Base fetcher classes

## Component Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      Request Forge                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │  Retry Logic   │  │  Hook Pipeline │  │  Auth System │   │
│  └────────────────┘  └────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Token Management                          │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │ Token Manager  │  │  Token Storage │  │  Provider    │   │
│  └────────────────┘  └────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Multi-Step Auth Pipeline                       │
│  ┌────────┐      ┌────────┐      ┌────────┐                 │
│  │ Step 1 │  →   │ Step 2 │  →   │ Step 3 │                 │
│  └────────┘      └────────┘      └────────┘                 │
│     (App Token)   (User Token)   (Access Token)             │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Migration from requests

### Before (using requests)

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Manual session setup
session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update({'Authorization': 'Bearer token'})

# Manual error handling
try:
    response = session.get('https://api.example.com/users', timeout=30)
    response.raise_for_status()
    users = response.json()
except requests.Timeout:
    print("Timeout!")
except requests.HTTPError as e:
    print(f"HTTP error: {e}")
```

### After (using http_client)

```python
from requestforge import http_client

with http_client('https://api.example.com') as client:
    try:
        response = client.get('/users')
        users = response.json()
    except TimeoutException:
        print("Timeout!")
    except HttpStatusException as e:
        print(f"HTTP error: {e.status_code}")
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### Development Setup

```bash
# Clone repository
git clone https://github.com/baratihd/requestforge.git
cd requestforge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=requestforge --cov-report=html --cov-report=term-missing

# Run linting
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Run tox for all Python versions
tox
```

### Code Quality Checklist

✅ All tests passing
✅ Code coverage > 90%
✅ Ruff linting passing
✅ Type hints added
✅ Documentation updated
✅ Changelog updated

### Pull Request Process

1. Fork the repository
1. Create a feature branch (git checkout -b feature/amazing-feature)
1. Commit your changes (git commit -m 'Add amazing feature')
1. Push to branch (git push origin feature/amazing-feature)
1. Open a Pull Request

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

Latest Version (1.0.0)

Added:

✅ Initial release
✅ Core HTTP client with retry strategies
✅ Token management with auto-refresh
✅ Multi-step authentication pipelines
✅ Comprehensive test suite (500+ tests)
✅ Full type hints and documentation

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on top of the excellent [requests](https://requests.readthedocs.io/) library
- Inspired by enterprise API client requirements
- Thanks to all contributors and users

## 📞 Support
- Documentation: https://requestforge.readthedocs.io
- Issues: [GitHub Issues](https://github.com/baratihd/requestforge/issues)
- Discussions: [GitHub Discussions](https://github.com/baratihd/requestforge/discussions)


## 🔗 Links

PyPI: https://pypi.org/project/requestforge/
GitHub: https://github.com/baratihd/requestforge
Documentation: https://requestforge.readthedocs.io
Changelog: [CHANGELOG.md](CHANGELOG.md)
