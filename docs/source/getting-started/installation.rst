Installation
============

Requirements
------------

* Python 3.10 or higher
* requests >= 2.31.0

Basic Installation
------------------

Install from PyPI using pip:

.. code-block:: bash

    pip install requestforge

This installs the package with only the required dependency (``requests``).

Optional Dependencies
---------------------

Django Support
~~~~~~~~~~~~~~

For Django cache integration:

.. code-block:: bash

    pip install requestforge[django]

This adds Django as a dependency for ``DjangoCacheTokenStorage``.

Development Installation
------------------------

For development with all dev tools:

.. code-block:: bash

    pip install requestforge[dev]

This includes:

* pytest - Testing framework
* pytest-cov - Coverage reporting
* pytest-mock - Mocking utilities
* responses - HTTP request mocking
* ruff - Linting and formatting
* mypy - Type checking
* tox - Multi-version testing
* pre-commit - Git hooks

From Source
-----------

Clone the repository and install in development mode:

.. code-block:: bash

    git clone https://github.com/baratihd/requestforge.git
    cd requestforge
    pip install -e .

Verifying Installation
----------------------

Verify the installation:

.. code-block:: python

    import requestforge
    print(requestforge.__version__)

    # Create a simple client
    from requestforge import create_client
    client = create_client('https://api.github.com')
    print("✅ Installation successful!")

Upgrading
---------

Upgrade to the latest version:

.. code-block:: bash

    pip install --upgrade requestforge

Uninstalling
------------

Uninstall the package:

.. code-block:: bash

    pip uninstall requestforge
