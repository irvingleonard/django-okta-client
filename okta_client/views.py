#python
"""

"""

from logging import getLogger

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from saml2 import BINDING_HTTP_POST
from saml2.client import Saml2Client

from .mixins import SPConfig

LOGGER = getLogger(__name__)

@csrf_exempt
def acs(request):
	
	next_url = request.session.get('next_url', SPConfig.next_url(request))
	saml_client = Saml2Client(config=SPConfig(request))
	
	response = request.POST.get('SAMLResponse', None)
	if response:
		LOGGER.debug('ACS received SAML response: %s', response)
	else:
		LOGGER.error('No POST request to ACS')
		return HttpResponse(status=407)

	authn_response = saml_client.parse_authn_request_response(response, BINDING_HTTP_POST)
	if authn_response is None:
		LOGGER.error('Unable to parse SAML response: %s', response)
		return HttpResponse(status=400)
	else:
		LOGGER.debug('Parsed SAML response: %s', authn_response)
	
	login_id = authn_response.get_subject().text
	
	user_identity = authn_response.get_identity()
	if user_identity is None:
		LOGGER.error('Malformed SAML response (get_identity failed): %s', authn_response)
		return HttpResponse(status=401)
	else:
		LOGGER.debug('Identity correctly extracted: %s', user_identity)

	saml_values = {key : value[0] if isinstance(value, list) and (len(value) == 1) else value for key, value in user_identity.items() if key not in ['login', 'request']}

	user = authenticate(request, login=login_id, **saml_values)
	if user is None:
		raise RuntimeError('Unable to authenticate. Did you add "okta_client.auth_backends.OktaBackend" to AUTHENTICATION_BACKENDS on your settings.py?')
	
	LOGGER.info('Logging in "%s"', user)
	login(request, user)
	
	LOGGER.debug('Redirecting after login to "%s"', next_url)
	return HttpResponseRedirect(next_url)

def login_view(request):
	
	LOGGER.debug('Logging in: %s', request)
	
	request.session['next_url'] = SPConfig.next_url(request)
	LOGGER.debug('Saved "next_url" into session: %s', request.session['next_url'])
	
	saml_client = Saml2Client(config=SPConfig(request))
	LOGGER.debug('Preparing authentication with: %s', saml_client)
	session_id, request_info = saml_client.prepare_for_authenticate()
	LOGGER.debug('Session id %s includes: %s', session_id, request_info)

	for key, value in request_info['headers']:
		if key == 'Location':
			LOGGER.debug('Found "Location" header. Redirecting to "%s"', value)
			return HttpResponseRedirect(value)
	
	LOGGER.error('The "Location" header was not found')
	return HttpResponseServerError()

def logout_view(request):
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
