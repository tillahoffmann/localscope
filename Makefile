.PHONY : dist docs doctests lint tests

# Build documentation, lint the code, and run tests.
build : setup.py docs doctests lint tests
	python setup.py sdist
	twine check dist/*.tar.gz

lint :
	flake8
	black --check .

docs :
	# Always build from scratch because of dodgy Sphinx caching.
	rm -rf docs/_build
	sphinx-build -nW -b html . docs/_build

doctests :
	# Always build from scratch because of dodgy Sphinx caching.
	rm -rf docs/_build
	sphinx-build -nW -b doctest . docs/_build

tests :
	pytest -v --cov localscope --cov-report=html --cov-report=term-missing \
		--cov-fail-under=100

# Build pinned requirements file.
requirements.txt : requirements.in setup.py
	pip-compile -v $<
	pip-sync $@
