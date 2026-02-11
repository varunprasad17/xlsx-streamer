"""Example: Reading XLSX from AWS S3."""

from xlsx_streamer.reader import XLSXReader

# Read from S3 using URI (auto-detection)
reader = XLSXReader("s3://my-bucket/path/to/file.xlsx", sheet_name="Sheet1")

# Or use explicit S3Source for more control
# from xlsx_streamer.sources import S3Source
# import boto3
# s3_client = boto3.client("s3", region_name="us-east-1")
# source = S3Source(bucket="my-bucket", key="path/to/file.xlsx", client=s3_client)
# reader = XLSXReader(source, sheet_name="Sheet1")

# Stream rows
print("Sheet metadata:", reader.get_metadata())
print("\nRows:")
try:
    row_iterator = enumerate(reader.stream_rows(), 1)
    while True:
        # Fetch and print the next 10 rows
        rows_in_batch = 0
        for _ in range(10):
            try:
                i, row = next(row_iterator)
                print(f"Row {i}: {row}")
                rows_in_batch += 1
            except StopIteration:
                print("\n--- End of file ---")
                break  # Exit inner for loop

        if rows_in_batch < 10:
            # Reached end of file
            break  # Exit outer while loop

        # Wait for user input
        user_input = input("\nPress Enter for next 10 rows, or type 'q' and Enter to quit: ")
        if user_input.lower() == "q":
            break
except KeyboardInterrupt:
    print("\nUser interrupted. Exiting.")
