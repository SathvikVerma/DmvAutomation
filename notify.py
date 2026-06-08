# notify.py
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PW  = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL  = os.getenv("NOTIFY_EMAIL")
PHONE_DIGITS  = os.getenv("NOTIFY_PHONE_DIGITS")
CARRIER       = os.getenv("CARRIER", "tmomail.net")  # default T-Mobile

CARRIER_GATEWAYS = {
    "tmobile":  "tmomail.net",
    "att":      "txt.att.net",
    "verizon":  "vtext.com",
    "cricket":  "sms.cricketwireless.net",
    "mint":     "tmomail.net",
    "boost":    "sms.myboostmobile.com",
    "sprint":   "messaging.sprintpcs.com",
}


def _smtp_send(to_address: str, subject: str, body: str) -> bool:
    """Shared SMTP helper used by both SMS and email."""
    if not all([GMAIL_ADDRESS, GMAIL_APP_PW]):
        print("  ✗ Gmail credentials missing in .env")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PW)
            server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())
        return True
    except Exception as e:
        print(f"  ✗ SMTP error: {e}")
        return False


def send_sms(slot, phone_digits: str = None, carrier: str = None) -> bool:
    """Send SMS via email-to-text carrier gateway."""
    digits  = phone_digits or PHONE_DIGITS
    gateway = carrier or CARRIER

    if not digits:
        print("  ✗ No phone number configured")
        return False

    from database import is_opted_out
    if is_opted_out(digits):
        print(f"  SMS skipped — {digits} has opted out")
        return False

    sms_address = f"{digits}@{gateway}"

    # Keep SMS short — carrier gateways truncate long messages
    body = (
        f"DMV Slot Alert\n"
        f"{slot.display_datetime}\n"
        f"{slot.office_name} ({slot.distance_mi} mi)\n"
        f"Book: {slot.booking_url}"
    )

    success = _smtp_send(sms_address, "", body)
    if success:
        print(f"  ✓ SMS sent to {sms_address}")
    return success


def send_email(slot, to_email: str = None) -> bool:
    """Send a formatted HTML email notification."""
    recipient = to_email or NOTIFY_EMAIL
    if not recipient:
        print("  ✗ No email address configured")
        return False

    subject = f"DMV Slot: {slot.office_name} — {slot.display_datetime}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; color: #222;">
        <div style="background: #1a56a0; padding: 20px 24px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0; font-size: 20px;">DMV Appointment Available</h2>
        </div>
        <div style="background: #f9f9f9; padding: 24px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
            <p style="font-size: 22px; font-weight: bold; margin: 0 0 4px;">{slot.display_date}</p>
            <p style="font-size: 18px; color: #1a56a0; margin: 0 0 16px;">{slot.display_time}</p>
            <p style="margin: 0 0 4px;"><strong>{slot.office_name}</strong></p>
            <p style="margin: 0 0 4px; color: #555;">{slot.office_address}</p>
            <p style="margin: 0 0 24px; color: #555;">{slot.distance_mi} miles away</p>
            <a href="{slot.booking_url}"
               style="display: inline-block; background: #1a56a0; color: white;
                      padding: 12px 28px; text-decoration: none; border-radius: 6px;
                      font-size: 16px; font-weight: bold;">
              Book This Slot →
            </a>
            <p style="color: #aaa; font-size: 12px; margin-top: 32px;">
              Sent by DMV Notifier · Reply STOP to unsubscribe
            </p>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PW)
            server.sendmail(GMAIL_ADDRESS, recipient, msg.as_string())
        print(f"  ✓ Email sent to {recipient}")
        return True
    except Exception as e:
        print(f"  ✗ Email failed: {e}")
        return False


def notify_new_slots(slots: list, prefs: dict = None) -> int:
    """
    Filter to new slots only, apply user prefs, send notifications.
    Returns count of notifications sent.
    """
    from database import (
        init_db, save_slot, mark_notified, is_new_slot,
        can_notify_now, update_last_notified
    )

    init_db()

    if prefs is None:
        prefs = {}

    max_slots        = prefs.get("max_slots", 3)
    notify_frequency = prefs.get("notify_frequency", "realtime")
    phone_digits     = prefs.get("phone_digits", PHONE_DIGITS)
    email            = prefs.get("email", NOTIFY_EMAIL)

    # Check notification frequency throttle
    if phone_digits and not can_notify_now(phone_digits, notify_frequency):
        print(f"  Skipping — {notify_frequency} limit not yet reached")
        return 0

    # Sort by date then time, pick only new slots
    new_slots = []
    for slot in sorted(slots, key=lambda s: (s.slot_date, s.slot_time)):
        if is_new_slot(slot.slot_key):
            new_slots.append(slot)
        if len(new_slots) >= max_slots:
            break

    if not new_slots:
        print("  No new slots since last check.")
        return 0

    sent_count = 0
    for slot in new_slots:
    print(f"\n  New slot: {slot.display_datetime} at {slot.office_name}")
    save_slot(slot)

    sms_sent   = send_sms(slot, phone_digits=phone_digits)
    time.sleep(2)  # wait 2 seconds between SMS sends
    email_sent = send_email(slot, to_email=email)

    if sms_sent or email_sent:
        mark_notified(slot.slot_key)
        sent_count += 1

    if sent_count > 0 and phone_digits:
        update_last_notified(phone_digits)

    return sent_count


if __name__ == "__main__":
    print("Run python scraper.py to test the full pipeline.")
    print("Or run python main.py to start the scheduler.")