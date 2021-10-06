# django-okta-client
 
This project aims to transform Django into a full SAML service provider targeting Okta. The builtin User model gets replaced with a custom model equivalent to the [default Okta profile](https://developer.okta.com/docs/reference/api/users/#default-profile-properties)

## Using it

1. The first step would be to install the module. You probably want to add it to the *requirements* file for your site.

2. Configure the intended app in Okta. Some attribute statements are required: `email`, `firstName`, and `lastName`. Any other attribute from the default Okta profile will be applied to the user in Django.

3. You'll need to add some values to your Django configuration, mainly [AUTH_USER_MODEL](https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-AUTH_USER_MODEL) and *OKTA_CLIENT*. A minimal configuration would look like:
```
INSTALLED_APPS += [
	'okta_client.apps.OktaClientConfig',
]

AUTH_USER_MODEL = 'okta_client.OktaUser'
OKTA_CLIENT = 'METADATA_AUTO_CONF_URL'	: 'https://yourdomain.okta.com/path/to/the/app/metadata'}

```
You might want to configure other settings too. The `settings.py` file included in the root of the project can be used as a reference of suggested settings.
