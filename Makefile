# Default values (override with .env file / environment variables)
NICOBOT_IMAGE?= nicolabs/nicobot

check:
	echo ${NICOBOT_IMAGE}

clean:
	rm -rf build

build:
	pip3 install --upgrade -c constraints.txt -r requirements-build.txt -r requirements-runtime.txt
	python3 setup.py build sdist bdist_wheel

docker-build-alpine:
	# E.g. ARGS="-v debug" make docker-build-alpine
	docker build -t ${NICOBOT_IMAGE}:dev-alpine -f alpine.Dockerfile $(ARGS) .

docker-build-debian:
	docker build -t ${NICOBOT_IMAGE}:dev-debian -f debian.Dockerfile $(ARGS) .

docker-build-debian-signal: docker-build-debian
	docker build -t ${NICOBOT_IMAGE}:dev-signal-debian --build-arg NICOBOT_DEPLOY_BASE_IMAGE=${NICOBOT_IMAGE}:dev-debian -f signal-debian.Dockerfile $(ARGS) .

docker-build-all: docker-build-debian docker-build-debian-signal docker-build-alpine

compose-build:
	docker-compose -f tests/transbot-sample-conf/docker-compose.yml ${ARGS} build

compose-up:
	docker-compose -f tests/transbot-sample-conf/docker-compose.yml ${ARGS} up --build

compose-down:
	docker-compose -f tests/transbot-sample-conf/docker-compose.yml ${ARGS} down

aws-up:
	# E.g. ARGS="--env-file /home/me/deploy/nicobot-aws-prod.env" make aws-up
	docker compose -f tests/transbot-sample-conf/docker-compose.yml ${ARGS} up

aws-down:
	# E.g. ARGS="--env-file /home/me/deploy/nicobot-aws-prod.env" make aws-down
	docker compose -f tests/transbot-sample-conf/docker-compose.yml ${ARGS} down

test:
	python3 -m unittest discover -v -s tests

askbot:
	python3 -m nicobot.askbot $(ARGS)

transbot:
	python3 -m nicobot.transbot $(ARGS)

docker-askbot:
	docker run --rm -it ${NICOBOT_IMAGE}:dev-signal-debian askbot $(ARGS)

docker-transbot:
	docker run --rm -it ${NICOBOT_IMAGE}:dev-signal-debian transbot $(ARGS)

# All targets might be declared phony, since this Makefile is just a helper
# However most just don't match a file/directory so they will work without it
.PHONY: build test
