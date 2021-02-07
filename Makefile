build:
	python3 setup.py build sdist bdist_wheel

test:
	python3 -m unittest discover -v -s tests
