#python
"""
Okta authentication backend for Django.
"""

from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group

from rest_framework.authentication import TokenAuthentication as DjangoRESTTokenAuthentication

from .api_client import OktaAPIClient

LOGGER = getLogger(__name__)
UserModel = get_user_model()


class OktaBackend(OktaAPIClient, ModelBackend):
	"""Okta auth backend
	Include Okta related specifics to the authentication process.
	"""

	def authenticate(self, request, login, **user_details):
		"""Noop check
		Retrieve the user details using the Okta API, check for admin access, and update group membership (creating groups if needed)
		"""

		try:
			self.okta_api_client
		except Exception as err:
			okta_user = None
			LOGGER.warning('Unable to use the Okta API client: %s', err)
		else:
			try:
				okta_user = self.okta_api_request('get_user', login)
			except RuntimeError:
				LOGGER.error('User not found in Okta: %s', login)
				return None

		try:
			user = UserModel.objects.get(pk=login)
		except UserModel.DoesNotExist:
			LOGGER.debug('Creating new local user: %s', login)
			user = UserModel(login=login) if okta_user is None else UserModel.from_okta_profile(okta_user.profile)
		else:
			if okta_user is not None:
				LOGGER.debug('Updating existing local user: %s', login)
				user.update_from_okta_profile(okta_user.profile)
		if user_details:
			LOGGER.info('Updating user "%s" with values from the SAML assertion: %s', login, user_details)
			user.update(**user_details)
		user.is_active = True
		
		user_groups = []
		if okta_user is not None:
			user_groups = [group.profile.name for group in self.okta_api_request('list_user_groups', okta_user.id)]

			if 'SUPER_USER_GROUPS' in settings.OKTA_CLIENT:
				if frozenset(settings.OKTA_CLIENT['SUPER_USER_GROUPS']) & frozenset(user_groups):
					LOGGER.debug('Found a super user: %s', login)
					user.is_staff = True
					user.is_superuser = True

			if 'STAFF_USER_GROUPS' in settings.OKTA_CLIENT:
				if frozenset(settings.OKTA_CLIENT['STAFF_GROUPS']) & frozenset(user_groups):
					LOGGER.debug('Found a staff user: %s', login)
					user.is_staff = True

		user.save()

		if okta_user is not None:
			LOGGER.debug('Adding user to groups: %s -> %s', login, user_groups)
			for group_name in user_groups:
				try:
					group = Group.objects.get(name=group_name)
				except Group.DoesNotExist:
					LOGGER.debug('Creating local group: %s', group_name)
					group = Group(name=group_name)
					group.save()
				group.user_set.add(user)

			leaving_groups = frozenset([user_group.name for user_group in user.groups.all()]) - frozenset(user_groups)
			if leaving_groups:
				LOGGER.debug('Removing user from groups: %s <- %s', login, list(leaving_groups))
				for removing_from_group in leaving_groups:
					group = Group.objects.get(name=removing_from_group)
					group.user_set.remove(user)

		return user


class DjangoRESTBearerTokenAuthentication(DjangoRESTTokenAuthentication):
	"""Token authentication for REST
	Like the builtin rest_framework.authentication.TokenAuthentication method but using the "Bearer" word instead of the default "Token" (it simplifies the compatibility with Postman)
	"""

	keyword = 'Bearer'