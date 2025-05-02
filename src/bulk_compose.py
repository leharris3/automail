import argparse
import base64
import csv
import os
import pathlib
import sys
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"


# ────────────────────────────────────────────────────────────── auth
def get_service():
    """Return an authenticated Gmail service resource."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ─────────────────────────────────────────────────────── helpers
def create_message(row: dict, subject_fmt: str, body_template: str, sender: str) -> dict:
    """Create a MIME e‑mail and wrap it for the Gmail API."""
    msg = EmailMessage()
    msg["To"] = row["email"]
    msg["From"] = sender
    msg["Subject"] = subject_fmt.format(**row)
    msg.set_content(body_template.format(**row))

    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": encoded}


def send_message(service, message):
    """Send one message with the Gmail API."""
    return service.users().messages().send(userId="me", body=message).execute()


# ──────────────────────────────────────────────────────────── cli
def main():
    ap = argparse.ArgumentParser(description="Simple Gmail mail‑merge CLI")
    ap.add_argument("--csv", required=True, type=pathlib.Path)
    ap.add_argument("--template", required=True, type=pathlib.Path)
    ap.add_argument("--subject", required=True, help="Subject line (may contain {placeholders})")
    ap.add_argument("--from", dest="sender", required=True, help='"Name <addr@example.com>"')
    ap.add_argument("--dry-run", action="store_true", help="Just print; don’t send")
    args = ap.parse_args()

    body_template = args.template.read_text()
    rows = list(csv.DictReader(args.csv.open()))

    service = None if args.dry_run else get_service()

    for i, row in enumerate(rows, 1):
        try:
            message = create_message(row, args.subject, body_template, args.sender)
            if args.dry_run:
                print(f"[DRY‑RUN] Would send to {row['email']}")
            else:
                send_message(service, message)
                print(f"✓ Sent to {row['email']}  ({i}/{len(rows)})")
        except HttpError as e:
            print(f"‼️  Error sending to {row['email']}: {e}")
        except KeyError as e:
            print(f"‼️  Missing column {e} in CSV; skipping {row.get('email')}")
        # Gmail’s per‑second user quota is tight (250 QP / s); one send = 100 QP.
        # Small merges usually don’t need a sleep, but if you hit 403 rate limits,
        # add    time.sleep(1)

if __name__ == "__main__":
    sys.exit(main())
