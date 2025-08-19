# django-okta-client
 
This project aims to integrate your Django site with Okta.

TLDR; using the [`Normalized Django settings system`](https://github.com/irvingleonard/devautotools?tab=readme-ov-file#normalized-django-settings-system) you'll leverage the `common_settings`function to simplify the configuration.
At least make your site's `settings.py` look like this:
```
from okta_client.settings import common_settings as okta_client_common_settings

global_state = globals()
global_state |= okta_client_common_settings(globals())
```
You should probably include the basic stuff too by doing instead:
```
from devautotools import django_common_settings
from okta_client.settings import common_settings as okta_client_common_settings

global_state = globals()
global_state |= okta_client_common_settings(globals(), parent_callables=[django_common_settings])
```
Your site's `urls.py` should start with:
```
urlpatterns += [
    path('', include('okta_client.urls')),
]
```
With any of that you'll have "everything" configured. You'll still have to provide values via environment which would enable the different things. Such environmental values would be:
```
EXPECTED_VALUES_FROM_ENV = {
	'OKTA_CLIENT_AUTH_SETTINGS_FROM_ENV': {
		'OKTA_CLIENT_PRIVATE_KEY',
		'OKTA_CLIENT_PRIVATE_KEY_BASE64',
		'OKTA_CLIENT_TOKEN',
	},
	'OKTA_CLIENT_OAUTH_SETTINGS_FROM_ENV': {
		'OKTA_CLIENT_ID',
		'OKTA_CLIENT_SCOPES',
	},
	'OKTA_CLIENT_SETTINGS_FROM_ENV' : {
		'OKTA_CLIENT_LOCAL_PATH',
		'OKTA_CLIENT_ORG_URL',
		'OKTA_DJANGO_STAFF_USER_GROUPS',
		'OKTA_DJANGO_SUPER_USER_GROUPS',
		'OKTA_SAML_ASSERTION_DOMAIN_URL',
		'OKTA_SAML_METADATA_AUTO_CONF_URL',
	},
}
```
The explanation of how each of those work is contained in the rest of this document. 

## Adding the app

You'll have to install it and add the app in your site's `settings.py`.
```
INSTALLED_APPS += [
	'okta_client',
]
```
(_`common_settings` adds this unconditionally_)

## User Authentication

One of the basic goals is to replace the builtin Django authentication system with Okta.

### User model

A custom user model that follows the [default Okta profile](https://developer.okta.com/docs/reference/api/users/#default-profile-properties) is available to replace the builtin [Django user model](https://docs.djangoproject.com/en/dev/ref/contrib/auth/#user-model). To use it, you should update your `settings.py` with:
```
AUTH_USER_MODEL = 'okta_client.OktaUser'
```
(_`common_settings` adds this unconditionally_)

This model uses the `login` attribute as the user id. It also requires the users to have: `email`, `firstName`, and `lastName`. You should enable the [API client](#api-client) or configure [SAML Assertion Attributes](#saml-assertion-attributes) to satisfy this requirement.

### Authentication backends

A federated authentication backend is provided to replace the [builtin Django backend](https://github.com/django/django/blob/main/django/contrib/auth/backends.py). To enable you'll need edit your `settings.py` and add:
```
AUTHENTICATION_BACKENDS = ['okta_client.auth_backends.OktaBackend']
```
(_`common_settings` adds this if there's any "Okta client" configured_)

You could add `django.contrib.auth.backends.ModelBackend` to the list (always after `OktaBackend`) if you want to keep supporting local accounts (with passwords). Keep in mind that `OktaBackend` is a federated authentication method, so it won't actually perform any local "authentication".

### SAML Federated Authentication

At this point you could add support for SAML authentication. To do so you'll need to expose the authentication endpoints by editing your site's `urls.py` and adding:
```
urlpatterns += [
    path('', include('okta_client.urls')),
]
```
(_`common_settings` can change the location of the app's views via `OKTA_CLIENT_LOCAL_PATH` which defaults to `okta_client`_)

This should be added as early as possible (near the top of the list in `urlpatterns`) to avoid other apps taking over the authentication process. This will take over the regular login process in Django so going forward it won't be possible to login with username and password following the regular way (there's still a way, with the [Noop configuration](#noop-configuration)).

After this you should register your app in Okta, with the URL pattern `https://yoursite.example/okta_client/acs/`. After that's done, take note of the `metadata autoconfiguration` URL found on the "Sign On" tab of your app in the Okta admin interface. Edit your `settings.py` and populate your `OKTA_CLIENT` setting:
```
OKTA_CLIENT = {
	'METADATA_AUTO_CONF_URL'	: 'https://yourdomain.okta.com/path/to/the/app/metadata',
	'ASSERTION_DOMAIN_URL'		: 'https//yoursite.example',
}
```
(_`common_settings` will pull these values from `OKTA_SAML_METADATA_AUTO_CONF_URL` and `OKTA_SAML_ASSERTION_DOMAIN_URL` and "declare an `Okta client configured`"_)

The `ASSERTION_DOMAIN_URL` is only required for HTTPS sites, it's not needed for unencrypted HTTP.

#### SAML Assertion Attributes

**_(If you plan to configure the [API client](#api-client) you should skip this section.)_**

You could map Okta user attributes to matching SAML attributes, which will be captured in Django's side and applied to the authenticating user. If you configure SAML attributes AND the API client, the LATER will take precedence.

#### Keeping password authentication too

**_(You should NOT do this on a production site!!)_**

You could add the Django Admin site which will keep its regular user & password login as a backup by adding another line to `urlpatterns`:
```
urlpatterns += [
    path('admin/', admin.site.urls),
]
```
Keep in mind that this WILL BECOME an attack vector in a production site so you shouldn't do it there, but it could be helpful for local development or test sites which are secured some other way.

### Noop configuration

If you perform all these steps but DO NOT create an `OKTA_CLIENT` setting then the app will wire the regular `django.contrib.auth.urls` to your site (use regular username & password authentication). A working SAML site requires the `xmlsec1` binary which is hard to get on Windows and macOS. In those cases (or any time you don't want to use SAML) you can use this effect to have a site that still works even if you don't have a functional SAML setup.

For the whole thing to work you'd have to have the `django.contrib.auth.backends.ModelBackend` added in the [Authentication backends](#authentication-backends) section. You'll also need to provide a `templates/registration/login.html` Django template in your **site's** directory. Such file could contain something like:
```
<h2>Login</h2>
<form method="post">
	{% csrf_token %}
	{{ form.as_p }}
	<button type="submit">Login</button>
</form>
```
For this template to be found, you'll need to configure your `settings.py` to contain something along the lines:
```
from pathlib import Path

# ...

SITE_DIR = Path(__file__).parent

# ...

TEMPLATES[0]['DIRS'].append((SITE_DIR / 'templates').resolve(strict=True))
```
The latest is the critical line, but it requires the other 2 to be complete (to actually work). These 3 lines shouldn't probably be together in your `settings.py` file. You should follow better code styles: first line goes with your imports, second with your constants, third could go in any point after your `from .settings import *` (if you're expanding `settings.py`) or after `TEMPLATES = ...` if you have everything in a single file (assuming your first template system is `django.template.backends.django.DjangoTemplates` otherwise change the `0` to match).

You'll also need a user with a password to login. Since Okta users have no passwords set, the easiest way to use this it to create a superuser with a password when setting up the site.

## API Client

You can connect your site to the Okta API to have more data available.

### API authentication

The client has 2 ways to connect to Okta's API. If both methods are configured together only the OAuth2 one will be used.

#### Using OAuth2

The OAuth2 connection requires the setup of a "Client Application" in the Okta admin with the permissions/scopes that you intend to use. Then you'll need to generate a key. With those details then you'll populate your `settings.py` with:
```
OKTA_CLIENT = {
	'ORG_URL'           : 'https://yourdomain.okta.com',
	'API_CLIENT_ID'     : 'some_random_string',
	'API_PRIVATE_KEY'   : 'super_secret_super_random_super_long_string',
	'API_SCOPES'        : 'comma,separated,list,of,scopes',
}
```
(_`common_settings` will pull these values from `OKTA_SAML_METADATA_AUTO_CONF_URL`/`OKTA_CLIENT_ORG_URL`, `OKTA_CLIENT_ID`, `OKTA_CLIENT_PRIVATE_KEY`/`OKTA_CLIENT_PRIVATE_KEY_BASE64`, and `OKTA_CLIENT_SCOPES` and "declare an `Okta client configured`"_)

The scopes would be from [this list](https://developer.okta.com/docs/api/oauth2/).

#### Using an API token

The API token connection requires the generation of such token in the admin console. Then you'll need to populate your `settings.py` with:
```
OKTA_CLIENT = {
	'ORG_URL'   : 'https://yourdomain.okta.com',
	'API_TOKEN' : 'super_secret_super_random_super_long_string',
}
```
(_`common_settings` will pull these values from `OKTA_SAML_METADATA_AUTO_CONF_URL`/`OKTA_CLIENT_ORG_URL` and `OKTA_CLIENT_TOKEN` and "declare an `Okta client configured`"_)

### User details via API

Just by configuring the API client you'll enable the auto-population of user details during the authentication process. Every attribute in the Okta directory will be copied over to the Django entry. The group membership will also be copied, and missing groups will be created.

### Group based authorization

You could use Okta groups to set access levels in Django. You can provide a list of groups whose membership will promote the user to "admin" and another list of groups to signal "staff". The associated entries in your `settings.py` would be:
```
OKTA_CLIENT = {
	'SUPER_USER_GROUPS' : ['Administrators', 'MySecretAdmins'],
	'STAFF_USER_GROUPS' : ['PowerUsers'],
}
```
(_`common_settings` will pull these values from `OKTA_DJANGO_SUPER_USER_GROUPS` and `OKTA_DJANGO_STAFF_USER_GROUPS` as comma separated lists_)

Keep in mind that neither of this is about access: the access to the app is controlled in the Okta side, your Django app effectively transferred the authentication to Okta (assuming SAML is configured). With these you can control the associated attributes/flags which in turn affect the permissions in the Django Admin site. You could also create custom permissions based on this attributes, of course. 

## Devautotools

This app leverages the [devautotools](https://pypi.org/project/devautotools/) module.

### Local deployments

The main goal of the module is to help with local deployments which includes Django sites. To create a deployment you'll want to aggregate your configuration settings into a JSON file, called `conf/my_settings.json` for the illustration purposes. Then you'll need an installed version of `devautotools` running "somewhere else". Part of the process consists on re-creating the local virtual environment, so you can't run it from there. A simple solution could be:
```
python3 -m venv ~/venv
~/venv/bin/python -m pip install --upgrade pip
~/venv/bin/pip install devautotools
```
The Windows version would instead use `~/venv/Scripts/python.exe` and `~/venv/Scripts/pip.exe`.

Assuming the previous arrangement, to deploy a local dev version of the app in a site you'll run:
```
 ~/venv/bin/python -m devautotools deploy_local_django_site --extra_paths_to_link templates  --superuser_password SuperSecretThing conf/my_settings.json
```
This will re-create the virtual environment, install all the dependencies (all of them, all the optional sections, be careful with what you put in `pyproject.toml`), setup a linked Django `test_site`, run the migrations, and start the test server. You'll get a command to get the test server up again without having to go over all the deployment again.
