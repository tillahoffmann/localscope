ARG version
FROM python:${version}
WORKDIR /workdir
COPY README.rst requirements.txt setup.py ./
RUN pip install -r requirements.txt
COPY . .
