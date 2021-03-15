clean:
	rm -rf build

build:
	pip3 install --upgrade -c constraints.txt -r requirements-build.txt -r requirements-runtime.txt
	python3 setup.py build sdist bdist_wheel

docker-build-alpine:
	docker build -t nicolabs/nicobot:dev-alpine -f alpine.Dockerfile $(ARGS) .

docker-build-debian:
	docker build -t nicolabs/nicobot:dev-debian -f debian.Dockerfile $(ARGS) .

docker-build-debian-signal: docker-build-debian
	docker build -t nicolabs/nicobot:dev-signal-debian --build-arg NICOBOT_BASE_IMAGE=nicolabs/nicobot:dev-debian -f signal-debian.Dockerfile $(ARGS) .

docker-build-all: docker-build-debian docker-build-debian-signal docker-build-alpine

compose-build:
	cd aws && docker-compose -f transbot.docker-compose.yml build

compose-up:
	cd aws && docker-compose -f transbot.docker-compose.yml up --build

test:
	python3 -m unittest discover -v -s tests

askbot:
	python3 -m nicobot.askbot $(ARGS)

transbot:
	python3 -m nicobot.transbot $(ARGS)

docker-askbot:
	docker run --rm -it nicobot:dev-signal-debian askbot $(ARGS)

docker-transbot:
	docker run --rm -it nicobot:dev-signal-debian transbot $(ARGS)

# All targets might be declared phony, since this Makefile is just a helper
# However most just don't match a file/directory so they will work without it
.PHONY: build test
