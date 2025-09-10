"""
Logic for membership of Django Groups.
"""

from logging import getLogger

from django.contrib.auth.models import Group

LOGGER = getLogger(__name__)


def group_add(group, user):
	"""Add the user to a group
	Since the group system is not pluggable, any customization to it should be done elsewhere.

	:param group: the group instance or something that can be used to retrieve it
	:type group: object|str
	:param user: the user instance
	:type user: object
	"""

	if not isinstance(group, Group):
		group = Group.objects.get_or_create(name=group)
	LOGGER.debug('Group %s is getting a new member: %s', group, user)
	group.user_set.add(user)


def group_remove(group, user):
	"""Removes the user from a group
	Since the group system is not pluggable, any customization to it should be done elsewhere.

	:param group: the group instance or something that can be used to retrieve it
	:type group: object|str
	:param user: the user instance
	:type user: object
	"""

	if not isinstance(group, Group):
		try:
			group = Group.get(name=group)
		except Group.DoesNotExist:
			LOGGER.debug("Unexisting group %s couldn't lose user: %s", group, user)
			return

	LOGGER.debug('Group %s is losing a member: %s', group, user)
	group.user_set.remove(user)