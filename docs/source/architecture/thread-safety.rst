Thread Safety
=============

HTTP Client is designed to be thread-safe, allowing safe concurrent usage in multi-threaded applications like Django, Flask, and FastAPI.

Thread-Safe Components
----------------------

HttpClient
~~~~~~~~~~

**Thread Safety:** ✅ **Safe**

**Mechanism:**

* **Thread-local sessions:** Each thread gets its own ``requests.Session`` instance
* **Lazy initialization:** Sessions created on first use per thread
* **Session lock:** ``threading.Lock`` protects session creation

**Implementation:**

.. code-block:: python

    class HttpClient:
        def __init__(self, config, session=None):
            self._session = session  # Optional shared session
            self._session_lock = threading.Lock()
            self._local = threading.local()  # Thread-local storage

        @property
        def session(self) -> requests.Session:
            """Get or create thread-safe session."""
            if self._session:
                return self._session  # Use shared session if provided

            # Thread-local session
            if not hasattr(self._local, 'session') or self._local.session is None:
                with self._session_lock:
                    self._local.session = self._create_session()

            return self._local.session

**Thread-Local Sessions:**

.. code-block:: text

    Thread 1                     Thread 2                     Thread 3
        ↓                            ↓                            ↓
    Get session                  Get session                  Get session
        ↓                            ↓                            ↓
    Create session 1             Create session 2             Create session 3
        ↓                            ↓                            ↓
    Use session 1                Use session 2                Use session 3
        ↓                            ↓                            ↓
    Connection pool 1            Connection pool 2            Connection pool 3

**Usage:**

.. code-block:: python

    # Safe: Single client shared across threads
    client = HttpClient(config)

    def worker():
        response = client.get('/users')  # Each thread gets own session

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()

**Caveat - Shared Session:**

.. code-block:: python

    # If you provide a shared session, YOU are responsible for thread-safety
    shared_session = requests.Session()
    client = HttpClient(config, session=shared_session)

    # This may not be thread-safe depending on requests.Session implementation
    # Better to let HttpClient manage sessions (don't pass session parameter)

TokenManager
~~~~~~~~~~~~

**Thread Safety:** ✅ **Safe**

**Mechanism:**

* **Refresh lock:** ``threading.Lock`` prevents concurrent token fetches
* **Double-checked locking:** Minimizes lock contention

**Implementation:**

.. code-block:: python

    class TokenManager:
        def __init__(self, provider, storage):
            self._provider = provider
            self._storage = storage
            self._lock = threading.RLock()
            self._refresh_lock = threading.Lock()

        def get_token(self):
            # Try cache first (no lock)
            token = self._storage.get(self._cache_key)
            if token and not token.is_expired:
                return token

            # Need refresh - acquire lock
            with self._refresh_lock:
                # Double-check after acquiring lock
                token = self._storage.get(self._cache_key)
                if token and not token.is_expired:
                    return token  # Another thread refreshed

                # Actually fetch new token
                new_token = self._provider.fetch_token()
                self._storage.set(self._cache_key, new_token)
                return new_token

**Concurrent Access Pattern:**

.. code-block:: text

    Thread 1                Thread 2                Thread 3
        ↓                       ↓                       ↓
    get_token()             get_token()             get_token()
        ↓                       ↓                       ↓
    Check cache             Check cache             Check cache
        ↓                       ↓                       ↓
    Expired!                Expired!                Expired!
        ↓                       ↓                       ↓
    Acquire lock            Wait for lock           Wait for lock
        ↓                       ↓                       ↓
    Fetch token             Lock acquired           Lock acquired
    Store token             Token in cache!         Token in cache!
        ↓                   Return cached           Return cached
    Release lock
        ↓
    Return token

**Benefits:**

* Only one thread fetches token
* Other threads wait for result
* No duplicate token requests
* Cache hit after first fetch

**Usage:**

.. code-block:: python

    # Safe: Share token manager across threads
    token_manager = TokenManager(provider, storage)

    def worker():
        token = token_manager.get_token()  # Thread-safe

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()

InMemoryTokenStorage
~~~~~~~~~~~~~~~~~~~~

**Thread Safety:** ✅ **Safe**

**Mechanism:**

* **RLock:** ``threading.RLock()`` protects dictionary access
* **Reentrant:** Same thread can acquire lock multiple times

**Implementation:**

.. code-block:: python

    class InMemoryTokenStorage:
        def __init__(self):
            self._tokens = {}
            self._lock = threading.RLock()

        def get(self, key):
            with self._lock:
                return self._tokens.get(key)

        def set(self, key, token):
            with self._lock:
                self._tokens[key] = token

        def delete(self, key):
            with self._lock:
                self._tokens.pop(key, None)

**Why RLock?**

* Allows same thread to acquire lock multiple times
* Prevents deadlock in nested calls
* Example: ``set()`` called from within ``get()`` in same thread

**Usage:**

.. code-block:: python

    # Safe: Share storage across threads
    storage = InMemoryTokenStorage()

    def writer():
        storage.set('key', token)

    def reader():
        token = storage.get('key')

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()

DjangoCacheTokenStorage
~~~~~~~~~~~~~~~~~~~~~~~

**Thread Safety:** ✅ **Safe**

**Mechanism:**

* Delegates to Django cache backend
* Django cache backends are thread-safe
* Redis/Memcached backends are process-safe

**Implementation:**

.. code-block:: python

    class DjangoCacheTokenStorage:
        def get(self, key):
            from django.core.cache import caches
            cache = caches[self._cache_alias]
            return cache.get(self._make_key(key))

        def set(self, key, token):
            from django.core.cache import caches
            cache = caches[self._cache_alias]
            cache.set(self._make_key(key), token, timeout=ttl)

**Django Cache Backend Thread-Safety:**

.. list-table::
   :header-rows: 1
   :widths: 30 20 25 25

   * - Backend
     - Thread-Safe
     - Process-Safe
     - Recommended For
   * - LocMemCache
     - ✅ Yes
     - ❌ No
     - Development only
   * - RedisCache
     - ✅ Yes
     - ✅ Yes
     - Production
   * - MemcachedCache
     - ✅ Yes
     - ✅ Yes
     - Production
   * - DatabaseCache
     - ✅ Yes
     - ✅ Yes
     - Production
   * - FileBasedCache
     - ⚠️ Depends
     - ⚠️ Depends
     - Not recommended

**Usage:**

.. code-block:: python

    # Safe for multi-process Django deployment
    storage = DjangoCacheTokenStorage(cache_alias='default')
    token_manager = TokenManager(provider, storage)

    # Multiple Django workers/processes can share tokens

TokenFetchPipeline
~~~~~~~~~~~~~~~~~~

**Thread Safety:** ✅ **Safe** (with thread-safe storage)

**Mechanism:**

* Lock-free design
* Relies on storage locking
* Each step is independent

**Implementation:**

.. code-block:: python

    class TokenFetchPipeline:
        def execute(self, force_refresh=False):
            context = FetchContext()

            for step in self._steps:
                # Check cache (storage handles locking)
                if not force_refresh:
                    cached = self._get_cached_token(step)
                    if cached:
                        context.add_token(step.name, cached)
                        continue

                # Fetch (storage handles locking)
                token = step.fetch(context.tokens)
                self._cache_token(step, token)
                context.add_token(step.name, token)

            return final_token

**Thread Safety Analysis:**

* Reads from storage (thread-safe)
* Writes to storage (thread-safe)
* ``FetchContext`` is local to each execution (no sharing)
* Multiple threads can execute pipeline concurrently

**Concurrent Pipeline Execution:**

.. code-block:: text

    Thread 1                    Thread 2
        ↓                           ↓
    execute()                   execute()
        ↓                           ↓
    Check cache (step 1)        Check cache (step 1)
        ↓                           ↓
    Cache miss                  Cache hit (Thread 1's fetch)
        ↓                           ↓
    Fetch step 1                Use cached
    Store step 1
        ↓                           ↓
    Fetch step 2                Fetch step 2
    Store step 2                Store step 2

**Usage:**

.. code-block:: python

    # Safe: Share pipeline across threads
    pipeline = TokenFetchPipeline(steps, storage)

    def worker():
        token = pipeline.execute()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()

Immutable Components
--------------------

Immutable objects are inherently thread-safe:

HttpRequest
~~~~~~~~~~~

**Thread Safety:** ✅ **Safe** (immutable)

.. code-block:: python

    @dataclass(frozen=True)
    class HttpRequest:
        method: HttpMethod
        url: str
        headers: dict | None = None
        # ... other fields

**Safety:**

* Cannot be modified after creation
* Safe to share across threads
* Methods return new instances

HttpResponse
~~~~~~~~~~~~

**Thread Safety:** ✅ **Safe** (immutable)

.. code-block:: python

    @dataclass(frozen=True)
    class HttpResponse:
        status_code: int
        headers: dict
        content: bytes
        # ... other fields

HttpClientConfig
~~~~~~~~~~~~~~~~

**Thread Safety:** ✅ **Safe** (immutable)

.. code-block:: python

    @dataclass(frozen=True)
    class HttpClientConfig:
        base_url: str
        default_timeout: float
        # ... other fields

TokenData
~~~~~~~~~

**Thread Safety:** ✅ **Safe** (effectively immutable)

.. code-block:: python

    @dataclass
    class TokenData:
        access_token: str
        token_type: str
        expires_at: datetime | None
        # ... other fields

**Note:** While not frozen, TokenData is used as immutable in practice.

Mutable Components
------------------

RequestContext
~~~~~~~~~~~~~~

**Thread Safety:** ⚠️ **Not thread-safe** (by design)

**Reason:** Mutable, designed for single-thread request lifecycle.

.. code-block:: python

    @dataclass
    class RequestContext:
        request: HttpRequest
        attempt: int = 0
        max_retries: int = 0
        metadata: dict = field(default_factory=dict)

        def increment_attempt(self):
            self.attempt += 1  # Mutable

**Usage:**

* Created per request
* Not shared across threads
* Modified during retry loop
* Each request gets own context

**Why Not Thread-Safe?**

.. code-block:: python

    # Each request has its own context
    def handle_request(request):
        context = RequestContext(request)  # Local to this call

        # Multiple retries in same thread
        while context.attempt < context.max_retries:
            try:
                response = execute(request)
                return response
            except Exception:
                context.increment_attempt()  # Safe: single thread

FetchContext
~~~~~~~~~~~~

**Thread Safety:** ⚠️ **Not thread-safe** (by design)

**Reason:** Mutable, designed for single pipeline execution.

.. code-block:: python

    @dataclass
    class FetchContext:
        tokens: dict[str, TokenData] = field(default_factory=dict)
        metadata: dict[str, Any] = field(default_factory=dict)

        def add_token(self, name, token):
            self.tokens[name] = token  # Mutable

**Usage:**

* Created per pipeline execution
* Not shared across threads
* Modified as steps execute

Common Patterns
---------------

Sharing Client Across Threads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Pattern: Single Shared Client**

.. code-block:: python

    # Create once
    client = HttpClient(config)

    # Safe: Share across threads
    def worker(user_id):
        response = client.get(f'/users/{user_id}')
        return response.json()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(100)]
        results = [f.result() for f in futures]

**Why Safe:**

* Each thread gets own session (thread-local)
* Config is immutable
* Retry strategy is stateless
* Hooks are stateless

Sharing TokenManager Across Threads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Pattern: Single Shared TokenManager**

.. code-block:: python

    # Create once
    provider = ClientCredentialsTokenProvider(...)
    storage = InMemoryTokenStorage()
    token_manager = TokenManager(provider, storage)

    # Safe: Share across threads
    def worker():
        token = token_manager.get_token()
        # Use token

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()

**Why Safe:**

* Refresh lock prevents concurrent fetches
* Storage is thread-safe
* Only one thread fetches at a time
* Others wait and get cached result

Django Integration
~~~~~~~~~~~~~~~~~~

**Pattern: Application-Wide Client**

.. code-block:: python

    # settings.py
    from requestforge import HttpClient, HttpClientConfigBuilder, TokenManager

    # Single client instance
    API_CLIENT = HttpClient(
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_token_auth(token_manager=TOKEN_MANAGER)
        .build()
    )

    # views.py
    from django.conf import settings

    def my_view(request):
        # Safe: Each request uses same client
        response = settings.API_CLIENT.get('/users')
        # Each request thread gets own session

**Why Safe:**

* Django request threads are independent
* Thread-local sessions
* Shared token manager with locking

Potential Issues
----------------

Sharing Mutable State
~~~~~~~~~~~~~~~~~~~~~

**❌ Unsafe:**

.. code-block:: python

    # Don't do this!
    class BadHook(RequestHookInterface):
        def __init__(self):
            self.counter = 0  # Shared mutable state!

        def before_request(self, request, context):
            self.counter += 1  # Race condition!
            return request

    hook = BadHook()
    config = builder.with_request_hook(hook).build()
    client = HttpClient(config)

    # Multiple threads increment counter
    # Race condition: lost updates

**✅ Safe:**

.. code-block:: python

    # Use context metadata instead
    class GoodHook(RequestHookInterface):
        def before_request(self, request, context):
            # Each request has own context
            context.metadata['hook_call_count'] = \
                context.metadata.get('hook_call_count', 0) + 1
            return request

Blocking in Hooks
~~~~~~~~~~~~~~~~~

**⚠️ Caution:**

.. code-block:: python

    # This blocks all threads using this hook
    class SlowHook(RequestHookInterface):
        def before_request(self, request, context):
            time.sleep(5)  # Blocks for 5 seconds!
            return request

**Impact:**

* Slows down all requests
* Reduces throughput
* May cause timeouts

**Solution:**

* Keep hooks fast
* Avoid I/O in hooks
* Use async operations if needed

Testing Thread Safety
---------------------

Example Test
~~~~~~~~~~~~

.. code-block:: python

    import pytest
    import threading
    from requestforge import HttpClient, TokenManager

    def test_concurrent_requests():
        """Test concurrent requests are thread-safe."""
        client = HttpClient(config)
        results = []
        errors = []

        def worker(i):
            try:
                response = client.get(f'/users/{i}')
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # 100 concurrent requests
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(errors) == 0
        assert len(results) == 100

    def test_concurrent_token_fetch():
        """Test only one thread fetches token."""
        fetch_count = 0
        lock = threading.Lock()

        class CountingProvider(TokenProviderInterface):
            def fetch_token(self):
                nonlocal fetch_count
                with lock:
                    fetch_count += 1
                return TokenData(access_token='token')

        provider = CountingProvider()
        token_manager = TokenManager(provider)

        # 100 threads request token simultaneously
        def worker():
            token_manager.get_token()

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one fetch should occur
        assert fetch_count == 1

Best Practices
--------------

1. **Share HttpClient Instances**

   .. code-block:: python

       # Good ✅ - Share client
       client = HttpClient(config)

       def worker():
           response = client.get('/data')

2. **Share TokenManager Instances**

   .. code-block:: python

       # Good ✅ - Share token manager
       token_manager = TokenManager(provider, storage)

       config = builder.with_token_auth(token_manager).build()

3. **Use Thread-Safe Storage in Production**

   .. code-block:: python

       # Good ✅ - For multi-process
       storage = DjangoCacheTokenStorage()

       # Avoid ❌ - For multi-process
       storage = InMemoryTokenStorage()  # Not shared across processes

4. **Keep Hooks Stateless**

   .. code-block:: python

       # Good ✅ - Stateless hook
       class StatelessHook(RequestHookInterface):
           def before_request(self, request, context):
               # No shared mutable state
               return request.with_headers({'X-ID': uuid.uuid4()})

5. **Don't Share RequestContext**

   .. code-block:: python

       # Good ✅ - Each request gets own context
       def handle_request(request):
           context = RequestContext(request)
           # Use context

6. **Test Concurrent Access**

   .. code-block:: python

       # Good ✅ - Test with multiple threads
       def test_thread_safety():
           threads = [threading.Thread(target=worker) for _ in range(100)]
           # ... test concurrent access

Summary
-------

**Thread-Safe ✅:**

* ``HttpClient`` (with thread-local sessions)
* ``TokenManager`` (with locking)
* ``InMemoryTokenStorage`` (with locking)
* ``DjangoCacheTokenStorage`` (delegates to Django)
* ``TokenFetchPipeline`` (with thread-safe storage)
* All immutable models (HttpRequest, HttpResponse, etc.)

**Not Thread-Safe ⚠️ (by design):**

* ``RequestContext`` (per-request, not shared)
* ``FetchContext`` (per-execution, not shared)

**Key Takeaways:**

1. Share client and token manager instances safely
2. Use thread-safe storage (Django cache, Redis)
3. Keep hooks stateless
4. Don't share mutable context objects
5. Test concurrent access

See Also
--------

* :doc:`design-principles` - Design principles
* :doc:`components` - Components overview
* :doc:`../user-guide/concurrent-requests` - Concurrent requests guide
