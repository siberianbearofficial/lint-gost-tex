.PHONY: build publish clean

build:
\tpoetry build

publish:
\tpoetry publish --no-interaction --username "$$PYPI_USERNAME" --password "$$PYPI_PASSWORD"

clean:
\trm -rf dist build *.egg-info
