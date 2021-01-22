REPO						= gianlu33/reactive-tools
TAG_LATEST			= latest
TAG_NATIVE			= native
TAG_SGX					= sgx
TAG_SANCUS			= sancus

TAG							?= latest
VOLUME					?= $(shell pwd)

run:
	docker run --rm -it --network=host -v $(VOLUME):/usr/src/app/ -v /var/run/aesmd/:/var/run/aesmd $(REPO):$(TAG) bash

clean:
	docker rm $(shell docker ps -a -q) 2> /dev/null || true
	docker image prune -f
