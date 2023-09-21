from django.urls import path, include

from . import views

app_name = 'okta-client'

urlpatterns = [
	path('saml/', views.acs, name = 'acs'),
	path('login/', views.login_, name = 'login'),
	path('logout/', views.logout_, name = 'logout'),
]
