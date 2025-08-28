#python
"""
Django application configuration for the Okta client.
"""

from logging import getLogger

from django.apps import AppConfig

from .signals.events import user_lifecycle_create

LOGGER = getLogger(__name__)


class OktaClientConfig(AppConfig):
	"""
	Configuration class for the 'okta_client' Django application.
	"""

	default_auto_field = 'django.db.models.BigAutoField'
	name = 'okta_client'
