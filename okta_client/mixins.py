#python
"""

"""

from json import loads as json_loads
from logging import getLogger
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.urls import reverse

from asgiref.sync import async_to_sync
from okta.client import Client as OktaClient
from saml2 import BINDING_HTTP_POST, BINDING_HTTP_REDIRECT
from saml2.config import SPConfig as SPConfig_

LOGGER = getLogger(__name__)


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


class OktaAPIClient:
	"""

	"""

	def __getattr__(self, name):
		"""Lazy instantiation
		Some computation that is left pending until is needed
		"""

		if name == 'okta_api_client':
			client_config = {'orgUrl': self.okta_orgUrl} | self.okta_api_credentials
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
				raise RuntimeError('Missing API token for Okta client')
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

		result = async_to_sync(getattr(self.api_client, method_name), )(*args, **kwargs)

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
	"""Okta Event Hook endpoint
	Follow Okta's way to do Okta Event Hooks, for your convenience.

	Your class based view, the one that inherits this mixin, should implement an *okta_"type_of_event"* method for each event type that this view will handle where "type_of_event" will be the event type reported by okta with the dots replaced by underscores. Ex: okta_user_session_start

	There's also the option to implement a fallback "okta_event" method that will be used if no specific method exists for an event type.

	All these methods should expect 3 parameters:
	- request: is the Django request object provided to the view
	- event: is the already parsed event that should be processed in this iteration
	- event_targets: is the list of targets in the event as a dictionary keyed by type (an error will be raised if overlapping types). It could be "None" if no targets are present on the event object.

	Ref: https://developer.okta.com/docs/concepts/event-hooks/
	"""
	
	def _okta_event_dispatcher(self, request, request_json, event, event_targets):
		"""Default event dispatcher
		It looks for a properly named method and calls it with the regular parameters (same as this method's signature)
		"""
		
		method_name = 'okta_' + event['eventType'].replace('.', '_')
		if hasattr(self, method_name):
			getattr(self, method_name)(request, request_json, event, event_targets)
		elif hasattr(self, 'okta_event'):
			getattr(self, 'okta_event')(request, request_json, event, event_targets)
		else:
			LOGGER.warning('Okta event support not implemented: %s', event['eventType'])
			return HttpResponse(status=501)
	
	def get(self, request, *args, **kwargs):
		"""HTTP GET
		Only used to confirm that it follows Okta's convention.
		"""
		
		if args or kwargs:
			LOGGER.warning('OktaEventHookMixin.GET is ignoring: %s | %s', args, kwargs)
		return JsonResponse({'verification': request.headers.get('x-okta-verification-challenge', '')})
	
	def post(self, request, request_json=None):
		"""HTTP GET
		Regular Event Hook handling.
		"""
		
		if request_json is None:
			request_json = json_loads(request.body)
		results = []
		for event in request_json['data']['events']:
			if ('target' in event) and (event['target'] is not None):
				event_targets = {}
				for target in event['target']:
					if target['type'] in event_targets:
						raise RuntimeError('Okta event with overlapping targets: {}'.format(event['uuid']))
					event_targets[target['type']] = {key: value for key, value in target.items() if key not in ['type']}
			else:
				event_targets = None
			result = self._okta_event_dispatcher(request, request_json, event, event_targets)
			if result is not None:
				results.append(result)
		if len(results) > 1:
			raise RuntimeError('Too many results for a single Okta hook: {}'.format(results))
		elif results:
			return results[0]
		else:
			return HttpResponse(status=204)