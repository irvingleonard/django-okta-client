#python
"""
Django Okta Client Views
"""

from json import JSONDecodeError
from logging import getLogger

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views import View

from rest_framework.permissions import IsAuthenticated as RESTIsAuthenticated
from rest_framework.views import APIView

from .exceptions import SAMLAssertionError
from .mixins import LoginLogoutMixin, OktaEventHookMixin

LOGGER = getLogger(__name__)


class ACSView(LoginLogoutMixin, View):
	"""
	Handles the Assertion Consumer Service (ACS) for SAML responses from Okta.
	"""

	def post(self, request):
		"""POST verb
		Handles the POST request for the ACS endpoint, processing the SAML assertion.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		try:
			next_url = self.saml_assertion(request)
		except SAMLAssertionError:
			return HttpResponseBadRequest()
		else:
			return HttpResponseRedirect(next_url)


class LoginView(LoginLogoutMixin, View):
	"""
	Handles the login process for Okta.
	"""

	def get(self, request):
		"""GET verb
		Handles the GET request for the login endpoint.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		try:
			next_url = self.login_user(request)
		except RuntimeError:
			return HttpResponseBadRequest()
		else:
			return HttpResponseRedirect(next_url)


class LogoutView(LoginLogoutMixin, LoginRequiredMixin, View):
	"""
	Handles the logout process for Okta.
	"""

	def get(self, request):
		"""GET verb
		Handles the GET request for the logout endpoint.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		next_url = self.logout_user(request)
		return HttpResponseRedirect(next_url)

	def post(self, request):
		"""POST verb
		Handles the POST request for the logout endpoint.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		next_url = self.logout_user(request)
		return HttpResponseRedirect(next_url)


class OktaEventHooks(OktaEventHookMixin, APIView):
	"""
	Handles Okta event hooks.
	"""

	permission_classes = [RESTIsAuthenticated]

	def get(self, request):
		"""HTTP GET
		Only used to confirm that it follows Okta's convention.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		return JsonResponse(self.authenticate_endpoint(request))

	def post(self, request):
		"""HTTP GET
		Regular Event Hook handling.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		try:
			self.handle_events(request)
		except (JSONDecodeError, UnicodeDecodeError):
			return HttpResponseBadRequest()
		else:
			return HttpResponse(status=204)


######## Demo View ########

class IndexView(LoginRequiredMixin, View):
	"""
	A simple view to demonstrate a protected page after successful login.
	"""

	def get(self, request):
		"""GET verb
		Handles the GET request for the index page.

		:param request: the Django request
		:type request: object
		:returns object: the Django response
		"""

		return render(request, 'okta-client/index.html')