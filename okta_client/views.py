#python
"""

"""

from json import JSONDecodeError
from logging import getLogger

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views import View

from rest_framework.permissions import IsAuthenticated as RESTIsAuthenticated
from rest_framework.views import APIView

from .exceptions import SAMLAssertionError
from .mixins import LoginLogoutMixin, OktaEventHookMixin

LOGGER = getLogger(__name__)


class LoginView(LoginLogoutMixin, View):
	"""

	"""

	def get(self, request):
		"""

		"""

		try:
			next_url = self.login_user(request)
		except RuntimeError:
			return HttpResponseBadRequest()
		else:
			return HttpResponseRedirect(next_url)

	def post(self, request):
		"""

		"""

		try:
			next_url = self.saml_assertion(request)
		except SAMLAssertionError:
			return HttpResponseBadRequest()
		else:
			return HttpResponseRedirect(next_url)


class LogoutView(LoginLogoutMixin, LoginRequiredMixin, View):
	"""

	"""

	def get(self, request):
		"""

		"""

		next_url = self.logout_user(request)
		return HttpResponseRedirect(next_url)

	def post(self, request):
		"""

		"""

		next_url = self.logout_user(request)
		return HttpResponseRedirect(next_url)


class OktaEventHooks(OktaEventHookMixin, APIView):
	"""

	"""

	permission_classes = [RESTIsAuthenticated]

	def get(self, request):
		"""HTTP GET
		Only used to confirm that it follows Okta's convention.
		"""

		return JsonResponse(self.authenticate_endpoint(request))

	def post(self, request):
		"""HTTP GET
		Regular Event Hook handling.
		"""

		try:
			self.handle_event(request)
		except (JSONDecodeError, UnicodeDecodeError):
			return HttpResponseBadRequest()
		else:
			return HttpResponse(status=204)


######## Demo View ########

class IndexView(LoginRequiredMixin, View):
	"""

	"""

	def get(self, request):
		"""

		"""

		return render(request, 'okta-client/index.html')