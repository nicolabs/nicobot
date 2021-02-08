clean:
	rm -rf build

build:
	pip3 install --upgrade -r requirements-build.txt -r requirements-runtime.txt
	python3 setup.py build sdist bdist_wheel

docker-build-alpine:
	docker build -t nicolabs/nicobot:alpine -f alpine.Dockerfile .

docker-build-debian-signal:
	docker build -t nicolabs/nicobot:signal-debian -f signal-debian.Dockerfile .

docker-build-debian:
	docker build -t nicolabs/nicobot:debian -f debian.Dockerfile .

docker-build: docker-build-debian

test:
	python3 -m unittest discover -v -s tests

askbot:
	python3 -m nicobot.askbot $(ARGS)

transbot:
	python3 -m nicobot.transbot $(ARGS)

docker-askbot:
	docker run --rm -it nicolabs/nicobot:debian askbot $(ARGS)

docker-transbot:
	docker run --rm -it nicolabs/nicobot:debian transbot $(ARGS)

# All targets might be declared phony, since this Makefile is just a helper
# However most just don't match a file/directory so they will work without it
.PHONY: build test
