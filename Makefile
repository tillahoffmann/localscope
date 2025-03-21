.PHONY : dist docs doctests docker-image lint tests

# Build documentation, lint the code, and run tests.
build : doctests docs lint tests dist

dist : pyproject.toml
	python -m build
	twine check dist/*.tar.gz dist/*.whl

lint :
	flake8
	black --check .
	mypy localscope

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
requirements.txt : requirements.in pyproject.toml
	pip-compile -v $<

# Docker versions.
VERSIONS = 3.9 3.10 3.11 3.12 3.13
IMAGES = $(addprefix docker-image/,${VERSIONS})
RUNS = $(addprefix docker-run/,${VERSIONS})

docker-images : ${IMAGES}
${IMAGES} : docker-image/% :
	docker build --build-arg version=$* -t localscope:$* .

$(addprefix docker-shell/,${VERSIONS}) : docker-shell/% : docker-image/%
	docker run --rm -it localscope:$* bash

docker-runs : ${RUNS}
${RUNS} : docker-run/% : docker-image/%
	docker run --rm -it localscope:$* make build
