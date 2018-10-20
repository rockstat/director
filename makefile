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

build_image:
	docker build -t director .
	docker tag director rockstat/director:dev

push_image_dev:
	docker push rockstat/director:dev
