#!python
"""Configuration module for standalone django-okta-client
Configuration parameters for a test deployment of django-okta-client.
"""

from pathlib import Path

from normalized_django_settings import normalize_settings

from .settings import *

SITE_DIR = Path(__file__).parent

settings_module_names = (
    'normalized_django_settings.settings',
    'okta_client.settings',
)
global_state = globals()
global_state |= normalize_settings(*settings_module_names, django_settings=globals())

TEMPLATES[0]['DIRS'].append((SITE_DIR / 'templates').resolve(strict=True))

from re import compile as re_compile
from django.views.debug import SafeExceptionReporterFilter
class UnsafeExceptionReporterFilter(SafeExceptionReporterFilter):
    hidden_settings = re_compile(r'/Z/A')

DEFAULT_EXCEPTION_REPORTER_FILTER = 'test_site.local_settings.UnsafeExceptionReporterFilter'
