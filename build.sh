#!/bin/sh
set -x

./venv/bin/python setup.py bdist_wheel && \
docker build --tag django-okta-client:`./venv/bin/python -c "import okta_client; print(okta_client.__version__, end = '')"` . && \
docker run -d --rm -e DJANGO_DEBUG=true -e OKTA_METADATA="`cat conf/metadata.url`" -e PORT=8080 -p "127.0.0.1:8080:8080" django-okta-client:`./venv/bin/python -c "import okta_client; print(okta_client.__version__, end = '')"`
