from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from okta_client import views

urlpatterns = [
    path('accounts/', include('okta_client.urls') if hasattr(settings, 'OKTA_CLIENT') else include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('', views.index),
]

