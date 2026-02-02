.PHONY: build publish clean

build:
	poetry build

publish:
	poetry publish --no-interaction --username "$$PYPI_USERNAME" --password "$$PYPI_PASSWORD"

clean:
	rm -rf dist build *.egg-info
