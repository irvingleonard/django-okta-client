#python
"""
Mixins for Django Okta Client.
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
	Handles user login and logout processes, including SAML assertion parsing.
	"""

	def login_user(self, request):
		"""Login user
		Initiates the SAML authentication process by preparing an authentication request and returning the URL to which the user should be redirected for authentication.

		:param request: the Django request
		:type request: object
		:return: The "Location" header
		:rtype: str
		:raises: RuntimeError if there's no "Location" header in the request
		"""

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
		"""Logs out the current user.
		If the user is authenticated, they are logged out. Otherwise, a RuntimeError is raised. After logout, the user is redirected to the 'next_url' stored in the session or the default next URL.

		:param request: The Django request object.
		:type request: object
		:return: The URL to redirect to after logout.
		:rtype: str
		:raises RuntimeError: If the user is not authenticated.
		"""
		if request.user.is_authenticated:
			LOGGER.info('Logging out user: %s', request.user)
			logout(request)
		else:
			raise RuntimeError('User is not authenticated')

		next_url = request.session.get('next_url', SPConfig.next_url(request))
		LOGGER.debug('Redirecting after logout: %s', next_url)
		return next_url

	def saml_assertion(self, request):
		"""Handles the SAML assertion process.
		This method is responsible for parsing the SAML response received from the Identity Provider (IdP), authenticating the user based on the SAML assertion, and logging them into the Django application.

		:param request: The Django request object containing the SAML response.
		:type request: object
		:return: The URL to redirect to after successful authentication.
		:rtype: str
		:raises SAMLAssertionError: If there is no SAML response, the response cannot be parsed, or the user identity cannot be extracted.
		:raises RuntimeError: If authentication fails or the OktaBackend is not configured.
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
	Handles interactions with the Okta API, including lazy instantiation of the Okta client and making API requests.
	"""

	def __getattr__(self, name):
		"""Lazy instantiation
		It provides a mechanism for lazy instantiation of the Okta API client, its credentials, and the Okta organization URL.

		:param name: The name of the attribute being accessed.
		:type name: str
		:returns: the attribute value
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
		else:
			return getattr(super(), name)
		self.__setattr__(name, value)
		return value

	def okta_api_request(self, method_name, *args, **kwargs):
		"""Okta API request
		Makes a request to the Okta API using the configured Okta client.

		:param method_name: The name of the method to call on the Okta client (e.g., 'list_users').
		:type method_name: str
		:param args: Positional arguments to pass to the Okta client method.
		:param kwargs: Keyword arguments to pass to the Okta client method.
		:return: The result of the Okta API call.
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
	Handles Okta event hooks, including verification and processing of incoming events.
	"""

	def authenticate_endpoint(self, request):
		"""Authenticates the Okta event hook endpoint.
		This method is called when Okta attempts to verify the event hook endpoint. It extracts the 'x-okta-verification-challenge' header from the request and returns it as part of a dictionary. Okta expects this challenge to be returned to confirm the endpoint's authenticity.

		:param request: The Django request object containing the verification challenge.
		:type request: object
		:return: A dictionary containing the 'verification' challenge string.
		:rtype: dict
		"""

		return {'verification': request.headers.get('x-okta-verification-challenge', '')}

	def handle_event(self, request):
		"""Handles incoming Okta event hook notifications.
		This method parses the JSON payload from the request body, which represents an Okta event. It then dispatches this event to registered signal handlers via the `okta_event_hook` signal. It logs the outcome of each handler's execution, noting errors, unexpected return values, or successful completion. Okta does not expect a response body for event hooks, so any return values from handlers are logged as warnings and discarded.

		:param request: The Django request object containing the Okta event hook payload in its body.
		:type request: object
		:return: None
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
	Manages the Service Provider (SP) configuration for SAML authentication.
	"""

	class OktaConfig(dict):
		"""
		Represents the Okta configuration for the Service Provider (SP).
		"""

		def __init__(self, request, django_settings=settings):
			"""Initializes the OktaConfig with request and Django settings.
			This constructor sets up the SAML Service Provider (SP) configuration based on the provided Django settings and the current request. It determines the Assertion Consumer Service (ACS) URL, configures metadata (local or remote), and defines various SAML SP service parameters like endpoints, signing requirements, and name ID format.

			:param request: The Django request object.
			:type request: object
			:param django_settings: The Django settings object, defaults to `settings`.
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
		"""Creates a new SPConfig instance, loading the Okta configuration.
		This method acts as a factory for `SPConfig_` (from `saml2.config`), initializing it with the Okta-specific SAML configuration.

		:param request: The Django request object.
		:param django_config: The Django settings object, defaults to `settings`.
		:return: An initialized `saml2.config.SPConfig` object.
		"""

		sp_config = SPConfig_()
		sp_config.load(cls.OktaConfig(request, django_config))
		sp_config.allow_unknown_attributes = True
		return sp_config

	@classmethod
	def next_url(cls, request, django_config=settings):
		"""Determines the next URL for redirection after a successful login or logout.
		It first checks for a 'next' parameter in the request's GET query. If not found, it falls back to the 'DEFAULT_NEXT_URL' defined in the Okta client settings. If neither is specified, it defaults to the root URL ('/').

		:param request: The Django request object.
		:type request: object
		:param django_config: The Django settings object, defaults to `settings`.
		:type django_config: object
		:return: The URL to redirect to.
		:rtype: str
		"""

		config = cls.OktaConfig(request, django_config)
		return request.GET.get('next', config.get('DEFAULT_NEXT_URL', '/'))