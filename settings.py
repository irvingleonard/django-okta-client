#!python
'''Configuration module for standalone django-okta-client
Configuration parameters for a test deployment of django-okta-client.
'''

import os
import pathlib

from .settings import *

SITE_DIR = pathlib.Path(__file__).parent
PROJECT_DIR = SITE_DIR.parent

DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() in ['true', 'yes', 'on']

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [
	'okta_client',
]

AUTH_USER_MODEL = 'okta_client.OktaUser'

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'handlers': {
		'console': {
			'level': 'DEBUG',
			'class': 'logging.StreamHandler',
		},
	},
	'loggers': {
		'': {
			'handlers': ['console'],
			'level': 'DEBUG' if DEBUG else (os.getenv('DJANGO_LOG_LEVEL', 'info').upper() if os.getenv('DJANGO_LOG_LEVEL', 'info').upper() in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'] else 'INFO'),
			'propagate': True,
		},
	},
}

okta_metadata = os.getenv('OKTA_METADATA', False)
if okta_metadata:
	OKTA_CLIENT = {
		'METADATA_AUTO_CONF_URL'	: okta_metadata,
	}
