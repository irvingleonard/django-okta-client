#python
"""

"""

from django.contrib import admin
from django.urls import path, include

from okta_client import views

urlpatterns = [
    path('', include('okta_client.urls')),
    path('admin/', admin.site.urls),
    path('', views.IndexView.as_view()),
]

