HTTP_LISTEN=8089
SOCK_LISTEN=5000
CH_DSN=tcp://stage.rstat.org:9000/?database=stats

watchj:
	JSON_LOGS=1 nodemon --exec /usr/bin/env python3 -m director -e 'py'

watch:
	# nodemon --exec /usr/bin/env python3 -m director -e 'py'
	reflex -r '\.py$$' -s -- /usr/bin/env python3 -m director -e 'py'

dev:
	bash -c "/usr/bin/env python3 -m \"$${PWD##*/}\" && exit 0"

patch:
	bumpversion patch

minor:
	bumpversion minor

