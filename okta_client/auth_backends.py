import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group

import asgiref.sync
import okta.client

LOGGER = logging.getLogger(__name__)
UserModel = get_user_model()


class OktaBackend(ModelBackend):
	'''Okta auth backend
	Include Okta related specifics to the authentication process.
	'''

	def __getattr__(self, name):
		'''Lazy instantiation
		Some computation that is left pending until is needed
		'''

		if name == '_client':
			client_config = {'orgUrl' : settings.OKTA_CLIENT['API_ORG_URL'], 'token' : settings.OKTA_CLIENT['API_TOKEN']}
			if 'SSL_CONTEXT' in settings.OKTA_CLIENT:
				client_config['sslContext'] = settings.OKTA_CLIENT['SSL_CONTEXT']
			value = okta.client.Client(client_config)
		else:
			return getattr(super(), name)
		self.__setattr__(name, value)
		return value

	def _query_okta_api(self, method_name, *args, **kwargs):
		'''
		'''

		result = asgiref.sync.async_to_sync(getattr(self._client, method_name),)(*args, **kwargs)

		if len(result) == 3:
			result, response, err = result
		elif len(result) == 2:
			response, err = result
		else:
			raise RuntimeError('Unknown result: {}'.format(result))

		if err is not None:
			raise RuntimeError(err)

		while response.has_next():
			partial, err = asgiref.sync.async_to_sync(response.next)()
			if err is not None:
				raise RuntimeError(err)
			result.extend(partial)

		return result

	def authenticate(self, request, login, **user_details):
		'''Noop check
		Retrieve the user details using the Okta API, check for admin access, and update group membership (creating groups if needed)
		'''

		try:
			okta_user = self._query_okta_api('get_user', login)
		except RuntimeError:
			LOGGER.error('User not found in Okta: %s', login)
			return None

		try:
			user = UserModel.objects.get(pk = login)
		except UserModel.DoesNotExist:
			LOGGER.debug('Creating new local user: %s', login)
			user = UserModel.from_okta_profile(okta_user.profile)
		else:
			LOGGER.debug('Updating existing local user: %s', login)
			user.update_from_okta_profile(okta_user.profile)
		if user_details:
			LOGGER.info('Updating user "%s" with values from the SAML assertion: %s', login, user_details)
			user.update(**user_details)
		user.is_active = True

		user_groups = [group.profile.name for group in self._query_okta_api('list_user_groups', okta_user.id)]

		if 'ADMIN_GROUPS' in settings.OKTA_CLIENT:
			if frozenset(settings.OKTA_CLIENT['ADMIN_GROUPS']) & frozenset(user_groups):
				LOGGER.debug('Found an admin: %s', login)
				user.is_staff = True
				user.is_superuser = True

		user.save()

		for group_name in user_groups:
			try:
				group = Group.objects.get(name = group_name)
			except Group.DoesNotExist:
				LOGGER.debug('Creating local group: %s', group_name)
				group = Group(name = group_name)
				group.save()
			LOGGER.debug('Adding user to group: %s -> %s', login, group_name)
			group.user_set.add(user)

		current_groups = frozenset([user_group.name for user_group in user.groups.all()])
		for removing_from_group in current_groups - frozenset(user_groups):
			LOGGER.debug('Removing user from group: %s <- %s', login, removing_from_group)
			group = Group.objects.get(name = removing_from_group)
			group.user_set.remove(user)

		return user
