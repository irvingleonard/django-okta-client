#!/bin/sh

# Recreate virtual environment and install site dependencies
rm -rfv ./venv
(set -x; python3 -m venv venv)
./venv/bin/pip install --upgrade pip
./venv/bin/pip install --upgrade setuptools wheel
./venv/bin/pip install --upgrade django pysaml2

# Create site structure
rm -rfv ./test_site
(set -x; ./venv/bin/django-admin startproject test_site)
(set -x; ln -s ../okta_client ./test_site/okta_client)
(set -x; rm -fv ./test_site/test_site/urls.py && ln -s ../../urls.py ./test_site/test_site/urls.py)
(set -x; ln -s ../../settings.py ./test_site/test_site/local_settings.py)

# DB handling
(set -x; ./venv/bin/python ./test_site/manage.py migrate --settings=test_site.local_settings)

# Create super user
export DJANGO_SUPERUSER_LOGIN=`whoami`
export DJANGO_SUPERUSER_FIRSTNAME="$DJANGO_SUPERUSER_LOGIN"
export DJANGO_SUPERUSER_LASTNAME="$DJANGO_SUPERUSER_LOGIN"
export DJANGO_SUPERUSER_EMAIL="$DJANGO_SUPERUSER_LOGIN@invalid.local"
export DJANGO_SUPERUSER_PASSWORD="My sup3r p4ssw0rd!"
echo $DJANGO_SUPERUSER_PASSWORD | ./venv/bin/python ./test_site/manage.py createsuperuser --noinput --settings=test_site.local_settings

echo "Now run with:

env DJANGO_DEBUG=true ./venv/bin/python ./test_site/manage.py runserver --settings=test_site.local_settings

Then go to http://localhost:8000/admin and use credentials $DJANGO_SUPERUSER_LOGIN:\"$DJANGO_SUPERUSER_PASSWORD\"
"
