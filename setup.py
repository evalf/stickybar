from setuptools import setup
import re

with open('stickybar.py') as f:
  version = next(filter(None, map(re.compile("^version = '([a-zA-Z0-9.]+)'$").match, f))).group(1)

tests_require = ['pyte']

setup(
  name = 'stickybar',
  version = version,
  description = 'Stdout wrapper that prints a status bar below the cursor',
  author = 'Evalf',
  author_email = 'info@evalf.com',
  url = 'https://github.com/evalf/stickybar',
  py_modules = ['stickybar'],
  license = 'MIT',
  python_requires = '>=3.5',
  tests_require = tests_require,
  extras_require = dict(test=tests_require),
)
