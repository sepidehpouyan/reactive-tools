REPO						= gianlu33/reactive-tools
TAG_LATEST			= latest
TAG_NATIVE			= native
TAG_SGX					= sgx
TAG_SANCUS			= sancus

TAG							?= latest

run: check_workspace
	docker run --rm -it --network=host -v $(WORKSPACE):/usr/src/app/ -v /var/run/aesmd/:/var/run/aesmd $(REPO):$(TAG) bash

clean:
	docker rm $(shell docker ps -a -q) 2> /dev/null || true
	docker image prune -f

check_workspace:
	@test $(WORKSPACE) || (echo "WORKSPACE variable not defined. Run make <target> WORKSPACE=<path_to_project>" && return 1)
