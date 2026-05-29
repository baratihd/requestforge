# Contributing to Request Forge

Thank you for your interest in contributing! We welcome contributions from the community.

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Git
- pip

### Development Setup

1. **Fork and Clone**
```bash
git clone https://github.com/baratihd/requestforge.git
cd requestforge
```

1. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

1. **Install Development Dependencies**
```bash
pip install -e ".[dev]"
```

1. **Install Pre-commit Hooks**
```bash
pre-commit install
```

## 🧪 Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=requestforge --cov-report=html --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_client.py -v
```

### Run Linting

```bash
ruff check src/ tests/
```

### Run Formatting

```bash
ruff format src/ tests/
```

### Run All Quality Checks

```bash
make lint
make test
```

## 📝 Code Style

We use:
    - ruff for linting and formatting
    - pytest for testing
Code Conventions
    - Follow PEP 8 style guide
    - Use type hints for all functions
    - Write docstrings for all public APIs
    - Keep functions small and focused
    - Aim for 90%+ test coverage

## 🔀 Pull Request Process

1. Create a Feature Branch

```bash
git checkout -b feature/amazing-feature
```

2. Make Your Changes
    - Write code
    - Add tests
    - Update documentation

3. Run Tests

```bash
pytest
ruff check .
```

4. Commit Changes

```bash
git add .
git commit -m "Add amazing feature"
```

Pre-commit hooks will automatically run linting and formatting.

5. Push to GitHub

```bash
git push origin feature/amazing-feature
```

6. Create Pull Request
    - Go to GitHub
    - Click "New Pull Request"
    - Fill in description
    - Link related issues

### PR Checklist

- Tests pass locally
- Code coverage maintained or increased
- Linting passes
- Type checking passes
- Documentation updated
- CHANGELOG.md updated
- Commit messages are clear

## 📋 Reporting Issues

### Bug Reports
When reporting bugs, please include:
- Python version
- Package version
- Minimal code to reproduce
- Expected behavior
- Actual behavior
- Error messages/stack traces

### Feature Requests
When requesting features, please include:
- Use case description
- Proposed API (if applicable)
- Alternative solutions considered

## 🎯 Development Guidelines

### Adding New Features
- Discuss in an issue first
- Follow existing patterns
- Add comprehensive tests
- Document in docstrings
- Update README if needed

### Writing Tests
- Use class-based pytest style
- Mock external dependencies
- Test happy path and error cases
- Aim for edge case coverage

### Documentation
- Update docstrings
- Add examples to README
- Update CHANGELOG.md
- Keep documentation in sync with code

## 🏗️ Project Structure

```text
requestforge/
├── src/
│   └── requestforge/
│       ├── __init__.py
│       ├── client.py
│       ├── config.py
│       ├── exceptions.py
│       ├── fetcher.py
│       ├── hooks.py
│       ├── interfaces.py
│       ├── models.py
│       ├── pipelines.py
│       ├── retry.py
│       ├── token_manager.py
│       └── utils.py
├── tests/
│   ├── conftest.py
│   ├── test_*.py
├── .github/
│   └── workflows/
│       └── test.yml
├── pyproject.toml
├── tox.ini
├── README.md
└── CHANGELOG.md
```

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the project
- Show empathy towards others

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions make this project better for everyone!
