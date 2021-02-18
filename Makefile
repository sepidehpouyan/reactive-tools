REPO						= gianlu33/reactive-tools
TAG_LATEST			= latest
TAG_NATIVE			= native
TAG_SGX					= sgx
TAG_SANCUS			= sancus

PWD 						= $(shell pwd)

TAG							?= latest
VOLUME					?= $(PWD)

PYPI_REPO				?= gianlu33/pypi
PYPI_USERNAME		?= __token__

create_pkg:
	docker run --rm -it -v $(PWD):/usr/src/app $(PYPI_REPO) python setup.py sdist bdist_wheel

upload: create_pkg
	docker run --rm -it -v $(PWD):/usr/src/app $(PYPI_REPO) twine upload --repository pypi dist/* -u $(PYPI_USERNAME)

run:
	docker run --rm -it --network=host -v $(VOLUME):/usr/src/app/ -v /var/run/aesmd/:/var/run/aesmd $(REPO):$(TAG) bash

clean:
	sudo rm -rf dist/*
