#python
"""Okta user manager module
This module defines the custom user manager for the Okta user model.
"""

from logging import getLogger

from django.contrib.auth.base_user import BaseUserManager

from okta.models.user import User as OktaAPIUser

from .api_client import OktaAPIClient

LOGGER = getLogger(__name__)


class OktaUserManager(BaseUserManager):
	"""Okta user remote manager
	Custom user manager to work with the Okta user model acting on the Okta directory via the API client.
	"""

	IDENTIFYING_FIELDS = ('pk', 'login', 'okta_id', 'email')

	use_in_migrations = True
	_api_client = OktaAPIClient()

	@classmethod
	def _get_search_term_for_okta(cls, **attributes):
		"""Get search term for Okta
		The Okta "get_user" call can use several attributes to identify the user. This function check the list provided in "attributes" and selects the value of any applicable one or returns None.
		:param attributes: the mapping of attributes and values
		:type attributes: Any
		:return: the value of a matching attribute or None
		:rtype: Any|None
		"""

		for field_ in cls.IDENTIFYING_FIELDS:
			if field_ in attributes:
				return attributes[field_]

		return None

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
		user.set_unusable_password()
		user.save()

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
		if password is not None:
			user.set_password(password)
		user.save()

		if groups is not None:
			user.update_groups(groups)

		return user

	def get(self, **search_attributes):
		"""Override for default get
		Tries to sync the associated user before calling the underlying "get".

		:param search_attributes: the "query"
		:type search_attributes: any
		:return: the user
		:rtype: self.model
		:raises self.model.DoesNotExist: if the user doesn't exist
		"""

		login = self._get_search_term_for_okta(**search_attributes)
		if login is not None:
			try:
				self.get_user(login)
			except ValueError:
				pass

		return super().get_queryset().get(**search_attributes)

	def get_or_create(self, **user_details):
		"""Override of base method
		A hybrid method taking into account remote Okta users. Users will only be "created" if done locally, not if they already exist in Okta.

		:param user_details: the other user details, needed for the "create" case.
		:type user_details: any
		:return: the user and the creation flag
		:rtype: tuple
		"""

		created = False
		search_term = self._get_search_term_for_okta(**user_details)
		user = None if search_term is None else self._api_client.get_user(search_term)
		if user is None:
			user, created = super().get_or_create(**user_details)
		else:
			user.update_from_okta_user(user)
			user.save()
		return user, created

	def get_user(self, user):
		"""Get user
		Updates from Okta (if applicable) and retrieves a UserModel user. Local users won't be updated. If the user doesn't match an Okta user or a local user a ValueError will be raised.

		:param user: the user to get
		:type user: self.model|OktaAPIUser|str
		:return: the user
		:rtype: self.model
		:raises ValueError: if the user doesn't exist in Okta or locally
		"""

		user_param = user
		if not isinstance(user, self.model) and not isinstance(user, OktaAPIUser):
			user = self._api_client.get_user(user)

		if user is None:
			try:
				user = super().get_queryset().get(login=user_param)
			except self.model.DoesNotExist:
				user = None
		elif isinstance(user, OktaAPIUser):
			try:
				user = super().get_queryset().get(login=user.profile.login).update_from_okta_user(user)
			except self.model.DoesNotExist:
				user = self.model.from_okta_user(user)
				user.set_unusable_password()
			user.save()

		if user is None:
			raise ValueError(f"Couldn't find user anywhere: {user_param}")

		user.update_groups_from_okta()

		return user

	def update_all(self):
		"""Update all
		Leverages the side effects of self.get_user to update all the users from the Okta directory.

		:return: the list of updated users
		:rtype: list
		"""

		return [self.get_user(user) for user in self._api_client.list_users()]
