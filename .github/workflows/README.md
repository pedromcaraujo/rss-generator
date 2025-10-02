# GitHub Actions Workflows

This directory contains CI/CD workflows for the RSS Generator project.

## Workflows

### `test.yml` - Automated Testing

Runs on every push and pull request to `main` and `develop` branches.

**Jobs:**
- **Test** - Runs unit tests across Python 3.12 and 3.13
  - Installs system dependencies for Playwright
  - Runs tests with pytest and tox
  - Generates coverage reports
  - Uploads coverage to Codecov (optional)

- **Lint** - Code quality checks
  - Runs `ruff check` for linting
  - Runs `ruff format --check` for formatting

**Badge:**
Add this to your README.md to show build status:
```markdown
![Tests](https://github.com/pedromcaraujo/rss-generator/workflows/Tests/badge.svg)
```

## Local Development

You can run the same checks locally:

```bash
# Run tests
pytest

# Run tests with tox (multiple Python versions)
tox

# Run linting
ruff check rss_generator tests

# Check formatting
ruff format --check rss_generator tests
```
