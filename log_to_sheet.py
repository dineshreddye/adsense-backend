import gspread
import json
import os  # <-- ✅ Needed to access environment variable
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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
    SHEET_NAME = "Compliance"  # 👈 make sure this matches your sheet name
    sheet = client.open(SHEET_NAME).worksheet("logs")

except Exception as e:
    print("❌ Failed to connect to Google Sheets:", e)
    sheet = None

def log_ad_check(data: dict):
    if not sheet:
        print("⚠️ Sheet is not initialized. Skipping log.")
        return

    try:

        headlines = data.get("headline", [])
        descriptions = data.get("description", [])
        
        row = [
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("source", ""),
            data.get("url", ""),
            "\n".join(headlines) if isinstance(headlines, list) else headlines,
            "\n".join(descriptions) if isinstance(descriptions, list) else descriptions,
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
