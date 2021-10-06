#!/bin/sh
set -x

./venv/bin/python setup.py bdist_wheel && \
docker build --tag django-okta-client:`./venv/bin/python -c "import okta_client; print(okta_client.__version__, end = '')"` . && \
docker run -d -e DJANGO_DEBUG=true -e OKTA_METADATA="https://yourdomain.okta.com/path/to/the/app/metadata" -e PORT=8080 -p "127.0.0.1:8080:8080" django-okta-client:`./venv/bin/python -c "import okta_client; print(okta_client.__version__, end = '')"`
