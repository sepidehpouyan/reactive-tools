REPO						?= gianlu33/reactive-tools
TAG							?= latest

PWD 						= $(shell pwd)
VOLUME					?= $(PWD)

PYPI_REPO				?= gianlu33/pypi
PYPI_USERNAME		?= __token__

create_pkg:
	docker run --rm -it -v $(PWD):/usr/src/app $(PYPI_REPO) python setup.py sdist bdist_wheel

upload: create_pkg
	docker run --rm -it -v $(PWD):/usr/src/app $(PYPI_REPO) twine upload --repository pypi dist/* -u $(PYPI_USERNAME)

clean:
	sudo rm -rf dist/*

generate_key:
	openssl genrsa -3 3072 > examples/vendor_key.pem

run:
	docker run --rm -it --network=host -v $(VOLUME):/usr/src/app/ $(REPO):$(TAG) bash

pull:
	docker pull $(REPO):$(TAG)

build:
	docker build -t $(REPO):$(TAG) --build-arg DUMMY=$(shell date +%s) .

push: login
	docker push $(REPO):$(TAG)

login:
	docker login
