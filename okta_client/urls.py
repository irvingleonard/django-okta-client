#python
"""

"""

from django.urls import path

from . import views

app_name = 'okta-client'

urlpatterns = [
	path('saml/', views.acs, name='acs'),
	path('login/', views.login_view, name='login'),
	path('logout/', views.logout_view, name='logout'),
]
