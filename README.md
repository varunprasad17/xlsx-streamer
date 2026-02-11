# xlsx-streamer

[![GitHub Actions][github-actions-badge]](https://github.com/johnthagen/python-blueprint/actions)
[![uv][uv-badge]](https://github.com/astral-sh/uv)
[![Nox][nox-badge]](https://github.com/wntrblm/nox)
[![Ruff][ruff-badge]](https://github.com/astral-sh/ruff)
[![Type checked with mypy][mypy-badge]](https://mypy-lang.org/)

[github-actions-badge]: https://github.com/johnthagen/python-blueprint/actions/workflows/ci.yml/badge.svg
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[nox-badge]: https://img.shields.io/badge/%F0%9F%A6%8A-Nox-D85E00.svg
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[mypy-badge]: https://www.mypy-lang.org/static/mypy_badge.svg

xlsx-streamer is a memory-efficient Python library and CLI tool for streaming large XLSX files to CSV format from any data source. It supports reading from local files, AWS S3, and HTTP/HTTPS URLs without loading entire files into memory.

## Features

- **Multi-source support**: Read XLSX files from local filesystem, AWS S3, and HTTP/HTTPS URLs
- **Memory-efficient streaming**: Process large files without loading them entirely into memory
- **Simple unified API**: Single `XLSXReader` class works with all source types
- **Flexible output**: Stream rows as Python lists or convert directly to CSV files
- **Type hints**: Fully typed for better IDE support and type checking
- **CLI tool**: Command-line interface with source auto-detection

## Quick Start

### Python API

```python
from xlsx_streamer import XLSXReader

# Auto-detect source type
reader = XLSXReader("s3://bucket/file.xlsx", sheet_name="Sheet1")  # S3
reader = XLSXReader("https://example.com/file.xlsx")                 # HTTP
reader = XLSXReader("/path/to/file.xlsx")                            # Local file

# Stream rows
for row in reader.stream_rows():
    print(row)

# Convert to CSV
reader.to_csv("output.csv")
```

### CLI

```shell
# Local file
xlsx-streamer input.xlsx > output.csv

# From S3
xlsx-streamer s3://bucket/path/file.xlsx > output.csv

# From HTTP
xlsx-streamer https://example.com/file.xlsx > output.csv

# Save to file
xlsx-streamer input.xlsx --output output.csv

# Specify sheet
xlsx-streamer input.xlsx --sheet "Sheet2" > output.csv

# Enable verbose logging
xlsx-streamer input.xlsx --verbose
```

## Installation

Install the base package with support for local files:

```shell
pip install xlsx-streamer
```

Add optional support for S3:

```shell
pip install xlsx-streamer[s3]
```

Add optional support for HTTP:

```shell
pip install xlsx-streamer[http]
```

Install all optional dependencies:

```shell
pip install xlsx-streamer[all]
```

## Documentation

- **[Developer Guide](DEVELOPER.md)** - Setup, testing, and deployment
- **[Architecture & Development](AGENTS.md)** - Technical guidelines for contributors
- **[Project Roadmap](PLAN.md)** - Future plans and feature pipeline

## Acknowledgments

This project builds on the excellent work of:

- [stream-unzip](https://github.com/uktrade/stream-unzip) - Memory-efficient ZIP streaming library
- [typer-slim](https://github.com/tiangolo/typer) - Simplified CLI framework
- [boto3](https://github.com/boto/boto3) - AWS SDK for Python
- [httpx](https://github.com/encode/httpx) - Modern HTTP client

## License

MIT
