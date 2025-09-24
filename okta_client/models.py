#python
"""Okta Client Models
This module defines the Django models for integrating with Okta user profiles.
"""

from datetime import datetime as DateTime
from logging import getLogger

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db.models import BooleanField, CharField, DateTimeField, EmailField, TextChoices, URLField, fields
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from asgiref.sync import sync_to_async
from okta.exceptions.exceptions import OktaAPIException

from .api_client import OktaAPIClient, ERROR_CODE_MAP
from .groups import set_user_groups
from .managers import OktaUserManager

LOGGER = getLogger(__name__)

validator_5_to_100 = RegexValidator(regex = '^.{5,100}$', message = '5 <= value length <= 100')
nullable_5_to_100 = RegexValidator(regex = '(^.{5,100}$)|(ˆ$)', message = '5 <= value length <= 100 (or nothing)')


class OktaStatuses(TextChoices):
	"""Choices for OktaUser.okta_status
	Ref: https://help.okta.com/en-us/content/topics/users-groups-profiles/usgp-end-user-states.htm
	"""

	STAGED = 'STAGED', _('Staged')
	PROVISIONED = 'PROVISIONED', _('Pending User Action')
	ACTIVE = 'ACTIVE', _('Active')
	RECOVERY = 'RECOVERY', _('Password Reset')
	PASSWORD_EXPIRED = 'PASSWORD_EXPIRED', _('Password Expired')
	LOCKED_OUT = 'LOCKED_OUT', _('Locked Out')
	SUSPENDED = 'SUSPENDED', _('Suspended')
	DEPROVISIONED = 'DEPROVISIONED', _('Deprovisioned')


class AbstractOktaUser(AbstractBaseUser, PermissionsMixin):
	"""Default Okta profile
	Based on the official documentation as of (10/2021) https://developer.okta.com/docs/reference/api/users/#default-profile-properties
	"""

	login = CharField(primary_key=True, max_length=100, validators=[validator_5_to_100], verbose_name=_('login'), help_text=_('Unique identifier for the user (username)'))
	email = EmailField(blank=False, validators=[validator_5_to_100], verbose_name=_('email'), help_text=_('Primary email address of user'))
	secondEmail = EmailField(blank=True, validators=[nullable_5_to_100], verbose_name=_('second email'), help_text=_('Secondary email address of user typically used for account recovery'))
	firstName = CharField(blank=False, max_length=50, verbose_name=_('first name'), help_text=_('Given name of the user (givenName)'))
	lastName = CharField(blank=False, max_length=50, verbose_name=_('last name'), help_text=_('Family name of the user (familyName)'))
	middleName = CharField(blank=True, max_length=50, verbose_name=_('middle name'), help_text=_('Middle name(s) of the user'))
	honorificPrefix = CharField(blank=True, max_length=50, verbose_name=_('honorific prefix'), help_text=_('Honorific prefix(es) of the user, or title in most Western languages'))
	honorificSuffix = CharField(blank=True, max_length=50, verbose_name=_('honorific suffix'), help_text=_('Honorific suffix(es) of the user'))
	title = CharField(blank=True, max_length=100, verbose_name=_('title'), help_text=_('''User's title, such as "Vice President"'''))
	displayName = CharField(blank=True, max_length=250, verbose_name=_('display name'), help_text=_('Name of the user, suitable for display to end users'))
	nickName = CharField(blank=True, max_length=50, verbose_name=_('nickname'), help_text=_('Casual way to address the user in real life'))
	profileUrl = URLField(blank=True, verbose_name=_('profile URL'), help_text=_("URL of user's online profile (e.g. a web page)"))
	primaryPhone = CharField(blank=True, max_length=100, verbose_name=_('primary phone'), help_text=_('Primary phone number of user such as home number'))
	mobilePhone = CharField(blank=True, max_length=100, verbose_name=_('mobile phone'), help_text=_('Mobile phone number of user'))
	streetAddress = CharField(blank=True, max_length=100, verbose_name=_('street address'), help_text=_("Full street address component of user's address"))
	city = CharField(blank=True, max_length=100, verbose_name=_('city'), help_text=_("City or locality component of user's address (locality)"))
	state = CharField(blank=True, max_length=100, verbose_name=_('state'), help_text=_("State or region component of user's address (region)"))
	zipCode = CharField(blank=True, max_length=100, verbose_name=_('ZIP code'), help_text=_("Zipcode or postal code component of user's address (postalCode)"))
	countryCode = CharField(blank=True, max_length=2, verbose_name=_('country code'), help_text=_("Country name component of user's address (country)"))
	postalAddress = CharField(blank=True, max_length=100, verbose_name=_('postal address'), help_text=_("Mailing address component of user's address"))
	preferredLanguage = CharField(blank=True, max_length=100, verbose_name=_('preferred language'), help_text=_("User's preferred written or spoken languages"))
	locale = CharField(blank=True, max_length=5, verbose_name=_('locale'), help_text=_("User's default location for purposes of localizing items such as currency, date time format, numerical representations, etc."))
	timezone = CharField(blank=True, max_length=100, verbose_name=_('time zone'), help_text=_("User's time zone"))
	userType = CharField(blank=True, max_length=100, verbose_name=_('user type'), help_text=_('Used to describe the organization to user relationship such as "Employee" or "Contractor"'))
	employeeNumber = CharField(blank=True, max_length=100, verbose_name=_('employee number'), help_text=_('Organization or company assigned unique identifier for the user'))
	costCenter = CharField(blank=True, max_length=100, verbose_name=_('cost center'), help_text=_('Name of a cost center assigned to user'))
	organization = CharField(blank=True, max_length=100, verbose_name=_('organization'), help_text=_("Name of user's organization"))
	division = CharField(blank=True, max_length=100, verbose_name=_('division'), help_text=_("Name of user's division"))
	department = CharField(blank=True, max_length=100, verbose_name=_('department'), help_text=_("Name of user's department"))
	managerId = CharField(blank=True, max_length=100, verbose_name=_('manager ID'), help_text=_("ID of a user's manager"))
	manager = CharField(blank=True, max_length=100, verbose_name=_('manager'), help_text=_("DisplayName of the user's manager"))
	
	is_active = BooleanField(default=True, verbose_name=_("active"), help_text=_('Designates whether this user should be treated as active. \nUnselect this instead of deleting accounts.'))
	is_staff = BooleanField(default=False, verbose_name=_("staff status"), help_text=_("Designates whether the user can log into the admin site."))
	date_joined = DateTimeField(auto_now_add=True, verbose_name=_("date joined"), help_text=_('The timestamp when the local account was created'))

	okta_id = CharField(null=True, blank=True, unique=True, max_length=50, verbose_name=_('id'), help_text=_("Okta internal ID for the user."))
	okta_activated = DateTimeField(null=True, blank=True, verbose_name=_("activated"), help_text=_("Timestamp of the account activation."))
	okta_created = DateTimeField(null=True, blank=True, verbose_name=_("created"), help_text=_("Timestamp of the account creation."))
	okta_status = CharField(blank=True, max_length=30, choices=OktaStatuses, verbose_name=_('status'), help_text=_("Status of the Okta account."))
	okta_status_changed = DateTimeField(null=True, blank=True, verbose_name=_("status changed"), help_text=_('Timestamp of the last update of the "status" attribute.'))
	last_refresh_timestamp = DateTimeField(null=True, blank=True, verbose_name=_("Last refresh timestamp"), help_text=_('The last time the user was updated (refreshed) from Okta'))

	objects = OktaUserManager()
	
	EMAIL_FIELD = 'email'
	USERNAME_FIELD = 'login'
	REQUIRED_FIELDS = ['email', 'firstName', 'lastName']

	class Meta:
		verbose_name = _('okta user')
		verbose_name_plural = _('okta users')
		abstract = True

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

	def __str__(self):
		"""String representation of the Okta user.

		:return: The login (username) of the Okta user.
		:rtype: str
		"""

		return self.login
	
	@classmethod
	def _attributes_from_okta_user(cls, okta_user):
		"""Extracts relevant attributes from an Okta user object.
		This method iterates through the model's fields and attempts to retrieve corresponding values from the provided `okta_user` object. It handles `DateTimeField` conversion and filters out empty or None values.

		:return: Attributes extracted from the Okta user, suitable for model instantiation or update.
		:rtype: dict
		"""

		attributes = {}
		for field in cls._meta.fields:
			if hasattr(okta_user.profile, field.name):
				okta_attr = getattr(okta_user.profile, field.name)
				if (okta_attr is None) or (isinstance(okta_attr, str) and not len(okta_attr)):
					continue
				if isinstance(field, fields.DateTimeField):
					okta_attr = DateTime.fromisoformat(okta_attr)
				attributes[field.name] = okta_attr

		attributes['okta_id'] = okta_user.id
		for dates_ in ('activated', 'created', 'status_changed'):
			if (attr := getattr(okta_user, dates_)) is not None:
				attributes[f'okta_{dates_}'] = DateTime.fromisoformat(attr)
		attributes['okta_status'] = OktaStatuses[okta_user.status]
		if attributes['okta_status'] != OktaStatuses.ACTIVE:
			attributes['is_active'] = False

		return attributes

	@classmethod
	def from_okta_user(cls, okta_user):
		"""Creates an instance of the OktaUser model from an Okta user object.
		This method uses `_attributes_from_okta_user` to extract relevant data and then instantiates the model.

		:param okta_user: An object representing the Okta user.
		:type okta_user: object
		:return: An instance of the OktaUser model.
		:rtype: cls
		"""

		return cls(**cls._attributes_from_okta_user(okta_user))

	def get_full_name(self):
		"""Returns the user's full name.
		This method prioritizes the `displayName` field. If `displayName` is not set, it constructs the full name by concatenating `honorificPrefix`, `firstName`, `middleName`, `lastName`, and `honorificSuffix`, including only non-empty components.

		:return: The user's full name
		:rtype: str
		"""

		if self.displayName:
			return self.displayName
		else:
			components = ('honorificPrefix', 'firstName', 'middleName', 'lastName', 'honorificSuffix')
			return ' '.join([getattr(self, component) for component in components if getattr(self, component)])

	def get_short_name(self):
		"""Returns the user's short name.
		This method prioritizes the `nickName` field. If `nickName` is not set, it returns the `firstName`.

		:return: The user's short name
		:rtype: str
		"""

		if self.nickName:
			return self.nickName
		else:
			return self.firstName

	@property
	def is_outdated(self):
		"""Are user attributes too old?
		Uses the "last_refresh_timestamp" and the API Client's "get_refresh_delta" to figure out if the attributes need to be updated.
		"""

		return (self.last_refresh_timestamp is None) or (now() > (self.last_refresh_timestamp + self._api_client.get_refresh_delta()))

	async def set_groups_from_okta(self, force_empty=False):
		"""Set groups from Okta
		Queries Okta for the group membership of the user and sets the local groups accordingly. Assumes that an empty list from "list_user_groups" was a failed query.

		:param force_empty: forces the update with an empty list if present (remove all groups)
		:type force_empty: bool
		"""

		if not self.okta_id:
			return
		okta_groups = await self._api_client('list_user_groups', self.okta_id)
		if okta_groups or force_empty:
			await sync_to_async(set_user_groups)(self, [group.profile.name async for group in okta_groups])

	def update(self, **updated_values):
		"""Updates user attributes from a dictionary of values.
		This method iterates through the provided keyword arguments and updates the corresponding fields on the user model instance. It only updates fields that exist on the model; any unknown fields will be ignored and a warning will be logged.

		:param updated_values: Keyword arguments where keys are model field names and values are the new values for those fields.
		"""
		
		local_fields = [field.name for field in self._meta.fields]
		for key, value in updated_values.items():
			if key in local_fields:
				setattr(self, key, value)
			else:
				LOGGER.warning('Dropping unknown field "%s" in object: %s', key, type(self))

	async def update_from_okta(self, force_update=False, save_model=True):
		"""Update attributes from Okta
		Queries the Okta API for the user's details and updates the local attributes
		"""

		if not await self._api_client.ping_users_endpoint():
			LOGGER.debug("Okta user endpoint not available; skipping user update: %s", self.login)
			return

		if self.is_outdated or force_update:
			if self.okta_id:
				okta_user = await self._api_client('get_user', self.okta_id)
			else:
				try:
					okta_user = await self._api_client('get_user', self.login)
				except OktaAPIException as error_:
					if error_.args[0]['errorCode'] != ERROR_CODE_MAP['USER_NOT_FOUND']:
						okta_user = None
					else:
						raise
				else:
					if self.login != okta_user.profile.login:
						okta_user = None
			if okta_user is None:
				LOGGER.debug('Local user not found in Okta: %s', self.login)
			else:
				LOGGER.debug('Retrieving info from Okta to update user: %s', self.login)
				await sync_to_async(self.update_from_okta_user)(okta_user, save_model=False)
				self.last_refresh_timestamp = now()
				if save_model:
					await self.asave()
		else:
			LOGGER.debug('User local attributes are current enough, skipping update: %s', self.login)

	def update_from_okta_user(self, okta_user, save_model=False):
		"""Updates the user's attributes from an Okta user object.
		This method extracts relevant attributes from the provided `okta_user` using `_attributes_from_okta_user` and then updates the corresponding fields on the current user instance.

		:param okta_user: An object representing the Okta user.
		:type okta_user: OktaAPIUser
		"""

		self.update(**self._attributes_from_okta_user(okta_user))
		if save_model:
			self.save()


class OktaUser(AbstractOktaUser):
	"""Django user model
	Alternate user model for Django based on Okta profiles.
	"""
	
	class Meta(AbstractOktaUser.Meta):
		swappable = 'AUTH_USER_MODEL'
