from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone as timezone_utils
from django.utils.translation import gettext_lazy as _

from .managers import OktaUserManager

validator_5_to_100 = RegexValidator(regex = '^.{5,100}$', message = '5 <= value length <= 100')
nullable_5_to_100 = RegexValidator(regex = '(^.{5,100}$)|(ˆ$)', message = '5 <= value length <= 100 (or nothing)')

class AbstractOktaUser(AbstractBaseUser, PermissionsMixin):
	'''Default Okta profile
	Based on the official documentation as of (10/2021) https://developer.okta.com/docs/reference/api/users/#default-profile-properties
	'''
	
	login = models.CharField(primary_key = True, max_length = 100, validators=[validator_5_to_100], verbose_name = _('login'), help_text = _('unique identifier for the user (username)'))
	email = models.EmailField(blank = False, validators=[validator_5_to_100], verbose_name = _('email'), help_text = _('primary email address of user'))
	secondEmail = models.EmailField(blank = True, validators=[nullable_5_to_100], verbose_name = _('second email'), help_text = _('secondary email address of user typically used for account recovery'))
	firstName = models.CharField(blank = False, max_length = 50, verbose_name = _('first name'), help_text = _('given name of the user (givenName)'))
	lastName = models.CharField(blank = False, max_length = 50, verbose_name = _('last name'), help_text = _('family name of the user (familyName)'))
	middleName = models.CharField(blank = True, max_length = 50, verbose_name = _('middle name'), help_text = _('middle name(s) of the user'))
	honorificPrefix = models.CharField(blank = True, max_length = 50, verbose_name = _('honorific prefix'), help_text = _('honorific prefix(es) of the user, or title in most Western languages'))
	honorificSuffix = models.CharField(blank = True, max_length = 50, verbose_name = _('honorific suffix'), help_text = _('honorific suffix(es) of the user'))
	title = models.CharField(blank = True, max_length = 100, verbose_name = _('title'), help_text = _('user\'s title, such as "Vice President'))
	displayName = models.CharField(blank = True, max_length = 250, verbose_name = _('display name'), help_text = _('name of the user, suitable for display to end users'))
	nickName = models.CharField(blank = True, max_length = 50, verbose_name = _('nickname'), help_text = _('casual way to address the user in real life'))
	profileUrl = models.URLField(blank = True, verbose_name = _('profile URL'), help_text = _("url of user's online profile (e.g. a web page)"))
	primaryPhone = models.CharField(blank = True, max_length = 100, verbose_name = _('primary phone'), help_text = _('primary phone number of user such as home number'))
	mobilePhone = models.CharField(blank = True, max_length = 100, verbose_name = _('mobile phone'), help_text = _('mobile phone number of user'))
	streetAddress = models.CharField(blank = True, max_length = 100, verbose_name = _('street address'), help_text = _("full street address component of user's address"))
	city = models.CharField(blank = True, max_length = 100, verbose_name = _('city'), help_text = _("city or locality component of user's address (locality)"))
	state = models.CharField(blank = True, max_length = 100, verbose_name = _('state'), help_text = _("state or region component of user's address (region)"))
	zipCode = models.CharField(blank = True, max_length = 100, verbose_name = _('ZIP code'), help_text = _("zipcode or postal code component of user's address (postalCode)"))
	countryCode = models.CharField(blank = True, max_length = 2, verbose_name = _('country code'), help_text = _("country name component of user's address (country)"))
	postalAddress = models.CharField(blank = True, max_length = 100, verbose_name = _('postal address'), help_text = _("mailing address component of user's address"))
	preferredLanguage = models.CharField(blank = True, max_length = 100, verbose_name = _('preferred language'), help_text = _("user's preferred written or spoken languages"))
	locale = models.CharField(blank = True, max_length = 5, verbose_name = _('locale'), help_text = _("user's default location for purposes of localizing items such as currency, date time format, numerical representations, etc."))
	timezone = models.CharField(blank = True, max_length = 100, verbose_name = _('time zone'), help_text = _("user's time zone"))
	userType = models.CharField(blank = True, max_length = 100, verbose_name = _('user type'), help_text = _('used to describe the organization to user relationship such as "Employee" or "Contractor"'))
	employeeNumber = models.CharField(blank = True, max_length = 100, verbose_name = _('employee number'), help_text = _('organization or company assigned unique identifier for the user'))
	costCenter = models.CharField(blank = True, max_length = 100, verbose_name = _('cost center'), help_text = _('name of a cost center assigned to user'))
	organization = models.CharField(blank = True, max_length = 100, verbose_name = _('organization'), help_text = _("name of user's organization"))
	division = models.CharField(blank = True, max_length = 100, verbose_name = _('division'), help_text = _("name of user's division"))
	department = models.CharField(blank = True, max_length = 100, verbose_name = _('department'), help_text = _("name of user's department"))
	managerId = models.CharField(blank = True, max_length = 100, verbose_name = _('manager ID'), help_text = _("id of a user's manager"))
	manager = models.CharField(blank = True, max_length = 100, verbose_name = _('manager'), help_text = _("displayName of the user's manager"))
	
	is_staff = models.BooleanField(default = False, verbose_name = _("staff status"), help_text=_("Designates whether the user can log into this admin site."))
	is_active = models.BooleanField(default = True, verbose_name = _("active"), help_text = _('Designates whether this user should be treated as active. \nUnselect this instead of deleting accounts.'))
	date_joined = models.DateTimeField(verbose_name = _("date joined"), default = timezone_utils.now)
	
	objects = OktaUserManager()
	
	EMAIL_FIELD = 'email'
	USERNAME_FIELD = 'login'
	REQUIRED_FIELDS = ['email', 'firstName', 'lastName']
	
	class Meta:
		verbose_name = _('okta user')
		verbose_name_plural = _('okta users')
		abstract = True
	
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


class OktaUser(AbstractOktaUser):
	'''Django user model
	Alternate user model for Django based on Okta profiles.
	'''
	
	class Meta(AbstractOktaUser.Meta):
		swappable = 'AUTH_USER_MODEL'
