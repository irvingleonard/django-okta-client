#python
"""Okta Client Models
This module defines the Django models for integrating with Okta user profiles.
"""

from datetime import datetime as DateTime
from logging import getLogger

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db.models import BooleanField, CharField, DateTimeField, EmailField, URLField, fields
from django.utils import timezone as timezone_utils
from django.utils.translation import gettext_lazy as _

from .managers import OktaUserManager

LOGGER = getLogger(__name__)

validator_5_to_100 = RegexValidator(regex = '^.{5,100}$', message = '5 <= value length <= 100')
nullable_5_to_100 = RegexValidator(regex = '(^.{5,100}$)|(ˆ$)', message = '5 <= value length <= 100 (or nothing)')

class AbstractOktaUser(AbstractBaseUser, PermissionsMixin):
	"""Default Okta profile
	Based on the official documentation as of (10/2021) https://developer.okta.com/docs/reference/api/users/#default-profile-properties
	"""
	
	login = CharField(primary_key=True, max_length=100, validators=[validator_5_to_100], verbose_name=_('login'), help_text=_('unique identifier for the user (username)'))
	email = EmailField(blank=False, validators=[validator_5_to_100], verbose_name=_('email'), help_text=_('primary email address of user'))
	secondEmail = EmailField(blank=True, validators=[nullable_5_to_100], verbose_name=_('second email'), help_text=_('secondary email address of user typically used for account recovery'))
	firstName = CharField(blank=False, max_length=50, verbose_name=_('first name'), help_text=_('given name of the user (givenName)'))
	lastName = CharField(blank=False, max_length=50, verbose_name=_('last name'), help_text=_('family name of the user (familyName)'))
	middleName = CharField(blank=True, max_length=50, verbose_name=_('middle name'), help_text=_('middle name(s) of the user'))
	honorificPrefix = CharField(blank=True, max_length=50, verbose_name=_('honorific prefix'), help_text=_('honorific prefix(es) of the user, or title in most Western languages'))
	honorificSuffix = CharField(blank=True, max_length=50, verbose_name=_('honorific suffix'), help_text=_('honorific suffix(es) of the user'))
	title = CharField(blank=True, max_length=100, verbose_name=_('title'), help_text=_('user\'s title, such as "Vice President'))
	displayName = CharField(blank=True, max_length=250, verbose_name=_('display name'), help_text=_('name of the user, suitable for display to end users'))
	nickName = CharField(blank=True, max_length=50, verbose_name=_('nickname'), help_text=_('casual way to address the user in real life'))
	profileUrl = URLField(blank=True, verbose_name=_('profile URL'), help_text=_("url of user's online profile (e.g. a web page)"))
	primaryPhone = CharField(blank=True, max_length=100, verbose_name=_('primary phone'), help_text=_('primary phone number of user such as home number'))
	mobilePhone = CharField(blank=True, max_length=100, verbose_name=_('mobile phone'), help_text=_('mobile phone number of user'))
	streetAddress = CharField(blank=True, max_length=100, verbose_name=_('street address'), help_text=_("full street address component of user's address"))
	city = CharField(blank=True, max_length=100, verbose_name=_('city'), help_text=_("city or locality component of user's address (locality)"))
	state = CharField(blank=True, max_length=100, verbose_name=_('state'), help_text=_("state or region component of user's address (region)"))
	zipCode = CharField(blank=True, max_length=100, verbose_name=_('ZIP code'), help_text=_("zipcode or postal code component of user's address (postalCode)"))
	countryCode = CharField(blank=True, max_length=2, verbose_name=_('country code'), help_text=_("country name component of user's address (country)"))
	postalAddress = CharField(blank=True, max_length=100, verbose_name=_('postal address'), help_text=_("mailing address component of user's address"))
	preferredLanguage = CharField(blank=True, max_length=100, verbose_name=_('preferred language'), help_text=_("user's preferred written or spoken languages"))
	locale = CharField(blank=True, max_length=5, verbose_name=_('locale'), help_text=_("user's default location for purposes of localizing items such as currency, date time format, numerical representations, etc."))
	timezone = CharField(blank=True, max_length=100, verbose_name=_('time zone'), help_text=_("user's time zone"))
	userType = CharField(blank=True, max_length=100, verbose_name=_('user type'), help_text=_('used to describe the organization to user relationship such as "Employee" or "Contractor"'))
	employeeNumber = CharField(blank=True, max_length=100, verbose_name=_('employee number'), help_text=_('organization or company assigned unique identifier for the user'))
	costCenter = CharField(blank=True, max_length=100, verbose_name=_('cost center'), help_text=_('name of a cost center assigned to user'))
	organization = CharField(blank=True, max_length=100, verbose_name=_('organization'), help_text=_("name of user's organization"))
	division = CharField(blank=True, max_length=100, verbose_name=_('division'), help_text=_("name of user's division"))
	department = CharField(blank=True, max_length=100, verbose_name=_('department'), help_text=_("name of user's department"))
	managerId = CharField(blank=True, max_length=100, verbose_name=_('manager ID'), help_text=_("id of a user's manager"))
	manager = CharField(blank=True, max_length=100, verbose_name=_('manager'), help_text=_("displayName of the user's manager"))
	
	is_active = BooleanField(default=True, verbose_name=_("active"), help_text=_('Designates whether this user should be treated as active. \nUnselect this instead of deleting accounts.'))
	is_staff = BooleanField(default=False, verbose_name=_("staff status"), help_text=_("Designates whether the user can log into the admin site."))
	date_joined = DateTimeField(verbose_name=_("date joined"), default=timezone_utils.now)
	
	objects = OktaUserManager()
	
	EMAIL_FIELD = 'email'
	USERNAME_FIELD = 'login'
	REQUIRED_FIELDS = ['email', 'firstName', 'lastName']
	
	class Meta:
		verbose_name = _('okta user')
		verbose_name_plural = _('okta users')
		abstract = True
	
	def __str__(self):
		"""String representation of the Okta user.

		:return: The login (username) of the Okta user.
		:rtype: str
		"""

		return self.login
	
	@classmethod
	def _attributes_from_okta_profile(cls, okta_profile):
		"""Extracts relevant attributes from an Okta profile object.
		This method iterates through the model's fields and attempts to retrieve corresponding values from the provided `okta_profile` object. It handles `DateTimeField` conversion and filters out empty or None values.

		:return: Attributes extracted from the Okta profile, suitable for model instantiation or update.
		:rtype: dict
		"""

		attributes = {}
		for field in cls._meta.fields:
			if hasattr(okta_profile, field.name):
				okta_attr = getattr(okta_profile, field.name)
				if (okta_attr is None) or not len(okta_attr):
					continue
				if isinstance(field, fields.DateTimeField):
					okta_attr = DateTime.fromisoformat(okta_attr.rstrip('Z'))
				attributes[field.name] = okta_attr
		return attributes

	@classmethod
	def from_okta_profile(cls, okta_profile):
		"""Creates an instance of the Okta user model from an Okta profile object.
		This method uses `_attributes_from_okta_profile` to extract relevant data and then instantiates the model.

		:param okta_profile: An object representing the Okta user profile.
		:type okta_profile: object
		:return: An instance of the Okta user model.
		:rtype: cls
		"""

		return cls(**cls._attributes_from_okta_profile(okta_profile))

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

	def update(self, **updated_values):
		"""Updates user attributes from a dictionary of values.
		This method iterates through the provided keyword arguments and updates the corresponding fields on the user model instance. It only updates fields that exist on the model; any unknown fields will be ignored and a warning will be logged.

		:param updated_values: Keyword arguments where keys are model field names and values are the new values for those fields.
		:return: The updated user instance.
		:rtype: self
		"""
		
		local_fields = [field.name for field in self._meta.fields]
		for key, value in updated_values.items():
			if key in local_fields:
				setattr(self, key, value)
			else:
				LOGGER.warning('Dropping unknown field "%s" in object: %s', key, type(self))
		return self

	def update_from_okta_profile(self, okta_profile):
		"""Updates the user's attributes from an Okta profile object.
		This method extracts relevant attributes from the provided `okta_profile` using `_attributes_from_okta_profile` and then updates the corresponding fields on the current user instance.

		:param okta_profile: An object representing the Okta user profile.
		:type okta_profile: object
		:return: The updated user instance.
		:rtype: self
		"""

		for field_name, field_value in self._attributes_from_okta_profile(okta_profile).items():
			setattr(self, field_name, field_value)
		return self


class OktaUser(AbstractOktaUser):
	"""Django user model
	Alternate user model for Django based on Okta profiles.
	"""
	
	class Meta(AbstractOktaUser.Meta):
		swappable = 'AUTH_USER_MODEL'
