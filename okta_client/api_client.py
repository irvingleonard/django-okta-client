"""
Here are some utility pieces.
"""

from logging import getLogger

from django.conf import settings

from asgiref.sync import async_to_sync
from okta.client import Client as OktaClient

LOGGER = getLogger(__name__)

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

	def __call__(self, method_name, *args, **kwargs):
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
