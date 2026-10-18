"""Local Mac watcher: persistent Chrome session, no cloud CAPTCHA bypass."""
import fcntl
import getpass
import hashlib
import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from monitor import TABLE_URL, notify, observe

APP = Path.home() / "Library" / "Application Support" / "ajax-ticket-watch"
APP.mkdir(parents=True, exist_ok=True)
APP.chmod(0o700)
CONFIG = APP / "mail.json"
STATE = APP / "local-state.json"

def configure_mail():
    import keyring
    if keyring.get_keyring().priority <= 0:
        raise RuntimeError("A secure OS Keychain backend is required; no plaintext fallback.")
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text())
    else:
        print("Email setup is stored only on this Mac.")
        sender = input("Sending Gmail address: ").strip()
        recipient = input("Alert recipient (Enter = same address): ").strip() or sender
        if not sender or "@" not in sender or "@" not in recipient:
            raise RuntimeError("Enter valid sending and recipient addresses.")
        config = {"sender": sender, "recipient": recipient}
        CONFIG.write_text(json.dumps(config))
        CONFIG.chmod(0o600)
    password = keyring.get_password("ajax-ticket-watch-smtp", config["sender"])
    if not password:
        print("Use a Gmail app password, not your normal Google password.")
        password = getpass.getpass("Gmail app password (hidden): ").replace(" ", "")
        if not password:
            raise RuntimeError("App password is required for email alerts.")
        keyring.set_password("ajax-ticket-watch-smtp", config["sender"], password)
    os.environ.update(SMTP_HOST="smtp.gmail.com", SMTP_USER=config["sender"],
                      SMTP_PASSWORD=password, MAIL_FROM=config["sender"],
                      MAIL_TO=config["recipient"])
    # Verify email delivery independently of ticket availability.
    if not config.get("tested"):
        notify([{"setup_test": True, "message": "Setup test only; no tickets detected."}], setup_test=True)
        config["tested"] = True
        CONFIG.write_text(json.dumps(config))
        CONFIG.chmod(0o600)
        print("Setup email delivered to the configured recipient.")

def save(state):
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2))
    temporary.chmod(0o600)
    temporary.replace(STATE)

def main():
    lock = open(APP / "watch.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("A watcher is already running. Close the other watcher before starting another.")
        return
    configure_mail()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(APP / "chrome-profile"), channel="chrome", headless=False, locale="en-GB")
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(TABLE_URL, wait_until="domcontentloaded", timeout=60000)
        print("Sign in to Ajax in the Chrome window. If verification appears, complete it yourself.")
        print("Open the Ajax–ADO event table. Do not add anything to the cart.")
        input("When the event table is visible, press Enter here: ")
        print("Monitoring every 5 minutes. Keep this Terminal and Chrome open; keep the Mac awake.")
        print("Press Ctrl+C to stop. Login sessions and mail credentials are never uploaded.")
        while True:
            try:
                response = page.goto(TABLE_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(8000)
                status, offers = observe(page, response.status if response else 200)
                state["status"] = status
                state["offers"] = offers
                save(state)
                print(time.strftime("%Y-%m-%d %H:%M:%S"), status, json.dumps(offers), flush=True)
                if status not in ("available_indication", "below_threshold"):
                    print("Access/layout/login needs your attention. No availability alert sent.")
                    input("Resolve it manually in Chrome, then press Enter to resume: ")
                    continue
                if status == "available_indication":
                    fingerprint = hashlib.sha256(json.dumps(offers, sort_keys=True).encode()).hexdigest()
                    if fingerprint not in state.get("notified", []):
                        notify(offers)
                        state["notified"] = state.get("notified", []) + [fingerprint]
                        save(state)
                        print("Ticket alert sent.", flush=True)
            except KeyboardInterrupt:
                break
            except Exception as error:
                # No browser call diagnostics or credential-bearing exceptions.
                print("Check failed:", type(error).__name__, "No alert recorded. Will retry in 5 minutes.", flush=True)
            page.wait_for_timeout(300000)
        context.close()

if __name__ == "__main__":
    main()
