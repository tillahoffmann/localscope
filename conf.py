project = 'localscope'
copyright = '2020, Till Hoffmann'
author = 'Till Hoffmann'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.napoleon',
]
exclude_patterns = [
    '*.egg-info',
    '_build',
    'venv',
]
doctest_global_setup = "from localscope import localscope"
