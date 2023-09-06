PROJECT = djiutil

install_requirements:
	pip install -r requirements.txt

install: install_requirements
	pip install .

install_dev: install_requirements
	pip install -e .

uninstall:
	pip uninstall -y $(PROJECT)
