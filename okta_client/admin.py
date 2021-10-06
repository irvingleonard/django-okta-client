from django.contrib import admin

from .models import OktaUser


class OktaUserAdmin(admin.ModelAdmin):
	'''User admin
	Customized user admin for Okta users.
	'''
	
	fieldsets = (
		('Basic Info',		{'fields': ('login', 'firstName', 'lastName', 'email')}),
		('Names',			{'fields': ('displayName', 'honorificPrefix', 'middleName', 'honorificSuffix', 'nickName')}),
		('Contact Info',	{'fields': ('primaryPhone', 'mobilePhone', 'profileUrl', 'secondEmail')}),
		('Organization',	{'fields': ('organization', 'division', 'department', 'title', 'userType', 'employeeNumber', 'costCenter', 'managerId', 'manager')}),
		('Addresses',		{'fields': ('streetAddress', 'city', 'state', 'zipCode', 'countryCode', 'postalAddress')}),
		('International',	{'fields': ('locale', 'preferredLanguage', 'timezone')}),
		('Permissions',		{'fields': ('is_staff', 'is_superuser', 'is_active')}),
	)
	list_display = ('login', 'firstName', 'lastName', 'email', 'is_staff', 'is_superuser', 'is_active')
	list_filter = ('is_active', 'userType', 'organization', 'division', 'department', 'title', 'managerId')
	ordering = ('login',)
	search_fields = ('login', 'firstName', 'lastName', 'email')
	
	def save_model(self, request, obj, form, change):
		
		if change:
			return super().save_model(request, obj, form, change)
		else:
			return type(obj).objects.create_user(**form.cleaned_data)


admin.site.register(OktaUser, OktaUserAdmin)
