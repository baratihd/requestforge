Django Integration Examples
============================

This page demonstrates how to integrate HTTP Client with Django applications.

Basic Django Setup
------------------

settings.py Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # settings.py
    from requestforge import (
        HttpClient,
        HttpClientConfigBuilder,
        TokenManager,
        ClientCredentialsTokenProvider,
        DjangoCacheTokenStorage
    )
    import os

    # OAuth2 Token Provider
    OAUTH_PROVIDER = ClientCredentialsTokenProvider(
        token_url=os.getenv('OAUTH_TOKEN_URL'),
        client_id=os.getenv('OAUTH_CLIENT_ID'),
        client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
        service_name='external-api'
    )

    # Token Manager with Django Cache
    TOKEN_MANAGER = TokenManager(
        provider=OAUTH_PROVIDER,
        storage=DjangoCacheTokenStorage(
            cache_alias='default',
            key_prefix='api_tokens'
        )
    )

    # HTTP Client Configuration
    API_CLIENT_CONFIG = (
        HttpClientConfigBuilder()
        .with_base_url(os.getenv('API_BASE_URL'))
        .with_timeout(30.0)
        .with_retry(max_retries=3)
        .with_token_auth(token_manager=TOKEN_MANAGER)
        .with_logging(log_headers=True)
        .build()
    )

    # HTTP Client Instance (shared across application)
    API_CLIENT = HttpClient(API_CLIENT_CONFIG)

    # Django Cache Configuration
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'myapp',
            'TIMEOUT': 300,
        }
    }

Using in Views
~~~~~~~~~~~~~~

.. code-block:: python

    # views.py
    from django.conf import settings
    from django.http import JsonResponse
    from requestforge import HttpClientException

    def get_users(request):
        """Fetch users from external API."""
        try:
            response = settings.API_CLIENT.get('/users')

            if response.is_success:
                users = response.json()
                return JsonResponse({'users': users})
            else:
                return JsonResponse(
                    {'error': f'API returned {response.status_code}'},
                    status=response.status_code
                )

        except HttpClientException as e:
            return JsonResponse(
                {'error': str(e)},
                status=500
            )

    def create_user(request):
        """Create user in external API."""
        import json

        try:
            data = json.loads(request.body)

            response = settings.API_CLIENT.post('/users', json_data={
                'name': data.get('name'),
                'email': data.get('email')
            })

            if response.status_code == 201:
                user = response.json()
                return JsonResponse({'user': user}, status=201)
            else:
                return JsonResponse(
                    {'error': 'Failed to create user'},
                    status=response.status_code
                )

        except HttpClientException as e:
            return JsonResponse({'error': str(e)}, status=500)

Service Layer Pattern
---------------------

API Service Class
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # services/api_service.py
    from django.conf import settings
    from requestforge import HttpClientException, NotFoundException
    import logging

    logger = logging.getLogger(__name__)

    class ExternalAPIService:
        """Service for interacting with external API."""

        def __init__(self):
            self.client = settings.API_CLIENT

        def get_user(self, user_id):
            """Get user by ID."""
            try:
                response = self.client.get(f'/users/{user_id}')
                return response.json()
            except NotFoundException:
                return None
            except HttpClientException as e:
                logger.error(f"Failed to fetch user {user_id}: {e}")
                raise

        def list_users(self, page=1, limit=10):
            """List users with pagination."""
            try:
                response = self.client.get('/users', params={
                    'page': page,
                    'limit': limit
                })
                return response.json()
            except HttpClientException as e:
                logger.error(f"Failed to list users: {e}")
                return {'items': [], 'total': 0}

        def create_user(self, name, email):
            """Create a new user."""
            try:
                response = self.client.post('/users', json_data={
                    'name': name,
                    'email': email
                })

                if response.status_code == 201:
                    return response.json()
                else:
                    raise ValueError(f"Failed to create user: {response.status_code}")

            except HttpClientException as e:
                logger.error(f"Failed to create user: {e}")
                raise

        def update_user(self, user_id, **kwargs):
            """Update user."""
            try:
                response = self.client.patch(f'/users/{user_id}', json_data=kwargs)
                return response.json()
            except HttpClientException as e:
                logger.error(f"Failed to update user {user_id}: {e}")
                raise

        def delete_user(self, user_id):
            """Delete user."""
            try:
                response = self.client.delete(f'/users/{user_id}')
                return response.status_code == 204
            except HttpClientException as e:
                logger.error(f"Failed to delete user {user_id}: {e}")
                return False

Using Service in Views
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # views.py
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    from .services.api_service import ExternalAPIService

    api_service = ExternalAPIService()

    def user_detail(request, user_id):
        """Get user detail."""
        user = api_service.get_user(user_id)

        if user:
            return JsonResponse({'user': user})
        else:
            return JsonResponse({'error': 'User not found'}, status=404)

    def user_list(request):
        """List users."""
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))

        data = api_service.list_users(page=page, limit=limit)
        return JsonResponse(data)

    @require_http_methods(["POST"])
    def user_create(request):
        """Create user."""
        import json

        data = json.loads(request.body)

        try:
            user = api_service.create_user(
                name=data['name'],
                email=data['email']
            )
            return JsonResponse({'user': user}, status=201)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'Internal error'}, status=500)

Django REST Framework Integration
----------------------------------

API Client Mixin
~~~~~~~~~~~~~~~~

.. code-block:: python

    # mixins.py
    from rest_framework.response import Response
    from rest_framework import status
    from requestforge import HttpClientException, NotFoundException
    import logging

    logger = logging.getLogger(__name__)

    class ExternalAPIMixin:
        """Mixin for views that interact with external API."""

        def __init__(self):
            from .services.api_service import ExternalAPIService
            self.api_service = ExternalAPIService()

        def handle_api_exception(self, e):
            """Handle API exceptions."""
            if isinstance(e, NotFoundException):
                return Response(
                    {'error': 'Resource not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            logger.error(f"API error: {e}")
            return Response(
                {'error': 'External API error'},
                status=status.HTTP_502_BAD_GATEWAY
            )

ViewSet Example
~~~~~~~~~~~~~~~

.. code-block:: python

    # viewsets.py
    from rest_framework import viewsets, status
    from rest_framework.response import Response
    from rest_framework.decorators import action
    from .mixins import ExternalAPIMixin
    from requestforge import HttpClientException

    class UserViewSet(ExternalAPIMixin, viewsets.ViewSet):
        """ViewSet for managing users via external API."""

        def list(self, request):
            """List users."""
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 10))

            try:
                data = self.api_service.list_users(page=page, limit=limit)
                return Response(data)
            except HttpClientException as e:
                return self.handle_api_exception(e)

        def retrieve(self, request, pk=None):
            """Get user by ID."""
            try:
                user = self.api_service.get_user(pk)
                if user:
                    return Response(user)
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except HttpClientException as e:
                return self.handle_api_exception(e)

        def create(self, request):
            """Create user."""
            try:
                user = self.api_service.create_user(
                    name=request.data['name'],
                    email=request.data['email']
                )
                return Response(user, status=status.HTTP_201_CREATED)
            except HttpClientException as e:
                return self.handle_api_exception(e)

        def update(self, request, pk=None):
            """Update user."""
            try:
                user = self.api_service.update_user(pk, **request.data)
                return Response(user)
            except HttpClientException as e:
                return self.handle_api_exception(e)

        def destroy(self, request, pk=None):
            """Delete user."""
            try:
                if self.api_service.delete_user(pk):
                    return Response(status=status.HTTP_204_NO_CONTENT)
                return Response(
                    {'error': 'Failed to delete'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except HttpClientException as e:
                return self.handle_api_exception(e)

Async Views (Django 4.1+)
--------------------------

Async View Example
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # views.py
    from django.http import JsonResponse
    from asgiref.sync import sync_to_async
    from django.conf import settings

    async def async_get_users(request):
        """Async view to fetch users."""
        # Run sync HTTP client in thread pool
        response = await sync_to_async(settings.API_CLIENT.get)('/users')

        if response.is_success:
            users = response.json()
            return JsonResponse({'users': users})
        else:
            return JsonResponse(
                {'error': 'Failed to fetch users'},
                status=response.status_code
            )

Celery Integration
------------------

Celery Task
~~~~~~~~~~~

.. code-block:: python

    # tasks.py
    from celery import shared_task
    from django.conf import settings
    from requestforge import HttpClientException
    import logging

    logger = logging.getLogger(__name__)

    @shared_task
    def sync_users():
        """Background task to sync users from external API."""
        from .models import User

        try:
            response = settings.API_CLIENT.get('/users')

            if response.is_success:
                users_data = response.json()

                for user_data in users_data:
                    User.objects.update_or_create(
                        external_id=user_data['id'],
                        defaults={
                            'name': user_data['name'],
                            'email': user_data['email']
                        }
                    )

                logger.info(f"Synced {len(users_data)} users")
                return {'synced': len(users_data)}
            else:
                logger.error(f"Sync failed: {response.status_code}")
                return {'error': response.status_code}

        except HttpClientException as e:
            logger.error(f"Sync failed: {e}")
            raise

    @shared_task
    def fetch_user_details(user_id):
        """Fetch and update user details."""
        from .models import User

        try:
            response = settings.API_CLIENT.get(f'/users/{user_id}')

            if response.is_success:
                data = response.json()
                User.objects.update_or_create(
                    external_id=user_id,
                    defaults={'name': data['name'], 'email': data['email']}
                )
                return {'updated': True}

        except HttpClientException as e:
            logger.error(f"Failed to fetch user {user_id}: {e}")
            raise

Django Management Command
--------------------------

Custom Management Command
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # management/commands/sync_api_data.py
    from django.core.management.base import BaseCommand
    from django.conf import settings
    from requestforge import HttpClientException

    class Command(BaseCommand):
        help = 'Sync data from external API'

        def add_arguments(self, parser):
            parser.add_argument(
                '--resource',
                type=str,
                default='users',
                help='Resource to sync (users, posts, etc.)'
            )

        def handle(self, *args, **options):
            resource = options['resource']

            self.stdout.write(f'Syncing {resource}...')

            try:
                response = settings.API_CLIENT.get(f'/{resource}')

                if response.is_success:
                    data = response.json()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully fetched {len(data)} {resource}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed: HTTP {response.status_code}'
                        )
                    )

            except HttpClientException as e:
                self.stdout.write(
                    self.style.ERROR(f'Error: {e}')
                )

Middleware Integration
----------------------

Request ID Middleware
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # middleware.py
    import uuid

    class RequestIDMiddleware:
        """Add request ID to all API calls."""

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            # Generate request ID
            request_id = str(uuid.uuid4())
            request.request_id = request_id

            # Add to HTTP client context (via thread-local or similar)
            # This would require custom hook implementation

            response = self.get_response(request)
            return response

Testing with Django
-------------------

Test Case with Mocked API
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # tests.py
    from django.test import TestCase, override_settings
    from unittest.mock import Mock, patch
    from requestforge import HttpResponse, HttpRequest, HttpMethod
    from .services.api_service import ExternalAPIService

    class ExternalAPIServiceTest(TestCase):
        """Test external API service."""

        def setUp(self):
            self.service = ExternalAPIService()

        @patch('django.conf.settings.API_CLIENT.get')
        def test_get_user_success(self, mock_get):
            # Mock successful response
            mock_response = Mock(spec=HttpResponse)
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.json.return_value = {
                'id': 1,
                'name': 'John Doe',
                'email': 'john@example.com'
            }
            mock_get.return_value = mock_response

            # Call service
            user = self.service.get_user(1)

            # Assertions
            self.assertEqual(user['name'], 'John Doe')
            mock_get.assert_called_once_with('/users/1')

        @patch('django.conf.settings.API_CLIENT.get')
        def test_get_user_not_found(self, mock_get):
            from requestforge import NotFoundException

            # Mock 404 response
            mock_get.side_effect = NotFoundException()

            # Call service
            user = self.service.get_user(999)

            # Should return None
            self.assertIsNone(user)

Using responses Library
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import responses
    from django.test import TestCase
    from .services.api_service import ExternalAPIService

    class ExternalAPIIntegrationTest(TestCase):
        """Integration tests with mocked HTTP."""

        def setUp(self):
            self.service = ExternalAPIService()

        @responses.activate
        def test_list_users(self):
            # Mock API response
            responses.add(
                responses.GET,
                'https://api.example.com/users',
                json={
                    'items': [
                        {'id': 1, 'name': 'User 1'},
                        {'id': 2, 'name': 'User 2'}
                    ],
                    'total': 2
                },
                status=200
            )

            # Call service
            result = self.service.list_users()

            # Assertions
            self.assertEqual(len(result['items']), 2)
            self.assertEqual(result['total'], 2)

Environment-Based Configuration
--------------------------------

Multiple Environments
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # settings/base.py
    from requestforge import (
        HttpClientConfigBuilder,
        HttpClient,
        TokenManager,
        ClientCredentialsTokenProvider,
        DjangoCacheTokenStorage
    )

    def create_api_client():
        """Factory for creating API client."""
        provider = ClientCredentialsTokenProvider(
            token_url=os.getenv('OAUTH_TOKEN_URL'),
            client_id=os.getenv('OAUTH_CLIENT_ID'),
            client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
            service_name='api'
        )

        token_manager = TokenManager(
            provider=provider,
            storage=DjangoCacheTokenStorage()
        )

        config = (
            HttpClientConfigBuilder()
            .with_base_url(os.getenv('API_BASE_URL'))
            .with_token_auth(token_manager=token_manager)
            .build()
        )

        return HttpClient(config)

    API_CLIENT = create_api_client()

    # settings/development.py
    from .base import *

    # Development-specific settings
    DEBUG = True
    API_CLIENT_CONFIG = (
        HttpClientConfigBuilder()
        .with_base_url('http://localhost:8000')
        .with_verify_ssl(False)
        .with_logging(log_headers=True, log_body=True)
        .build()
    )

    # settings/production.py
    from .base import *

    # Production-specific settings
    DEBUG = False
    API_CLIENT_CONFIG = (
        HttpClientConfigBuilder()
        .with_base_url(os.getenv('API_BASE_URL'))
        .with_verify_ssl(True)
        .with_retry(max_retries=5)
        .with_pool_connection(50)
        .with_pool_maxsize(100)
        .build()
    )

See Also
--------

* :doc:`basic-requests` - Basic request examples
* :doc:`oauth2-flow` - OAuth2 authentication
* :doc:`../user-guide/authentication` - Authentication guide
* :doc:`../api-reference/token-manager` - Token manager API
