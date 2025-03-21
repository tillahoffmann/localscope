#!/usr/bin/env python
import tomllib
import re

version = tomllib.load(open("pyproject.toml", "rb"))["project"]["version"]
input = open("localscope/__init__.py").read()
output = re.sub(r"__version__ = .*\n", f"__version__ = '{version}'\n", input)
open("localscope/__init__.py", "w").write(output)
