.PHONY : clean dist docs lint tests

# Build documentation, lint the code, and run tests
build : setup.py docs lint tests
	python setup.py sdist
	twine check dist/*.tar.gz

lint :
	flake8

docs :
	sphinx-build -b doctest . docs/_build
	sphinx-build -b html . docs/_build

clean :
	rm -rf docs/_build

tests :
	pytest -v --cov localscope --cov-report=html --cov-report=term-missing \
		--cov-fail-under=100 tests

# Build pinned requirements file
requirements.txt : requirements.in setup.py
	pip-compile -v $<
	pip-sync $@
