Development Guide
=================

This guide covers setting up a development environment and contributing to Request Forge.

Getting Started
---------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.10 or higher
* Git
* pip and virtualenv

Fork and Clone
~~~~~~~~~~~~~~

1. **Fork the repository** on GitHub

2. **Clone your fork**:

   .. code-block:: bash

       git clone https://github.com/YOUR_USERNAME/requestforge.git
       cd requestforge

3. **Add upstream remote**:

   .. code-block:: bash

       git remote add upstream https://github.com/baratihd/requestforge.git

Development Setup
-----------------

Create Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Create virtual environment
    python -m venv venv

    # Activate (Linux/Mac)
    source venv/bin/activate

    # Activate (Windows)
    venv\Scripts\activate

Install Dependencies
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Install package in editable mode with dev dependencies
    pip install -e ".[dev]"

This installs:

* Core dependencies (requests)
* Testing tools (pytest, pytest-cov, responses)
* Linting tools (ruff)
* Build tools (build, twine)

Install Pre-commit Hooks
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Install pre-commit hooks
    pre-commit install

This automatically runs linters and formatters before each commit.

Project Structure
-----------------

.. code-block:: text

    requestforge/
    ├── src/
    │   └── requestforge/
    │       ├── __init__.py          # Package initialization
    │       ├── client.py            # Main HTTP client
    │       ├── config.py            # Configuration classes
    │       ├── exceptions.py        # Custom exceptions
    │       ├── fetcher.py           # Token fetchers
    │       ├── hooks.py             # Lifecycle hooks
    │       ├── interfaces.py        # Abstract interfaces
    │       ├── models.py            # Data models
    │       ├── pipelines.py         # Token pipelines
    │       ├── retry.py             # Retry strategies
    │       ├── token_manager.py     # Token management
    │       └── utils.py             # Utilities
    ├── tests/
    │   ├── __init__.py
    │   ├── conftest.py              # Pytest configuration
    │   ├── test_client.py           # Client tests
    │   ├── test_config.py           # Config tests
    │   └── ...                      # More tests
    ├── docs/
    │   └── source/                  # Documentation source
    ├── .github/
    │   └── workflows/
    │       └── test.yml             # CI/CD workflow
    ├── pyproject.toml               # Project metadata
    ├── tox.ini                      # Tox configuration
    ├── .pre-commit-config.yaml      # Pre-commit hooks
    ├── README.md                    # Project README
    ├── CHANGELOG.md                 # Changelog
    └── CONTRIBUTING.md              # Contributing guide

Development Workflow
--------------------

1. Create Feature Branch
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Update main branch
    git checkout main
    git pull upstream main

    # Create feature branch
    git checkout -b feature/amazing-feature

2. Make Changes
~~~~~~~~~~~~~~~

* Write code
* Add tests
* Update documentation
* Follow code style guidelines

3. Run Tests
~~~~~~~~~~~~

.. code-block:: bash

    # Run all tests
    pytest

    # Run with coverage
    pytest --cov=requestforge --cov-report=html

    # Run specific test file
    pytest tests/test_client.py

    # Run specific test
    pytest tests/test_client.py::TestHttpClient::test_get_request

4. Run Linters
~~~~~~~~~~~~~~

.. code-block:: bash

    # Check code style
    ruff check src/ tests/

    # Fix auto-fixable issues
    ruff check --fix src/ tests/

    # Format code
    ruff format src/ tests/

5. Commit Changes
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Stage changes
    git add .

    # Commit (pre-commit hooks run automatically)
    git commit -m "Add amazing feature"

    # If pre-commit fails, fix issues and commit again

6. Push to Your Fork
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git push origin feature/amazing-feature

7. Create Pull Request
~~~~~~~~~~~~~~~~~~~~~~

* Go to GitHub
* Click "New Pull Request"
* Select your branch
* Fill in description
* Link related issues

Adding New Features
-------------------

Adding a New Retry Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Create strategy class** in ``src/requestforge/retry.py``:

   .. code-block:: python

       from requestforge.interfaces import RetryStrategyInterface

       class MyRetryStrategy(RetryStrategyInterface):
           def __init__(self, max_retries=3):
               self._max_retries = max_retries

           @property
           def max_retries(self):
               return self._max_retries

           def should_retry(self, context, exception):
               # Your logic here
               return context.attempt < self._max_retries

           def get_delay(self, context):
               # Your delay logic
               return 1.0

2. **Add tests** in ``tests/test_retry.py``:

   .. code-block:: python

       def test_my_retry_strategy():
           strategy = MyRetryStrategy(max_retries=3)
           # Test logic

3. **Update documentation** in ``docs/source/api-reference/retry.rst``

4. **Add to CHANGELOG.md**

Adding a New Hook
~~~~~~~~~~~~~~~~~

1. **Create hook class** in ``src/requestforge/hooks.py``:

   .. code-block:: python

       from requestforge.interfaces import RequestHookInterface

       class MyHook(RequestHookInterface):
           def before_request(self, request, context):
               # Your logic
               return request

2. **Add tests** in ``tests/test_hooks.py``

3. **Update documentation**

Adding a New Exception
~~~~~~~~~~~~~~~~~~~~~~

1. **Create exception class** in ``src/requestforge/exceptions.py``:

   .. code-block:: python

       class MyException(HttpClientException):
           """Custom exception for specific case."""
           pass

2. **Add tests**

3. **Update exception documentation**

Running Tests
-------------

Test Commands
~~~~~~~~~~~~~

.. code-block:: bash

    # Run all tests
    pytest

    # Run with verbose output
    pytest -v

    # Run with coverage
    pytest --cov=requestforge --cov-report=html --cov-report=term-missing

    # Run specific test file
    pytest tests/test_client.py

    # Run tests matching pattern
    pytest -k "test_get"

    # Run only unit tests
    pytest -m unit

    # Run only integration tests
    pytest -m integration

    # Stop on first failure
    pytest -x

    # Run tests in parallel
    pytest -n auto

Coverage Reports
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Generate HTML coverage report
    pytest --cov=requestforge --cov-report=html

    # Open report in browser
    # open htmlcov/index.html  (Mac)
    # start htmlcov/index.html (Windows)
    # xdg-open htmlcov/index.html (Linux)

Code Quality
------------

Linting
~~~~~~~

.. code-block:: bash

    # Check all code
    ruff check src/ tests/

    # Check specific file
    ruff check src/requestforge/client.py

    # Fix auto-fixable issues
    ruff check --fix src/ tests/

    # Show diff of fixes
    ruff check --diff src/

Formatting
~~~~~~~~~~

.. code-block:: bash

    # Format all code
    ruff format src/ tests/

    # Check formatting without changes
    ruff format --check src/ tests/

    # Format specific file
    ruff format src/requestforge/client.py

Type Checking
~~~~~~~~~~~~~

.. code-block:: bash

    # Run mypy (if configured)
    mypy src/requestforge

Pre-commit Hooks
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Run all hooks manually
    pre-commit run --all-files

    # Run specific hook
    pre-commit run ruff --all-files

    # Update hooks to latest version
    pre-commit autoupdate

Building Documentation
----------------------

.. code-block:: bash

    # Install documentation dependencies
    pip install -r docs/requirements.txt

    # Build HTML documentation
    cd docs
    make html

    # Open documentation
    open build/html/index.html

    # Clean build
    make clean

    # Build and watch for changes (requires sphinx-autobuild)
    make livehtml

Testing Against Multiple Python Versions
-----------------------------------------

.. code-block:: bash

    # Install tox
    pip install tox

    # Run tests on all Python versions
    tox

    # Run tests on specific Python version
    tox -e py310

    # Run tests on Python 3.11 with requests 2.31
    tox -e py311-requests231

    # Recreate environments
    tox -r

Creating a Release
------------------

1. Update Version
~~~~~~~~~~~~~~~~~

Update version in ``pyproject.toml``:

.. code-block:: toml

    [project]
    version = "1.1.0"

2. Update CHANGELOG
~~~~~~~~~~~~~~~~~~~

Add release notes to ``CHANGELOG.md``:

.. code-block:: markdown

    ## [1.1.0] - 2024-02-01

    ### Added
    - New feature X
    - New feature Y

    ### Fixed
    - Bug fix Z

3. Create Release Commit
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git add pyproject.toml CHANGELOG.md
    git commit -m "Release version 1.1.0"
    git tag -a v1.1.0 -m "Version 1.1.0"

4. Build Distribution
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Clean old builds
    rm -rf dist/ build/

    # Build
    python -m build

    # Check distribution
    twine check dist/*

5. Publish to PyPI
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Publish to Test PyPI first
    twine upload --repository testpypi dist/*

    # Test installation
    pip install --index-url https://test.pypi.org/simple/ requestforge

    # Publish to PyPI
    twine upload dist/*

6. Push to GitHub
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    git push origin main
    git push origin v1.1.0

Troubleshooting
---------------

Tests Failing
~~~~~~~~~~~~~

.. code-block:: bash

    # Clear pytest cache
    rm -rf .pytest_cache

    # Run tests with verbose output
    pytest -vv

    # Run tests with print statements
    pytest -s

Import Errors
~~~~~~~~~~~~~

.. code-block:: bash

    # Reinstall package in editable mode
    pip install -e ".[dev]"

    # Check Python path
    python -c "import sys; print(sys.path)"

Pre-commit Hook Failures
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Skip pre-commit hooks (not recommended)
    git commit --no-verify

    # Fix issues and commit again
    ruff check --fix src/ tests/
    git add .
    git commit

Getting Help
------------

* **GitHub Issues**: https://github.com/baratihd/requestforge/issues
* **GitHub Discussions**: https://github.com/baratihd/requestforge/discussions
* **Documentation**: https://requestforge.readthedocs.io

Best Practices
--------------

1. **Write Tests**: All new features should have tests
2. **Update Documentation**: Keep docs in sync with code
3. **Follow Code Style**: Use ruff for formatting and linting
4. **Small Commits**: Make atomic commits with clear messages
5. **Update CHANGELOG**: Document all changes
6. **Be Respectful**: Follow code of conduct

See Also
--------

* :doc:`testing` - Testing guide
* :doc:`code-style` - Code style guide
* :doc:`../architecture/design-principles` - Design principles
