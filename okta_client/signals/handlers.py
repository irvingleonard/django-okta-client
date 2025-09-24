"""
Signal handlers. Should be included in the app's "ready" method and that would be it.
"""

from logging import getLogger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .groups import user_joined_group, user_left_group
from ..utils import report_signal_results

LOGGER = getLogger(__name__)
UserModel = get_user_model()


@receiver(user_joined_group)
async def user_attribute_set_from_group(sender, **kwargs):
	"""User attribute from group join
	Use group join event to update the user's "is_superuser" and "is_staff" attributes.
	"""

	if not hasattr(settings, 'OKTA_CLIENT') or ('API' not in settings.OKTA_CLIENT):
		return

	if ((not kwargs['user'].is_superuser) or (not kwargs['user'].is_staff)) and ('SUPER_USER_GROUPS' in settings.OKTA_CLIENT['API']):
		if sender.name in settings.OKTA_CLIENT['API']['SUPER_USER_GROUPS']:
			LOGGER.debug('User "%s" is becoming a super user because of group membership: %s', kwargs['user'], sender.name)
			kwargs['user'].is_staff = True
			kwargs['user'].is_superuser = True
			await kwargs['user'].asave(update_fields=['is_staff', 'is_superuser'])
			return

	if not kwargs['user'].is_staff and ('STAFF_USER_GROUPS' in settings.OKTA_CLIENT['API']):
		if sender.name in settings.OKTA_CLIENT['API']['STAFF_USER_GROUPS']:
			LOGGER.debug('User "%s" is becoming a staff member because of group membership: %s', kwargs['user'], sender.name)
			kwargs['user'].is_staff = True
			await kwargs['user'].asave(update_fields=['is_staff'])


@receiver(user_left_group)
async def user_attribute_remove_from_group(sender, **kwargs):
	"""User attribute from group leave
	Use group leave event to update the user's "is_superuser" and "is_staff" attributes.
	"""

	if not hasattr(settings, 'OKTA_CLIENT') or ('API' not in settings.OKTA_CLIENT):
		return

	keep_staff = False
	if kwargs['user'].is_staff and ('STAFF_USER_GROUPS' in settings.OKTA_CLIENT['API']):
		if sender.name in settings.OKTA_CLIENT['API']['STAFF_USER_GROUPS']:
			current_groups = [user_group.name async for user_group in kwargs['user'].groups.all()]
			if frozenset(settings.OKTA_CLIENT['API']['SUPER_USER_GROUPS']) & frozenset(current_groups):
				keep_staff = True
			elif not kwargs['user'].is_superuser:
				LOGGER.debug('User "%s" is losing staff member status by leaving group: %s', kwargs['user'], sender.name)
				kwargs['user'].is_staff = False
				await kwargs['user'].asave(update_fields=['is_staff'])

	if (kwargs['user'].is_superuser or kwargs['user'].is_staff) and ('SUPER_USER_GROUPS' in settings.OKTA_CLIENT['API']):
		if sender.name in settings.OKTA_CLIENT['API']['SUPER_USER_GROUPS']:
			current_groups = [user_group.name async for user_group in kwargs['user'].groups.all()]
			if not (frozenset(settings.OKTA_CLIENT['API']['SUPER_USER_GROUPS']) & frozenset(current_groups)):
				LOGGER.debug('User "%s" is losing super user status by leaving group: %s', kwargs['user'], sender.name)
				kwargs['user'].is_staff = keep_staff
				kwargs['user'].is_superuser = False
				await kwargs['user'].asave(update_fields=['is_staff', 'is_superuser'])


@receiver(m2m_changed, sender=UserModel.groups.through)
async def signals_for_group_membership(sender, **kwargs):
	"""
	Trigger signals for group membership changes.
	"""

	results = []
	if kwargs['action'] == 'post_add':
		if kwargs['model'] is Group:
			groups = [await kwargs['model'].objects.aget(pk=pk) for pk in kwargs['pk_set']]
			for group in groups:
				results += await user_joined_group.asend_robust(sender=group, user=kwargs['instance'])
		elif kwargs['model'] is UserModel:
			users = [await kwargs['model'].objects.aget(pk=pk) for pk in kwargs['pk_set']]
			for user in users:
				results += await user_joined_group.asend_robust(sender=kwargs['instance'], user=user)
		else:
			LOGGER.error("Don't know how to handle user model to groups addition: %s", kwargs)

		# await sync_to_async(report_signal_results)(results, 'Group addition')

	elif kwargs['action'] == 'post_remove':
		if kwargs['model'] is Group:
			groups = [await kwargs['model'].objects.aget(pk=pk) for pk in kwargs['pk_set']]
			for group in groups:
				results += await user_left_group.asend_robust(sender=group, user=kwargs['instance'])
		elif kwargs['model'] is UserModel:
			users = [await kwargs['model'].objects.aget(pk=pk) for pk in kwargs['pk_set']]
			for user in users:
				results += await user_left_group.asend_robust(sender=kwargs['instance'], user=user)
		else:
			LOGGER.error("Don't know how to handle user model to groups removal: %s", kwargs)

		# await sync_to_async(report_signal_results)(results, 'Group removal')


