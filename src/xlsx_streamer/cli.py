"""Command-line interface for XLSX streaming."""

import logging
import sys

import typer

from xlsx_streamer.reader import XLSXReader

app = typer.Typer(add_completion=False)


@app.command()
def main(
    source: str = typer.Argument(
        ...,
        help="Data source: s3://bucket/key, https://url, or /path/to/file.xlsx",
    ),
    sheet_name: str | None = typer.Option(
        None,
        help="Sheet name to read (default: first sheet)",
    ),
    output: str | None = typer.Option(
        None,
        help="Output CSV file path (default: stdout)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Stream XLSX files to CSV format from any source.

    Sources:
    - Local files: /path/to/file.xlsx
    - S3: s3://bucket/key
    - HTTP/HTTPS: https://example.com/file.xlsx
    """
    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        # Create reader
        reader = XLSXReader(source, sheet_name=sheet_name)

        # Output to file or stdout
        if output:
            reader.to_csv(output)
            typer.echo(f"CSV written to: {output}", file=sys.stderr)
        else:
            for row_bytes in reader.handler.stream_rows():
                sys.stdout.buffer.write(row_bytes)

    except FileNotFoundError as e:
        typer.echo(f"Error: File not found: {e}", err=True)
        raise typer.Exit(code=1) from None
    except ImportError as e:
        typer.echo(
            f"Error: Missing dependency: {e}\nInstall with: pip install xlsx-streamer[all]",
            err=True,
        )
        raise typer.Exit(code=1) from None
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc(file=sys.stderr)
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
