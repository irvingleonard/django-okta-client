#!/bin/sh

DEFAULT_SUPERUSER_PASSWORD="My sup3r p4ssw0rd!"
CURRENT_USER=`whoami`

die () {
	echo >&2 "$@"
	exit 1
}
[ "$#" -eq 1 ] || die "You must provide the path to the JSON secrets file"
[[ -f "$1" ]] || die "Can't find that file: $1"

# Recreate virtual environment and install site dependencies
rm -rfv ./venv
(set -x; python3 -m venv venv)
./venv/bin/pip install --upgrade pip
./venv/bin/pip install --upgrade tomli
./venv/bin/pip install --upgrade `./venv/bin/python -c "import tomli; tf = open('pyproject.toml', 'rb'); c = tomli.load(tf); print(' '.join(c['project']['dependencies']))"`
./venv/bin/pip install --upgrade `./venv/bin/python -c "import tomli; tf = open('pyproject.toml', 'rb'); c = tomli.load(tf); print(' '.join(c['build-system']['requires']))"`
./venv/bin/pip install --upgrade `./venv/bin/python -c "import tomli; tf = open('pyproject.toml', 'rb'); c = tomli.load(tf); print(' '.join(c['project']['optional-dependencies']['dev']))"`

# Create site structure
rm -rfv ./test_site
(set -x; ./venv/bin/django-admin startproject test_site)
(set -x; ln -s ../okta_client ./test_site/okta_client)
(set -x; ln -s ../../site_templates ./test_site/test_site/templates)
(set -x; rm -fv ./test_site/test_site/urls.py && ln -s ../../urls.py ./test_site/test_site/urls.py)
(set -x; ln -s ../../settings.py ./test_site/test_site/local_settings.py)

# DB handling
(set -x; env `./venv/bin/python -m env_pipes vars_from_file --uppercase_vars $1` ./venv/bin/python ./test_site/manage.py migrate --settings=test_site.local_settings)

# Create super user
(export DJANGO_SUPERUSER_LOGIN=$CURRENT_USER
export DJANGO_SUPERUSER_FIRSTNAME="$DJANGO_SUPERUSER_LOGIN"
export DJANGO_SUPERUSER_LASTNAME="$DJANGO_SUPERUSER_LOGIN"
export DJANGO_SUPERUSER_EMAIL="$DJANGO_SUPERUSER_LOGIN@invalid.local"
export DJANGO_SUPERUSER_PASSWORD=$DEFAULT_SUPERUSER_PASSWORD
env `./venv/bin/python -m env_pipes vars_from_file --uppercase_vars $1` ./venv/bin/python ./test_site/manage.py createsuperuser --noinput --settings=test_site.local_settings)

echo "Now run with:

env DJANGO_DEBUG=true \`./venv/bin/python -m env_pipes vars_from_file --uppercase_vars $1\` ./venv/bin/python ./test_site/manage.py runserver --settings=test_site.local_settings

Then go to http://localhost:8000/admin and use credentials $CURRENT_USER:$DEFAULT_SUPERUSER_PASSWORD
"
