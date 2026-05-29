Request Forge Documentation
===========================

.. image:: https://img.shields.io/pypi/v/requestforge.svg
   :target: https://pypi.org/project/requestforge/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/requestforge.svg
   :target: https://pypi.org/project/requestforge/
   :alt: Python versions

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. image:: https://github.com/baratihd/requestforge/workflows/Tests/badge.svg
   :target: https://github.com/baratihd/requestforge/actions
   :alt: Tests

Welcome to Request Forge
------------------------

**Request Forge** is a production-ready, thread-safe Request Forge library for Python with advanced features including:

* ✅ **Automatic Retry Strategies** - Exponential backoff, circuit breaker patterns
* ✅ **Token Management** - Automatic token caching, refresh, and expiration handling
* ✅ **Multi-Step Authentication** - Pipeline-based authentication for complex OAuth flows
* ✅ **Lifecycle Hooks** - Extensible request/response interception
* ✅ **Thread-Safe** - Safe for use in multi-threaded environments (Django, Flask, FastAPI)
* ✅ **Comprehensive Error Handling** - Rich exception hierarchy with detailed context
* ✅ **Type Hints** - Full type annotations for IDE autocomplete

Quick Example
-------------

.. code-block:: python

    from requestforge import HttpClient, HttpClientConfigBuilder

    # Create configured client
    config = (
        HttpClientConfigBuilder()
        .with_base_url('https://api.example.com')
        .with_retry(max_retries=3)
        .with_logging()
        .build()
    )

    client = HttpClient(config)

    # Make requests
    response = client.get('/users/1')
    if response.is_success:
        user = response.json()
        print(f"User: {user['name']}")

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/installation
   getting-started/quickstart
   getting-started/configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user-guide/basic-usage
   user-guide/authentication
   user-guide/retry-strategies
   user-guide/hooks
   user-guide/error-handling
   user-guide/concurrent-requests
   user-guide/advanced-usage

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api-reference/client
   api-reference/config
   api-reference/models
   api-reference/retry
   api-reference/hooks
   api-reference/token-manager
   api-reference/pipelines
   api-reference/fetcher
   api-reference/exceptions
   api-reference/utils

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic-requests
   examples/oauth2-flow
   examples/multi-step-auth
   examples/custom-retry
   examples/django-integration

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/design-principles
   architecture/components
   architecture/thread-safety

.. toctree::
   :maxdepth: 2
   :caption: Development

   contributing/development
   contributing/testing
   contributing/code-style
   changelog

Features
--------

Core Features
~~~~~~~~~~~~~

* **Clean API**: Intuitive interface for all HTTP methods
* **Thread-Safe**: Connection pooling and thread-local sessions
* **Builder Pattern**: Fluent configuration interface
* **Context Managers**: Clean resource management
* **Type Hints**: Full type annotations

Authentication
~~~~~~~~~~~~~~

* **Token Management**: Automatic caching and refresh
* **Multi-Step Pipelines**: Chain multiple auth steps
* **Auto-Retry on 401**: Automatic token refresh and retry
* **Multiple Auth Types**: Bearer, API Key, Basic, Custom

Retry Strategies
~~~~~~~~~~~~~~~~

* **Exponential Backoff**: Configurable with jitter
* **Circuit Breaker**: Prevent cascade failures
* **Custom Strategies**: Implement your own logic
* **Status Code Retry**: Retry on specific HTTP codes

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
