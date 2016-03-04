# Distributing gnlpy

Distributing gnlpy makes it easier for people to install gnlpy in their python
environment using pip.

This document explains the process to build a new package.

## Requirements

```
pip install twine wheel
```
or
```
make deps
```

## Building the package

Before building a new package:
* change the version number in `setup.py`.
* update the `CHANGELOG.md`
* tag the release in github

We build a wheel package as this is pure python module:
```
python setup.py bdist_wheel
```
or
```
make build
```

## Upload to PyPI
To upload to [PyPI](https://pypi.python.org/pypi) we use twine. First make
sure you have an [account](http://python-packaging-user-guide.readthedocs.org/en/latest/distributing/#create-an-account).

```
twine upload dist/gnlpy-version-py2-none-any.whl
```
or
```
make upload
```

## References:

* [Distributing packages](http://python-packaging-user-guide.readthedocs.org/en/latest/distributing/)
