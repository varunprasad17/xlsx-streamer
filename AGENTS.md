# Agent Instructions for XLSX-Streamer Development

## Project Overview

**XLSX-Streamer** is a memory-efficient Python library for streaming large XLSX files and converting them to CSV format. The project supports multiple data sources: **S3**, **HTTP**, and **local files**.

## Current Codebase State

### Key Files & Their Roles

#### Core Streaming Components
- **`src/xlsx_streamer/xlsx_handler.py`** - Main orchestrator, coordinates metadata extraction and row streaming
- **`src/xlsx_streamer/xlsx_generator.py`** - StreamingXlsxReader class, parses worksheet XML with minimal memory
- **`src/xlsx_streamer/xlsx_metadata_extractor.py`** - Extracts shared strings and worksheet paths from XLSX ZIP

#### Source Abstraction Layer
- **`src/xlsx_streamer/sources/base.py`** - StreamSource abstract base class
- **`src/xlsx_streamer/sources/s3.py`** - S3Source implementation
- **`src/xlsx_streamer/sources/http.py`** - HTTPSource implementation
- **`src/xlsx_streamer/sources/local.py`** - LocalFileSource implementation

#### Public API & CLI
- **`src/xlsx_streamer/reader.py`** - XLSXReader unified public API
- **`src/xlsx_streamer/cli.py`** - Command-line interface
- **`src/xlsx_streamer/lib.py`** - Legacy module (deprecated)

#### Tests
- **`tests/test_reader.py`** - Tests for XLSXReader unified API
- **`tests/test_sources_*.py`** - Tests for each source type (S3, HTTP, Local)
- **`tests/test_cli.py`** - CLI tests
- **`tests/test_lib.py`** - Tests for legacy lib

### Current Dependencies
- `stream-unzip` - Memory-efficient ZIP streaming
- `typer-slim` - CLI framework
- `boto3` - AWS S3 client (optional dependency)
- `httpx` - HTTP client (optional dependency)

## Architecture

### Current Architecture
```
User → XLSXReader → StreamSource (S3/HTTP/Local) → Core Parser → CSV Output
```

### Data Flow
1. User provides source (URI string or StreamSource object)
2. XLSXReader auto-detects source type or uses provided StreamSource
3. XlsxHandler coordinates metadata extraction and row streaming
4. StreamingXlsxReader parses worksheet XML with minimal memory
5. Output as CSV or list of row values

## Development Guidelines

### Code Style
- **Type hints required** for all functions and methods
- **Docstrings required** in Google style
- Use `ruff` for linting (already configured)
- Use `mypy` for type checking (strict mode enabled)
- Maximum line length: 99 characters

### Memory Efficiency Principles
1. **Never load entire files into memory**
2. **Stream XML using iterparse**, not fromstring
3. **Clear XML elements after processing** (`elem.clear()`)
4. **Use generators/iterators** instead of lists where possible
5. **Chunk-based processing** for large data

### Testing Requirements
- **Minimum 90% code coverage**
- Unit tests for each source type
- Integration tests for full pipeline
- Use `pytest` fixtures for test data
- Mock external services (S3, HTTP)

## Active Development Tasks

### High Priority
- [ ] **Add MCP (Model Context Protocol) server** - Enable AI assistants to use xlsx-streamer as a tool
  - Implement MCP server with tools for streaming rows, converting to CSV, extracting metadata
  - Support all three source types through MCP
  - Add proper error handling and streaming support

### Medium Priority
- [ ] **Export main classes in `__init__.py`** - Enable `from xlsx_streamer import XLSXReader`
- [ ] **Add comprehensive integration tests** - End-to-end tests with real XLSX files
- [ ] **Performance benchmarking** - Add benchmarks for memory usage and throughput

### Low Priority
- [ ] **Documentation cleanup** - Update README, examples, and docs to remove remaining "fact" references
- [ ] **Add type stub file** - Create `py.typed` for type hint distribution
- [ ] **Docker optimization** - Update Dockerfile if needed

## Common Tasks

### Task 1: Implementing a New StreamSource

**Location**: `src/xlsx_streamer/sources/`

**Template**:
```python
from typing import Iterator, Any
from xlsx_streamer.sources.base import StreamSource

class MySource(StreamSource):
    """Description of the source."""
    
    def __init__(self, **config):
        """Initialize with source-specific config."""
        self.config = config
    
    def get_stream(self) -> Iterator[bytes]:
        """Return byte chunks from source."""
        # Implementation here
        yield b"chunk"
    
    def get_metadata(self) -> dict[str, Any]:
        """Return source metadata."""
        return {"size": 0, "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
```

**Testing checklist**:
- [ ] Test successful streaming
- [ ] Test authentication/authorization
- [ ] Test network errors/retries
- [ ] Test large file handling
- [ ] Test metadata extraction

### Task 2: Adding MCP Tool Support

**Goal**: Enable AI assistants to use xlsx-streamer as an MCP (Model Context Protocol) tool.

**MCP Server Features**:
- `stream_rows` - Stream XLSX rows from any source
- `convert_to_csv` - Convert XLSX to CSV format
- `get_metadata` - Extract sheet metadata (names, dimensions, etc.)
- `query_range` - Extract specific cell ranges

**Implementation**:
```python
# src/xlsx_streamer/mcp_server.py
from mcp.server import Server
from xlsx_streamer.reader import XLSXReader

app = Server("xlsx-streamer")

@app.tool()
def stream_xlsx_rows(source: str, sheet_name: str | None = None) -> Iterator[list]:
    """Stream rows from an XLSX file."""
    reader = XLSXReader(source, sheet_name=sheet_name)
    for row in reader.stream_rows():
        yield row
```

### Task 3: Writing Integration Tests

**Location**: `tests/`

**Example**:
```python
import pytest
from xlsx_streamer.reader import XLSXReader
from xlsx_streamer.sources import S3Source
from moto import mock_aws
import boto3

@mock_aws
def test_s3_full_pipeline():
    """Test complete S3 → CSV pipeline."""
    # Setup mock S3
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    
    # Upload test XLSX
    with open('tests/fixtures/sample.xlsx', 'rb') as f:
        s3.put_object(Bucket='test-bucket', Key='test.xlsx', Body=f)
    
    # Test streaming
    source = S3Source(bucket='test-bucket', key='test.xlsx', client=s3)
    reader = XLSXReader(source)
    
    rows = list(reader.stream_rows())
    assert len(rows) > 0
    assert rows[0] == ['A', 'B', 'C']  # Header
```

## Common Pitfalls to Avoid

### ❌ Don't Do This
```python
# Loading entire file into memory
content = b"".join(stream)
wb = openpyxl.load_workbook(BytesIO(content))

# Using mutable default arguments
def process_row(row, buffer=[]):
    buffer.append(row)

# Hardcoding source types
if self.source_type == "s3":
    # S3 logic
elif self.source_type == "http":
    # HTTP logic
```

### ✅ Do This Instead
```python
# Stream processing
for chunk in stream:
    process_chunk(chunk)

# Proper defaults
def process_row(row, buffer=None):
    if buffer is None:
        buffer = []
    buffer.append(row)

# Polymorphism via protocol
def read_data(source: StreamSource):
    for chunk in source.get_stream():
        yield chunk
```

## Key Algorithms & Concepts

### 1. XLSX Structure
XLSX files are ZIP archives containing:
- `xl/workbook.xml` - Sheet names and relationships
- `xl/worksheets/sheet1.xml` - Actual data
- `xl/sharedStrings.xml` - String pool (memory optimization)
- `xl/_rels/workbook.xml.rels` - Relationship mappings

### 2. Streaming XML Parsing
Use `ET.iterparse()` for memory efficiency:
```python
def stream_parse_worksheet(chunks):
    chunks_stream = IterableToFile(chunks)
    context = ET.iterparse(chunks_stream, events=("start", "end"))
    
    for event, elem in context:
        if event == "end" and elem.tag.endswith("row"):
            yield process_row(elem)
            elem.clear()  # Critical for memory!
```

### 3. Sparse to Dense Row Conversion
Excel XML contains sparse rows (only non-empty cells). Convert to dense:
```python
def sparse_to_dense(sparse_row: dict[int, Any]) -> list[Any]:
    """Convert {2: 'B', 5: 'E'} → ['', '', 'B', '', '', 'E']"""
    if not sparse_row:
        return []
    max_col = max(sparse_row.keys())
    dense = [""] * (max_col + 1)
    for col_idx, value in sparse_row.items():
        dense[col_idx] = value
    return dense
```

### 4. Excel Column Address Parsing
Convert "A", "B", "AA" to indices:
```python
def address_to_index(address: str) -> int:
    """Convert 'B3' → 1, 'AA10' → 26"""
    col_part = "".join(filter(str.isalpha, address.upper()))
    index = 0
    for char in col_part:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1
```

## Entrypoints

### Python API
```python
from xlsx_streamer.reader import XLSXReader
from xlsx_streamer.sources import S3Source, HTTPSource, LocalFileSource

# Auto-detect source type
reader = XLSXReader("s3://bucket/file.xlsx")
reader = XLSXReader("https://example.com/file.xlsx")
reader = XLSXReader("/path/to/file.xlsx")

# Stream rows
for row in reader.stream_rows():
    print(row)

# Convert to CSV
reader.to_csv("output.csv")
```

### CLI
```bash
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
```

## Debugging Tips

### Enable Detailed Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Memory Profiling
```python
from memory_profiler import profile

@profile
def my_function():
    # Your code here
```

### Inspect XML Structure
```bash
# Extract XLSX to see internal structure
unzip test.xlsx -d test_xlsx/
cat test_xlsx/xl/worksheets/sheet1.xml | head -n 50
```

## Git Workflow

### Branch Naming
- Features: `feature/mcp-server`, `feature/http-source`
- Bugs: `bugfix/memory-leak-worksheet-parser`
- Docs: `docs/update-readme`

### Commit Messages
```
feat(mcp): add MCP server implementation

- Implement MCP server with stream_rows tool
- Add CSV conversion tool
- Add metadata extraction tool
- Add tests for MCP server

Closes #123
```

### PR Checklist
- [ ] All tests passing (`uv run nox`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Linting passes (`ruff check src/`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No hardcoded credentials or paths

## Environment Setup

### Quick Start
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run all checks (tests, lint, type check)
uv run nox

# Run specific nox session
uv run nox -s test
uv run nox -s type_check
```

### IDE Setup (VS Code)
Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)

## Performance Targets

- **Memory usage**: < 100MB for files up to 1GB
- **Throughput**: > 10,000 rows/second
- **Startup time**: < 500ms (for local files)

## Security Considerations

### Credentials
- **Never hardcode** AWS credentials
- Use environment variables or AWS profiles
- Support IAM roles for EC2/ECS

### Input Validation
- Validate file sizes before processing
- Sanitize file paths (prevent directory traversal)
- Validate XLSX structure (prevent ZIP bombs)

### Error Messages
- Don't expose internal paths in production
- Sanitize error messages (remove credentials)

## Contact & Resources

### Documentation
- **PLAN.md** - Project roadmap and future plans
- **README.md** - User-facing documentation
- **Code comments** - Implementation details

### External Resources
- [XLSX Format Spec](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-xlsx/)
- [stream-unzip docs](https://github.com/uktrade/stream-unzip)
- [Python typing guide](https://mypy.readthedocs.io/)
- [MCP Protocol](https://modelcontextprotocol.io/)

## Quick Reference Commands

```bash
# Create new branch for feature
git checkout -b feature/my-feature

# Run tests for specific file
uv run pytest tests/sources/test_s3_source.py -v

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Type check specific file
mypy src/xlsx_streamer/sources/s3.py

# Lint and auto-fix
ruff check src/ --fix

# Format code
ruff format src/

# Install optional dependencies
uv sync --extra s3
uv sync --extra http
uv sync --extra all
```

## Version History

- **v0.1.0** - Multi-source support (S3, HTTP, local) - CURRENT
- **v0.2.0** (planned) - MCP server support
- **v1.0.0** (future) - Stable API, full documentation

---

**Remember**: This is a memory-efficient streaming library. Every design decision should prioritize low memory usage and high throughput. When in doubt, stream it!
