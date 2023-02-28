# django-okta-client
 
This project aims to transform Django into a full SAML service provider targeting Okta. The builtin User model gets replaced with a custom model equivalent to the [default Okta profile](https://developer.okta.com/docs/reference/api/users/#default-profile-properties)

## Using it

1. The first step would be to install the module. You probably want to add it to the *requirements* file for your site.

2. Configure the intended app in Okta: `okta_client`. Some attribute statements are required: `email`, `firstName`, and `lastName`. Any other attribute from the default Okta profile will be applied to the user in Django.

3. You'll need to add some values to your Django configuration, mainly [AUTH_USER_MODEL](https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-AUTH_USER_MODEL) and *OKTA_CLIENT*. A minimal configuration would look like:
```
INSTALLED_APPS += [
	'okta_client',
]

AUTH_USER_MODEL = 'okta_client.OktaUser'
OKTA_CLIENT = {'METADATA_AUTO_CONF_URL' : 'https://yourdomain.okta.com/path/to/the/app/metadata'}

```
You might want to configure other settings too. The `settings.py` file included in the root of the project can be used as a reference of suggested settings.

## Local deployment

You can run a local instance of the Django app, which won't support SAML authentication, by running the provided script `deploy_fresh_test_site.sh` and following the instructions that it will give you. This solution would allow you to iterate really quick, by using Django's builtin reloader.

There's a way to leverage [Docker](https://www.docker.com/) to run the app, in which case SAML authentication will be supported. You can accomplish it by running `env OKTA_METADATA=https://your-domain.okta.com/app/your-app-id/sso/saml/metadata ./start_local_container.sh`; remember to use a valid URL, where `your-domain` and `your-app-id` are replaced with real values. Such app would have to be configured with `SSO URL=http://localhost:8080/accounts/saml`. You could also run it without the SAML support by simply running `./start_local_container.sh` if you need it for whatever reason. This solution would take some time to get anything up and running and you'll need to run `stop_local_container.sh` before trying to `./start_local_container.sh` again.
