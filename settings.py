#!python
"""Configuration module for standalone django-okta-client
Configuration parameters for a test deployment of django-okta-client.
"""

from pathlib import Path

from .settings import *

from devautotools import django_common_settings
from okta_client.settings import common_settings as okta_client_common_settings

SITE_DIR = Path(__file__).parent

global_state = globals()
global_state |= okta_client_common_settings(globals(), parent_callables=[django_common_settings])

TEMPLATES[0]['DIRS'].append((SITE_DIR / 'templates').resolve(strict=True))
