#python
"""
Okta Client Django settings.
"""

from base64 import b64decode
from urllib.parse import urlsplit, urlunsplit
from warnings import warn

from devautotools import django_settings_env_capture, setting_is_true

DEFAULT_LOCAL_PATH = 'okta_client'

EXPECTED_VALUES_FROM_ENV = {
	'OKTA_CLIENT_AUTH_SETTINGS_FROM_ENV': {
		'OKTA_CLIENT_PRIVATE_KEY',
		'OKTA_CLIENT_PRIVATE_KEY_BASE64',
		'OKTA_CLIENT_TOKEN',
	},
	'OKTA_CLIENT_OAUTH_SETTINGS_FROM_ENV': {
		'OKTA_CLIENT_ID',
		'OKTA_CLIENT_SCOPES',
	},
	'OKTA_CLIENT_SETTINGS_FROM_ENV' : {
		'OKTA_CLIENT_LOCAL_PATH',
		'OKTA_CLIENT_ORG_URL',
		'OKTA_DJANGO_STAFF_USER_GROUPS',
		'OKTA_DJANGO_SUPER_USER_GROUPS',
		'OKTA_SAML_ASSERTION_DOMAIN_URL',
		'OKTA_SAML_METADATA_AUTO_CONF_URL',
	},
}

def common_settings(settings_globals, parent_callables=None):
	"""Common values for Django
	Applies common Okta client settings to a Django settings dictionary.
	It's usually added as:

	global_state = globals()
	global_state |= common_settings(globals())

	:param settings_globals: the caller's "globals"
	:param parent_callables: an optional list of parent "common_settings" callables
	:type parent_callables: [callable]|None
	:return: new content for "globals"
	"""

	django_settings = settings_globals.copy()

	if 'EXPECTED_VALUES_FROM_ENV' not in django_settings:
		django_settings['EXPECTED_VALUES_FROM_ENV'] = {}
	django_settings['EXPECTED_VALUES_FROM_ENV'] |= EXPECTED_VALUES_FROM_ENV

	if parent_callables is None:
		if 'ENVIRONMENTAL_SETTINGS' not in django_settings:
			django_settings['ENVIRONMENTAL_SETTINGS'] = {}
		django_settings['ENVIRONMENTAL_SETTINGS'] |= django_settings_env_capture(**EXPECTED_VALUES_FROM_ENV)
		django_settings['ENVIRONMENTAL_SETTINGS_KEYS'] = frozenset(django_settings['ENVIRONMENTAL_SETTINGS'].keys())
	elif parent_callables:
		parent_common_settings = parent_callables.pop(0)
		django_settings = parent_common_settings(django_settings, parent_callables=parent_callables)
	else:
		if 'ENVIRONMENTAL_SETTINGS' not in django_settings:
			django_settings['ENVIRONMENTAL_SETTINGS'] = {}
		django_settings['ENVIRONMENTAL_SETTINGS'] |= django_settings_env_capture(**django_settings['EXPECTED_VALUES_FROM_ENV'])
		django_settings['ENVIRONMENTAL_SETTINGS_KEYS'] = frozenset(django_settings['ENVIRONMENTAL_SETTINGS'].keys())

	if 'okta_client' not in django_settings['INSTALLED_APPS']:
		django_settings['INSTALLED_APPS'].append('okta_client')

	if 'AUTH_USER_MODEL' not in django_settings:
		django_settings['AUTH_USER_MODEL'] = 'okta_client.OktaUser'

	okta_client = {}
	if 'OKTA_SAML_METADATA_AUTO_CONF_URL' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
		okta_client |= {
			'METADATA_AUTO_CONF_URL': django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_SAML_METADATA_AUTO_CONF_URL'],
			'ORG_URL': urlunsplit(urlsplit(django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_SAML_METADATA_AUTO_CONF_URL'])[:2] + ('', '', '')),
		}
		if 'OKTA_SAML_ASSERTION_DOMAIN_URL' in django_settings['ENVIRONMENTAL_SETTINGS']:
			okta_client['ASSERTION_DOMAIN_URL'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_SAML_ASSERTION_DOMAIN_URL']
	elif 'OKTA_CLIENT_ORG_URL' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
		okta_client['ORG_URL'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_ORG_URL']

	if EXPECTED_VALUES_FROM_ENV['OKTA_CLIENT_AUTH_SETTINGS_FROM_ENV'].intersection(django_settings['ENVIRONMENTAL_SETTINGS_KEYS']):
		if 'OKTA_CLIENT_TOKEN' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['API_TOKEN'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_TOKEN']
		if EXPECTED_VALUES_FROM_ENV['OKTA_CLIENT_OAUTH_SETTINGS_FROM_ENV'].issubset(django_settings['ENVIRONMENTAL_SETTINGS_KEYS']):
			okta_client['API_CLIENT_ID'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_ID']
			okta_client['API_SCOPES'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_SCOPES']
			if 'OKTA_CLIENT_PRIVATE_KEY' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
				okta_client['API_PRIVATE_KEY'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_PRIVATE_KEY']
			else:
				okta_client['API_PRIVATE_KEY'] = b64decode(django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_PRIVATE_KEY_BASE64'])
		else:
			warn('Not enough configuration provided for Okta OAuth', RuntimeWarning)

		if 'OKTA_DJANGO_SUPER_USER_GROUPS' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['SUPER_USER_GROUPS'] = [group.strip() for group in django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_DJANGO_SUPER_USER_GROUPS'].split(',')]
		if 'OKTA_DJANGO_STAFF_USER_GROUPS' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['STAFF_USER_GROUPS'] = [group.strip() for group in django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_DJANGO_STAFF_USER_GROUPS'].split(',')]

	if okta_client:
		django_settings['OKTA_CLIENT'] = okta_client

		if 'AUTHENTICATION_BACKENDS' not in django_settings:
			django_settings['AUTHENTICATION_BACKENDS'] = ['okta_client.auth_backends.OktaBackend', 'django.contrib.auth.backends.ModelBackend']
		elif 'okta_client.auth_backends.OktaBackend' not in django_settings['AUTHENTICATION_BACKENDS']:
			django_settings['AUTHENTICATION_BACKENDS'] = ['okta_client.auth_backends.OktaBackend'] + django_settings['AUTHENTICATION_BACKENDS']

	django_settings['OKTA_CLIENT_LOCAL_PATH'] = django_settings['ENVIRONMENTAL_SETTINGS'].get('OKTA_CLIENT_LOCAL_PATH', DEFAULT_LOCAL_PATH).strip('/')

	if 'REST_FRAMEWORK' not in django_settings:
		django_settings['REST_FRAMEWORK'] = {
			'DEFAULT_AUTHENTICATION_CLASSES': ['okta_client.auth_backends.DjangoRESTBearerTokenAuthentication', 'rest_framework.authentication.SessionAuthentication'],
		}
		if 'rest_framework' not in django_settings['INSTALLED_APPS']:
			django_settings['INSTALLED_APPS'].append('rest_framework')
		if 'rest_framework.authtoken' not in django_settings['INSTALLED_APPS']:
			django_settings['INSTALLED_APPS'].append('rest_framework.authtoken')

	return django_settings
