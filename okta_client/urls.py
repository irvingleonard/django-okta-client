#python
"""
URL patterns for the Okta client application.
"""

from django.conf import settings
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'okta-client'

if hasattr(settings, 'OKTA_CLIENT') and ('SAML' in settings.OKTA_CLIENT):
	urlpatterns = [
		path('accounts/login/', views.LoginView.as_view(), name='login'),
		path('accounts/logout/', views.LogoutView.as_view(), name='logout'),
		path(f'{settings.OKTA_CLIENT_LOCAL_PATH}/acs/', csrf_exempt(views.ACSView.as_view()), name='acs'),
	]
else:
	urlpatterns = [
		path('accounts/', include('django.contrib.auth.urls')),
	]

urlpatterns += [
	path(f'{settings.OKTA_CLIENT_LOCAL_PATH}/event-hooks/', views.OktaEventHooks.as_view(), name='event-hooks'),
]
