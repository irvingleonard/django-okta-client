#python
"""
Okta Client Admin
"""

from django.contrib.admin import site

from ..models import OktaUser
from .options import OktaUserModelAdmin


site.register(OktaUser, OktaUserModelAdmin)
