#python
"""
Django application configuration for the Okta client.
"""

from django.apps import AppConfig


class OktaClientConfig(AppConfig):
    """
    Configuration class for the 'okta_client' Django application.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'okta_client'
