build:
	python3 setup.py build sdist bdist_wheel

build-docker-debian:
	docker build -t nicolabs/nicobot:debian -f debian.Dockerfile .

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
