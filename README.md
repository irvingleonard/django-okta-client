# django-okta-client
 
This project aims to transform Django into a full SAML service provider targeting Okta. The builtin User model gets replaced with a custom model equivalent to the [default Okta profile](https://developer.okta.com/docs/reference/api/users/#default-profile-properties) and there's a new auth backend included for cleaner SAML Federation.

## Using it

1. The first step would be to install the module. You probably want to add it to the *requirements* file for your site.

2. Configure the intended app in Okta: `okta_client`. Some attribute statements are required: `email`, `firstName`, and `lastName`. Any other attribute from the default Okta profile will be applied to the user in Django.

3. You'll need to add some values to your Django configuration, mainly [AUTH_USER_MODEL](https://docs.djangoproject.com/en/4.2/ref/settings/#auth-user-model), [AUTHENTICATION_BACKENDS](https://docs.djangoproject.com/en/4.2/ref/settings/#authentication-backends), and *OKTA_CLIENT*. A regular configuration would look like:
```
INSTALLED_APPS += [
	'okta_client',
]

AUTH_USER_MODEL = 'okta_client.OktaUser'
AUTHENTICATION_BACKENDS = ['okta_client.auth_backends.OktaBackend'] #You could add "django.contrib.auth.backends.ModelBackend" to the list (probably at the end) if you want to keep supporting local accounts (with passwords)
OKTA_CLIENT = {
	'METADATA_AUTO_CONF_URL'	: 'https://yourdomain.okta.com/path/to/the/app/metadata', # Found on the "Sign On" tab of your app in the Okta admin interface
	'ASSERTION_DOMAIN_URL'		: 'https://your-apps-domain.net', # Required for HTTPS sites, no needed for unencrypted HTTP
	'API_TOKEN'					: 'S0m3r4nd0mstr1ng0fch4r4ct3rs', # A secret generated on your Okta admin interface (Security -> API)
	'ADMIN_GROUPS'				: 'admins,bosses,others', # Comma separated list of Okta groups that would allow users to access the Django Admin site
}

```
The `settings.py` file included in the root of the project can be used as a reference of suggested settings.

## Local deployment

You can run a local instance of the Django app, which won't support SAML authentication (unless you're on linux or another OS with the `xmlsec1` binary available), by running the provided script `deploy_fresh_test_site.sh` and following the instructions that it will give you. This solution would allow you to iterate really quick, by using Django's builtin reloader.

There's a way to leverage [Docker](https://www.docker.com/) to run the app, in which case SAML authentication will be definitely supported. You can accomplish it by running `./venv/bin/python ./start_local_container.py path/to/your/secret/json`; where the JSON file will contain the value for the required settings. Such app would have to be configured with `SSO URL=http://localhost:8080/accounts/saml`. This solution would take some time to get anything up and running and you'll need to run `stop_local_container.sh` before trying to `./start_local_container.py` again.
