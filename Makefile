PROJECT = djiutil

clean:
	pip uninstall -y $(PROJECT)

install:
	pip install .

install_dev:
	pip install -e .
