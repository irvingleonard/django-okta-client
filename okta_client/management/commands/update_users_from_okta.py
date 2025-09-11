#!python3
"""
Custom command to update the local users by pulling the details via Okta API.
"""

from logging import getLogger

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

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

	def handle(self, *args, **options):
		"""Actual command behavior
		If a list of "users" is provided, only those will be updated; otherwise all of them will.
		"""

		api_client = OktaAPIClient()

		try:
			api_client.ping_users_endpoint()
		except AttributeError:
			raise CommandError("The API client doesn't seem to be configured")
		except OktaAPIException as error_:
			raise CommandError(f'There seems to be an issue with the Okta configuration; attempting to access the list of users yield: {error_}')
		self.stdout.write('The Okta client is configured and functional')

		success_count, failures = 0, []
		if ('users' in options) and options['users']:
			self.stdout.write(f"Updating {len(options['users'])} users")
			for user in options['users']:
				try:
					UserModel.objects.get_user(user)
				except ValueError:
					failures.append(user)
				else:
					success_count += 1
		else:
			success_count = len(UserModel.objects.update_all())

		if failures:
			self.stdout.write(self.style.ERROR(f"Failed to update {len(failures)} users: {', '.join(failures)}"))
			if success_count:
				self.stdout.write(f'The other {success_count} users were updated')
			else:
				self.stdout.write(self.style.WARNING('No users were updated'))
		else:
			self.stdout.write(self.style.SUCCESS(f'Successfully updated {success_count} users'))
