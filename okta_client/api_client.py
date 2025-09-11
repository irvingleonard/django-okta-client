"""
Here are some utility pieces.
"""

from logging import getLogger

from django.conf import settings
from django.core.cache import cache

from asgiref.sync import async_to_sync
from okta.client import Client as OktaClient
from okta.exceptions.exceptions import OktaAPIException

ERROR_CODE_MAP = {
	'USER_NOT_FOUND' : 'E0000007',
}
LOGGER = getLogger(__name__)


class OktaAPIClient:
	"""
	Handles interactions with the Okta API, including lazy instantiation of the Okta client and making API requests.
	"""

	CACHE_PREFIX = 'okta_client_api_client'
	STATIC_CONFIG = {'raiseException': True}

	def __getattr__(self, name):
		"""Lazy instantiation
		It provides a mechanism for lazy instantiation of the Okta API client, its credentials, and the Okta organization URL.

		:param name: The name of the attribute being accessed.
		:type name: str
		:returns: the attribute value
		"""

		if name == 'okta_api_client':
			client_config = {'orgUrl': settings.OKTA_CLIENT['API']['ORG_URL']} | self.okta_api_credentials
			if 'SSL_CONTEXT' in settings.OKTA_CLIENT:
				client_config['sslContext'] = settings.OKTA_CLIENT['SSL_CONTEXT']
			value = OktaClient(client_config | self.STATIC_CONFIG)
		elif name == 'okta_api_credentials':
			if ('API_CLIENT_ID' in settings.OKTA_CLIENT['API']) and ('API_PRIVATE_KEY' in settings.OKTA_CLIENT['API']):
				value = {
					'authorizationMode'	: 'PrivateKey',
					'clientId'			: settings.OKTA_CLIENT['API']['API_CLIENT_ID'],
					'privateKey'		: settings.OKTA_CLIENT['API']['API_PRIVATE_KEY'],
					'scopes'			: settings.OKTA_CLIENT['API'].get('API_SCOPES', None),
				}
			elif 'API_TOKEN' in settings.OKTA_CLIENT:
				value = {'token': settings.OKTA_CLIENT['API']['API_TOKEN']}
			else:
				raise RuntimeError('Missing auth settings for Okta client')
		else:
			return getattr(super(), name)
		self.__setattr__(name, value)
		return value

	def __call__(self, method_name, *args, retrieve_all_pages=True, **kwargs):
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

		if retrieve_all_pages:
			while response.has_next():
				partial, err = async_to_sync(response.next)()
				if err is not None:
					raise RuntimeError(err)
				result.extend(partial)

		return result

	def get_user(self, *args, **kwargs):
		"""Get user
		Attempt to call the "get_user" endpoint and return the results.

		:param args: positional argument parameters, passed as is to the "get_user" call
		:type args: Any
		:param kwargs: keyword argument parameters, passed as is to the "get_user" call
		:type kwargs: Any
		:return: the matching user or None
		:rtype: OktaAPIUser|None
		"""

		try:
			return self('get_user', *args, **kwargs)
		except AttributeError:
			LOGGER.debug("Okta API Client is not available, couldn't retrieve remote user: %s | %s", args, kwargs)
		except OktaAPIException as error_:
			if error_.args[0]['errorCode'] != ERROR_CODE_MAP['USER_NOT_FOUND']:
				LOGGER.exception('Unknown error occurred when retrieving Okta user: %s | %s', args, kwargs)

		return None

	def list_users(self, **kwargs):
		"""List all users
		A subset of users can be returned that match a supported filter expression or search criteria. Different results are returned depending on specified queries in the request.

		It will swallow the exceptions and report via logging, for your convenience.
		"""

		try:
			return self('list_users', query_params=kwargs)
		except AttributeError:
			LOGGER.debug("Okta API Client is not available, couldn't retrieve remote user: %s", **kwargs)
		except OktaAPIException as error_:
			LOGGER.exception('Unknown error occurred when retrieving Okta user: %s', **kwargs)

		return []

	def ping_users_endpoint(self):
		"""Ping users endpoint
		Attempt a query to the users endpoint and report availability. Doesn't handle exceptions, it will let them bubble up.

		:return: True if the query succeeds.
		:rtype: bool
		"""

		result = len(self('list_users', retrieve_all_pages=False, query_params={'limit':'1'})) > 0