# Developer Guide

This guide covers setup, testing, and deployment for contributors.

## Package Management

This package uses [uv](https://docs.astral.sh/uv/) to manage dependencies and
isolated [Python virtual environments](https://docs.python.org/3/library/venv.html).

To proceed,
[install uv globally](https://docs.astral.sh/uv/getting-started/installation/)
onto your system.

To [install a specific version of Python](https://docs.astral.sh/uv/guides/install-python/):

```shell
uv python install 3.13
```

To upgrade a specific version of Python to the latest patch release:

```shell
uv python install --reinstall 3.13
```

## Dependencies

Dependencies are defined in [`pyproject.toml`](./pyproject.toml) and specific versions are locked
into [`uv.lock`](./uv.lock). This allows for exact reproducible environments across
all machines that use the project, both during development and in production.

To install all dependencies into an isolated virtual environment:

```shell
uv sync
```

To upgrade all dependencies to their latest versions:

```shell
uv lock --upgrade
```

## Packaging & Building

This project is designed as a Python package, meaning that it can be bundled up and redistributed
as a single compressed file.

Packaging is configured by:

- [`pyproject.toml`](./pyproject.toml)

To package the project as both a
[source distribution](https://packaging.python.org/en/latest/flow/#the-source-distribution-sdist)
and a [wheel](https://packaging.python.org/en/latest/specifications/binary-distribution-format/):

```shell
uv build
```

This will generate `dist/xlsx_streamer-0.1.0.tar.gz` and `dist/xlsx_streamer-0.1.0-py3-none-any.whl`.

> [!TIP]
> Read more about the [advantages of wheels](https://pythonwheels.com/) to understand why
> generating wheel distributions are important.

## Publishing to PyPI

Source and wheel redistributable packages can
be [published to PyPI](https://docs.astral.sh/uv/guides/package/) or installed
directly from the filesystem using `pip`.

```shell
uv publish
```

> [!NOTE]
> To enable publishing, remove the `"Private :: Do Not Upload"`
> [trove classifier](https://pypi.org/classifiers/).

## Code Quality

Automated code quality checks are performed using [Nox](https://nox.thea.codes/en/stable/) and
[`nox-uv`](https://github.com/dantebben/nox-uv). Nox will automatically create virtual environments
and run commands based on [`noxfile.py`](./noxfile.py) for unit testing, PEP 8 style guide
checking, type checking and documentation generation.

> [!NOTE]
> `nox` is installed into the virtual environment automatically by the `uv sync` command
> above.

To run all default sessions:

```shell
uv run nox
```

## Unit Testing

Unit testing is performed with [pytest](https://pytest.org/). pytest has become the de facto Python
unit testing framework. Some key advantages over the built-in
[unittest](https://docs.python.org/3/library/unittest.html) module are:

1. Significantly less boilerplate needed for tests.
2. PEP 8 compliant names (e.g. `pytest.raises()` instead of `self.assertRaises()`).
3. Vibrant ecosystem of plugins.

pytest will automatically discover and run tests by recursively searching for folders and `.py`
files prefixed with `test` for any functions prefixed by `test`.

The `tests` folder is created as a Python package (i.e. there is an `__init__.py` file within it)
because this helps `pytest` uniquely namespace the test files. Without this, two test files cannot
be named the same, even if they are in different subdirectories.

Code coverage is provided by the [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/) plugin.

When running a unit test Nox session (e.g. `nox -s test`), an HTML report is generated in
the `htmlcov` folder showing each source file and which lines were executed during unit testing.
Open `htmlcov/index.html` in a web browser to view the report. Code coverage reports help identify
areas of the project that are currently not tested.

pytest and code coverage are configured in [`pyproject.toml`](./pyproject.toml).

To pass arguments to `pytest` through `nox`:

```shell
uv run nox -s test -- -k test_function_name
```

## Code Style Checking

[PEP 8](https://peps.python.org/pep-0008/) is the universally accepted style guide for Python
code. PEP 8 code compliance is verified using [Ruff](https://github.com/astral-sh/ruff). Ruff is configured in the
`[tool.ruff]` section of [`pyproject.toml`](./pyproject.toml).

Some code style settings are included in [`.editorconfig`](./.editorconfig) and will be configured
automatically in editors such as PyCharm.

To lint code, run:

```shell
uv run nox -s lint
```

To automatically fix fixable lint errors, run:

```shell
uv run nox -s lint_fix
```

## Automated Code Formatting

[Ruff](https://github.com/astral-sh/ruff) is used to automatically format code and group and sort imports.

To automatically format code, run:

```shell
uv run nox -s fmt
```

## Type Checking

[Type annotations](https://docs.python.org/3/library/typing.html) allows developers to include
optional static typing information to Python source code. This allows static analyzers such
as [mypy](http://mypy-lang.org/), [PyCharm](https://www.jetbrains.com/pycharm/),
or [Pyright](https://github.com/microsoft/pyright) to check that functions are used with the
correct types before runtime.

Editors such as [PyCharm](https://www.jetbrains.com/help/pycharm/type-hinting-in-product.html) and
VS Code are able to provide much richer auto-completion, refactoring, and type checking while the
user types, resulting in increased productivity and correctness.

```python
def example(n: int) -> str:
    return str(n)
```

mypy is configured in [`pyproject.toml`](./pyproject.toml). To type check code, run:

```shell
uv run nox -s type_check
```

See also [awesome-python-typing](https://github.com/typeddjango/awesome-python-typing).

### Distributing Type Annotations

[PEP 561](https://www.python.org/dev/peps/pep-0561/) defines how a Python package should
communicate the presence of inline type annotations to static type
checkers. [mypy's documentation](https://mypy.readthedocs.io/en/stable/installed_packages.html)
provides further examples on how to do this.

Mypy looks for the existence of a file named [`py.typed`](./src/xlsx_streamer/py.typed) in the root of the
installed package to indicate that inline type annotations should be checked.

## Continuous Integration

Continuous integration is provided by [GitHub Actions](https://github.com/features/actions). This
runs all tests, lints, and type checking for every commit and pull request to the repository.

GitHub Actions is configured in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml).

## Documentation

### User Guide

[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) is a powerful static site
generator that combines easy-to-write Markdown, with a number of Markdown extensions that increase
the power of Markdown. This makes it a great fit for user guides and other technical documentation.

The example MkDocs project included in this project is configured to allow the built documentation
to be hosted at any URL or viewed offline from the file system.

To build the user guide, run:

```shell
uv run nox -s docs
```

and open `docs/user_guide/site/index.html` using a web browser.

To build the user guide, additionally validating external URLs, run:

```shell
uv run nox -s docs_check_urls
```

To build the user guide in a format suitable for viewing directly from the file system, run:

```shell
uv run nox -s docs_offline
```

To build and serve the user guide with automatic rebuilding as you change the contents, run:

```shell
uv run nox -s docs_serve
```

and open <http://127.0.0.1:8000> in a browser.

Each time the `main` Git branch is updated, the
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) GitHub Action will
automatically build the user guide and publish it to [GitHub Pages](https://pages.github.com/).

## Licensing

Licensing for the project is defined in:

- [`LICENSE.txt`](./LICENSE.txt)
- [`pyproject.toml`](./pyproject.toml)

This project uses a common permissive license, the MIT license.

A license report of all third party packages and their transitive dependencies is generated and
built into the user guide. This allows application developers to comply with these licenses, which
require that the license be included when the library is shipped to end users.

To automatically list the licenses for all dependencies and regenerate the license report using
[pip-licenses-cli](https://github.com/stefan6419846/pip-licenses-cli):

```shell
uv run nox -s licenses
```

## Docker

[Docker](https://www.docker.com/) is a tool that allows for software to be packaged into isolated
containers. The Docker configuration in this repository is optimized for small size and increased security.

Docker is configured in:

- [`Dockerfile`](./Dockerfile)
- [`.dockerignore`](./.dockerignore)

To build the container image:

```shell
docker build --tag xlsx-streamer .
```

To run the image in a container:

```shell
docker run --rm --interactive --tty xlsx-streamer input.xlsx > output.csv
```

## IDE Setup

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)

### PyCharm

To configure [PyCharm](https://www.jetbrains.com/pycharm/) to align to the code style used in this project:

- Settings | Search "Hard wrap at" (Note, this will be automatically set by [`.editorconfig`](./.editorconfig))
    - Editor | Code Style | General | Hard wrap at: 99

- Settings | Search "Optimize Imports"
    - Editor | Code Style | Python | Imports
        - ☑ Sort import statements
            - ☑ Sort imported names in "from" imports
            - ☐ Sort plain and "from" imports separately within a group
            - ☐ Sort case-insensitively
        - Structure of "from" imports
            - ◎ Leave as is
            - ◉ Join imports with the same source
            - ◎ Always split imports

- Settings | Search "Docstrings"
    - Tools | Python Integrated Tools | Docstrings | Docstring Format: Google

- Settings | Search "pytest"
    - Tools | Python Integrated Tools | Testing | Default test runner: pytest

- Settings | Search "Force parentheses"
    - Editor | Code Style | Python | Wrapping and Braces | "From" Import Statements
        - ☑ Force parentheses if multiline

#### Ruff Integration

PyCharm natively supports [Ruff](https://docs.astral.sh/ruff/editors/setup/#pycharm) linting and formatting.

1. Open Preferences or Settings | Python | Tools | Ruff
    - **Check**: Enable
    - Open **All Actions on Save...**
        - **Check**: Reformat Code
            - Files: Python

Now, on <kbd>ctrl+s</kbd>, the current source file will be automatically formatted and linting
errors will be shown within the editor.

> [!TIP]
> These tools work best if you properly mark directories as excluded from the project that should
> be, such as `.nox`.

#### Nox Support

[PyCharm does not yet natively support Nox](https://youtrack.jetbrains.com/issue/PY-37302). The
recommended way to launch Nox from PyCharm is to create a **Python** Run Configuration.

- Beside **Script Path**, press `▼` and select **Module name**: `nox`
- **Parameters**, enter a Nox session: `-s test`
- **Working Directory**: Enter the path to the current project
- Select **Modify Options** | Check **Emulate terminal in output console** to enable colors to be rendered properly

## Project Structure

The source code is located in the `src/` directory:

```
src/
└── xlsx_streamer/
    ├── __init__.py
    ├── cli.py
    ├── reader.py
    ├── xlsx_handler.py
    ├── xlsx_generator.py
    ├── xlsx_metadata_extractor.py
    ├── py.typed
    └── sources/
        ├── __init__.py
        ├── base.py
        ├── http.py
        ├── local.py
        └── s3.py
```

The dedicated `src` directory is the [recommended solution](https://docs.pytest.org/en/latest/pythonpath.html#test-modules-conftest-py-files-inside-packages)
by `pytest` when using Nox. This prevents shadowing of installed packages during testing.

## Quick Reference Commands

```bash
# Create new branch for feature
git checkout -b feature/my-feature

# Run all checks (tests, lint, type check)
uv run nox

# Run specific nox session
uv run nox -s test
uv run nox -s lint
uv run nox -s type_check
uv run nox -s fmt

# Run tests for specific file
uv run pytest tests/test_reader.py -v

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Type check specific file
mypy src/xlsx_streamer/reader.py

# Lint and auto-fix
ruff check src/ --fix

# Format code
ruff format src/

# Check dependencies
uv tree --no-default-groups

# Build distribution
uv build

# Publish to PyPI
uv publish
```

## Contributing

For architectural details and development guidelines, see [AGENTS.md](AGENTS.md).
