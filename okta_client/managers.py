#python
"""Okta user manager module
This module defines the custom user manager for the Okta user model.
"""

from logging import getLogger, INFO

from django.contrib.auth.base_user import BaseUserManager
from django.utils.timezone import now

from okta.models.user import User as OktaAPIUser
from tqdm import tqdm as TQDM

from .api_client import OktaAPIClient
from .groups import set_group_members

LOGGER = getLogger(__name__)


class OktaUserManager(BaseUserManager):
	"""Okta user remote manager
	Custom user manager to work with the Okta user model acting on the Okta directory via the API client.
	"""

	IDENTIFYING_FIELDS = ('pk', 'login', 'okta_id', 'email')

	use_in_migrations = True

	def __getattr__(self, name):
		"""Lazy instantiation
		It provides a mechanism for lazy instantiation of the Okta API client.

		:param name: The name of the attribute being accessed.
		:type name: str
		:returns: the attribute value
		"""

		if name == '_api_client':
			value = OktaAPIClient()
		else:
			return getattr(super(), name)
		self.__setattr__(name, value)
		return value

	def create_from_okta_user(self, okta_user):
		"""Create form Okta API User
		Creates a model object from an Okta API User.
		
		:param okta_user: the Okta User to base the model on
		:type okta_user: OktaAPIUser
		:return: the model object
		:rtype: self.model
		"""
		
		user = self.model.from_okta_user(okta_user)
		user.last_refresh_timestamp = now()
		user.set_unusable_password()
		user.save()
		return user
	
	def create_user(self, login, email, firstName, lastName, password=None, groups=None, **other_fields):
		"""Create a local user
		Create and save a user with the provided details.

		:param login: the pk of the model (username)
		:type login: str
		:param email: the email of the user
		:type email: str
		:param firstName: the first name of the user
		:type firstName: str
		:param lastName: the last name of the user
		:type lastName: str
		:param password: the password for the user, will be ignored
		:type password: str
		:param groups: a list of groups that the user will be added to
		:type groups: list
		:param other_fields: other fields passed to the user model
		:type other_fields: any
		"""

		try:
			email = self.normalize_email(email)
		except Exception:
			pass

		user = self.model(login=login, email=email, firstName=firstName, lastName=lastName, **other_fields)
		user.update_from_okta(save_model=False)
		user.set_unusable_password()
		user.save()

		user.set_groups_from_okta()
		if groups is not None:
			user.update_groups(groups)

		return user

	def create_superuser(self, login, email, firstName, lastName, password=None, groups=None, **other_fields):
		"""Create a local superuser
		Create and save a superuser with the provided details, including a password.

		:param login: the pk of the model (username)
		:type login: str
		:param email: the email of the user
		:type email: str
		:param firstName: the first name of the user
		:type firstName: str
		:param lastName: the last name of the user
		:type lastName: str
		:param password: the password for the user
		:type password: str
		:param groups: a list of groups that the user will be added to
		:type groups: list
		:param other_fields: other fields passed to the user model
		:type other_fields: any
		"""

		try:
			email = self.normalize_email(email)
		except Exception:
			pass

		other_fields.setdefault('is_staff', True)
		other_fields.setdefault('is_superuser', True)
		other_fields.setdefault('is_active', True)

		if other_fields.get('is_staff') is not True:
			raise ValueError('Superuser must have is_staff=True.')
		if other_fields.get('is_superuser') is not True:
			raise ValueError('Superuser must have is_superuser=True.')

		user = self.model(login=login, email=email, firstName=firstName, lastName=lastName, **other_fields)
		user.update_from_okta(save_model=False)
		if password is not None:
			user.set_password(password)
		user.save()

		user.set_groups_from_okta()
		if groups is not None:
			user.update_groups(groups)

		return user

	def get_okta_updated(self, login, update_groups=True):
		"""Get user updated from Okta
		Returns a local model for a user with the attributes updated from Okta. If the user is not updated from Okta and is not an existing local user, it will return (None, False).

		:param login: the user login attribute (pk)
		:type login: str
		:return: the user
		:rtype: self.model
		"""

		user, created = self.get_or_create(login=login)
		user.update_from_okta()
		if created and not user.okta_id:
			user.delete()
			return None, False
		if update_groups:
			user.set_groups_from_okta()

		return user

	def update_all_from_okta(self, include_deprovisioned=True, include_groups=True, show_progress=False):
		"""Update all users and groups from Okta
		Queries Okta for the list of users, the list of groups, and the membership for each group. Updates the local users and groups accordingly.

		:param include_deprovisioned: also include users with the "Deprovisioned" status.
		:type include_deprovisioned: bool
		:param include_groups: also update groups.
		:type include_groups: bool
		:param show_progress: generate progress bar for the console output
		:type show_progress: bool
		:return: the number of users and groups updated
		:rtype: tuple[int, int]
		"""

		if show_progress:
			getLogger('asyncio').setLevel(INFO)
			iter_class = TQDM
		else:
			iter_class = lambda x: x

		if include_deprovisioned:
			LOGGER.debug('Retrieving all Okta users')
		else:
			LOGGER.debug('Retrieving non-deprovisioned Okta users')
		okta_users = self._api_client.list_users(include_deprovisioned=include_deprovisioned)
		LOGGER.debug('Updating %d users from Okta', len(okta_users))
		for okta_user in iter_class(okta_users):
			user, created = self.get_or_create(login=okta_user.profile.login)
			try:
				user.update_from_okta_user(okta_user, save_model=True)
			except Exception:
				LOGGER.exception('User Okta update failed: %s', user)

		okta_groups = {}
		if include_groups:
			LOGGER.debug('Retrieving all Okta groups')
			okta_groups = {group.id: group.profile.name for group in self._api_client.list_groups()}

			LOGGER.debug('Updating %d groups from Okta', len(okta_groups))
			for okta_group_id, okta_group_name in iter_class(okta_groups.items()):
				okta_members = [okta_user.profile.login for okta_user in self._api_client.list_group_users(okta_group_id)]
				try:
					group_members = [self.get(login=okta_member) for okta_member in okta_members]
				except self.model.DoesNotExist:
					LOGGER.error("Missing members prevented the update of group: %s <- %s", okta_group_name, okta_members)
				else:
					set_group_members(okta_group_name, group_members)

		return len(okta_users), len(okta_groups)
