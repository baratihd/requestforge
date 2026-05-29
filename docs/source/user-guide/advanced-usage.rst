Advanced Usage
==============

This guide covers advanced features and patterns for power users of HTTP Client.

Custom Session Configuration
-----------------------------

Using Shared Session
~~~~~~~~~~~~~~~~~~~~

Share a session across multiple client instances:

.. code-block:: python

    import requests
    from requestforge import HttpClient, HttpClientConfigBuilder

    # Create custom session
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'MyCustomAgent/1.0',
        'Accept-Encoding': 'gzip, deflate'
    })

    # Configure session adapter
    from requests.adapters import HTTPAdapter
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=50,
        max_retries=0
    )
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    # Share session across clients
    config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()

    client1 = HttpClient(config, session=session)
    client2 = HttpClient(config, session=session)

    # Both clients share the same connection pool
    response1 = client1.get('/users')
    response2 = client2.get('/posts')

Session Cookies
~~~~~~~~~~~~~~~

Persist cookies across requests:

.. code-block:: python

    session = requests.Session()

    # Set initial cookies
    session.cookies.set('session_id', 'abc123', domain='api.example.com')

    client = HttpClient(config, session=session)

    # Cookies automatically sent with requests
    response = client.get('/profile')

    # Access response cookies
    print(session.cookies.get_dict())

Custom Request Adapters
-----------------------

Implementing Custom Transport
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    class CustomAdapter(HTTPAdapter):
        """Custom adapter with additional features."""

        def __init__(self, timeout=30, *args, **kwargs):
            self.timeout = timeout
            super().__init__(*args, **kwargs)

        def send(self, request, **kwargs):
            # Set default timeout if not specified
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout

            # Add custom header
            request.headers['X-Custom-Transport'] = 'v1.0'

            return super().send(request, **kwargs)

    # Use custom adapter
    session = requests.Session()
    adapter = CustomAdapter(timeout=60)
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    client = HttpClient(config, session=session)

SSL/TLS Configuration
---------------------

Custom SSL Context
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import ssl
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    class SSLAdapter(HTTPAdapter):
        """Adapter with custom SSL configuration."""

        def init_poolmanager(self, *args, **kwargs):
            context = create_urllib3_context()
            context.load_default_certs()
            context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
            kwargs['ssl_context'] = context
            return super().init_poolmanager(*args, **kwargs)

    session = requests.Session()
    session.mount('https://', SSLAdapter())

    client = HttpClient(config, session=session)

Client Certificates
~~~~~~~~~~~~~~~~~~~

Authenticate with client certificates:

.. code-block:: python

    session = requests.Session()
    session.cert = ('/path/to/client.crt', '/path/to/client.key')

    client = HttpClient(config, session=session)
    response = client.get('/secure-endpoint')

Custom CA Bundle
~~~~~~~~~~~~~~~~

Use custom certificate authority:

.. code-block:: python

    session = requests.Session()
    session.verify = '/path/to/custom-ca-bundle.crt'

    client = HttpClient(config, session=session)

Proxy Configuration
-------------------

HTTP/HTTPS Proxies
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    session = requests.Session()
    session.proxies = {
        'http': 'http://proxy.example.com:8080',
        'https': 'https://proxy.example.com:8080',
    }

    client = HttpClient(config, session=session)

SOCKS Proxy
~~~~~~~~~~~

Requires ``requests[socks]``:

.. code-block:: python

    session = requests.Session()
    session.proxies = {
        'http': 'socks5://user:pass@proxy.example.com:1080',
        'https': 'socks5://user:pass@proxy.example.com:1080'
    }

    client = HttpClient(config, session=session)

Proxy with Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    session = requests.Session()
    session.proxies = {
        'http': 'http://user:password@proxy.example.com:8080',
        'https': 'http://user:password@proxy.example.com:8080',
    }

Request/Response Transformation
--------------------------------

Custom Request Transformer
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RequestHookInterface

    class RequestTransformerHook(RequestHookInterface):
        """Transform request data before sending."""

        def before_request(self, request, context):
            # Convert snake_case to camelCase for API
            if request.json_data:
                transformed = self._to_camel_case(request.json_data)
                return request.with_json_data(transformed)
            return request

        def _to_camel_case(self, data):
            if isinstance(data, dict):
                return {
                    self._camel_case_key(k): self._to_camel_case(v)
                    for k, v in data.items()
                }
            elif isinstance(data, list):
                return [self._to_camel_case(item) for item in data]
            return data

        def _camel_case_key(self, key):
            components = key.split('_')
            return components[0] + ''.join(x.title() for x in components[1:])

Custom Response Parser
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ResponseHookInterface

    class ResponseParserHook(ResponseHookInterface):
        """Parse and transform response data."""

        def after_response(self, response, context):
            if response.is_success and response.headers.get('Content-Type', '').startswith('application/json'):
                # Parse and store in context
                data = response.json_or_none()
                if data:
                    # Transform camelCase to snake_case
                    transformed = self._to_snake_case(data)
                    context.metadata['parsed_data'] = transformed

            return response

        def _to_snake_case(self, data):
            # Implementation similar to above

Dynamic Configuration
---------------------

Environment-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import os
    from requestforge import HttpClientConfigBuilder

    def create_config_for_environment():
        """Create configuration based on environment."""
        env = os.getenv('ENVIRONMENT', 'development')

        builder = HttpClientConfigBuilder()

        if env == 'production':
            builder = (
                builder
                .with_base_url('https://api.production.com')
                .with_retry(max_retries=5, base_delay=2.0)
                .with_pool_connection(50)
                .with_pool_maxsize(100)
                .with_verify_ssl(True)
            )
        elif env == 'staging':
            builder = (
                builder
                .with_base_url('https://api.staging.com')
                .with_retry(max_retries=3)
                .with_logging(log_headers=True)
            )
        else:  # development
            builder = (
                builder
                .with_base_url('http://localhost:8000')
                .with_retry(max_retries=1)
                .with_logging(log_headers=True, log_body=True)
                .with_verify_ssl(False)
            )

        return builder.build()

    # Usage
    config = create_config_for_environment()
    client = HttpClient(config)

Feature Flags
~~~~~~~~~~~~~

.. code-block:: python

    class FeatureFlagHook(RequestHookInterface):
        """Add feature flags to requests."""

        def __init__(self, feature_flags):
            self.flags = feature_flags

        def before_request(self, request, context):
            # Add active feature flags as header
            active_flags = ','.join([
                flag for flag, enabled in self.flags.items()
                if enabled
            ])

            return request.with_headers({
                'X-Feature-Flags': active_flags
            })

    # Usage
    flags = {
        'new_api_v2': True,
        'experimental_feature': False,
        'beta_endpoint': True
    }

    config = (
        builder
        .with_request_hook(FeatureFlagHook(flags))
        .build()
    )

Request Signing
---------------

HMAC Signing
~~~~~~~~~~~~

.. code-block:: python

    import hmac
    import hashlib
    import time
    from requestforge.interfaces import RequestHookInterface

    class HMACSigningHook(RequestHookInterface):
        """Sign requests with HMAC."""

        def __init__(self, access_key, secret_key):
            self.access_key = access_key
            self.secret_key = secret_key.encode()

        def before_request(self, request, context):
            timestamp = str(int(time.time()))

            # Create signature string
            sign_string = '\n'.join([
                request.method.value,
                request.url,
                timestamp,
                request.json_data or ''
            ])

            # Generate signature
            signature = hmac.new(
                self.secret_key,
                sign_string.encode(),
                hashlib.sha256
            ).hexdigest()

            return request.with_headers({
                'X-Access-Key': self.access_key,
                'X-Timestamp': timestamp,
                'X-Signature': signature
            })

AWS Signature V4
~~~~~~~~~~~~~~~~

.. code-block:: python

    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    import boto3

    class AWSSignatureHook(RequestHookInterface):
        """Sign requests with AWS Signature V4."""

        def __init__(self, service_name, region_name='us-east-1'):
            session = boto3.Session()
            credentials = session.get_credentials()
            self.signer = SigV4Auth(credentials, service_name, region_name)

        def before_request(self, request, context):
            # Convert to AWS request
            aws_request = AWSRequest(
                method=request.method.value,
                url=request.url,
                data=request.json_data,
                headers=request.headers or {}
            )

            # Sign request
            self.signer.add_auth(aws_request)

            # Return with signed headers
            return request.with_headers(dict(aws_request.headers))

Response Caching
----------------

In-Memory Cache
~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import ResponseHookInterface
    import hashlib
    import time

    class ResponseCacheHook(ResponseHookInterface):
        """Cache successful GET responses in memory."""

        def __init__(self, ttl=300):
            self.cache = {}
            self.ttl = ttl

        def after_response(self, response, context):
            if (response.request.method == HttpMethod.GET and
                response.is_success):

                cache_key = self._get_cache_key(response.request)
                self.cache[cache_key] = {
                    'response': response,
                    'timestamp': time.time()
                }

            return response

        def get_cached(self, request):
            """Check if cached response exists."""
            cache_key = self._get_cache_key(request)
            cached = self.cache.get(cache_key)

            if cached:
                age = time.time() - cached['timestamp']
                if age < self.ttl:
                    return cached['response']
                else:
                    del self.cache[cache_key]

            return None

        def _get_cache_key(self, request):
            """Generate cache key from request."""
            content = f"{request.url}:{request.params}"
            return hashlib.md5(content.encode()).hexdigest()

Redis Cache
~~~~~~~~~~~

.. code-block:: python

    import redis
    import pickle
    from requestforge.interfaces import ResponseHookInterface

    class RedisCacheHook(ResponseHookInterface):
        """Cache responses in Redis."""

        def __init__(self, redis_client, ttl=300):
            self.redis = redis_client
            self.ttl = ttl

        def after_response(self, response, context):
            if (response.request.method == HttpMethod.GET and
                response.is_success):

                cache_key = self._get_cache_key(response.request)

                # Serialize response
                cached_data = {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': response.content,
                    'elapsed_ms': response.elapsed_ms
                }

                self.redis.setex(
                    cache_key,
                    self.ttl,
                    pickle.dumps(cached_data)
                )

            return response

        def get_cached(self, request):
            """Retrieve cached response."""
            cache_key = self._get_cache_key(request)
            cached = self.redis.get(cache_key)

            if cached:
                data = pickle.loads(cached)
                # Reconstruct HttpResponse
                return HttpResponse(**data, request=request)

            return None

Request Batching
----------------

Batch Multiple Requests
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod

    class BatchRequestManager:
        """Batch multiple requests into single API call."""

        def __init__(self, client, batch_endpoint='/batch'):
            self.client = client
            self.batch_endpoint = batch_endpoint
            self.pending = []

        def add(self, request):
            """Add request to batch."""
            self.pending.append(request)

        def execute(self):
            """Execute all pending requests as batch."""
            if not self.pending:
                return []

            # Convert to batch format
            batch_request = {
                'requests': [
                    {
                        'method': req.method.value,
                        'url': req.url,
                        'body': req.json_data
                    }
                    for req in self.pending
                ]
            }

            # Send batch request
            response = self.client.post(
                self.batch_endpoint,
                json_data=batch_request
            )

            self.pending = []
            return response.json()['responses']

    # Usage
    batch = BatchRequestManager(client)
    batch.add(HttpRequest(method=HttpMethod.GET, url='/users/1'))
    batch.add(HttpRequest(method=HttpMethod.GET, url='/users/2'))
    batch.add(HttpRequest(method=HttpMethod.GET, url='/users/3'))

    responses = batch.execute()

GraphQL Support
---------------

GraphQL Client Wrapper
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class GraphQLClient:
        """GraphQL client wrapper."""

        def __init__(self, client, endpoint='/graphql'):
            self.client = client
            self.endpoint = endpoint

        def query(self, query, variables=None, operation_name=None):
            """Execute GraphQL query."""
            payload = {'query': query}

            if variables:
                payload['variables'] = variables

            if operation_name:
                payload['operationName'] = operation_name

            response = self.client.post(self.endpoint, json_data=payload)

            if not response.is_success:
                raise HttpStatusException(
                    message=f"GraphQL request failed: {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text
                )

            data = response.json()

            if 'errors' in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data['data']

        def mutate(self, mutation, variables=None):
            """Execute GraphQL mutation."""
            return self.query(mutation, variables)

    # Usage
    config = HttpClientConfigBuilder().with_base_url('https://api.example.com').build()
    requestforge = HttpClient(config)
    gql_client = GraphQLClient(requestforge)

    # Query
    query = """
        query GetUser($id: ID!) {
            user(id: $id) {
                id
                name
                email
            }
        }
    """

    result = gql_client.query(query, variables={'id': '123'})
    print(result['user']['name'])

    # Mutation
    mutation = """
        mutation CreateUser($input: CreateUserInput!) {
            createUser(input: $input) {
                id
                name
            }
        }
    """

    result = gql_client.mutate(mutation, variables={
        'input': {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
    })

Streaming Responses
-------------------

Download Large Files
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def download_large_file(client, url, output_path, chunk_size=8192):
        """Download large file with progress tracking."""
        import requests

        # Use raw requests for streaming
        response = client.session.get(
            client._build_url(url),
            stream=True,
            headers=client._config.default_headers
        )

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Progress
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"Downloaded: {percent:.1f}%", end='\r')

        print(f"\nDownload complete: {output_path}")

Stream JSON Lines
~~~~~~~~~~~~~~~~~

.. code-block:: python

    def stream_json_lines(client, url):
        """Stream and parse JSONL (JSON Lines) responses."""
        import json

        response = client.session.get(
            client._build_url(url),
            stream=True
        )

        for line in response.iter_lines():
            if line:
                yield json.loads(line.decode('utf-8'))

    # Usage
    for item in stream_json_lines(client, '/api/stream'):
        process_item(item)

Performance Monitoring
----------------------

Request Timing Hook
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge.interfaces import RequestHookInterface, ResponseHookInterface
    import time

    class TimingHooks:
        class Request(RequestHookInterface):
            def before_request(self, request, context):
                context.metadata['timing'] = {
                    'start': time.time(),
                    'url': request.url
                }
                return request

        class Response(ResponseHookInterface):
            def after_response(self, response, context):
                timing = context.metadata.get('timing', {})
                if timing:
                    total_time = time.time() - timing['start']
                    server_time = response.elapsed_ms / 1000
                    network_time = total_time - server_time

                    print(f"URL: {timing['url']}")
                    print(f"  Total: {total_time:.3f}s")
                    print(f"  Server: {server_time:.3f}s")
                    print(f"  Network: {network_time:.3f}s")

                return response

Memory Usage Tracking
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import sys
    from requestforge.interfaces import ResponseHookInterface

    class MemoryTrackingHook(ResponseHookInterface):
        def after_response(self, response, context):
            size_bytes = len(response.content)
            size_mb = size_bytes / (1024 * 1024)

            context.metadata['response_size'] = size_bytes

            if size_mb > 10:
                logger.warning(
                    f"Large response: {size_mb:.2f}MB from {response.url}"
                )

            return response

Distributed Tracing
-------------------

OpenTelemetry Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from opentelemetry import trace
    from requestforge.interfaces import RequestHookInterface, ResponseHookInterface

    tracer = trace.get_tracer(__name__)

    class OpenTelemetryHooks:
        class Request(RequestHookInterface):
            def before_request(self, request, context):
                # Start span
                span = tracer.start_span(
                    f"HTTP {request.method.value} {request.url}"
                )

                span.set_attribute("http.method", request.method.value)
                span.set_attribute("http.url", request.url)

                context.metadata['otel_span'] = span

                # Inject trace context
                from opentelemetry.propagate import inject
                headers = dict(request.headers or {})
                inject(headers)

                return request.with_headers(headers)

        class Response(ResponseHookInterface):
            def after_response(self, response, context):
                span = context.metadata.get('otel_span')
                if span:
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_attribute("http.response_size", len(response.content))
                    span.end()

                return response

Jaeger Integration
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from jaeger_client import Config
    from requestforge.interfaces import RequestHookInterface

    def init_jaeger_tracer(service_name):
        config = Config(
            config={
                'sampler': {'type': 'const', 'param': 1},
                'logging': True,
            },
            service_name=service_name,
        )
        return config.initialize_tracer()

    class JaegerTracingHook(RequestHookInterface):
        def __init__(self, tracer):
            self.tracer = tracer

        def before_request(self, request, context):
            span = self.tracer.start_span(f'{request.method.value} {request.url}')
            span.set_tag('http.method', request.method.value)
            span.set_tag('http.url', request.url)

            context.metadata['jaeger_span'] = span

            return request

Next Steps
----------

* Explore :doc:`../examples/django-integration` for framework integration
* Learn about :doc:`../architecture/design-principles` for design rationale
* Check :doc:`../contributing/development` for contribution guidelines
