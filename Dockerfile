FROM python:3

RUN apt-get update
RUN apt-get --assume-yes install xmlsec1

# Create a virtualenv for dependencies. This isolates these packages from
# system-level packages.
# Use -p python3 or -p python3.7 to select python version. Default is version 2.
RUN python3 -m venv /env

# Setting these environment variables are the same as running
# source /env/bin/activate.
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

# Copy the application's requirements.txt and run pip to install all
# dependencies into the virtualenv.
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel

# Add the application source code.
# ADD . /app
COPY /dist/* /tmp/
RUN pip install --find-links /tmp/ django-okta-client

#Create the project directory and populate
RUN mkdir /app
RUN django-admin startproject container_site /app/
COPY settings.py /app/container_site/site_settings.py
COPY urls.py /app/container_site/urls.py

#Migrate the models
RUN env python /app/manage.py migrate --settings=container_site.site_settings

#Create a superuser, for the admin site
RUN env DJANGO_SUPERUSER_USERNAME=django_admin DJANGO_SUPERUSER_PASSWORD="Sup3rSecur3PW!" DJANGO_SUPERUSER_EMAIL="django_admin@example.com" DJANGO_SUPERUSER_LOGIN=django_admin DJANGO_SUPERUSER_FIRSTNAME=Django DJANGO_SUPERUSER_LASTNAME=Admin python3 /app/manage.py createsuperuser --no-input --settings=container_site.site_settings

# Run the test server to serve the application (not for production).
CMD env OKTA_METADATA=$OKTA_METADATA python3 /app/manage.py runserver --settings=container_site.site_settings 0.0.0.0:$PORT
