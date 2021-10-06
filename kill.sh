#!/bin/sh
set -x

IMAGE_NAME="django-okta-client:`./venv/bin/python -c \"import okta_client; print(okta_client.__version__, end = '')\"`"
CONTAINER_ID=`docker ps --quiet --filter "ancestor=$IMAGE_NAME" --filter status=running`
docker stop $CONTAINER_ID
