#python
"""
Okta authentication backend for Django.
"""

from logging import getLogger

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend, RemoteUserBackend
from django.utils.timezone import now

from rest_framework.authentication import TokenAuthentication as DjangoRESTTokenAuthentication

from .api_client import OktaAPIClient

LOGGER = getLogger(__name__)
UserModel = get_user_model()


class OktaSAMLBackend(RemoteUserBackend):
	"""Okta auth backend
	Include Okta related specifics to the authentication process.
	"""
	
	create_unknown_user = True
	
	_api_client = OktaAPIClient()
	
	def authenticate(self, request, remote_user):
		"""
		
		"""
		
		user = super().authenticate(request, remote_user)
		
		if user is None:
			okta_user = self._api_client.get_user(remote_user)
			if okta_user is not None:
				return None
			user = UserModel.objects.create_from_okta_user(okta_user)
		else:
			if (user.last_refresh_timestamp is None) or (now() > (user.last_refresh_timestamp + self._api_client.get_refresh_delta())):
				okta_user = self._api_client.get_user(remote_user)
				if okta_user is not None:
					user.update_from_okta_user(okta_user)
					user.save()
		
		return user
		
		
	def user_can_authenticate(self):
		"""Returns whether the user is allowed to authenticate
		This backend should be used with SAML, which is a federated authentication scheme, so there shouldn't be a local permission check for authentication.
		
		:return: always True
		:rtype: bool
		"""
		
		return True
	
	def authenticate_old(self, request=None, username=None, login=None, **user_details):
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