# Contributing to RSS Generator

Thank you for your interest in contributing to RSS Generator!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/pedromcaraujo/rss-generator.git
cd rss-generator
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=rss_generator --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_parsers.py
```

### Run tests matching a pattern
```bash
pytest -k "test_parse"
```

## Testing Multiple Python Versions

We use `tox` to test across multiple Python versions:

```bash
# Install tox
pip install tox

# Run tests on all Python versions
tox

# Run tests on specific Python version
tox -e py312

# Run linting
tox -e lint

# Run formatting
tox -e format
```

## Code Quality

### Linting
```bash
ruff check rss_generator tests
```

### Formatting
```bash
# Check formatting
ruff format --check rss_generator tests

# Apply formatting
ruff format rss_generator tests
```

### Type Checking
```bash
mypy rss_generator
```

## Project Structure

```
rss-generator/
├── rss_generator/          # Main package
│   ├── cli.py             # CLI commands
│   ├── common.py          # Common utilities
│   ├── parsers.py         # Site-specific parsers
│   ├── sites.py           # Site configurations
│   └── templates/         # Jinja2 templates
├── tests/                 # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_parsers.py    # Parser tests
│   ├── test_common.py     # Common utilities tests
│   ├── test_sites.py      # Site config tests
│   ├── test_cli.py        # CLI tests
│   └── fixtures/          # Test data
├── examples/              # Example scripts
└── .github/workflows/     # CI/CD configuration
```

## Adding a New Site

1. Add site configuration to `rss_generator/sites.py`
2. Create parser function in `rss_generator/parsers.py`
3. Add parser to `PARSERS` registry
4. (Optional) Add content/metadata extractors
5. Add tests in `tests/test_parsers.py`

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass (`pytest`)
6. Ensure code is formatted (`ruff format`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to your fork (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Testing Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Use fixtures from `conftest.py` when applicable
- Mock external dependencies (network calls, file I/O)

## Questions?

Feel free to open an issue for any questions or suggestions!
