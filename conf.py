project = "localscope"
copyright = "2020, Till Hoffmann"
author = "Till Hoffmann"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]
exclude_patterns = [
    "_build",
    "*.egg-info",
    "README.rst",
    "venv",
]
doctest_global_setup = "from localscope import localscope"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
