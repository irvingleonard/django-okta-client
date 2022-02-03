from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy

from .managers import OktaUserManager

validator_5_to_100 = RegexValidator(regex = '^.{5,100}$', message = '5 <= value length <= 100')
nullable_5_to_100 = RegexValidator(regex = '(^.{5,100}$)|(ˆ$)', message = '5 <= value length <= 100 (or nothing)')

class UpstreamOktaUser(models.Model):
	'''Default Okta profile
	Based on the official documentation as of (10/2021) https://developer.okta.com/docs/reference/api/users/#default-profile-properties
	'''
	
	login = models.CharField(primary_key = True, max_length = 100, validators=[validator_5_to_100], help_text = 'unique identifier for the user (username)')
	email = models.EmailField(blank = False, validators=[validator_5_to_100], help_text = 'primary email address of user')
	secondEmail = models.EmailField(blank = True, validators=[nullable_5_to_100], help_text = 'secondary email address of user typically used for account recovery')
	firstName = models.CharField(blank = False, max_length = 50, help_text = 'given name of the user (givenName)')
	lastName = models.CharField(blank = False, max_length = 50, help_text = 'family name of the user (familyName)')
	middleName = models.CharField(blank = True, max_length = 50, help_text = 'middle name(s) of the user')
	honorificPrefix = models.CharField(blank = True, max_length = 50, help_text = 'honorific prefix(es) of the user, or title in most Western languages')
	honorificSuffix = models.CharField(blank = True, max_length = 50, help_text = 'honorific suffix(es) of the user')
	title = models.CharField(blank = True, max_length = 100, help_text = 'user\'s title, such as "Vice President')
	displayName = models.CharField(blank = True, max_length = 250, help_text = 'name of the user, suitable for display to end users')
	nickName = models.CharField(blank = True, max_length = 50, help_text = 'casual way to address the user in real life')
	profileUrl = models.URLField(blank = True, help_text = "url of user's online profile (e.g. a web page)")
	primaryPhone = models.CharField(blank = True, max_length = 100, help_text = 'primary phone number of user such as home number')
	mobilePhone = models.CharField(blank = True, max_length = 100, help_text = 'mobile phone number of user')
	streetAddress = models.CharField(blank = True, max_length = 100, help_text = "full street address component of user's address")
	city = models.CharField(blank = True, max_length = 100, help_text = "city or locality component of user's address (locality)")
	state = models.CharField(blank = True, max_length = 100, help_text = "state or region component of user's address (region)")
	zipCode = models.CharField(blank = True, max_length = 100, help_text = "zipcode or postal code component of user's address (postalCode)")
	countryCode = models.CharField(blank = True, max_length = 2, help_text = "country name component of user's address (country)")
	postalAddress = models.CharField(blank = True, max_length = 100, help_text = "mailing address component of user's address")
	preferredLanguage = models.CharField(blank = True, max_length = 100, help_text = "user's preferred written or spoken languages")
	locale = models.CharField(blank = True, max_length = 5, help_text = "user's default location for purposes of localizing items such as currency, date time format, numerical representations, etc.")
	timezone = models.CharField(blank = True, max_length = 100, help_text = "user's time zone")
	userType = models.CharField(blank = True, max_length = 100, help_text = 'used to describe the organization to user relationship such as "Employee" or "Contractor"')
	employeeNumber = models.CharField(blank = True, max_length = 100, help_text = 'organization or company assigned unique identifier for the user')
	costCenter = models.CharField(blank = True, max_length = 100, help_text = 'name of a cost center assigned to user')
	organization = models.CharField(blank = True, max_length = 100, help_text = "name of user's organization")
	division = models.CharField(blank = True, max_length = 100, help_text = "name of user's division")
	department = models.CharField(blank = True, max_length = 100, help_text = "name of user's department")
	managerId = models.CharField(blank = True, max_length = 100, help_text = "id of a user's manager")
	manager = models.CharField(blank = True, max_length = 100, help_text = "displayName of the user's manager")
	
	class Meta:
		abstract = True


class OktaUser(AbstractBaseUser, PermissionsMixin, UpstreamOktaUser):
	'''Django user model
	Alternate user model for Django based on Okta profiles.
	'''
	
	USERNAME_FIELD = 'login'
	EMAIL_FIELD = 'email'
	REQUIRED_FIELDS = ['email', 'firstName', 'lastName']

	password = models.CharField(blank = True, max_length = 128, help_text = "user's password")
	is_staff = models.BooleanField(gettext_lazy('staff status'), default = False, help_text = gettext_lazy('Designates whether the user can log into this admin site.'))
	is_active = models.BooleanField(gettext_lazy('active'), default = True, help_text = gettext_lazy('Designates whether this user should be treated as active. \nUnselect this instead of deleting accounts.'))
	date_joined = models.DateTimeField(auto_now_add = True)
	
	objects = OktaUserManager()
	
	def __str__(self):
		return self.login
	
	def get_full_name(self):
		if self.displayName:
			return self.displayName
		else:
			components = ('honorificPrefix', 'firstName', 'middleName', 'lastName', 'honorificSuffix')
			return ' '.join([getattr(self, component) for component in components if getattr(self, component)])

	def get_short_name(self):
		if self.nickName:
			return self.nickName
		else:
			return self.firstName
