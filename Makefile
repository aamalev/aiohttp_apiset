

swagger_ui:
	SWAGGER_UI_VERSION=2.2.10 python swagger_ui.py
	SWAGGER_UI_VERSION=3.52.5 python swagger_ui.py
	SWAGGER_UI_VERSION=4.10.3 python swagger_ui.py

aiohttp_apiset/version.py:
	echo "__version__ = '$(shell git describe --tags)'" > $@

clear:
	python swagger_ui.py delete
