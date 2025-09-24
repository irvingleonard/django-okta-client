FROM python:3

#Debug & logging settings
ARG DJANGO_DEBUG
ARG DJANGO_LOG_LEVEL

#Database settings
ARG DJANGO_DATABASE_ENGINE
ARG DJANGO_DATABASE_HOST
ARG DJANGO_DATABASE_PORT
ARG DJANGO_DATABASE_OPTIONS_sslmode
ARG DJANGO_DATABASE_OPTIONS_sslrootcert_base64
ARG DJANGO_DATABASE_OPTIONS_sslcert_base64
ARG DJANGO_DATABASE_OPTIONS_sslkey_base64
ARG DJANGO_DATABASE_USER
ARG DJANGO_DATABASE_PASSWORD
ARG DJANGO_DATABASE_NAME

#Okta SAML settings
ARG OKTA_SAML_METADATA_AUTO_CONF_URL
ARG OKTA_SAML_ASSERTION_DOMAIN_URL

#Okta API settings
ARG OKTA_CLIENT_ORG_URL
ARG OKTA_CLIENT_ID
ARG OKTA_CLIENT_SCOPES
ARG OKTA_CLIENT_PRIVATE_KEY_BASE64
ARG OKTA_CLIENT_TOKEN

#Group based attributes
ARG OKTA_DJANGO_STAFF_USER_GROUPS
ARG OKTA_DJANGO_SUPER_USER_GROUPS

#Update base system and install packages
RUN apt-get update
RUN apt-get --assume-yes upgrade
RUN apt-get --assume-yes install xmlsec1 python3-dev build-essential

# Create a virtualenv for dependencies. This isolates these packages from system-level packages.
RUN python3 -m venv /env

# Setting these environment variables are the same as running source /env/bin/activate.
# ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

# Upgrade the virtual environment
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel build

# Build the app into a wheel and install wheels
RUN mkdir /source
COPY /okta_client /source/okta_client
COPY pyproject.toml requirements.txt setup.py /source/
WORKDIR /source
RUN pip install --requirement requirements.txt --extra-index-url https://test.pypi.org/simple
RUN python -m build
RUN pip install --no-index --find-links=./dist django-okta-client

# Deploy the Django site
RUN mkdir /app
WORKDIR /app
RUN django-admin startproject test_site /app/
COPY settings.py /app/test_site/local_settings.py
COPY urls.py /app/test_site/urls.py
COPY templates /app/test_site/templates
RUN mkdir --parents storage/staticfiles
RUN python /app/manage.py collectstatic --settings=test_site.local_settings

# Migrate the models
RUN python manage.py migrate --settings=test_site.local_settings

# Create a superuser, for the admin site
#RUN python /app/manage.py createsuperuser --no-input --settings=test_site.local_settings

# Run the test server to serve the application (not for production).
ENTRYPOINT python /app/manage.py runserver --settings=test_site.local_settings 0.0.0.0:$PORT
