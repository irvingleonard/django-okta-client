#! python
'''Okta client Django app
This app adapts your Django site as a service provider to work with Okta SAML authentication.

It defines a custom AUTH_USER_MODEL based on the Okta API User object and it has an optional authentication backend that connects to the Okta API and synchronizes the users and groups on login.

There's also a mixin to handle Okta Event Hooks in your views easily.

TODO:
- Everything

Refs:
- ?
'''

__version__ = '0.4.1'
