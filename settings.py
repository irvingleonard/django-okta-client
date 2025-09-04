#!python
"""Configuration module for standalone django-okta-client
Configuration parameters for a test deployment of django-okta-client.
"""

from pathlib import Path

from devautotools import django_normalized_settings

from .settings import *

SITE_DIR = Path(__file__).parent

settings_module_names = (
    'devautotools',
    'okta_client.settings',
)
global_state = globals()
global_state |= django_normalized_settings(*settings_module_names, django_settings=globals())

TEMPLATES[0]['DIRS'].append((SITE_DIR / 'templates').resolve(strict=True))
