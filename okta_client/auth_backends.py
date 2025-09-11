#python
"""
Okta authentication backend for Django.
"""

from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from rest_framework.authentication import TokenAuthentication as DjangoRESTTokenAuthentication

from .api_client import OktaAPIClient

LOGGER = getLogger(__name__)
UserModel = get_user_model()


class OktaBackend(ModelBackend):
	"""Okta auth backend
	Include Okta related specifics to the authentication process.
	"""

	_api_client = OktaAPIClient()

	def authenticate(self, request, login, **user_details):
		"""Noop check
		Retrieve the user details using the Okta API, check for admin access, and update group membership (creating groups if needed)
		"""

		try:
			self._api_client.okta_api_client
		except Exception as err:
			okta_user = None
			LOGGER.warning('Unable to use the Okta API client: %s', err)
		else:
			try:
				okta_user = self._api_client('get_user', login)
			except RuntimeError:
				LOGGER.error('User not found in Okta: %s', login)
				return None

		try:
			user = UserModel.objects.get(pk=login)
		except UserModel.DoesNotExist:
			LOGGER.debug('Creating new local user: %s', login)
			user = UserModel(login=login) if okta_user is None else UserModel.from_okta_user(okta_user)
		else:
			if okta_user is not None:
				LOGGER.debug('Updating existing local user: %s', login)
				user.update_from_okta_user(okta_user)
		if user_details:
			LOGGER.info('Updating user "%s" with values from the SAML assertion: %s', login, user_details)
			user.update(**user_details)
		user.is_active = True

		user.save()

		if okta_user is not None:
			user.update_groups_from_okta()

		return user


class DjangoRESTBearerTokenAuthentication(DjangoRESTTokenAuthentication):
	"""Token authentication for REST
	Like the builtin rest_framework.authentication.TokenAuthentication method but using the "Bearer" word instead of the default "Token" (it simplifies the compatibility with Postman)
	"""

	keyword = 'Bearer'