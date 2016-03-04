
build: clean deps
	python setup.py bdist_wheel

deps:
	pip install twine wheel

clean:
	rm -rf dist build gnlpy.egg-info

upload:
	twine upload dists/*whl
