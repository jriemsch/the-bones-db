import csv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

# Output directory for CSV files
OUTPUT_DIR = "tables"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

sheets_service = build("sheets", "v4", credentials=creds)

file_id = "1jId8lX1aDgY5K-jU3j4xaqNj7CaCiD9Sto7hts5QFHc"

# Get sheet metadata to find all sheets
sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
sheets_list = sheet_metadata.get("sheets", [])

print(f"Found {len(sheets_list)} sheet(s) in the spreadsheet")

for sheet in sheets_list:
    title = sheet["properties"]["title"]
    sheet_id = sheet["properties"]["sheetId"]
    
    print(f"Downloading sheet: {title}")
    
    # Get the data from the sheet using A1 notation (gets all data)
    range_name = f"'{title}'"
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=file_id,
        range=range_name
    ).execute()
    
    values = result.get("values", [])
    
    if not values:
        print(f"  Warning: Sheet '{title}' is empty, skipping")
        continue
    
    # Write to CSV file
    # Sanitize filename to remove invalid characters
    safe_filename = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    if not safe_filename:
        safe_filename = f"sheet_{sheet_id}"
    
    csv_filename = os.path.join(OUTPUT_DIR, f"{safe_filename}.csv")
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(values)
    
    print(f"  ✓ Saved to {csv_filename} ({len(values)} rows)")

print(f"\nCompleted! Downloaded {len(sheets_list)} sheet(s) to {OUTPUT_DIR}/")
