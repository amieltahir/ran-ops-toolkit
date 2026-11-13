.PHONY: check fix

# Same steps as CI.
check:
	ruff check .
	ruff format --check .
	mypy src/ranops/core
	pytest

fix:
	ruff check --fix .
	ruff format .
