HTTP_LISTEN=8089
SOCK_LISTEN=5000
CH_DSN=tcp://stage.rstat.org:9000/?database=stats

run_watchj:
	JSON_LOGS=1 nodemon --exec /usr/bin/env python3 -m director -e 'py'

run_watch:
	nodemon --exec /usr/bin/env python3 -m director -e 'py'


