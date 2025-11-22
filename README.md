# aws-cdk-apache-doris

AWS CDK (Python) Construct(s) for Apache Doris.

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and uses a git flow branching strategy.

### Setup

Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone the repository and install dependencies:

```bash
git clone https://github.com/anentropic/aws-cdk-apache-doris.git
cd aws-cdk-apache-doris
uv sync --extra dev
```

### Running Tests

Run unit tests:

```bash
uv run pytest
```

Run integration test (CDK synth):

```bash
uv run cdk synth
```

Run linters and formatters:

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

### Pre-commit Hooks

This project uses [prek](https://prek.j178.dev/) for managing pre-commit hooks. Install the hooks:

```bash
uv run prek install
```

This will run ruff (check + format) and basedpyright automatically before each commit.

### Git Flow

This repository follows a git flow branching strategy:

- **feature branches**: Create from `develop`, PR to `develop`
- **develop branch**: Integration branch for features, runs tests on merge
- **main branch**: Production branch, publishes releases to PyPI on merge

### CI/CD

GitHub Actions workflows:

- **Pull Requests**: Tests run on all PRs to `develop` or `main`
- **Develop Branch**: Tests run on merge to `develop`
- **Main Branch**: Tests run and package is published to PyPI on merge to `main`

## License

MIT