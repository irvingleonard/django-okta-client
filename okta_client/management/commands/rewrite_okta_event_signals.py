#!python3
"""
Custom command to rewrite the okta_client.signals.events file with an updated list from Okta's documentation. It expects a CSV file, which is usually published by Okta.
"""

from csv import reader as csv_reader
from importlib import import_module
from logging import getLogger
from pathlib import Path
from urllib.request import urlopen

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template

DEFAULT_CSV_URL = 'https://developer.okta.com/docs/okta-event-types.csv'
DEFAULT_HOOK_ELIGIBLE_TAG = 'event-hook-eligible'
DEFAULT_HEADERS = ('Event Type', 'Description', 'Tags')
DEFAULT_OKTA_EVENT_MODULE = 'okta_client.signals.events'
LOGGER = getLogger(__name__)
SIGNALS_EVENTS_FILE_TEMPLATE = 'okta-client/signals_events.py-template'

class Command(BaseCommand):
	"""
	The custom command
	"""

	help = "Rewrites the module with the Okta event hook signals"

	def add_arguments(self, parser):
		"""
		Adding some optional user parameters
		"""

		parser.add_argument('--csv-url', default=DEFAULT_CSV_URL, help=f'The URL to the CSV file with all the Okta event types; defaults to {DEFAULT_CSV_URL}')
		parser.add_argument('--hook-eligible-tag', default=DEFAULT_HOOK_ELIGIBLE_TAG, help=f'The tag to filter event types by; defaults to "{DEFAULT_HOOK_ELIGIBLE_TAG}"')
		parser.add_argument('--event-type-header', default=DEFAULT_HEADERS[0], help=f'The tag to filter event types by; defaults to "{DEFAULT_HEADERS[0]}"')
		parser.add_argument('--description-header', default=DEFAULT_HEADERS[1], help=f'The tag to filter event types by; defaults to "{DEFAULT_HEADERS[1]}"')
		parser.add_argument('--tags-header', default=DEFAULT_HEADERS[2], help=f'The tag to filter event types by; defaults to "{DEFAULT_HEADERS[2]}"')
		parser.add_argument('--target-module', default=DEFAULT_OKTA_EVENT_MODULE, help=f'The module whose file will be rewritten with the result; defaults to "{DEFAULT_OKTA_EVENT_MODULE}"')

	def handle(self, *args, **options):
		"""Actual command behavior
		It performs some steps to accomplish its goals:
		1. retrieves the CSV file from the supplied URL
		2. uses Python's builtin csv parser to ingest it
		3. creates a map of columns based on the header (1st line of the file) and the supplied options
		4. filter rows based on the "--tags-header" and "--hook-eligible-tag" (the "tags" column should be a comma separated list)
		5. builds a dict with the filtered rows using "--event-type-header" column (with the "." replaced by "_") for the keys and "--description-header" column for the values
		6. uses the SIGNALS_EVENTS_FILE_TEMPLATE with the dict from #5 to generate the new file content
		7. Writes the content to the file in events.__file__
		"""

		try:
			with urlopen(options['csv_url']) as response:
				csv_content = csv_reader((line_.decode() for line_ in response.readlines()))
		except Exception:
			raise CommandError(f"Couldn't load the Okta event types CSV file correctly: {options['csv_url']}")

		csv_header, hookable_event_types = None, {}
		column_map = [None, None, None]
		for row in csv_content:
			if csv_header is None:
				for column_number in range(len(row)):
					if row[column_number] == options['tags_header']:
						column_map[0] = column_number
					elif row[column_number] == options['event_type_header']:
						column_map[1] = column_number
					elif row[column_number] == options['description_header']:
						column_map[2] = column_number
				csv_header = row
				if None in column_map:
					expected_haders = (options['tags_header'], options['event_type_header'], options['description_header'])
					raise CommandError(f"Missing requested columns: {[expected_haders[header_index] for header_index in range(len(expected_haders)) if column_map[header_index] is None]}")
				continue

			current_tags = [tag.strip() for tag in row[column_map[0]].split(',')]
			if options['hook_eligible_tag'] in current_tags:
				hookable_event_types[row[column_map[1]].replace('.','_')] = row[column_map[2]]

		try:
			template = get_template(SIGNALS_EVENTS_FILE_TEMPLATE)
			content = template.render({'signals': hookable_event_types})
		except Exception:
			raise CommandError(f"Couldn't render the template: {SIGNALS_EVENTS_FILE_TEMPLATE}")
		
		try:
			target_module = import_module(options['target_module'])
		except ImportError:
			raise CommandError(f'Not a valid output module: {options['target_module']}')
		
		target_file = Path(target_module.__file__)
		try:
			target_file.write_text(content)
		except Exception:
			raise CommandError(f"Couldn't write to the target file: {target_file}")

		self.stdout.write(self.style.SUCCESS(f'Successfully rewritten OKTA event signals. Total : {len(hookable_event_types)}'))
