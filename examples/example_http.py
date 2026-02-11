"""Example: Reading XLSX from HTTP/HTTPS URL."""

from xlsx_streamer.reader import XLSXReader

# Read from HTTP URL (auto-detection)
reader = XLSXReader(
    "https://docs.google.com/spreadsheets/d/1X6fZkSA9jW2IXBG6PikePKsgJK_T3hRz/edit?usp=sharing&ouid=106673592111793778775&rtpof=true&sd=true"
)

# Or use explicit HTTPSource for authentication
# from xlsx_streamer.sources import HTTPSource
# source = HTTPSource(
#     url="https://example.com/path/to/file.xlsx",
#     headers={"Authorization": "Bearer token123"},
#     timeout=60,
# )
# reader = XLSXReader(source, sheet_name="Sheet1")

# Stream rows
print("Source metadata:", reader.get_metadata())
print("\nRows:")
for i, row in enumerate(reader.stream_rows(), 1):
    print(f"Row {i}: {row}")
    if i >= 10:  # Print first 10 rows
        break

# # Or convert directly to CSV
# reader.to_csv("output.csv")
# print("\nCSV exported to output.csv")
