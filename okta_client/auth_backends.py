#python
"""
Okta authentication backend for Django.
"""

from logging import getLogger

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from rest_framework.authentication import TokenAuthentication as DjangoRESTTokenAuthentication

LOGGER = getLogger(__name__)
UserModel = get_user_model()


class OktaBackend(ModelBackend):
	"""Okta auth backend
	Include Okta related specifics to the authentication process.
	"""

	def authenticate(self, request=None, username=None, login=None, **user_details):
		"""Noop check
		Retrieve the user details using the Okta API, check for admin access, and update group membership (creating groups if needed)
		"""

		if login is None:
			return None

		try:
			return UserModel.objects.get_user(login)
		except ValueError:
			return None


class DjangoRESTBearerTokenAuthentication(DjangoRESTTokenAuthentication):
	"""Token authentication for REST
	Like the builtin rest_framework.authentication.TokenAuthentication method but using the "Bearer" word instead of the default "Token" (it simplifies the compatibility with Postman)
	"""

	keyword = 'Bearer'