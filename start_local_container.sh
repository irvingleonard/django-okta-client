#!/bin/sh

export DJANGO_SUPERUSER_LOGIN=`whoami`
export DJANGO_SUPERUSER_FIRSTNAME="$DJANGO_SUPERUSER_LOGIN"
export DJANGO_SUPERUSER_LASTNAME="$DJANGO_SUPERUSER_LOGIN"
export DJANGO_SUPERUSER_EMAIL="$DJANGO_SUPERUSER_LOGIN@invalid.local"
export DJANGO_SUPERUSER_PASSWORD="My sup3r p4ssw0rd!"

docker build \
	--build-arg DJANGO_SUPERUSER_LOGIN \
	--build-arg DJANGO_SUPERUSER_FIRSTNAME \
	--build-arg DJANGO_SUPERUSER_LASTNAME \
	--build-arg DJANGO_SUPERUSER_EMAIL \
	--build-arg DJANGO_SUPERUSER_PASSWORD \
	--tag django-okta-client:latest .
docker run --name django_okta_client_test \
	-e DJANGO_DEBUG=true \
	-e OKTA_METADATA \
	-e PORT=8080 \
	-p "127.0.0.1:8080:8080" -d --rm django-okta-client:latest
docker logs -f django_okta_client_test

