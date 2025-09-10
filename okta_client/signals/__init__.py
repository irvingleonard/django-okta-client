#python
"""
This module defines Django signals related to Okta events.
"""

from logging import getLogger

from django.dispatch import Signal

LOGGER = getLogger(__name__)

group_created = Signal()
user_joined_group = Signal()
user_left_group = Signal()

okta_event_hook = Signal()
