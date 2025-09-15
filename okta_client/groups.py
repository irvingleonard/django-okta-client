"""
Logic for membership of Django Groups.
"""

from logging import getLogger

from django.contrib.auth.models import Group

from .signals.groups import group_created, user_joined_group, user_left_group
from .utils import report_signal_results

LOGGER = getLogger(__name__)


def join_group(user, group):
	"""Join a group
	Add a user to a group. Since the group system is not pluggable, any customization to it should be done elsewhere.

	:param user: the user instance
	:type user: object
	:param group: the group instance or something that can be used to retrieve it
	:type group: object|str
	"""

	if not isinstance(group, Group):
		group, created = Group.objects.get_or_create(name=group)
		if created:
			LOGGER.debug('Created new local group: %s', group)
			group_created.send(sender=group)
	LOGGER.debug('Group %s is getting a new member: %s', group, user)
	group.user_set.add(user)


def leave_group(user, group):
	"""Leave a group
	Removes the user from a group. Since the group system is not pluggable, any customization to it should be done elsewhere.

	:param user: the user instance
	:type user: object
	:param group: the group instance or something that can be used to retrieve it
	:type group: object|str
	"""

	if not isinstance(group, Group):
		try:
			group = Group.get(name=group)
		except Group.DoesNotExist:
			LOGGER.debug("Unexisting group %s couldn't lose user: %s", group, user)
			return

	LOGGER.debug('Group %s is losing a member: %s', group, user)
	group.user_set.remove(user)


def set_group_members(group, users):
	"""Replace the group members
	Since the group system is not pluggable, any customization to it should be done elsewhere.

	:param group: the group instance or the name (to create it)
	:type group: Group|str
	:param users: a list of user instances
	:type users: list[UserModel]
	"""

	if not isinstance(group, Group):
		group, created = Group.objects.get_or_create(name=group)
		if created:
			LOGGER.debug('Created new local group: %s', group)
			group_created.send_robust(sender=group)

	group.user_set.set(users)


def set_user_groups(user, groups):
	"""Replace the user groups
	Since the group system is not pluggable, any customization to it should be done elsewhere.

	:param user: the user instance
	:type user: object
	:param groups: a list of group instances or something that can be used to retrieve it
	:type groups: list[object|str]
	"""

	new_groups = {}
	for group in groups:
		if not isinstance(group, Group):
			group, created = Group.objects.get_or_create(name=group)
			if created:
				LOGGER.debug('Created new local group: %s', group)
				group_created.send_robust(sender=group)
		new_groups[group.name] = group

	LOGGER.debug('Updating groups for user: %s <- %s', user, new_groups.keys())
	user.groups.set(new_groups.values())
