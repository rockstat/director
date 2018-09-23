HTTP_LISTEN=8089
SOCK_LISTEN=5000
CH_DSN=tcp://stage.rstat.org:9000/?database=stats

VERSION := 0.4.2
REPO := rockstat/director
BR := $(shell git branch | grep \* | cut -d ' ' -f2-)

watch:
	reflex -r '(\.py|\.yml)$$' -s -- /usr/bin/env python3 -m director -e 'py'

dev:
	bash -c "/usr/bin/env python3 -m \"$${PWD##*/}\" && exit 0"

bump-patch:
	bumpversion patch

bump-minor:
	bumpversion minor

build-dev:
	docker build -t $(REPO):$(BR) .
	docker push $(REPO):$(BR)
