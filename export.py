import csv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Name of the stable spreadsheet (must match the name used by the app)
SPREADSHEET_NAME = "the-bones-db-stable"

# Output directory for CSV files
OUTPUT_DIR = "tables"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

sheets_service = build("sheets", "v4", credentials=creds)
drive_service  = build("drive",  "v3", credentials=creds)

# Resolve spreadsheet ID by name, same way the app does
def find_spreadsheet_id(name: str) -> str:
    escaped = name.replace("'", "\\'")
    query = f"name='{escaped}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    result = drive_service.files().list(q=query, fields="files(id,name)").execute()
    files = result.get("files", [])
    if not files:
        raise RuntimeError(f"No spreadsheet named '{name}' found in Drive. "
                           "Make sure the service account has access to it.")
    if len(files) > 1:
        print(f"  Warning: {len(files)} spreadsheets named '{name}' found; using the first one.")
    return files[0]["id"]

file_id = find_spreadsheet_id(SPREADSHEET_NAME)
print(f"Using spreadsheet '{SPREADSHEET_NAME}' → {file_id}")

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
