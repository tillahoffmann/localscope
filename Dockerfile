ARG version
FROM python:${version}
WORKDIR /workdir
COPY README.rst requirements.txt pyproject.toml ./
RUN pip install -r requirements.txt
COPY . .
