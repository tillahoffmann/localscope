import re
from setuptools import setup, find_packages


with open('README.rst') as fp:
    long_description = fp.read()
long_description = long_description.replace('.. doctest::', '.. code-block:: python')
long_description = re.sub(r'(\.\. autofunction:: .*?$)', r':code:`\1`', long_description)


tests_require = [
    'flake8',
    'pytest',
    'pytest-cov',
]

setup(
    name='localscope',
    version='0.1.3',
    author='Till Hoffmann',
    packages=find_packages(),
    url='https://github.com/tillahoffmann/localscope',
    long_description_content_type="text/x-rst",
    long_description=long_description,
    tests_require=tests_require,
    extras_require={
        'docs': [
            'sphinx',
        ],
        'tests': tests_require,
    }
)
