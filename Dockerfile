FROM python:3

ARG DJANGO_SUPERUSER_LOGIN
ARG DJANGO_SUPERUSER_FIRSTNAME
ARG DJANGO_SUPERUSER_LASTNAME
ARG DJANGO_SUPERUSER_EMAIL
ARG DJANGO_SUPERUSER_PASSWORD

RUN apt-get update
RUN apt-get --assume-yes upgrade
RUN apt-get --assume-yes install xmlsec1 python3-dev build-essential

# Create a virtualenv for dependencies. This isolates these packages from system-level packages.
RUN python3 -m venv /env

# Setting these environment variables are the same as running source /env/bin/activate.
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

# Upgrade the virtual environment
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel

# Build the app into a wheel and install wheels
RUN mkdir /source
COPY /okta_client /source/okta_client
COPY setup.py /source/
WORKDIR /source
RUN python3 setup.py bdist_wheel
RUN pip install /source/dist/django_okta_client-*.whl

# Deploy the Django site
RUN mkdir /app
RUN django-admin startproject container_site /app/
COPY settings.py /app/container_site/local_settings.py
COPY urls.py /app/container_site/urls.py
COPY site_templates /app/container_site/templates

# Migrate the models
RUN python3 /app/manage.py migrate --settings=container_site.local_settings

# Create a superuser, for the admin site
RUN python3 /app/manage.py createsuperuser --no-input --settings=container_site.local_settings

# Run the test server to serve the application (not for production).
ENTRYPOINT python3 /app/manage.py runserver --settings=container_site.local_settings 0.0.0.0:$PORT
