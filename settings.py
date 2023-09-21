#!python
'''Configuration module for standalone django-okta-client
Configuration parameters for a test deployment of django-okta-client.
'''

import os
import atexit
import logging
import os
import pathlib
import tempfile
import warnings

from .settings import *

DEFAULT_LOG_LEVEL = 'INFO'
SITE_DIR = pathlib.Path(__file__).parent

REQUIRED_SETTINGS_FROM_ENV = frozenset()

MAIN_DATABASE_SETTINGS_FROM_ENV = {
	'DJANGO_DATABASE_BACKEND',
	'DJANGO_DATABASE_DB_NAME',
	'DJANGO_DATABASE_HOST',
	'DJANGO_DATABASE_PASSWORD',
	'DJANGO_DATABASE_PORT',
	'DJANGO_DATABASE_USER_NAME',
}

SSL_DATABASE_SETTINGS_FROM_ENV = {
	'DJANGO_DATABASE_SSL_CA',
	'DJANGO_DATABASE_SSL_CERTIFICATE',
	'DJANGO_DATABASE_SSL_KEY',
}

OPTIONAL_EXTRA_SETTINGS_FROM_ENV = {
	'DJANGO_DEBUG',
	'DJANGO_LOG_LEVEL',
	'OKTA_API_TOKEN',
	'OKTA_DJANGO_ADMIN_GROUPS',
	'OKTA_SAML_ASSERTION_DOMAIN_URL',
	'OKTA_SAML_METADATA_AUTO_CONF_URL',
}

ENVIRONMENTAL_SETTINGS = {}
missing_settings_from_env = []

for required_setting in REQUIRED_SETTINGS_FROM_ENV:
	required_setting_value = os.getenv(required_setting, '')
	if required_setting_value:
		ENVIRONMENTAL_SETTINGS[required_setting] = required_setting_value
	else:
		missing_settings_from_env.append(required_setting)

if missing_settings_from_env:
	raise RuntimeError('Missing required settings from env: {}'.format(missing_settings_from_env))

for optional_setting in MAIN_DATABASE_SETTINGS_FROM_ENV | SSL_DATABASE_SETTINGS_FROM_ENV | OPTIONAL_EXTRA_SETTINGS_FROM_ENV:
	optional_setting_value = os.getenv(optional_setting, '')
	if optional_setting_value:
		ENVIRONMENTAL_SETTINGS[optional_setting] = optional_setting_value
	else:
		missing_settings_from_env.append(optional_setting)

if missing_settings_from_env:
	warnings.warn('Missing some optional settings: {}'.format(missing_settings_from_env), RuntimeWarning)

DEBUG = ENVIRONMENTAL_SETTINGS.get('DJANGO_DEBUG', 'false').lower() in ['true', 'yes', 'on']

if DEBUG:
	LOG_LEVEL = 'DEBUG'
else:
	LOG_LEVEL = ENVIRONMENTAL_SETTINGS.get('DJANGO_LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
	if LOG_LEVEL not in logging.getLevelNamesMapping():
		warnings.warn('Invalid log level provided: "{}". Using the default one instead: {}'.format(LOG_LEVEL, DEFAULT_LOG_LEVEL), RuntimeWarning)
		LOG_LEVEL = DEFAULT_LOG_LEVEL

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [
	'okta_client',
]

AUTH_USER_MODEL = 'okta_client.OktaUser'
AUTHENTICATION_BACKENDS = ['okta_client.auth_backends.OktaBackend', 'django.contrib.auth.backends.ModelBackend']

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
			'level': LOG_LEVEL,
			'propagate': True,
		},
	},
}

if MAIN_DATABASE_SETTINGS_FROM_ENV.issubset(frozenset(ENVIRONMENTAL_SETTINGS.keys())):

	database_details = {
		'CONN__HEALTH_CHECKS'	: True,
		'CONN_MAX_AGE'			: None,
		'ENGINE'				: 'django.db.backends.{}'.format(ENVIRONMENTAL_SETTINGS['DJANGO_DATABASE_BACKEND']),
		'HOST'					: DJANGO_DATABASE_BACKEND['DJANGO_DATABASE_HOST'],
		'NAME'					: DJANGO_DATABASE_BACKEND['DJANGO_DATABASE_DB_NAME'],
		'PASSWORD'				: DJANGO_DATABASE_BACKEND['DJANGO_DATABASE_PASSWORD'],
		'PORT'					: DJANGO_DATABASE_BACKEND['DJANGO_DATABASE_PORT'],
		'USER'					: DJANGO_DATABASE_BACKEND['DJANGO_DATABASE_USER_NAME'],
	}

	if SSL_DATABASE_SETTINGS_FROM_ENV.issubset(frozenset(ENVIRONMENTAL_SETTINGS.keys())):

		db_ca_desc, db_ca_path = tempfile.mkstemp(text = True)
		atexit.register(os.remove, db_ca_path)
		with open(db_ca_desc, 'wt') as db_ca_obj:
			db_ca_obj.write(ENVIRONMENTAL_SETTINGS['DJANGO_DATABASE_SSL_CA'])

		db_cert_desc, db_cert_path = tempfile.mkstemp(text = True)
		atexit.register(os.remove, db_cert_path)
		with open(db_cert_desc, 'wt') as db_cert_obj:
			db_cert_obj.write(ENVIRONMENTAL_SETTINGS['DJANGO_DATABASE_SSL_CERTIFICATE'])

		db_key_desc, db_key_path = tempfile.mkstemp(text = True)
		atexit.register(os.remove, db_key_path)
		with open(db_key_desc, 'wt') as db_key_obj:
			db_key_obj.write(ENVIRONMENTAL_SETTINGS['DJANGO_DATABASE_SSL_KEY'])

	else:
		warnings.warn('Missing database SSL settings, connection will not be encrypted: {}'.format(SSL_DATABASE_SETTINGS_FROM_ENV - frozenset(ENVIRONMENTAL_SETTINGS.keys())))

	DATABASES = {'default' : database_details}

else:
	warnings.warn('Not enough info to connect to an external database; using the builtin SQLite')

if 'OKTA_SAML_METADATA_AUTO_CONF_URL' in ENVIRONMENTAL_SETTINGS:
	OKTA_CLIENT = {'METADATA_AUTO_CONF_URL' : ENVIRONMENTAL_SETTINGS['OKTA_SAML_METADATA_AUTO_CONF_URL']}
	if 'OKTA_SAML_ASSERTION_DOMAIN_URL' in ENVIRONMENTAL_SETTINGS:
		OKTA_CLIENT['ASSERTION_DOMAIN_URL'] = ENVIRONMENTAL_SETTINGS['OKTA_SAML_ASSERTION_DOMAIN_URL']
	if 'OKTA_API_TOKEN' in ENVIRONMENTAL_SETTINGS:
		OKTA_CLIENT['API_TOKEN'] = ENVIRONMENTAL_SETTINGS['OKTA_API_TOKEN']
	if 'OKTA_DJANGO_ADMIN_GROUPS' in ENVIRONMENTAL_SETTINGS:
		OKTA_CLIENT['ADMIN_GROUPS'] = [group.strip() for group in ENVIRONMENTAL_SETTINGS['OKTA_DJANGO_ADMIN_GROUPS'].split(',')]
else:
	TEMPLATES[0]['DIRS'].append((SITE_DIR / 'templates').resolve(strict = True))
