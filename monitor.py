"""Ajax table monitor. Never adds tickets to cart or bypasses access controls."""
import hashlib
import json
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

URL = "https://tickets.ajax.nl/selection/event/seat?perfId=10229728133611&ot=0&gtmStepTracking=true"
TABLE_URL = "https://tickets.ajax.nl/selection/event/seat?perfId=10229728133611&table=1&productId=10229728196808"
STATE = Path("state.json")
EXCLUDED = re.compile(r"\b(vip|premium|hospitality|business|skybox)\b", re.I)
ALLOWED = {"regulier", "regular", "official resale"}
def diagnose(page, response, stage):
    # Only called before entering credentials. Never record cookies, tokens,
    # request headers, query strings, authentication forms or account pages.
    if not response:
        print("Diagnostic:", stage, "no document response")
        return
    parsed = urlsplit(page.url)
    data = {"stage": stage, "status": response.status,
            "origin_path": parsed.scheme + "://" + parsed.netloc + parsed.path,
            "server": response.headers.get("server", ""),
            "content_type": response.headers.get("content-type", "")}
    if response.status >= 400:
        body = page.locator("body").inner_text(timeout=10000)[:2000]
        body = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[email]", body)
        body = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[ip]", body)
        body = re.sub(r"[A-Za-z0-9_./+=-]{60,}", "[long token]", body)
        data["error_text"] = body
    print("Diagnostic:", json.dumps(data))

def sign_in(page):
    email = os.environ.get("AJAX_EMAIL")
    password = os.environ.get("AJAX_PASSWORD")
    if not email or not password:
        return "ajax_credentials_required"
    try:
        # Follow the ordinary public storefront navigation before sign-in.
        # This establishes only the site's normal first-party session cookies.
        response = page.goto("https://tickets.ajax.nl/content", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        diagnose(page, response, "storefront")
        if response and response.status >= 400:
            return "storefront_http_" + str(response.status)
        links = page.get_by_role("link", name="Sign in", exact=True)
        if links.count() != 1:
            return "signin_link_missing"
        with page.expect_navigation(wait_until="domcontentloaded", timeout=60000) as navigation:
            links.click()
        response = navigation.value
        page.wait_for_timeout(5000)
        diagnose(page, response, "signin")
        text = page.locator("body").inner_text().lower()
        if response and response.status >= 400:
            return "login_http_" + str(response.status)
        if any(s in text for s in ["captcha", "verify you are human", "access denied"]):
            return "login_blocked"
        page.get_by_role("textbox", name="Email Address", exact=True).fill(email)
        page.get_by_label("Password", exact=True).fill(password)
        page.get_by_label("Password", exact=True).press("Enter")
        page.wait_for_timeout(8000)
        if page.locator('input[type="password"]').count():
            return "login_failed_or_interactive_verification_required"
        return None
    except Exception:
        # Do not log credential-bearing browser call diagnostics.
        return "login_error"

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Optional session JSON must be supplied as an encrypted Actions secret.
        # Never persist authentication state in the repository or logs.
        session = os.environ.get("AJAX_STORAGE_STATE")
        context = browser.new_context(locale="en-GB", **({"storage_state": json.loads(session)} if session else {}))
        page = context.new_page()
        if os.environ.get("AJAX_EMAIL") and os.environ.get("AJAX_PASSWORD"):
            auth_error = sign_in(page)
            if auth_error:
                return auth_error, []
        response = page.goto(TABLE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)
        return observe(page, response.status if response else 200)

def observe(page, http_status=200):
    text = page.locator("body").inner_text().lower()
    if http_status >= 400:
        return "http_" + str(http_status), []
    if any(s in text for s in ["verify you are human", "access denied", "security check", "captcha"]):
        return "blocked", []
    if page.locator('input[type="password"]').count() or "b2clogin" in page.url:
        return "login_required", []
    if "requested url was not found" in text or "error page" in text:
        return "invalid_event_or_login_required", []
    if "ado den haag" not in text or "22 november 2026" not in text:
        return "wrong_or_unknown_event", []
    # Selectors observed on the real event table, 2026-10-18.
    rows = page.locator('tr').filter(has=page.locator('select[aria-label="Quantity"]'))
    if rows.count() == 0:
        return "unknown_layout", []
    categories = {}
    offers = []
    for row in rows.all():
        if not row.is_visible():
            continue
        label = row.inner_text()
        if EXCLUDED.search(label):
            continue
        tariff = row.locator(".audience-subcat-name")
        category = row.locator("th.category")
        if tariff.count() != 1 or category.count() != 1:
            return "unknown_layout", []
        rate = tariff.inner_text().strip()
        if rate.casefold() not in ALLOWED:
            # Unknown rates cannot be assumed regular.
            continue
        select = row.locator('select[aria-label="Quantity"]')
        values = select.locator("option:not([disabled])").evaluate_all("(els) => els.map(e => e.value)")
        quantities = [int(v) for v in values if v.isdigit()]
        if not quantities or select.is_disabled():
            continue
        maximum = max(quantities)
        cat = category.inner_text().strip()
        # Multiple tariffs can share inventory: never add their quantities.
        categories[cat] = max(categories.get(cat, 0), maximum)
        if maximum:
            offers.append({"category": cat, "rate": rate, "max_quantity": maximum})
    # Distinct seat categories partition inventory. For multiple tariffs
    # within the same category, count only the maximum to avoid overlap.
    available = sum(categories.values()) >= 2
    return ("available_indication" if available else "below_threshold"), sorted(offers, key=lambda x: (x["category"], x["rate"]))

def notify(offers):
    os.environ["SMTP_HOST"] = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    os.environ["MAIL_FROM"] = os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER", "")
    keys = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM", "MAIL_TO"]
    if any(not os.environ.get(k) for k in keys):
        raise RuntimeError("SMTP secrets missing; alert not recorded as sent")
    msg = EmailMessage()
    msg["Subject"] = "Ajax: indication of at least two regular tickets"
    msg["From"] = os.environ["MAIL_FROM"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content("The Ajax quantity selector offers at least 2 regular / Official Resale tickets. Checkout availability is unverified. No tickets reserved.\n" + TABLE_URL + "\n" + json.dumps(offers))
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)

def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    status, offers = inspect()
    state["status"] = status
    state["offers"] = offers
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print("Observation:", status, "offers:", json.dumps(offers))
    if status == "available_indication":
        fingerprint = hashlib.sha256(json.dumps(offers, sort_keys=True).encode()).hexdigest()
        if fingerprint not in state.get("notified", []):
            notify(offers)
            state["notified"] = state.get("notified", []) + [fingerprint]
            STATE.write_text(json.dumps(state, indent=2) + "\n")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as f:
        f.write("### Ajax observation\nStatus: " + status + "\nOffers: " + json.dumps(offers) + "\n")
    if status not in ("available_indication", "below_threshold"):
        raise RuntimeError("Availability unverified: " + status)

if __name__ == "__main__":
    main()
