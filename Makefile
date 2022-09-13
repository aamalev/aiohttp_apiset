.PHONY: setup_ui clear_ui

clear_ui:
	python ui.py delete
setup_ui:
	python ui.py
aiohttp_apiset/version.py:
	echo "__version__ = '$(shell git describe --tags)'" > $@
