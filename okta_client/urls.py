#python
"""

"""

from django.conf import settings
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'okta-client'

if hasattr(settings, 'OKTA_CLIENT'):
	urlpatterns = [
		path('accounts/login/', views.LoginView.as_view(), name='login'),
		path('accounts/logout/', views.LogoutView.as_view(), name='logout'),
		path('accounts/saml/', csrf_exempt(views.LoginView.as_view()), name='acs'),
		path('api/okta_event_hooks/', views.OktaEventHooks.as_view(), name='event_hooks'),
	]
else:
	urlpatterns = [
		path('accounts/', include('django.contrib.auth.urls')),
	]
