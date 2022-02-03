from django.urls import path, include

from . import apps
from . import views

app_name = apps.OktaClientConfig.name

urlpatterns = [
	path('saml/', views.acs, name = 'acs'),
	path('login/', views.login_, name = 'login'),
	path('logout/', views.logout_, name = 'logout'),
]
