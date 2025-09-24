#python
"""
Okta authentication backend for Django.
"""

from logging import getLogger

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import RemoteUserBackend

from asgiref.sync import async_to_sync
from rest_framework.authentication import TokenAuthentication as DjangoRESTTokenAuthentication

from .api_client import OktaAPIClient
from .groups import set_user_groups

LOGGER = getLogger(__name__)
UserModel = get_user_model()


class OktaSAMLBackend(RemoteUserBackend):
	"""Okta auth backend
	Include Okta related specifics to the authentication process.
	"""
	
	create_unknown_user = True

	def __getattr__(self, name):
		"""Lazy instantiation
		It provides a mechanism for lazy instantiation of the Okta API client and some other things.

		:param name: The name of the attribute being accessed.
		:type name: str
		:returns: the attribute value
		"""

		if name == '_api_client':
			value = OktaAPIClient()
		else:
			return getattr(super(), name)
		self.__setattr__(name, value)
		return value

	def authenticate(self, request, login, **saml_attributes):
		"""Authenticate user
		Use the provided login to create a local account. It will try to update the attributes and group membership from Okta if the API client is configured. It will apply the SAML attributes if present. Since this is part of the SAML authentication, it will never return None, it will always create the local user matching the provided "login", since "create_unknown_user" is set to True.

		:param request: the request object, unused so far
		:type request: DjangoHTTPRequest
		:param login: the user login to "authenticate"
		:type login: str
		:param saml_attributes: the SAML attributes, if any
		:type saml_attributes: dict
		:return: the authenticated user
		:rtype: UserModel
		"""

		user = super().authenticate(request, login)
		if saml_attributes:
			groups = saml_attributes.pop('groups', [])
			LOGGER.debug('Updating user with SAML attributes: %s <- %s', login, saml_attributes)
			user.update(saml_attributes)
			user.save()
			if groups:
				set_user_groups(user, groups)
		return user

	async def aconfigure_user(self, request, user, created=True):
		"""Asynchronously configure the user
		User attributes and group membership are updated from Okta. It will only do so if the Users API endpoint is available and the user is outdated.

		:param request: the request object, not used so far
		:type request: DjangoHTTPRequest
		:param user: the user to configure
		:type user: UserModel
		:param created: if the "authenticate" method created the local record
		:type created: bool
		:return: the configured user
		:rtype: UserModel
		"""

		if user.is_outdated and await self._api_client.ping_users_endpoint():
			await user.update_from_okta()
			await user.set_groups_from_okta()
		return user

	def configure_user(self, request, user, created=True):
		"""Configure the user
		Just an adapter to the asynchronous version of this method.

		:param request: the request object, not used so far
		:type request: DjangoHTTPRequest
		:param user: the user to configure
		:type user: UserModel
		:param created: if the "authenticate" method created the local record
		:type created: bool
		:return: the configured user
		:rtype: UserModel
		"""

		return async_to_sync(self.aconfigure_user)(request=request, user=user, created=created)

	def user_can_authenticate(self, remote_user):
		"""Returns whether the user is allowed to authenticate
		This backend should be used with SAML, which is a federated authentication scheme, so there shouldn't be a local permission check for authentication.

		:param remote_user: the user to check for
		:type remote_user: str
		:return: always True
		:rtype: bool
		"""

		return True


class DjangoRESTBearerTokenAuthentication(DjangoRESTTokenAuthentication):
	"""Token authentication for REST
	Like the builtin rest_framework.authentication.TokenAuthentication method but using the "Bearer" word instead of the default "Token" (it simplifies the compatibility with Postman)
	"""

	keyword = 'Bearer'