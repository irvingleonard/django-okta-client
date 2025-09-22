#python
"""
Okta Client Django settings.
"""

from logging import getLogger
from urllib.parse import urlsplit, urlunsplit

from normalized_django_settings import decode_setting, path_for_setting, setting_is_true

DEFAULT_LOCAL_PATH = 'okta-client'
LOGGER = getLogger(__name__)

EXPECTED_VALUES_FROM_ENV = {
	'OKTA_CLIENT_OAUTH_SETTINGS_FROM_ENV': {
		'OKTA_CLIENT_ID',
		'OKTA_CLIENT_SCOPES',
	},
	'OKTA_CLIENT_SETTINGS_FROM_ENV' : {
		'OKTA_CLIENT_LOCAL_PATH',
		'OKTA_CLIENT_ORG_URL',
		'OKTA_CLIENT_PRIVATE_KEY',
		'OKTA_CLIENT_TOKEN',
		'OKTA_CLIENT_USER_TTL',
		'OKTA_DJANGO_STAFF_USER_GROUPS',
		'OKTA_DJANGO_SUPER_USER_GROUPS',
		'OKTA_SAML_ASSERTION_DOMAIN_URL',
		'OKTA_SAML_METADATA_AUTO_CONF_URL',
	},
}

IMPLICIT_ENVIRONMENTAL_SETTINGS = {
  'OKTA_CLIENT_LOCAL_PATH': DEFAULT_LOCAL_PATH,
  'OKTA_CLIENT_USER_TTL': '300',
}

def normalized_settings(**django_settings):
	"""Common values for Django
	Applies common Okta client settings to a Django settings dictionary.

	:param django_settings: the current globals() in Django's site
	:type django_settings: Any
	:return: new content for "globals"
	"""

	if 'okta_client' not in django_settings['INSTALLED_APPS']:
		django_settings['INSTALLED_APPS'].append('okta_client')

	if 'AUTH_USER_MODEL' not in django_settings:
		django_settings['AUTH_USER_MODEL'] = 'okta_client.OktaUser'

	django_settings['OKTA_CLIENT_LOCAL_PATH'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_LOCAL_PATH'].strip('/')

	okta_client = {}
	if 'OKTA_SAML_METADATA_AUTO_CONF_URL' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
		okta_client['SAML'] = {
			'METADATA_AUTO_CONF_URL': django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_SAML_METADATA_AUTO_CONF_URL'],
		}
		okta_client['API'] = {
			'ORG_URL': urlunsplit(urlsplit(django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_SAML_METADATA_AUTO_CONF_URL'])[:2] + ('', '', '')),
		}
		if 'OKTA_SAML_ASSERTION_DOMAIN_URL' in django_settings['ENVIRONMENTAL_SETTINGS']:
			okta_client['SAML']['ASSERTION_DOMAIN_URL'] = django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_SAML_ASSERTION_DOMAIN_URL']
	elif 'OKTA_CLIENT_ORG_URL' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
		okta_client['API'] = {'ORG_URL': django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_ORG_URL']}

	if 'API' in okta_client:
		okta_api_client_key = decode_setting(django_settings, 'OKTA_CLIENT_PRIVATE_KEY')
		if (okta_api_client_key is not None) and not isinstance(okta_api_client_key, str):
			okta_api_client_key = okta_api_client_key.decode('utf-8')
		if (okta_api_client_key is not None) and (EXPECTED_VALUES_FROM_ENV['OKTA_CLIENT_OAUTH_SETTINGS_FROM_ENV'].issubset(django_settings['ENVIRONMENTAL_SETTINGS_KEYS'])):
			okta_client['API'] |= {
				'API_CLIENT_ID': django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_ID'],
				'API_SCOPES': django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_SCOPES'].split(','),
				'API_PRIVATE_KEY': okta_api_client_key
			}
		elif 'OKTA_CLIENT_TOKEN' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['API'] |= {'API_TOKEN': django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_TOKEN']}
		else:
			LOGGER.debug('Missing authentication settings to configure the Okta API client')
			okta_client.pop('API')
	else:
		LOGGER.debug('The Okta API client is not configured')

	if 'API' in okta_client:
		if 'OKTA_DJANGO_SUPER_USER_GROUPS' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['API']['SUPER_USER_GROUPS'] = [group.strip() for group in django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_DJANGO_SUPER_USER_GROUPS'].split(',')]
		if 'OKTA_DJANGO_STAFF_USER_GROUPS' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['API']['STAFF_USER_GROUPS'] = [group.strip() for group in django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_DJANGO_STAFF_USER_GROUPS'].split(',')]
		if 'OKTA_CLIENT_USER_TTL' in django_settings['ENVIRONMENTAL_SETTINGS_KEYS']:
			okta_client['API']['USER_TTL'] = int(django_settings['ENVIRONMENTAL_SETTINGS']['OKTA_CLIENT_USER_TTL'])

	if okta_client:
		django_settings['OKTA_CLIENT'] = okta_client

	if 'SAML' in okta_client:
		if 'AUTHENTICATION_BACKENDS' not in django_settings:
			django_settings['AUTHENTICATION_BACKENDS'] = ['okta_client.auth_backends.OktaSAMLBackend', 'django.contrib.auth.backends.ModelBackend']
		elif 'okta_client.auth_backends.OktaSAMLBackend' not in django_settings['AUTHENTICATION_BACKENDS']:
			django_settings['AUTHENTICATION_BACKENDS'] = ['okta_client.auth_backends.OktaSAMLBackend'] + django_settings['AUTHENTICATION_BACKENDS']

	if 'REST_FRAMEWORK' not in django_settings:
		django_settings['REST_FRAMEWORK'] = {
			'DEFAULT_AUTHENTICATION_CLASSES': ['okta_client.auth_backends.DjangoRESTBearerTokenAuthentication', 'rest_framework.authentication.SessionAuthentication'],
		}
		if 'rest_framework' not in django_settings['INSTALLED_APPS']:
			django_settings['INSTALLED_APPS'].append('rest_framework')
		if 'rest_framework.authtoken' not in django_settings['INSTALLED_APPS']:
			django_settings['INSTALLED_APPS'].append('rest_framework.authtoken')

	return django_settings
