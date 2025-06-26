#python
"""

"""

from json import loads as json_loads
from logging import getLogger
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse

from asgiref.sync import async_to_sync
from okta.client import Client as OktaClient
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.client import Saml2Client
from saml2.config import SPConfig as SPConfig_

from .exceptions import SAMLAssertionError
from .signals import okta_event_hook

LOGGER = getLogger(__name__)


class LoginLogoutMixin:
	"""

	"""

	def login_user(self, request):

		LOGGER.debug('Logging in: %s', request)

		request.session['next_url'] = SPConfig.next_url(request)
		LOGGER.debug('Saved "next_url" into session: %s', request.session['next_url'])

		saml_client = Saml2Client(config=SPConfig(request))
		LOGGER.debug('Preparing authentication with: %s', saml_client)
		session_id, request_info = saml_client.prepare_for_authenticate()
		LOGGER.debug('Session id %s includes: %s', session_id, request_info)

		for key, value in request_info['headers']:
			if key == 'Location':
				LOGGER.debug('Found "Location" header: %s', value)
				return value

		raise RuntimeError('The "Location" header was not found')

	def logout_user(self, request):

		if request.user.is_authenticated:
			LOGGER.info('Logging out user: %s', request.user)
			logout(request)
		else:
			raise RuntimeError('User is not authenticated')

		next_url = request.session.get('next_url', SPConfig.next_url(request))
		LOGGER.debug('Redirecting after logout: %s', next_url)
		return next_url

	def saml_assertion(self, request):
		"""

		"""

		next_url = request.session.get('next_url', SPConfig.next_url(request))
		saml_client = Saml2Client(config=SPConfig(request))

		response = request.POST.get('SAMLResponse', None)
		if response:
			LOGGER.debug('The ACS received SAML response: %s', response)
		else:
			raise SAMLAssertionError('No POST request to the ACS')

		authn_response = saml_client.parse_authn_request_response(response, BINDING_HTTP_POST)
		if authn_response is None:
			raise SAMLAssertionError(f'Unable to parse SAML response: {response}')
		else:
			LOGGER.debug('Parsed SAML response: %s', authn_response)

		login_id = authn_response.get_subject().text

		user_identity = authn_response.get_identity()
		if user_identity is None:
			raise SAMLAssertionError(f'Malformed SAML response (get_identity failed): {authn_response}')
		else:
			LOGGER.debug('Identity correctly extracted: %s', user_identity)

		saml_values = {key: value[0] if isinstance(value, list) and (len(value) == 1) else value for key, value in user_identity.items() if key not in ['login', 'request']}

		user = authenticate(request, login=login_id, **saml_values)
		if user is None:
			raise RuntimeError('Unable to authenticate. Did you add "okta_client.auth_backends.OktaBackend" to AUTHENTICATION_BACKENDS on your settings.py?')

		LOGGER.info('Logging in "%s"', user)
		login(request, user)

		LOGGER.debug('Redirecting after login to "%s"', next_url)
		return next_url


class OktaAPIClient:
	"""

	"""

	def __getattr__(self, name):
		"""Lazy instantiation
		Some computation that is left pending until is needed
		"""

		if name == 'okta_api_client':
			client_config = {'orgUrl': settings.OKTA_CLIENT['ORG_URL']} | self.okta_api_credentials
			if 'SSL_CONTEXT' in settings.OKTA_CLIENT:
				client_config['sslContext'] = settings.OKTA_CLIENT['SSL_CONTEXT']
			value = OktaClient(client_config)
		elif name == 'okta_api_credentials':
			if ('API_CLIENT_ID' in settings.OKTA_CLIENT) and ('API_PRIVATE_KEY' in settings.OKTA_CLIENT):
				value = {
					'authorizationMode'	: 'PrivateKey',
					'clientId'			: settings.OKTA_CLIENT['API_CLIENT_ID'],
					'privateKey'		: settings.OKTA_CLIENT['API_PRIVATE_KEY'],
					'scopes'			: settings.OKTA_CLIENT.get('API_SCOPES', None),
				}
			elif 'API_TOKEN' in settings.OKTA_CLIENT:
				value = {'token': settings.OKTA_CLIENT['API_TOKEN']}
			else:
				raise RuntimeError('Missing auth settings for Okta client')
		elif name == 'okta_orgUrl':
			if 'METADATA_AUTO_CONF_URL' in settings.OKTA_CLIENT:
				value = urlunsplit(urlsplit(settings.OKTA_CLIENT['METADATA_AUTO_CONF_URL'])[:2] + ('', '', ''))
			else:
				raise RuntimeError('Missing orgUrl for Okta client')
		else:
			return getattr(super(), name)
		self.__setattr__(name, value)
		return value

	def okta_api_request(self, method_name, *args, **kwargs):
		"""

		"""

		result = async_to_sync(getattr(self.okta_api_client, method_name), )(*args, **kwargs)

		if len(result) == 3:
			result, response, err = result
		elif len(result) == 2:
			response, err = result
		else:
			raise RuntimeError('Unknown result: {}'.format(result))

		if err is not None:
			raise RuntimeError(err)

		while response.has_next():
			partial, err = async_to_sync(response.next)()
			if err is not None:
				raise RuntimeError(err)
			result.extend(partial)

		return result


class OktaEventHookMixin:
	"""

	"""

	def authenticate_endpoint(self, request):
		"""

		"""

		return {'verification': request.headers.get('x-okta-verification-challenge', '')}

	def handle_event(self, request):
		"""

		"""

		event_hook = json_loads(request.body)
		results = okta_event_hook.send_robust(self.__class__, event_hook=event_hook)
		for handler, result in results:
			handler = '.'.join((handler.__module__, handler.__name__))
			if isinstance(result, Exception):
				LOGGER.error('The "%s" experienced an error while handling an Okta event hook: %s', handler, result)
			elif result:
				LOGGER.warning('The "%s" returned a value while handling an Okta event hook. Okta does not expect an answer, discarding: %s', handler, result)
			else:
				LOGGER.debug('The "%s" completed successfully the handling of an Okta event hook.', handler)


class SPConfig:
	"""

	"""

	class OktaConfig(dict):
		"""

		"""

		def __init__(self, request, django_settings=settings):
			"""

			"""

			try:
				okta_settings = django_settings.OKTA_CLIENT
			except AttributeError:
				raise ValueError('Missing OKTA_CLIENT section in Django settings')

			super().__init__()

			local_domain_url = okta_settings.get('ASSERTION_DOMAIN_URL', '{}://{}'.format(request.scheme, request.get_host()))
			acs_url = ''.join((local_domain_url, reverse('okta-client:acs')))

			if 'METADATA_LOCAL_FILE_PATH' in okta_settings:
				self['metadata'] = {'local': okta_settings['METADATA_LOCAL_FILE_PATH']}
			else:
				self['metadata'] = {'remote': [{'url': okta_settings['METADATA_AUTO_CONF_URL']}]}

			self['entityid'] = okta_settings.get('ENTITY_ID', acs_url)
			self['service'] = {
				'sp': {
					'endpoints': {
						'assertion_consumer_service': [
							(acs_url, BINDING_HTTP_REDIRECT),
							(acs_url, BINDING_HTTP_POST)
						],
					},
					'allow_unsolicited': True,
					'authn_requests_signed': False,
					'logout_requests_signed': True,
					'want_assertions_signed': True,
					'want_response_signed': False,
				},
			}

			if 'NAME_ID_FORMAT' in okta_settings:
				self['service']['sp']['name_id_format'] = okta_settings['NAME_ID_FORMAT']

	def __new__(cls, request, django_config=settings):
		"""

		"""

		sp_config = SPConfig_()
		sp_config.load(cls.OktaConfig(request, django_config))
		sp_config.allow_unknown_attributes = True
		return sp_config

	@classmethod
	def next_url(cls, request, django_config=settings):
		"""

		"""

		config = cls.OktaConfig(request, django_config)
		return request.GET.get('next', config.get('DEFAULT_NEXT_URL', '/'))