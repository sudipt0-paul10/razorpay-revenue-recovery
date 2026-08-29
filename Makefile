.PHONY: test lint eval sweep docs

test:
	pytest

lint:
	ruff check .

eval:
	python -m rrx.eval.runner

sweep:
	python -m rrx.eval.runner --sweep

docs:
	python -m rrx.spec.sensitivity_doc