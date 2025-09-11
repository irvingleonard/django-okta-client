"""

"""

from logging import getLogger

from django.contrib.admin import ModelAdmin

LOGGER = getLogger(__name__)


class OktaUserModelAdmin(ModelAdmin):
	"""User admin
	Customized user admin for Okta users.
	"""
	
	fieldsets = (
		('Basic Info', {'fields': ('login', 'firstName', 'lastName', 'email')}),
		('Names', {
			'classes': ('collapse',),
			'fields': ('displayName', 'honorificPrefix', 'middleName', 'honorificSuffix', 'nickName'),
		}),
		('Contact Info', {
			'classes': ('collapse',),
			'fields': ('primaryPhone', 'mobilePhone', 'profileUrl', 'secondEmail'),
		}),
		('Organization', {
			'classes': ('collapse',),
			'fields': ('organization', 'division', 'department', 'title', 'userType', 'employeeNumber', 'costCenter',
					   'managerId', 'manager'),
		}),
		('Addresses', {
			'classes': ('collapse',),
			'fields': ('streetAddress', 'city', 'state', 'zipCode', 'countryCode', 'postalAddress'),
		}),
		('International', {
			'classes': ('collapse',),
			'fields': ('locale', 'preferredLanguage', 'timezone'),
		}),
		('Okta Details', {
			'classes': ('collapse',),
			'fields': ('okta_id', 'okta_created', 'okta_activated', 'okta_status', 'okta_status_changed'),
		}),
		('Groups', {
			'classes': ('collapse',),
			'fields': ('groups',),
		}),
		('Permissions', {'fields': ('is_staff', 'is_superuser', 'is_active')}),
	)
	list_display = ('login', 'firstName', 'lastName', 'email', 'is_staff', 'is_superuser', 'is_active')
	list_filter = ('is_active', 'userType', 'organization', 'division', 'department', 'title', 'managerId')
	ordering = ('login',)
	search_fields = ('login', 'firstName', 'lastName', 'email')
	
	def save_model(self, request, obj, form, change):
		"""
		Save model
		"""
		
		if change:
			return super().save_model(request, obj, form, change)
		else:
			return type(obj).objects.create_user(**form.cleaned_data)
