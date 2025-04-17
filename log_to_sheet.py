import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# Define the scope and credentials
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load the credentials
try:
    creds_json = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    SHEET_NAME = "Compliance"  # Change this to your actual sheet name
    sheet = client.open(SHEET_NAME).sheet1
except Exception as e:
    print("❌ Failed to connect to Google Sheets:", e)
    sheet = None

def log_ad_check(data: dict):
    if not sheet:
        print("⚠️ Sheet is not initialized. Skipping log.")
        return

    try:
        row = [
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("source", ""),
            data.get("url", ""),
            data.get("headline", ""),
            data.get("description", ""),
            data.get("primary_text", ""),
            data.get("keywords", ""),
            data.get("image_count", 0),
            str(data.get("compliant")),
            data.get("relevancy_score", ""),
            data.get("image_score", ""),
            ", ".join(data.get("issues", [])),
            ", ".join(data.get("suggestions", [])),
        ]
        sheet.append_row(row)
        print("✅ Logged to Google Sheet")
    except Exception as e:
        print("❌ Failed to write to Google Sheet:", e)
