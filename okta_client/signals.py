#python
"""

"""

from logging import getLogger

from django.dispatch import Signal

LOGGER = getLogger(__name__)

okta_event_hook = Signal()
