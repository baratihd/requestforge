Concurrent Requests
===================

HTTP Client provides built-in support for executing multiple requests concurrently using thread pools.

Overview
--------

The ``request_many()`` method allows you to execute multiple HTTP requests in parallel, improving throughput for batch operations.

**Benefits:**

* Execute multiple requests simultaneously
* Configurable number of worker threads
* Results returned in original request order
* Optional fail-fast mode
* Thread-safe execution

Basic Usage
-----------

Simple Concurrent Requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClient, HttpRequest, HttpMethod

    client = create_client('https://api.example.com')

    # Create multiple requests
    requests = [
        HttpRequest(method=HttpMethod.GET, url=f'/users/{i}')
        for i in range(1, 11)
    ]

    # Execute concurrently with 5 workers
    results = client.request_many(requests, max_workers=5)

    # Process results
    for index, result in results:
        if isinstance(result, HttpResponse):
            print(f"Request {index}: Success - {result.status_code}")
            user = result.json()
            print(f"  User: {user['name']}")
        else:
            print(f"Request {index}: Failed - {result}")

Fail-Fast Mode
~~~~~~~~~~~~~~

Stop execution on first error:

.. code-block:: python

    from requestforge import HttpClientException

    try:
        results = client.request_many(
            requests,
            max_workers=10,
            fail_fast=True  # Stop on first error
        )

        # All requests succeeded
        for index, response in results:
            process_response(response)

    except HttpClientException as e:
        print(f"Request failed: {e}")
        # Processing stopped at first error

Configuration
-------------

Worker Threads
~~~~~~~~~~~~~~

Control the number of concurrent requests:

.. code-block:: python

    # Conservative: 3 concurrent requests
    results = client.request_many(requests, max_workers=3)

    # Moderate: 10 concurrent requests (default: 5)
    results = client.request_many(requests, max_workers=10)

    # Aggressive: 20 concurrent requests
    results = client.request_many(requests, max_workers=20)

**Choosing max_workers:**

* **Too few**: Slower execution, underutilized resources
* **Too many**: May overwhelm server, hit rate limits
* **Rule of thumb**: Start with 5-10, adjust based on API rate limits

Request Order
~~~~~~~~~~~~~

Results are yielded as they complete, but include the original index:

.. code-block:: python

    requests = [
        HttpRequest(method=HttpMethod.GET, url='/slow-endpoint'),   # 0 - Takes 5s
        HttpRequest(method=HttpMethod.GET, url='/fast-endpoint'),   # 1 - Takes 1s
        HttpRequest(method=HttpMethod.GET, url='/medium-endpoint'), # 2 - Takes 3s
    ]

    for index, result in client.request_many(requests):
        print(f"Completed request {index}")

    # Output might be:
    # Completed request 1  (fast endpoint finished first)
    # Completed request 2  (medium endpoint finished second)
    # Completed request 0  (slow endpoint finished last)

Sorting Results
~~~~~~~~~~~~~~~

Collect and sort by original index:

.. code-block:: python

    # Collect all results
    results = list(client.request_many(requests, max_workers=10))

    # Sort by index
    results.sort(key=lambda x: x[0])

    # Process in order
    for index, response in results:
        print(f"Processing request {index}")

Common Patterns
---------------

Batch API Calls
~~~~~~~~~~~~~~~

Fetch multiple resources:

.. code-block:: python

    from requestforge import HttpRequest, HttpMethod, HttpClientException

    def fetch_users_batch(user_ids):
        """Fetch multiple users concurrently."""
        requests = [
            HttpRequest(method=HttpMethod.GET, url=f'/users/{user_id}')
            for user_id in user_ids
        ]

        users = []
        errors = []

        for index, result in client.request_many(requests, max_workers=10):
            if isinstance(result, HttpClientException):
                errors.append({
                    'user_id': user_ids[index],
                    'error': str(result)
                })
            else:
                users.append(result.json())

        return users, errors

    # Usage
    users, errors = fetch_users_batch([1, 2, 3, 4, 5])
    print(f"Fetched {len(users)} users, {len(errors)} errors")

Parallel POST Requests
~~~~~~~~~~~~~~~~~~~~~~

Create multiple resources:

.. code-block:: python

    def create_users_batch(users_data):
        """Create multiple users concurrently."""
        requests = [
            HttpRequest(
                method=HttpMethod.POST,
                url='/users',
                json_data=user_data
            )
            for user_data in users_data
        ]

        created_users = []
        failures = []

        for index, result in client.request_many(requests, max_workers=5):
            if isinstance(result, HttpResponse) and result.is_success:
                created_users.append(result.json())
            else:
                failures.append({
                    'data': users_data[index],
                    'error': result if isinstance(result, Exception) else f"HTTP {result.status_code}"
                })

        return created_users, failures

Mixed Request Types
~~~~~~~~~~~~~~~~~~~

Different HTTP methods in one batch:

.. code-block:: python

    requests = [
        # GET requests
        HttpRequest(method=HttpMethod.GET, url='/users/1'),
        HttpRequest(method=HttpMethod.GET, url='/users/2'),

        # POST requests
        HttpRequest(
            method=HttpMethod.POST,
            url='/users',
            json_data={'name': 'John'}
        ),

        # PUT requests
        HttpRequest(
            method=HttpMethod.PUT,
            url='/users/3',
            json_data={'name': 'Jane Updated'}
        ),

        # DELETE requests
        HttpRequest(method=HttpMethod.DELETE, url='/users/4'),
    ]

    results = client.request_many(requests, max_workers=10)

Pagination with Concurrency
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fetch multiple pages in parallel:

.. code-block:: python

    def fetch_all_pages(base_url, total_pages):
        """Fetch all pages concurrently."""
        requests = [
            HttpRequest(
                method=HttpMethod.GET,
                url=base_url,
                params={'page': page, 'limit': 100}
            )
            for page in range(1, total_pages + 1)
        ]

        all_items = []

        for index, response in client.request_many(requests, max_workers=10):
            if isinstance(response, HttpResponse) and response.is_success:
                data = response.json()
                all_items.extend(data.get('items', []))

        return all_items

    # First, get total count
    response = client.get('/items', params={'page': 1, 'limit': 100})
    total = response.json()['total']
    total_pages = (total + 99) // 100  # Ceiling division

    # Fetch all pages
    items = fetch_all_pages('/items', total_pages)

Error Handling
--------------

Collecting Errors
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from requestforge import HttpClientException, HttpResponse

    successful_responses = []
    failed_requests = []

    for index, result in client.request_many(requests, max_workers=10):
        if isinstance(result, HttpResponse):
            if result.is_success:
                successful_responses.append((index, result))
            else:
                failed_requests.append({
                    'index': index,
                    'status_code': result.status_code,
                    'error': result.text
                })
        elif isinstance(result, HttpClientException):
            failed_requests.append({
                'index': index,
                'error': str(result),
                'exception_type': type(result).__name__
            })

    print(f"Success: {len(successful_responses)}, Failed: {len(failed_requests)}")

Partial Retry
~~~~~~~~~~~~~

Retry only failed requests:

.. code-block:: python

    from requestforge import HttpClientException

    def fetch_with_retry(requests, max_retries=2):
        """Fetch requests with retry for failures."""
        remaining_requests = list(enumerate(requests))
        all_results = {}

        for attempt in range(max_retries + 1):
            if not remaining_requests:
                break

            print(f"Attempt {attempt + 1}: {len(remaining_requests)} requests")

            # Execute current batch
            batch = [req for _, req in remaining_requests]
            results = client.request_many(batch, max_workers=10, fail_fast=False)

            # Process results
            failed = []
            for result_index, result in results:
                original_index = remaining_requests[result_index][0]

                if isinstance(result, HttpResponse) and result.is_success:
                    all_results[original_index] = result
                else:
                    if attempt < max_retries:
                        failed.append(remaining_requests[result_index])

            remaining_requests = failed

        return all_results

Error Statistics
~~~~~~~~~~~~~~~~

Track error types:

.. code-block:: python

    from collections import Counter
    from requestforge import (
        TimeoutException,
        ConnectionException,
        HttpStatusException
    )

    error_types = Counter()
    status_codes = Counter()

    for index, result in client.request_many(requests, max_workers=10):
        if isinstance(result, TimeoutException):
            error_types['timeout'] += 1
        elif isinstance(result, ConnectionException):
            error_types['connection'] += 1
        elif isinstance(result, HttpStatusException):
            error_types['http_error'] += 1
            status_codes[result.status_code] += 1

    print(f"Error types: {dict(error_types)}")
    print(f"Status codes: {dict(status_codes)}")

Performance Optimization
------------------------

Connection Pooling
~~~~~~~~~~~~~~~~~~

Configure pool size for concurrent requests:

.. code-block:: python

    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_pool_connection(20)   # Pool connections
        .with_pool_maxsize(50)      # Max pool size
        .build()
    )

    client = HttpClient(config)

    # Now concurrent requests reuse connections
    results = client.request_many(requests, max_workers=20)

Batching Requests
~~~~~~~~~~~~~~~~~

Process requests in batches to control memory:

.. code-block:: python

    def process_in_batches(all_requests, batch_size=100, max_workers=10):
        """Process requests in batches."""
        all_results = []

        for i in range(0, len(all_requests), batch_size):
            batch = all_requests[i:i + batch_size]
            print(f"Processing batch {i // batch_size + 1}")

            batch_results = list(
                client.request_many(batch, max_workers=max_workers)
            )
            all_results.extend(batch_results)

        return all_results

    # Process 1000 requests in batches of 100
    results = process_in_batches(requests, batch_size=100)

Rate Limiting
~~~~~~~~~~~~~

Respect API rate limits:

.. code-block:: python

    import time
    from threading import Semaphore

    class RateLimitedClient:
        def __init__(self, client, requests_per_second=10):
            self.client = client
            self.min_interval = 1.0 / requests_per_second
            self.last_request_time = 0
            self.semaphore = Semaphore(1)

        def request(self, http_request):
            with self.semaphore:
                # Wait if needed
                now = time.time()
                time_since_last = now - self.last_request_time
                if time_since_last < self.min_interval:
                    time.sleep(self.min_interval - time_since_last)

                result = self.client.request(http_request)
                self.last_request_time = time.time()
                return result

    # Usage
    rate_limited = RateLimitedClient(client, requests_per_second=10)

Progress Tracking
-----------------

Progress Bar
~~~~~~~~~~~~

Using tqdm for progress:

.. code-block:: python

    from tqdm import tqdm

    requests = [
        HttpRequest(method=HttpMethod.GET, url=f'/users/{i}')
        for i in range(1, 101)
    ]

    results = []
    with tqdm(total=len(requests), desc="Fetching users") as pbar:
        for index, result in client.request_many(requests, max_workers=10):
            results.append((index, result))
            pbar.update(1)

Custom Progress
~~~~~~~~~~~~~~~

.. code-block:: python

    def fetch_with_progress(requests, max_workers=10):
        """Fetch with custom progress reporting."""
        total = len(requests)
        completed = 0
        successful = 0
        failed = 0

        print(f"Starting {total} requests with {max_workers} workers...")

        for index, result in client.request_many(requests, max_workers=max_workers):
            completed += 1

            if isinstance(result, HttpResponse) and result.is_success:
                successful += 1
            else:
                failed += 1

            # Print progress every 10 requests
            if completed % 10 == 0:
                print(f"Progress: {completed}/{total} "
                      f"(✓ {successful}, ✗ {failed})")

        print(f"Completed: {successful} successful, {failed} failed")

Advanced Patterns
-----------------

Request Prioritization
~~~~~~~~~~~~~~~~~~~~~~

Submit high-priority requests first:

.. code-block:: python

    from dataclasses import dataclass
    from typing import Any

    @dataclass
    class PrioritizedRequest:
        priority: int
        request: HttpRequest
        metadata: Any = None

    def execute_prioritized(prioritized_requests, max_workers=10):
        """Execute requests in priority order."""
        # Sort by priority (lower number = higher priority)
        sorted_requests = sorted(
            prioritized_requests,
            key=lambda x: x.priority
        )

        requests = [pr.request for pr in sorted_requests]

        results = {}
        for index, result in client.request_many(requests, max_workers=max_workers):
            original_request = sorted_requests[index]
            results[original_request.metadata] = result

        return results

    # Usage
    prioritized = [
        PrioritizedRequest(priority=1, request=HttpRequest(...), metadata='critical'),
        PrioritizedRequest(priority=5, request=HttpRequest(...), metadata='low'),
        PrioritizedRequest(priority=3, request=HttpRequest(...), metadata='medium'),
    ]

Request Deduplication
~~~~~~~~~~~~~~~~~~~~~

Avoid duplicate requests:

.. code-block:: python

    def deduplicate_requests(requests):
        """Remove duplicate requests based on URL."""
        seen = set()
        unique_requests = []
        index_map = {}

        for i, request in enumerate(requests):
            key = f"{request.method.value}:{request.url}"
            if key not in seen:
                seen.add(key)
                index_map[len(unique_requests)] = i
                unique_requests.append(request)

        return unique_requests, index_map

    # Deduplicate
    unique_requests, index_map = deduplicate_requests(requests)

    # Execute only unique requests
    results = list(client.request_many(unique_requests, max_workers=10))

    # Map back to original indices
    full_results = [None] * len(requests)
    for unique_index, (_, result) in enumerate(results):
        original_index = index_map[unique_index]
        full_results[original_index] = result

Dynamic Worker Adjustment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Adjust workers based on response times:

.. code-block:: python

    import statistics

    def adaptive_fetch(requests, initial_workers=5):
        """Adjust worker count based on performance."""
        batch_size = 50
        max_workers = initial_workers

        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]

            # Measure performance
            import time
            start = time.time()
            results = list(client.request_many(batch, max_workers=max_workers))
            duration = time.time() - start

            # Calculate average response time
            response_times = [
                r.elapsed_ms for _, r in results
                if isinstance(r, HttpResponse)
            ]

            if response_times:
                avg_time = statistics.mean(response_times)

                # Adjust workers (simple heuristic)
                if avg_time < 100:  # Fast responses
                    max_workers = min(max_workers + 2, 20)
                elif avg_time > 500:  # Slow responses
                    max_workers = max(max_workers - 2, 3)

                print(f"Avg response: {avg_time:.0f}ms, Workers: {max_workers}")

Testing
-------

Mock Concurrent Requests
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pytest
    from unittest.mock import Mock, patch
    import responses

    @responses.activate
    def test_concurrent_requests():
        # Mock multiple endpoints
        for i in range(1, 11):
            responses.add(
                responses.GET,
                f'https://api.example.com/users/{i}',
                json={'id': i, 'name': f'User {i}'},
                status=200
            )

        client = create_client('https://api.example.com')

        requests = [
            HttpRequest(method=HttpMethod.GET, url=f'/users/{i}')
            for i in range(1, 11)
        ]

        results = list(client.request_many(requests, max_workers=5))

        assert len(results) == 10
        for index, response in results:
            assert isinstance(response, HttpResponse)
            assert response.is_success

Test Error Scenarios
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @responses.activate
    def test_concurrent_with_errors():
        # Some succeed, some fail
        responses.add(responses.GET, 'https://api.example.com/users/1', json={'id': 1}, status=200)
        responses.add(responses.GET, 'https://api.example.com/users/2', json={'error': 'Not found'}, status=404)
        responses.add(responses.GET, 'https://api.example.com/users/3', body='Timeout', status=408)

        client = create_client('https://api.example.com')

        requests = [
            HttpRequest(method=HttpMethod.GET, url=f'/users/{i}')
            for i in range(1, 4)
        ]

        results = list(client.request_many(requests, max_workers=3, fail_fast=False))

        successful = sum(1 for _, r in results if isinstance(r, HttpResponse) and r.is_success)
        failed = len(results) - successful

        assert successful == 1
        assert failed == 2

Best Practices
--------------

1. **Choose Appropriate Worker Count**

   .. code-block:: python

       # Good ✅ - Moderate concurrency
       results = client.request_many(requests, max_workers=10)

       # Avoid ❌ - Too many workers may overwhelm server
       results = client.request_many(requests, max_workers=100)

2. **Handle Errors Gracefully**

   .. code-block:: python

       # Good ✅ - Process both success and failure
       for index, result in client.request_many(requests):
           if isinstance(result, HttpResponse):
               process_success(result)
           else:
               handle_error(index, result)

3. **Use Fail-Fast for Critical Operations**

   .. code-block:: python

       # Good ✅ - Stop on first error for critical batch
       try:
           results = client.request_many(requests, fail_fast=True)
       except HttpClientException:
           rollback_changes()

4. **Monitor Progress for Long Operations**

   .. code-block:: python

       # Good ✅ - Show progress to users
       with tqdm(total=len(requests)) as pbar:
           for index, result in client.request_many(requests):
               pbar.update(1)

5. **Respect Rate Limits**

   .. code-block:: python

       # Good ✅ - Limit concurrent requests
       results = client.request_many(requests, max_workers=5)

       # Or use rate limiting wrapper
       rate_limited_client = RateLimitedClient(client, requests_per_second=10)

Next Steps
----------

* Learn about :doc:`hooks` for concurrent request logging
* Explore :doc:`error-handling` for managing partial failures
* Check :doc:`../examples/django-integration` for async views
