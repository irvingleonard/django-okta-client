#python
"""
This module defines Django signals related to Okta events.
"""

from logging import getLogger

from django.dispatch import Signal

LOGGER = getLogger(__name__)

okta_event_hook = Signal()
