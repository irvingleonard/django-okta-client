from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('accounts/', include('okta_client.urls')),
    path('admin/', admin.site.urls),
    path('', admin.site.urls),
]
