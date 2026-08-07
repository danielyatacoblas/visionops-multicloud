PYTHON ?= python
export PYTHONPATH := src

bootstrap:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

demo:
	$(PYTHON) -m visionops --input data/sample --output artifacts

fmt-check:
	terraform fmt -check -recursive infra
