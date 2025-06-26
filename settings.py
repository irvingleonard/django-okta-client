#!python
"""Configuration module for standalone django-okta-client
Configuration parameters for a test deployment of django-okta-client.
"""

import pathlib

from .settings import *

from devautotools import django_common_settings
from okta_client.settings import EXPECTED_VALUES_FROM_ENV, common_settings

SITE_DIR = pathlib.Path(__file__).parent

global_state = globals()
global_state |= django_common_settings(globals())

global_state |= common_settings(globals())

TEMPLATES[0]['DIRS'].append((SITE_DIR / 'templates').resolve(strict=True))
