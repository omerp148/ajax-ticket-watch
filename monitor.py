"""Read-only monitoring. Unknown/error pages never imply sold out or availability."""
import json
import os
import re
import ssl
import smtplib
from pathlib import Path
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

URL = "https://tickets.ajax.nl/selection/event/seat?perfId=10229728133611&ot=0&gtmStepTracking=true"
STATE = Path("state.json")

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="en-GB")
        response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)
        text = page.locator("body").inner_text().lower()
        if response and response.status >= 400:
            return "http_error", []
        if "requested url was not found" in text or "error page" in text:
            return "invalid_event_url", []
        if any(s in text for s in ["verify you are human", "access denied", "security check", "captcha"]):
            return "blocked", []
        if page.locator('input[type="password"]').count() or "b2clogin" in page.url:
            return "login_required", []
        # Must be populated only after inspecting the actual event's rendered DOM.
        # Never infer quantity from global page numbers, prices, or generic Buy links.
        cfg = json.loads(Path("selectors.json").read_text()) if Path("selectors.json").exists() else {}
        if cfg.get("verified_event") != "10229728133611":
            return "adapter_not_verified", []
        root = page.locator(cfg["event_root"])
        if root.count() != 1 or not root.is_visible():
            return "unknown_layout", []
        ids = set()
        for row in root.locator(cfg["ticket_row"]).all():
            if not row.is_visible() or re.search(r"\b(vip|premium|hospitality|business|skybox)\b", row.inner_text(), re.I):
                continue
            kind = row.locator(cfg["ticket_type"]).inner_text().strip()
            if kind not in cfg["allowed_types"]:
                continue
            if not row.locator(cfg["available_marker"]).is_visible():
                continue
            seat = row.get_attribute(cfg["seat_id_attribute"])
            if not seat:
                return "unknown_layout", []
            ids.add(seat)
        return ("available" if len(ids) >= 2 else "below_threshold"), sorted(ids)

def notify(ids):
    keys = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM", "MAIL_TO"]
    if any(not os.environ.get(k) for k in keys):
        raise RuntimeError("SMTP secrets missing; notification NOT recorded as sent")
    msg = EmailMessage()
    msg["Subject"] = "Ajax: at least two regular tickets detected"
    msg["From"] = os.environ["MAIL_FROM"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content("Regular / Official Resale tickets detected. Availability can change; no seats reserved.\n" + URL)
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)

def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    status, ids = inspect()
    state["status"] = status
    print("Observation:", status, "eligible seats:", len(ids))
    # Persist observations, but only successful email delivery marks a set as notified.
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    if status == "available":
        fingerprint = "|".join(ids)
        sent = state.get("notified", [])
        if fingerprint not in sent:
            notify(ids)
            state["notified"] = sent + [fingerprint]
            STATE.write_text(json.dumps(state, indent=2) + "\n")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as f:
        f.write("### Ajax observation\nStatus: " + status + "\nEligible seats: " + str(len(ids)) + "\n")
    if status not in ("available", "below_threshold"):
        raise RuntimeError("Availability is unverified: " + status)

if __name__ == "__main__":
    main()
