.PHONY: test lint eval sweep

test:
	pytest

lint:
	ruff check .

eval:
	python -m rrx.eval.runner

sweep:
	python -m rrx.eval.runner --sweep