"""
Utility functions
"""

from logging import getLogger

LOGGER = getLogger(__name__)


def report_signal_results(results, signal_text):
	"""Report signal results
	To process the result of sending signals that expect no return.
	"""

	for handler, result in results:
		handler = '.'.join((handler.__module__, handler.__name__))
		if isinstance(result, Exception):
			LOGGER.error(f'Handler "%s" experienced an error while processing the "{signal_text}" signal: %s', handler, result)
		elif result:
			LOGGER.warning(f'Handler "%s" returned a value while processing the "{signal_text}" signal. The calling code does not expect an answer, discarding: %s', handler, result)
		else:
			LOGGER.debug(f'Handler "%s" completed successfully the processing of the "{signal_text}" signal.', handler)
