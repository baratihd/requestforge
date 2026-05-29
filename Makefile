.PHONY: \
	help \
	install \
	dev-install \
	pre-commit \
	test \
	test-all \
	lint \
	format \
	type \
	type-strict \
	clean \
	build \
	publish

PACKAGE=requestforge
SRC=src/requestforge
TESTS=tests

help:
	@echo "Available commands:"
	@echo ""
	@echo "  make install        Install package"
	@echo "  make dev-install    Install package with development dependencies"
	@echo "  make pre-commit     Install pre-commit hooks"
	@echo ""
	@echo "  make test           Run tests"
	@echo "  make test-all       Run tox matrix"
	@echo ""
	@echo "  make lint           Run Ruff lint checks"
	@echo "  make format         Auto-format code"
	@echo "  make type           Run mypy type checking"
	@echo "  make type-strict    Run strict mypy checks"
	@echo ""
	@echo "  make clean          Remove build/cache artifacts"
	@echo "  make build          Build wheel and sdist"
	@echo "  make publish        Upload package to PyPI"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

pre-commit:
	pre-commit install

test:
	pytest -v --cov=$(PACKAGE) --cov-report=term-missing --cov-report=html

test-all:
	tox

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

type:
	mypy $(SRC)

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .tox/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*
