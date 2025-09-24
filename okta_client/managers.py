#python
"""Okta user manager module
This module defines the custom user manager for the Okta user model.
"""

from logging import getLogger, INFO

from django.contrib.auth.base_user import BaseUserManager
from django.utils.timezone import now

from asgiref.sync import async_to_sync, sync_to_async
from okta.exceptions.exceptions import OktaAPIException
from okta.models.user import User as OktaAPIUser
from tqdm import tqdm as TQDM

from .api_client import OktaAPIClient
from .groups import set_group_members, set_user_groups

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
		try:
			async_to_sync(user.update_from_okta)(save_model=False)
		except OktaAPIException as err:
			LOGGER.debug(f"Couldn't update the user {user.login} from Okta: {err}")

		user.set_unusable_password()
		user.save()

		try:
			async_to_sync(user.set_groups_from_okta)()
		except OktaAPIException as err:
			LOGGER.debug(f"Couldn't update user {user.login} groups from Okta: {err}")
		if groups is not None:
			set_user_groups(user=user, groups=groups)

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
		try:
			async_to_sync(user.update_from_okta)(save_model=False)
		except OktaAPIException as err:
			LOGGER.debug(f"Couldn't update the user {user.login} from Okta: {err}")
		if password is not None:
			user.set_password(password)
		user.save()

		try:
			async_to_sync(user.set_groups_from_okta)()
		except OktaAPIException as err:
			LOGGER.debug(f"Couldn't update user {user.login} groups from Okta: {err}")
		if groups is not None:
			set_user_groups(user=user, groups=groups)

		return user

	async def get_okta_updated(self, login, update_groups=True):
		"""Get user updated from Okta
		Returns a local model for a user with the attributes updated from Okta. If the user is not updated from Okta and is not an existing local user, it will return (None, False).

		:param login: the user login attribute (pk)
		:type login: str
		:return: the user
		:rtype: self.model
		"""

		user, created = await sync_to_async(self.get_or_create)(login=login)
		await user.update_from_okta()
		if created and not user.okta_id:
			await user.adelete()
			return None, False
		if update_groups:
			await user.set_groups_from_okta()

		return user

	async def update_all_from_okta(self, include_deprovisioned=True, include_groups=True, show_progress=False):
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

		okta_users = await self._api_client.list_users(include_deprovisioned=include_deprovisioned)
		last_total = len(okta_users)
		pbar_desc = 'Updating all Okta users' if include_deprovisioned else 'Updating non-deprovisioned Okta users'
		pbar = TQDM(desc=pbar_desc, total=last_total, disable=not show_progress, unit='users', dynamic_ncols=True)
		async for okta_user in okta_users:
			user, created = await self.aget_or_create(login=okta_user.profile.login)
			try:
				await sync_to_async(user.update_from_okta_user)(okta_user)
				await user.asave()
			except Exception:
				LOGGER.exception('User Okta update failed: %s', user)
			else:
				pbar.update()
			if last_total != len(okta_users):
				pbar.total = last_total = len(okta_users)
				pbar.refresh()
		pbar.close()

		okta_groups = {}
		if include_groups:
			okta_groups = await self._api_client('list_groups')

			last_total = len(okta_groups)
			pbar = TQDM(desc='Updating groups from Okta', total=last_total, disable=not show_progress, unit='groups', dynamic_ncols=True)
			async for okta_group in okta_groups:
				okta_members = await self._api_client('list_group_users', okta_group.id)
				try:
					group_members = [await self.aget(login=okta_member.profile.login) async for okta_member in okta_members]
				except self.model.DoesNotExist:
					LOGGER.error("Missing members prevented the update of group: %s <- %s", okta_group.profile.name, okta_members)
				else:
					await sync_to_async(set_group_members)(okta_group.profile.name, group_members)
				pbar.update()
				if last_total != len(okta_groups):
					pbar.total = last_total = len(okta_groups)
					pbar.refresh()

			pbar.close()

		return len(okta_users), len(okta_groups)
