"""Local signal handlers
These are available to be called before the respective signals are triggered.
"""

from logging import getLogger

from django.contrib.auth import get_user_model

LOGGER = getLogger(__name__)

UserModel = get_user_model()


async def update_user_from_okta(request, event):
	"""Update user from Okta
	An adaptor from the signal handling code to the UserModel manager's "get_user".
	"""

	for target in event['target']:
		await UserModel.objects.get_okta_updated(login=target['alternateId'], update_groups=False)
