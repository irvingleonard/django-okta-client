from django.conf import settings
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

import logging

import saml2
import saml2.client 
import saml2.config

from . import apps
from . import models

LOGGER = logging.getLogger(__name__)


class SPConfig:
	
	class OktaConfig(dict):
		
		def __init__(self, request, django_settings = settings):
			
			try:
				okta_settings = django_settings.OKTA_CLIENT
			except AttributeError:
				raise ValueError('Missing OKTA_CLIENT section in Django settings')
				
			super().__init__()
			
			local_domain_url = okta_settings.get('ASSERTION_DOMAIN_URL', '{}://{}'.format(request.scheme, request.get_host()))	
			acs_url = ''.join((local_domain_url, reverse('{}:acs'.format(apps.OktaClientConfig.name))))
			
			if 'METADATA_LOCAL_FILE_PATH' in okta_settings:
				self['metadata'] = {'local' : okta_settings['METADATA_LOCAL_FILE_PATH']}
			else:
				self['metadata'] = {'remote' : [{'url' : okta_settings['METADATA_AUTO_CONF_URL']}]}
				
			self['entityid'] = okta_settings.get('ENTITY_ID', acs_url)
			self['service'] = {
				'sp': {
					'endpoints': {
						'assertion_consumer_service': [
							(acs_url, saml2.BINDING_HTTP_REDIRECT),
							(acs_url, saml2.BINDING_HTTP_POST)
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
	
	def __new__(cls, request, django_config = settings):
		
		sp_config = saml2.config.SPConfig()
		sp_config.load(cls.OktaConfig(request, django_config))
		sp_config.allow_unknown_attributes = True
		return sp_config
	
	@classmethod
	def next_url(cls, request, django_config = settings):
		config = cls.OktaConfig(request, django_config)
		return request.GET.get('next', config.get('DEFAULT_NEXT_URL', '/'))


@csrf_exempt
def acs(request):
	
	next_url = request.session.get('next_url', SPConfig.next_url(request))
	saml_client = saml2.client.Saml2Client(config = SPConfig(request))
	
	response = request.POST.get('SAMLResponse', None)
	if response:
		LOGGER.debug('ACS received SAML response: %s', response)
	else:
		LOGGER.error('No POST request to ACS')
		return HttpResponse(status = 407)

	authn_response = saml_client.parse_authn_request_response(response, saml2.entity.BINDING_HTTP_POST)
	if authn_response is None:
		LOGGER.error('Unable to parse SAML response: %s', response)
		return HttpResponse(status = 400)
	else:
		LOGGER.debug('Parsed SAML response: %s', authn_response)
	
	login_id = authn_response.get_subject().text
	
	if False:
		#Implement API calls and pull user from Okta
		pass
	else:
		user_identity = authn_response.get_identity()
		if user_identity is None:
			LOGGER.error('Malformed SAML response (get_identity failed): %s', authn_response)
			return HttpResponse(status = 401)
		else:
			LOGGER.debug('Identity correctly extracted: %s', user_identity)
	
		defaults = {key : value[0] if isinstance(value, list) and (len(value) == 1) else value for key, value in user_identity.items() if key not in ['login']}
		defaults['is_active'] = True
		LOGGER.debug('Updating or creating user "%s" with: %s', login_id, defaults)
		target_user, created_flag = get_user_model().objects.update_or_create(defaults = defaults, login = login_id)
	
	LOGGER.info('Logging in "%s"', target_user)
	login(request, target_user)
	
	LOGGER.debug('Redirecting after login to "%s"', next_url)
	return HttpResponseRedirect(next_url)

def login_(request):
	
	LOGGER.debug('Logging in: %s', request)
	
	request.session['next_url'] = SPConfig.next_url(request)
	LOGGER.debug('Saved "next_url" into session: %s', request.session['next_url'])
	
	saml_client = saml2.client.Saml2Client(config = SPConfig(request))
	LOGGER.debug('Preparing authentication with: %s', saml_client)
	session_id, request_info = saml_client.prepare_for_authenticate()
	LOGGER.debug('Session id %s includes: %s', session_id, request_info)

	for key, value in request_info['headers']:
		if key == 'Location':
			LOGGER.debug('Found "Location" header. Redirecting to "%s"', value)
			return HttpResponseRedirect(value)
	
	LOGGER.error('The "Location" header was not found')
	return HttpResponseServerError()


def logout_(request):
	if request.user.is_authenticated:
		LOGGER.info('Logging out user: %s', request.user)
		logout(request)
	else:
		LOGGER.debug('No authenticated user. Ignoring logout request')
		
	next_url = request.session.get('next_url', SPConfig.next_url(request))
	LOGGER.debug('Redirecting after logout: %s', next_url)
	return HttpResponseRedirect(next_url)

@login_required
def index(request):
	return render(request, 'okta-client/index.html')

