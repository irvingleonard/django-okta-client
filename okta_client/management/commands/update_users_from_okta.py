#!python3
"""
Custom command to update the local users by pulling the details via Okta API.
"""

from logging import getLogger

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from asgiref.sync import async_to_sync
from okta.exceptions.exceptions import OktaAPIException

from ...api_client import OktaAPIClient

LOGGER = getLogger(__name__)

UserModel = get_user_model()


class Command(BaseCommand):
	"""
	The custom command
	"""

	help = "Update local users by pulling the details via Okta API"

	def add_arguments(self, parser):
		"""
		Adding some optional parameters
		"""

		parser.add_argument('--users', action='extend', nargs='+', help="A list of users that you'd like to update")
		parser.add_argument('--no-deprovisioned', action='store_true', help="Don't update deprovisioned users (when updating all users)")
		parser.add_argument('--no-groups', action='store_true', help="Don't update groups")

	def handle(self, *args, **options):
		"""Actual command behavior
		If a list of "users" is provided, only those will be updated; otherwise all of them will.
		"""

		api_client = OktaAPIClient()

		try:
			async_to_sync(api_client.ping_users_endpoint)(required=True)
		except (AttributeError, KeyError):
			raise CommandError("The API client doesn't seem to be configured")
		except OktaAPIException as error_:
			raise CommandError(f'There seems to be an issue with the Okta configuration; attempting to access the list of users yield: {error_}')
		self.stdout.write('The Okta client is configured and functional')

		success_count, group_count, failures = 0, 0, []
		if ('users' in options) and options['users']:
			self.stdout.write(f"Updating {len(options['users'])} users")
			groups = set()
			for user in options['users']:
				try:
					user = UserModel.objects.get(login=user)
				except UserModel.DoesNotExist:
					failures.append(user)
					continue
				async_to_sync(user.update_from_okta)(force_update=True)
				success_count += 1
				if not options['no_groups']:
					async_to_sync(user.set_groups_from_okta)()
					groups |= frozenset([group.name for group in user.groups.all()])
			group_count = len(groups)
		else:
			success_count, group_count = async_to_sync(UserModel.objects.update_all_from_okta)(include_deprovisioned=not options['no_deprovisioned'], include_groups=not options['no_groups'], show_progress=True)

		if failures:
			self.stdout.write(self.style.ERROR(f"Failed to update {len(failures)} users: {', '.join(failures)}"))
			if success_count:
				self.stdout.write(f'The other {success_count} users were updated')
			else:
				self.stdout.write(self.style.WARNING('No users were updated'))
		else:
			self.stdout.write(self.style.SUCCESS(f'Successfully updated {success_count} users'))

		if group_count:
			self.stdout.write(self.style.NOTICE(f'Updated {group_count} groups from Okta with unknown results (check the output for errors)'))
		else:
			self.stdout.write(self.style.NOTICE('No groups were updated'))
