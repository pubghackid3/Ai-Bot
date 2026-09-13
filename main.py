"""Ultra SMS Forwarder Bot v18 - Final Premium Edition
Features:
  • Owner-only commands | Public buttons for group members
  • Beautiful animated message cards
  • Country flags + SIM operator + App detection
  • Smart OTP with confidence score
  • Analytics, Intruder log, Block system, CSV export
  • Fixed loop (no repeat), 409 handling
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import aiosqlite
import httpx
import phonenumbers

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════
GREEN_SMS_API = "http://147.135.212.197/crapi/had/viewstats"
GREEN_SMS_API_KEY = "Qk5VR0RBUzRndWVCgG6Bfnp0d3RHbpNTVGCFQ2NpmHtfblVrhJZTig=="
TELEGRAM_GROUP_ID = "-1004330079864"
TELEGRAM_OWNER_ID = 8762845215
TELEGRAM_CHANNEL_URL = "https://t.me/RN_OTP_1"
BOT_USERNAME = "RN_OTP_PROVIDER_BOT"
BUTTON_BOT_USERNAME = "RN_OTP1_bot"
BOT_TOKEN = "8683238433:AAFfJx-3ZT-Qrll-vZxq0toogD9_skFsxv4"

POLL_SECONDS = 5
DATABASE_FILE = "sms_telegram_bot.sqlite3"
MAX_RECORDS = 200
MAX_BATCHES = 100
CLEANUP_DAYS = 30
ANIMATION_ENABLED = True
PKT_OFFSET_HOURS = 5

# ═══════════════════════════════════════════════════════

runtime_last_error = None
runtime_last_poll = None
http_client = None
current_api_index = 0
api_keys = []
blocked_users = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("greensms_bot")

# ═══════════════════════════════════════════════════════
# EMOJI & DESIGN CONSTANTS
# ═══════════════════════════════════════════════════════
E_BELL = "\U0001F514"
E_CLIP = "\U0001F4CB"
E_EYES = "\U0001F440"
E_MEGA = "\U0001F4E2"
E_BOT = "\U0001F916"
E_CROSS = "\u274C"
E_CHECK = "\u2705"
E_GREEN = "\U0001F7E2"
E_RED = "\U0001F534"
E_YELLOW = "\U0001F7E1"
E_BLUE = "\U0001F535"
E_KEY = "\U0001F511"
E_OLDKEY = "\U0001F5DD"
E_CHART = "\U0001F4CA"
E_OUT = "\U0001F4E4"
E_HOUR = "\u23F3"
E_USER = "\U0001F464"
E_CLOCK = "\U0001F550"
E_TIME = "\U0001F552"
E_MSG = "\U0001F4AC"
E_ROCKET = "\U0001F680"
E_FILE = "\U0001F4C1"
E_DB = "\U0001F5C4"
E_BOLT = "\u26A1"
E_GLOBE = "\U0001F310"
E_SPARKLE = "\u2728"
E_DIAMOND = "\U0001F48E"
E_CROWN = "\U0001F451"
E_TAG = "\U0001F3F7"
E_SCROLL = "\U0001F4DC"
E_PHONE = "\U0001F4DE"
E_SIGNAL = "\U0001F4F6"
E_SHIELD = "\U0001F6E1"
E_CAL = "\U0001F4C5"
E_LOCK = "\U0001F510"
E_STAR = "\u2B50"
E_FIRE = "\U0001F525"
E_INBOX = "\U0001F4E9"
E_BOX = "\U0001F4E6"
E_MAGIC = "\U0001FA84"

DIVIDER = "\u2501" * 16
DIV_SHORT = "\u2501" * 10
DOT = "\u2022"

# ═══════════════════════════════════════════════════════
# COUNTRY DATA
# ═══════════════════════════════════════════════════════
COUNTRIES = {
    "PK": ("\U0001F1F5\U0001F1F0", "Pakistan"),
    "US": ("\U0001F1FA\U0001F1F8", "United States"),
    "GB": ("\U0001F1EC\U0001F1E7", "United Kingdom"),
    "IN": ("\U0001F1EE\U0001F1F3", "India"),
    "CA": ("\U0001F1E8\U0001F1E6", "Canada"),
    "AU": ("\U0001F1E6\U0001F1FA", "Australia"),
    "DE": ("\U0001F1E9\U0001F1EA", "Germany"),
    "FR": ("\U0001F1EB\U0001F1F7", "France"),
    "IT": ("\U0001F1EE\U0001F1F9", "Italy"),
    "ES": ("\U0001F1EA\U0001F1F8", "Spain"),
    "BR": ("\U0001F1E7\U0001F1F7", "Brazil"),
    "MX": ("\U0001F1F2\U0001F1FD", "Mexico"),
    "JP": ("\U0001F1EF\U0001F1F5", "Japan"),
    "CN": ("\U0001F1E8\U0001F1F3", "China"),
    "RU": ("\U0001F1F7\U0001F1FA", "Russia"),
    "ZA": ("\U0001F1FF\U0001F1E6", "South Africa"),
    "NG": ("\U0001F1F3\U0001F1EC", "Nigeria"),
    "EG": ("\U0001F1EA\U0001F1EC", "Egypt"),
    "SA": ("\U0001F1F8\U0001F1E6", "Saudi Arabia"),
    "AE": ("\U0001F1E6\U0001F1EA", "UAE"),
    "BD": ("\U0001F1E7\U0001F1E9", "Bangladesh"),
    "ID": ("\U0001F1EE\U0001F1E9", "Indonesia"),
    "MY": ("\U0001F1F2\U0001F1FE", "Malaysia"),
    "SG": ("\U0001F1F8\U0001F1EC", "Singapore"),
    "HK": ("\U0001F1ED\U0001F1F0", "Hong Kong"),
    "TR": ("\U0001F1F9\U0001F1F7", "Turkey"),
    "PL": ("\U0001F1F5\U0001F1F1", "Poland"),
    "UA": ("\U0001F1FA\U0001F1E6", "Ukraine"),
    "RO": ("\U0001F1F7\U0001F1F4", "Romania"),
    "NL": ("\U0001F1F3\U0001F1F1", "Netherlands"),
    "BE": ("\U0001F1E7\U0001F1EA", "Belgium"),
    "CH": ("\U0001F1E8\U0001F1ED", "Switzerland"),
    "AT": ("\U0001F1E6\U0001F1F9", "Austria"),
    "SE": ("\U0001F1F8\U0001F1EA", "Sweden"),
    "NO": ("\U0001F1F3\U0001F1F4", "Norway"),
    "DK": ("\U0001F1E9\U0001F1F0", "Denmark"),
    "FI": ("\U0001F1EB\U0001F1EE", "Finland"),
    "IE": ("\U0001F1EE\U0001F1EA", "Ireland"),
    "PT": ("\U0001F1F5\U0001F1F9", "Portugal"),
    "GR": ("\U0001F1EC\U0001F1F7", "Greece"),
    "KR": ("\U0001F1F0\U0001F1F7", "South Korea"),
    "NZ": ("\U0001F1F3\U0001F1FF", "New Zealand"),
    "TW": ("\U0001F1F9\U0001F1FC", "Taiwan"),
    "TH": ("\U0001F1F9\U0001F1ED", "Thailand"),
    "VN": ("\U0001F1FB\U0001F1F3", "Vietnam"),
    "PH": ("\U0001F1F5\U0001F1ED", "Philippines"),
}

PREFIX_FALLBACK = [
    ("92", "PK"), ("44", "GB"), ("91", "IN"), ("880", "BD"),
    ("62", "ID"), ("60", "MY"), ("65", "SG"), ("852", "HK"),
    ("90", "TR"), ("48", "PL"), ("380", "UA"), ("40", "RO"),
    ("31", "NL"), ("32", "BE"), ("41", "CH"), ("43", "AT"),
    ("46", "SE"), ("47", "NO"), ("45", "DK"), ("358", "FI"),
    ("353", "IE"), ("351", "PT"), ("30", "GR"), ("27", "ZA"),
    ("234", "NG"), ("20", "EG"), ("966", "SA"), ("971", "AE"),
    ("7", "RU"), ("86", "CN"), ("81", "JP"), ("82", "KR"),
    ("61", "AU"), ("64", "NZ"), ("55", "BR"), ("52", "MX"),
    ("49", "DE"), ("33", "FR"), ("39", "IT"), ("34", "ES"),
    ("886", "TW"), ("66", "TH"), ("84", "VN"), ("63", "PH"),
    ("1", "US"),
]

APP_LOGOS = {
    "whatsapp": "\U0001F4F1", "telegram": "\u2708\uFE0F",
    "instagram": "\U0001F4F8", "facebook": "\U0001F535",
    "twitter": "\U0001F426", "tiktok": "\U0001F3B5",
    "snapchat": "\U0001F47B", "discord": "\U0001F3AE",
    "youtube": "\U0001F4FA", "linkedin": "\U0001F4BC",
    "google": "\U0001F50D", "gmail": "\U0001F4E7",
    "microsoft": "\U0001F7EA", "apple": "\U0001F34E",
    "amazon": "\U0001F4E6", "netflix": "\U0001F3AC",
    "paypal": "\U0001F4B3", "binance": "\U0001F4B0",
    "coinbase": "\U0001FA99", "uber": "\U0001F697",
    "airbnb": "\U0001F3E0", "reddit": "\U0001F47D",
    "pinterest": "\U0001F4CC", "skype": "\u260E\uFE0F",
    "zoom": "\U0001F3A5", "signal": "\U0001F512",
    "viber": "\U0001F4DE", "line": "\U0001F4AC",
    "wechat": "\U0001F49A", "imo": "\U0001F4F2",
    "truecaller": "\U0001F4DE", "bank": "\U0001F3E6",
    "hdfc": "\U0001F3E6", "icici": "\U0001F3E6",
    "sbi": "\U0001F3E6", "paytm": "\U0001F4B8",
    "phonepe": "\U0001F4B8", "gpay": "\U0001F4B8",
    "default": "\U0001F4E9",
}

APP_KEYWORDS = [
    ("whatsapp",  ["whatsapp", "whats app", "wa code", "wa-", "wa otp"]),
    ("telegram",  ["telegram", "tg code", "tg-", "telegram code"]),
    ("instagram", ["instagram", "ig code", "ig-", "insta"]),
    ("facebook",  ["facebook", "fb code", "fb-", "meta"]),
    ("twitter",   ["twitter", "x code", "tweet"]),
    ("tiktok",    ["tiktok", "tik tok"]),
    ("snapchat",  ["snapchat", "snap"]),
    ("discord",   ["discord"]),
    ("youtube",   ["youtube", "yt code"]),
    ("linkedin",  ["linkedin"]),
    ("google",    ["google", "g-", "gmail"]),
    ("microsoft", ["microsoft", "outlook", "ms code"]),
    ("apple",     ["apple", "icloud", "apple id"]),
    ("amazon",    ["amazon", "amzn"]),
    ("netflix",   ["netflix"]),
    ("paypal",    ["paypal"]),
    ("binance",   ["binance"]),
    ("coinbase",  ["coinbase"]),
    ("uber",      ["uber"]),
    ("airbnb",    ["airbnb"]),
    ("reddit",    ["reddit"]),
    ("pinterest", ["pinterest"]),
    ("skype",     ["skype"]),
    ("zoom",      ["zoom"]),
    ("signal",    ["signal"]),
    ("viber",     ["viber"]),
    ("line",      ["line app", "line code"]),
    ("wechat",    ["wechat", "we chat"]),
    ("imo",       ["imo app", "imo code"]),
    ("truecaller", ["truecaller"]),
    ("paytm",     ["paytm"]),
    ("phonepe",   ["phonepe", "phone pe"]),
    ("gpay",      ["google pay", "gpay"]),
    ("hdfc",      ["hdfc"]),
    ("icici",     ["icici"]),
    ("sbi",       ["sbi ", "sbi-", "state bank"]),
    ("bank",      ["bank", "otp for transaction", "transaction"]),
]

SIM_OPERATORS = {
    "9230": ("Jazz", E_GREEN), "9231": ("Jazz", E_GREEN),
    "9232": ("Warid/Jazz", E_GREEN), "9233": ("Ufone", E_YELLOW),
    "9234": ("Telenor", E_BLUE), "9235": ("Telenor", E_BLUE),
    "9236": ("Jazz", E_GREEN),
    "919": ("Airtel/Vi", E_RED), "918": ("Airtel", E_RED), "917": ("Idea", E_YELLOW),
    "447": ("UK Mobile", E_BLUE),
    "9715": ("Etisalat", E_GREEN), "97150": ("Etisalat", E_GREEN), "97155": ("du", E_RED),
    "9665": ("STC/Mobily", E_GREEN),
    "8801": ("Grameenphone", E_RED),
    "1": ("US Carrier", E_BLUE),
}


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def escape_html(text):
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mask_number(number):
    if not number:
        return "Unknown"
    n = re.sub(r"\D", "", str(number))
    if len(n) > 7:
        return n[:3] + "\u2022\u2022\u2022" + n[-4:]
    return n or "Unknown"


def detect_country_code(value):
    if not value:
        return "UNKNOWN"
    clean = re.sub(r"\D", "", str(value))
    if not clean:
        return "UNKNOWN"
    for region in (None, "PK", "US", "GB", "IN", "AE", "SA"):
        try:
            parsed = phonenumbers.parse(clean, region)
            if phonenumbers.is_valid_number(parsed):
                r = phonenumbers.region_code_for_number(parsed)
                if r:
                    return r
        except Exception:
            continue
    for prefix, code in PREFIX_FALLBACK:
        if clean.startswith(prefix):
            return code
    return "UNKNOWN"


def country_info(value):
    code = detect_country_code(value)
    flag, name = COUNTRIES.get(code, (E_GLOBE, "Unknown"))
    return flag, name, code


def detect_sim_operator(number):
    if not number:
        return None, None
    clean = re.sub(r"\D", "", str(number))
    for prefix in sorted(SIM_OPERATORS.keys(), key=len, reverse=True):
        if clean.startswith(prefix):
            return SIM_OPERATORS[prefix]
    return None, None


def detect_app(message_text):
    if not message_text:
        return "unknown", APP_LOGOS["default"]
    low = message_text.lower()
    for app_name, keywords in APP_KEYWORDS:
        for kw in keywords:
            if kw in low:
                return app_name, APP_LOGOS.get(app_name, APP_LOGOS["default"])
    return "unknown", APP_LOGOS["default"]


def extract_otp(message_text):
    """Returns (otp, confidence, category)"""
    if not message_text:
        return "N/A", "LOW", "NONE"

    m = re.search(r"(?<!\d)(\d{3,4}[\s\-]\d{3,4})(?!\d)", message_text)
    if m:
        raw = m.group(1)
        clean = re.sub(r"\s+", "-", raw)
        return clean, "HIGH", "CODE"

    high_patterns = [
        (r"(?:otp|o\.t\.p)[^\d]{0,15}(\d{3,9})", "OTP"),
        (r"(?:verification code|verify code)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:login code|security code)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:your code is|code:)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:one[-\s]?time[-\s]?password)[^\d]{0,15}(\d{3,9})", "OTP"),
        (r"(?:use code)[^\d]{0,15}(\d{3,9})", "CODE"),
    ]
    for pattern, cat in high_patterns:
        m = re.search(pattern, message_text, re.IGNORECASE)
        if m:
            return m.group(1), "HIGH", cat

    medium_patterns = [
        (r"(?:کوڈ|پاس کوڈ)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:कोड|ओटीपी|पिन)[^\d]{0,15}(\d{3,9})", "OTP"),
        (r"(?:رمز|كود)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:কোড|ওটিপি)[^\d]{0,15}(\d{3,9})", "OTP"),
        (r"(?:kode|verifikasi)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:kod|şifre)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:code|vérification)[^\d]{0,15}(\d{3,9})", "CODE"),
        (r"(?:pin)[^\d]{0,15}(\d{3,9})", "PIN"),
        (r"(?:password)[^\d]{0,15}(\d{3,9})", "PIN"),
    ]
    for pattern, cat in medium_patterns:
        m = re.search(pattern, message_text, re.IGNORECASE)
        if m:
            return m.group(1), "MEDIUM", cat

    m = re.search(r"(?<!\d)(\d{4,8})(?!\d)", message_text)
    if m:
        return m.group(1), "LOW", "CODE"

    m = re.search(r"(?<!\d)(\d{3,9})(?!\d)", message_text)
    if m:
        return m.group(1), "LOW", "CODE"

    return "N/A", "LOW", "NONE"


def message_category(message_text):
    if not message_text:
        return []
    low = message_text.lower()
    tags = []
    if any(w in low for w in ["otp", "verification", "verify", "one-time"]):
        tags.append("OTP")
    if any(w in low for w in ["bank", "transaction", "debit", "credit", "account"]):
        tags.append("Banking")
    if any(w in low for w in ["login", "sign in", "sign-in"]):
        tags.append("Login")
    if any(w in low for w in ["payment", "paid", "purchase", "order"]):
        tags.append("Payment")
    if any(w in low for w in ["delivery", "shipped", "courier"]):
        tags.append("Delivery")
    if any(w in low for w in ["password", "reset", "recover"]):
        tags.append("Password")
    if any(w in low for w in ["offer", "discount", "sale", "promo"]):
        tags.append("Promo")
    return tags


def relative_time(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow()
        diff = (now - dt).total_seconds()
        if diff < 60:
            return "just now"
        if diff < 3600:
            return str(int(diff // 60)) + " min ago"
        if diff < 86400:
            return str(int(diff // 3600)) + " hour ago"
        return str(int(diff // 86400)) + " day ago"
    except Exception:
        return ""


def pkt_time():
    return (datetime.utcnow() + timedelta(hours=PKT_OFFSET_HOURS)).strftime("%H:%M:%S")


def generate_sms_id(message):
    dt = str(message.get("dt", ""))
    num = str(message.get("num", ""))
    cli = str(message.get("cli", ""))
    msg = str(message.get("message", ""))
    content_hash = hashlib.md5((cli + ":" + msg).encode()).hexdigest()[:8]
    return dt + "_" + num + "_" + content_hash


def is_owner(user_id):
    try:
        return int(user_id) == int(TELEGRAM_OWNER_ID)
    except (TypeError, ValueError):
        return False


# ═══════════════════════════════════════════════════════
# PREMIUM SMS CARD
# ═══════════════════════════════════════════════════════

def sms_text(message, masked=True):
    number = str(message.get("num", ""))
    text = str(message.get("message", ""))
    dt = str(message.get("dt", ""))

    app_name, app_logo = detect_app(text)
    flag, country_name, country_code = country_info(number)
    sim_name, sim_dot = detect_sim_operator(number)
    otp, confidence, otp_cat = extract_otp(text)
    tags = message_category(text)
    rel_time = relative_time(dt) if dt else ""

    display_number = mask_number(number) if masked else (number or "Unknown")

    lines = []
    lines.append(E_SPARKLE + " " + E_BELL + " <b>N E W   M E S S A G E</b> " + E_BELL + " " + E_SPARKLE)
    lines.append(DIV_SHORT)

    if app_name != "unknown":
        app_line = app_logo + " <b>" + app_name.upper() + "</b>"
    else:
        app_line = E_MSG + " <b>SMS</b>"
    app_line += "  " + DOT + "  " + flag + " " + country_name
    lines.append(app_line)

    if otp != "N/A":
        conf_icon = E_GREEN if confidence == "HIGH" else (E_YELLOW if confidence == "MEDIUM" else E_RED)
        lines.append(DIV_SHORT)
        lines.append(E_KEY + " <b>" + otp_cat + " :</b>  <code>" + escape_html(otp) + "</code>  " + conf_icon)
        lines.append(DIV_SHORT)

    num_line = E_BOLT + " <code>" + escape_html(display_number) + "</code>"
    if sim_name:
        num_line += "  " + (sim_dot or E_SIGNAL) + " " + sim_name
    lines.append(num_line)

    time_parts = []
    if rel_time:
        time_parts.append(E_CLOCK + " " + rel_time)
    time_parts.append(E_TIME + " " + pkt_time() + " PKT")
    lines.append("  " + DOT + "  ".join(time_parts))

    if tags:
        tag_str = " ".join(["#" + t for t in tags])
        lines.append(E_TAG + " <i>" + tag_str + "</i>")

    lines.append(E_DIAMOND + " <i>RN OTP Premium</i> " + E_DIAMOND)
    return "\n".join(lines)


def message_buttons(message_text, sms_id, fallback=False):
    """Buttons — accessible by EVERYONE in the group"""
    otp, _, _ = extract_otp(message_text)
    keyboard = []

    row1 = []
    if otp != "N/A":
        if fallback:
            row1.append({
                "text": E_CLIP + " Copy OTP: " + otp,
                "callback_data": "otp:" + otp
            })
        else:
            row1.append({
                "text": E_CLIP + " Copy OTP: " + otp,
                "copy_text": {"text": otp}
            })
    else:
        row1.append({
            "text": E_CROSS + " No OTP Found",
            "callback_data": "otp:none"
        })
    keyboard.append(row1)

    row2 = [{"text": E_EYES + " Full Message", "callback_data": "full:" + sms_id}]
    if TELEGRAM_CHANNEL_URL:
        row2.append({"text": E_MEGA + " Channel", "url": TELEGRAM_CHANNEL_URL})
    keyboard.append(row2)

    clean_username = BUTTON_BOT_USERNAME.lstrip("@")
    keyboard.append([
        {"text": E_ROCKET + " Open Bot", "url": "https://t.me/" + clean_username}
    ])

    return {"inline_keyboard": keyboard}


def build_full_message_alert(message_text, otp="N/A", app_name="unknown",
                              country_code="UNKNOWN", number="", dt=""):
    flag, name = COUNTRIES.get(country_code, (E_GLOBE, country_code))
    app_logo = APP_LOGOS.get(app_name, APP_LOGOS["default"])
    rel = relative_time(dt) if dt else ""

    lines = []
    lines.append(E_SCROLL + " <b>FULL MESSAGE</b> " + E_SCROLL)
    lines.append(DIVIDER)

    if app_name != "unknown":
        lines.append(app_logo + " <b>" + app_name.upper() + "</b>")
    else:
        lines.append(E_MSG + " <b>SMS</b>")

    lines.append(flag + " " + name + "  " + DOT + "  " + E_PHONE + " <code>" + escape_html(number) + "</code>")

    if rel:
        lines.append(E_CLOCK + " " + rel + "  " + DOT + "  " + E_TIME + " " + pkt_time() + " PKT")

    if otp != "N/A":
        lines.append(DIVIDER)
        lines.append(E_KEY + " <b>OTP:</b> <code>" + escape_html(otp) + "</code>")

    lines.append(DIVIDER)
    lines.append(E_MSG + " <b>Message:</b>")
    lines.append("")
    lines.append(escape_html(message_text))
    lines.append("")
    lines.append(E_DIAMOND + " <i>RN OTP Premium</i> " + E_DIAMOND)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════

async def init_db():
    conn = await aiosqlite.connect(DATABASE_FILE)
    conn.row_factory = aiosqlite.Row
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS forwarded_messages ("
        "sms_id TEXT PRIMARY KEY, claimed_at TEXT NOT NULL, sent_at TEXT, "
        "raw_num TEXT, cli TEXT, message_text TEXT, payout TEXT, dt TEXT, "
        "app TEXT, country TEXT, otp TEXT)"
    )
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_sent_at ON forwarded_messages(sent_at)")
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS api_keys ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, api_key TEXT UNIQUE NOT NULL, "
        "is_active BOOLEAN DEFAULT 1, added_at TEXT NOT NULL)"
    )
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS intruders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, "
        "first_name TEXT, action TEXT, seen_at TEXT)"
    )
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS blocked_users ("
        "user_id TEXT PRIMARY KEY, username TEXT, blocked_at TEXT)"
    )
    await conn.commit()
    return conn


async def state_value(conn, key, default=""):
    async with conn.execute("SELECT value FROM bot_state WHERE key = ?", (key,)) as c:
        row = await c.fetchone()
        return str(row["value"]) if row else default


async def set_state(conn, key, value):
    await conn.execute(
        "INSERT INTO bot_state(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await conn.commit()


async def save_message_data(conn, sms_id, raw_num, cli, message_text,
                            payout, dt, app, country, otp):
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO forwarded_messages("
        "sms_id, claimed_at, raw_num, cli, message_text, payout, dt, app, country, otp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(sms_id) DO UPDATE SET "
        "raw_num=excluded.raw_num, cli=excluded.cli, message_text=excluded.message_text, "
        "payout=excluded.payout, dt=excluded.dt, app=excluded.app, "
        "country=excluded.country, otp=excluded.otp",
        (sms_id, now, raw_num, cli, message_text, payout, dt, app, country, otp),
    )
    await conn.commit()


async def claim_message(conn, sms_id):
    async with conn.execute(
        "SELECT sent_at FROM forwarded_messages WHERE sms_id = ?", (sms_id,)
    ) as c:
        existing = await c.fetchone()
    if existing and existing["sent_at"] is not None:
        return False
    if existing:
        return True
    await conn.execute(
        "INSERT OR IGNORE INTO forwarded_messages(sms_id, claimed_at) VALUES (?, ?)",
        (sms_id, datetime.now(timezone.utc).isoformat()),
    )
    await conn.commit()
    async with conn.execute(
        "SELECT 1 FROM forwarded_messages WHERE sms_id = ?", (sms_id,)
    ) as c:
        row = await c.fetchone()
        return row is not None


async def mark_sent(conn, sms_id):
    await conn.execute(
        "UPDATE forwarded_messages SET sent_at = ? WHERE sms_id = ?",
        (datetime.now(timezone.utc).isoformat(), sms_id),
    )
    await conn.commit()


async def get_message_data(conn, sms_id):
    async with conn.execute(
        "SELECT raw_num, cli, message_text, payout, dt, app, country, otp "
        "FROM forwarded_messages WHERE sms_id = ?", (sms_id,)
    ) as c:
        row = await c.fetchone()
    if not row:
        return None
    return {
        "raw_num": row["raw_num"] or "N/A",
        "cli": row["cli"] or "N/A",
        "message_text": row["message_text"] or "N/A",
        "payout": row["payout"] or "0",
        "dt": row["dt"] or "N/A",
        "app": row["app"] or "unknown",
        "country": row["country"] or "UNKNOWN",
        "otp": row["otp"] or "N/A",
    }


async def cleanup_old_records(conn, days=30):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with conn.execute(
        "DELETE FROM forwarded_messages WHERE sent_at < ?", (cutoff,)
    ) as c:
        deleted = c.rowcount
    await conn.commit()
    return deleted


async def get_db_stats(conn):
    async with conn.execute(
        "SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NOT NULL"
    ) as c:
        sent = (await c.fetchone())["c"]
    async with conn.execute(
        "SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NULL"
    ) as c:
        pending = (await c.fetchone())["c"]
    async with conn.execute("SELECT COUNT(*) AS c FROM forwarded_messages") as c:
        total = (await c.fetchone())["c"]
    async with conn.execute(
        "SELECT COALESCE(app,'unknown') AS app, COUNT(*) AS c "
        "FROM forwarded_messages WHERE sent_at IS NOT NULL "
        "GROUP BY COALESCE(app,'unknown') ORDER BY c DESC LIMIT 10"
    ) as c:
        by_app = await c.fetchall()
    return {
        "sent": sent, "pending": pending, "total": total,
        "by_app": [dict(r) for r in by_app],
    }


# ═══════════════════════════════════════════════════════
# API KEY MANAGEMENT
# ═══════════════════════════════════════════════════════

async def add_api_key(conn, api_key):
    try:
        await conn.execute(
            "INSERT INTO api_keys (api_key, added_at) VALUES (?, ?)",
            (api_key, datetime.now(timezone.utc).isoformat()),
        )
        await conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


async def remove_api_key(conn, api_key):
    async with conn.execute(
        "DELETE FROM api_keys WHERE api_key = ?", (api_key,)
    ) as c:
        deleted = c.rowcount
    await conn.commit()
    return deleted > 0


async def get_all_api_keys(conn):
    async with conn.execute(
        "SELECT api_key, is_active, added_at FROM api_keys ORDER BY id"
    ) as c:
        rows = await c.fetchall()
    return [dict(r) for r in rows]


async def load_api_keys(conn):
    global api_keys, current_api_index, GREEN_SMS_API_KEY
    keys = await get_all_api_keys(conn)
    active = [k["api_key"] for k in keys if k["is_active"]]
    if active:
        api_keys = active
        current_api_index = 0
        GREEN_SMS_API_KEY = api_keys[0]
        logger.info("Loaded " + str(len(api_keys)) + " API keys from DB")
    else:
        api_keys = [GREEN_SMS_API_KEY]
        current_api_index = 0
        logger.info("Using hardcoded API key")
    return api_keys


def get_current_api_key():
    global api_keys, current_api_index
    if api_keys and current_api_index < len(api_keys):
        return api_keys[current_api_index]
    return GREEN_SMS_API_KEY


async def rotate_api_key(conn):
    global current_api_index, GREEN_SMS_API_KEY
    if not api_keys:
        return None
    current_api_index = (current_api_index + 1) % len(api_keys)
    GREEN_SMS_API_KEY = api_keys[current_api_index]
    logger.info("Rotated to API key #" + str(current_api_index + 1))
    return GREEN_SMS_API_KEY


# ═══════════════════════════════════════════════════════
# API FETCH
# ═══════════════════════════════════════════════════════

async def fetch_all_messages(since_dt=""):
    api_key = get_current_api_key()
    if not api_key:
        raise RuntimeError("No API key available")

    all_messages = []
    if not since_dt:
        since_dt = "2020-01-01 00:00:00"

    current_dt2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    batch_count = 0
    total_fetched = 0
    last_used_dt2 = None
    records_limit = MAX_RECORDS

    logger.info("Fetching: " + since_dt + " -> " + current_dt2)

    while True:
        try:
            batch_count += 1
            params = {"dt1": since_dt, "dt2": current_dt2, "records": records_limit}

            response = await http_client.get(
                GREEN_SMS_API,
                headers={"Authorization": "Bearer " + api_key},
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited. Wait " + str(retry_after) + "s")
                await asyncio.sleep(retry_after)
                continue

            if response.status_code == 503:
                new_limit = max(10, records_limit // 2)
                if new_limit < records_limit:
                    records_limit = new_limit
                    continue
                break

            if response.status_code == 401:
                logger.error("401 Unauthorized")
                conn = await init_db()
                try:
                    new_key = await rotate_api_key(conn)
                    if new_key and new_key != api_key:
                        api_key = new_key
                        continue
                finally:
                    await conn.close()
                raise RuntimeError("API 401 - invalid key")

            if response.status_code != 200:
                logger.error("HTTP " + str(response.status_code))
                break

            payload = response.json()
            if payload.get("status") == "error":
                logger.error("API error: " + str(payload.get("msg", "Unknown")))
                break

            results = payload.get("data", [])
            if not results:
                break

            all_messages.extend(results)
            total_fetched += len(results)

            if len(results) < records_limit:
                break

            oldest_dt_str = results[-1].get("dt", "")
            if not oldest_dt_str or oldest_dt_str == last_used_dt2:
                break

            last_used_dt2 = current_dt2
            current_dt2 = oldest_dt_str

            if batch_count >= MAX_BATCHES:
                break

        except httpx.TimeoutException:
            await asyncio.sleep(5)
            continue
        except Exception as e:
            logger.error("Fetch error: " + str(e))
            break

    logger.info("Fetched " + str(total_fetched) + " messages")
    all_messages.reverse()
    return all_messages


# ═══════════════════════════════════════════════════════
# TELEGRAM HELPERS
# ═══════════════════════════════════════════════════════

async def telegram_call(method, payload, retries=3):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/" + method
    for attempt in range(retries):
        try:
            response = await http_client.post(url, json=payload, timeout=30)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                await asyncio.sleep(retry_after)
                continue

            if not response.is_success:
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError("TG HTTP " + str(response.status_code) + ": " + response.text[:300])

            result = response.json()
            if not result.get("ok"):
                desc = result.get("description", "Unknown")
                d = desc.lower()
                if ("reply markup" in d) or ("button" in d) or ("parse" in d) or ("copy_text" in d):
                    raise RuntimeError("TG markup error: " + desc)
                if result.get("error_code") == 429 and attempt < retries - 1:
                    wait = result.get("parameters", {}).get("retry_after", 1)
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError("TG error: " + desc)
            return result

        except httpx.TimeoutException:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise RuntimeError("TG timeout")
        except RuntimeError:
            raise
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise RuntimeError("TG request failed: " + str(e))


async def send_group_message(text, reply_markup):
    payload = {
        "chat_id": TELEGRAM_GROUP_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
        "disable_web_page_preview": True,
    }
    try:
        return await telegram_call("sendMessage", payload)
    except RuntimeError as e:
        err = str(e).lower()
        bad = (("reply markup" in err) or ("button" in err) or
               ("parse" in err) or ("copy_text" in err))
        if bad:
            logger.warning("copy_text unsupported -> fallback")
            sms_id = ""
            for row in reply_markup.get("inline_keyboard", []):
                for btn in row:
                    cb = btn.get("callback_data", "")
                    if cb.startswith("full:"):
                        sms_id = cb.split(":", 1)[1]
                        break
            fallback_markup = message_buttons(text, sms_id, fallback=True)
            payload["reply_markup"] = fallback_markup
            return await telegram_call("sendMessage", payload)
        raise


async def telegram_updates(offset):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/getUpdates"
    params = {"offset": offset, "timeout": 30, "limit": 100}
    try:
        response = await http_client.get(url, params=params, timeout=35)
        if response.status_code == 409:
            logger.warning("409 Conflict: doosra instance chal raha hai. 30s wait...")
            await asyncio.sleep(30)
            return []
        if not response.is_success:
            return []
        result = response.json()
        if not result.get("ok"):
            return []
        return result.get("result", [])
    except httpx.TimeoutException:
        return []
    except Exception as e:
        logger.error("Updates error: " + str(e))
        return []


async def get_full_message_alert(conn, sms_id):
    msg = await get_message_data(conn, sms_id)
    if not msg:
        return None
    otp, _, _ = extract_otp(msg["message_text"])
    app_name, _ = detect_app(msg["message_text"])
    return build_full_message_alert(
        message_text=msg["message_text"],
        otp=otp,
        app_name=app_name,
        country_code=msg.get("country", "UNKNOWN"),
        number=mask_number(msg.get("raw_num", "")),
        dt=msg.get("dt", ""),
    )


# ═══════════════════════════════════════════════════════
# SECURITY (Intruder + Block)
# ═══════════════════════════════════════════════════════

async def load_blocked_users(conn):
    global blocked_users
    async with conn.execute("SELECT user_id FROM blocked_users") as c:
        rows = await c.fetchall()
        blocked_users = {str(r["user_id"]) for r in rows}
    logger.info("Blocked users: " + str(len(blocked_users)))


async def log_intruder(conn, user_id, username, first_name, action):
    try:
        await conn.execute(
            "INSERT INTO intruders(user_id, username, first_name, action, seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(user_id), str(username or ""), str(first_name or ""),
             str(action), datetime.now(timezone.utc).isoformat()),
        )
        await conn.commit()
    except Exception as e:
        logger.warning("Intruder log failed: " + str(e))


async def notify_owner_intrusion(conn, user_id, username, first_name, action):
    try:
        text = "\n".join([
            "\U0001F6A8 <b>UNAUTHORIZED ATTEMPT</b>",
            DIV_SHORT,
            E_USER + " <b>ID:</b> <code>" + str(user_id) + "</code>",
            "\U0001F4DB <b>User:</b> @" + escape_html(username or "N/A"),
            E_TAG + " <b>Name:</b> " + escape_html(first_name or "N/A"),
            E_BOLT + " <b>Action:</b> <code>" + escape_html(action) + "</code>",
            E_CLOCK + " <b>Time:</b> " + pkt_time() + " PKT",
        ])
        await telegram_call("sendMessage", {
            "chat_id": TELEGRAM_OWNER_ID, "text": text, "parse_mode": "HTML",
        })
    except Exception as e:
        logger.warning("Owner notify failed: " + str(e))


async def block_user(conn, user_id, username=""):
    global blocked_users
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO blocked_users(user_id, username, blocked_at) "
            "VALUES (?, ?, ?)",
            (str(user_id), str(username or ""), datetime.now(timezone.utc).isoformat()),
        )
        await conn.commit()
        blocked_users.add(str(user_id))
        return True
    except Exception:
        return False


async def unblock_user(conn, user_id):
    global blocked_users
    try:
        await conn.execute("DELETE FROM blocked_users WHERE user_id = ?", (str(user_id),))
        await conn.commit()
        blocked_users.discard(str(user_id))
        return True
    except Exception:
        return False


async def get_blocked_list(conn):
    async with conn.execute(
        "SELECT user_id, username, blocked_at FROM blocked_users ORDER BY blocked_at DESC"
    ) as c:
        rows = await c.fetchall()
    return [dict(r) for r in rows]


async def get_intruders(conn, limit=20):
    async with conn.execute(
        "SELECT user_id, username, first_name, action, seen_at "
        "FROM intruders ORDER BY id DESC LIMIT ?", (limit,)
    ) as c:
        rows = await c.fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════
# FORWARD LOOP
# ═══════════════════════════════════════════════════════

async def forward_loop(forward_event: asyncio.Event) -> None:
    global runtime_last_error, runtime_last_poll
    conn = await init_db()
    try:
        while True:
            try:
                runtime_last_poll = datetime.now(timezone.utc).isoformat()
                last_dt = await state_value(conn, "last_sms_dt")

                logger.info("-" * 50)
                logger.info("Poll @ " + runtime_last_poll)
                logger.info("Last DT: " + (last_dt or "None"))

                messages = await fetch_all_messages(last_dt)

                if last_dt:
                    messages = [m for m in messages if str(m.get("dt", "")) > last_dt]

                if not messages:
                    logger.info("No new SMS")
                else:
                    logger.info("Processing " + str(len(messages)) + " messages")

                    newest_dt = ""
                    for m in messages:
                        d = str(m.get("dt", ""))
                        if d > newest_dt:
                            newest_dt = d

                    for message in messages:
                        sms_id = generate_sms_id(message)
                        claimed = await claim_message(conn, sms_id)
                        if not claimed:
                            continue

                        raw_num = str(message.get("num", ""))
                        cli = str(message.get("cli", ""))
                        msg_text = str(message.get("message", ""))
                        payout = str(message.get("payout", "0"))
                        dt = str(message.get("dt", ""))

                        app_name, _ = detect_app(msg_text)
                        country_code = detect_country_code(raw_num)
                        otp, _, _ = extract_otp(msg_text)

                        await save_message_data(
                            conn, sms_id, raw_num, cli, msg_text,
                            payout, dt, app_name, country_code, otp,
                        )

                        display_text = sms_text(message, masked=True)
                        markup = message_buttons(msg_text, sms_id)

                        try:
                            await send_group_message(display_text, markup)
                            await mark_sent(conn, sms_id)
                            logger.info("Sent " + sms_id[:40])
                        except Exception as send_err:
                            logger.error("Send failed: " + str(send_err))
                            continue

                        await asyncio.sleep(0.5)

                    if newest_dt:
                        try:
                            dt_obj = datetime.strptime(
                                newest_dt, "%Y-%m-%d %H:%M:%S"
                            ) + timedelta(seconds=1)
                            new_dt = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            new_dt = newest_dt
                        await set_state(conn, "last_sms_dt", new_dt)
                        logger.info("Advanced last_dt -> " + new_dt)

                runtime_last_error = None

            except Exception as error:
                runtime_last_error = str(error)
                logger.error("Forward error: " + runtime_last_error)

            try:
                await asyncio.wait_for(forward_event.wait(), timeout=POLL_SECONDS)
                forward_event.clear()
            except asyncio.TimeoutError:
                pass
    finally:
        await conn.close()


# ═══════════════════════════════════════════════════════
# COMMAND LOOP
# ═══════════════════════════════════════════════════════

async def command_loop(forward_event: asyncio.Event) -> None:
    conn = await init_db()
    offset = int(await state_value(conn, "telegram_update_offset") or "0")
    await load_blocked_users(conn)

    try:
        while True:
            try:
                updates = await telegram_updates(offset)
                for update in updates:
                    update_id = int(update.get("update_id", 0))
                    offset = max(offset, update_id + 1)
                    await set_state(conn, "telegram_update_offset", str(offset))

                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    callback = update.get("callback_query")

                    sender = callback.get("from", {}) if callback else message.get("from", {})
                    sender_id = sender.get("id")
                    text = str(message.get("text", ""))

                    if str(sender_id) in blocked_users:
                        continue

                    # ═══ BUTTONS — EVERYONE ═══
                    if callback:
                        data = str(callback.get("data", ""))
                        callback_id = callback.get("id", "")
                        if not callback_id:
                            continue

                        if data.startswith("full:"):
                            sms_id = data.split(":", 1)[1]
                            alert = await get_full_message_alert(conn, sms_id)
                            if not alert:
                                alert = "\u274C Message expired."
                            try:
                                await telegram_call("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": alert[:200],
                                    "show_alert": True,
                                })
                            except Exception as e:
                                logger.warning("Callback failed: " + str(e))

                        elif data.startswith("otp:"):
                            otp = data.split(":", 1)[1]
                            alert = "\u274C No OTP found." if otp == "none" else "\U0001F4CB OTP: " + otp
                            try:
                                await telegram_call("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": alert,
                                    "show_alert": True,
                                })
                            except Exception:
                                pass
                        continue

                    # ═══ COMMANDS — OWNER ONLY ═══
                    if not is_owner(sender_id):
                        action = "cmd:" + text[:40]
                        await log_intruder(
                            conn, sender_id,
                            sender.get("username", ""),
                            sender.get("first_name", ""),
                            action,
                        )
                        last_notify = await state_value(conn, "last_intrusion_notify")
                        should_notify = True
                        if last_notify:
                            try:
                                if (datetime.now(timezone.utc) -
                                    datetime.fromisoformat(last_notify)).total_seconds() < 60:
                                    should_notify = False
                            except Exception:
                                pass
                        if should_notify:
                            await notify_owner_intrusion(
                                conn, sender_id,
                                sender.get("username", ""),
                                sender.get("first_name", ""),
                                action,
                            )
                            await set_state(
                                conn, "last_intrusion_notify",
                                datetime.now(timezone.utc).isoformat()
                            )
                        continue

                    if chat.get("type") != "private":
                        continue

                    cmd = text.strip().split(maxsplit=1)[0].split("@")[0].lower()

                    if cmd == "/start":
                        start_lines = [
                            E_CROWN + " <b>Owner Panel</b>",
                            DIVIDER,
                            E_BOT + " <b>SMS Forwarder Bot v18</b>",
                            E_GREEN + " <b>Status:</b> Online & Secured",
                            "",
                            E_USER + " <b>Owner:</b> <code>" + str(TELEGRAM_OWNER_ID) + "</code>",
                            E_MEGA + " <b>Group:</b> <code>" + escape_html(TELEGRAM_GROUP_ID) + "</code>",
                            E_CLOCK + " <b>PKT:</b> " + pkt_time(),
                            "",
                            E_KEY + " <b>Commands</b>",
                            "\u2022 /status \u2014 Bot status",
                            "\u2022 /stats \u2014 Statistics",
                            "\u2022 /analytics \u2014 Deep insights",
                            "\u2022 /export \u2014 CSV export",
                            "\u2022 /reset \u2014 Reset cursor",
                            "\u2022 /forwardnow \u2014 Force poll",
                            "\u2022 /cleanup \u2014 Delete old",
                            "\u2022 /addapi KEY \u2014 Add API",
                            "\u2022 /remapi KEY \u2014 Remove API",
                            "\u2022 /apilist \u2014 List APIs",
                            "",
                            E_SHIELD + " <b>Security</b>",
                            "\u2022 /intruders \u2014 Access attempts",
                            "\u2022 /blocked \u2014 Blocked list",
                            "\u2022 /block ID \u2014 Block user",
                            "\u2022 /unblock ID \u2014 Unblock",
                        ]
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\n".join(start_lines),
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/status":
                        status = await build_status_text(conn, runtime_last_error)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": status, "parse_mode": "HTML",
                        })

                    elif cmd == "/stats":
                        st = await build_stats_text(conn)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": st, "parse_mode": "HTML",
                        })

                    elif cmd == "/analytics":
                        an = await build_analytics_text(conn)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": an, "parse_mode": "HTML",
                        })

                    elif cmd == "/export":
                        csv_data = await export_csv(conn)
                        if not csv_data:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"], "text": "\u274C No data.",
                            })
                            continue
                        try:
                            await http_client.post(
                                "https://api.telegram.org/bot" + BOT_TOKEN + "/sendDocument",
                                data={"chat_id": chat["id"], "caption": "\U0001F4C1 SMS Export"},
                                files={"document": ("sms_export.csv", csv_data, "text/csv")},
                                timeout=60,
                            )
                        except Exception as e:
                            logger.error("Export failed: " + str(e))

                    elif cmd == "/reset":
                        await set_state(conn, "last_sms_dt", "")
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\u2705 Reset done. Bot re-fetch karega.",
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/forwardnow":
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": "\U0001F680 Triggered",
                        })
                        forward_event.set()

                    elif cmd == "/cleanup":
                        deleted = await cleanup_old_records(conn, CLEANUP_DAYS)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\U0001F9F9 Cleaned: " + str(deleted) + " records",
                        })

                    elif cmd == "/addapi":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u274C Usage: /addapi YOUR_KEY",
                            })
                            continue
                        api_key = parts[1]
                        if await add_api_key(conn, api_key):
                            await load_api_keys(conn)
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u2705 API Added: <code>" + escape_html(api_key[:20]) + "...</code>",
                                "parse_mode": "HTML",
                            })
                        else:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"], "text": "\u274C Already exists.",
                            })

                    elif cmd == "/remapi":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            continue
                        if await remove_api_key(conn, parts[1]):
                            await load_api_keys(conn)
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"], "text": "\u2705 API Removed",
                            })

                    elif cmd == "/apilist":
                        keys = await get_all_api_keys(conn)
                        cur = get_current_api_key()
                        lines = [E_KEY + " <b>API Keys</b>", DIVIDER]
                        for k in keys:
                            mark = E_GREEN + " ACTIVE" if k["api_key"] == cur else E_GLOBE + " standby"
                            lines.append(mark + " <code>" + escape_html(k["api_key"][:20]) + "...</code>")
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": "\n".join(lines), "parse_mode": "HTML",
                        })

                    elif cmd == "/intruders":
                        rows = await get_intruders(conn, 20)
                        if not rows:
                            txt = E_GREEN + " No intruders. Bot secure."
                        else:
                            lines = ["\U0001F6A8 <b>Recent Intruders</b>", DIV_SHORT]
                            for r in rows[:15]:
                                lines.append(E_USER + " <code>" + str(r["user_id"]) + "</code>")
                                lines.append("   @" + escape_html(r.get("username") or "N/A"))
                                lines.append("   \u26A1 <code>" + escape_html(str(r.get("action"))[:40]) + "</code>")
                            txt = "\n".join(lines)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": txt, "parse_mode": "HTML",
                        })

                    elif cmd == "/blocked":
                        rows = await get_blocked_list(conn)
                        if not rows:
                            txt = E_GREEN + " No blocked users."
                        else:
                            lines = ["\U0001F6AB <b>Blocked Users</b>", DIV_SHORT]
                            for r in rows[:20]:
                                lines.append(E_USER + " <code>" + str(r["user_id"]) + "</code>")
                            txt = "\n".join(lines)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"], "text": txt, "parse_mode": "HTML",
                        })

                    elif cmd == "/block":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            continue
                        target = parts[1].strip()
                        if is_owner(target):
                            continue
                        if await block_user(conn, target):
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\U0001F6AB Blocked: <code>" + escape_html(target) + "</code>",
                                "parse_mode": "HTML",
                            })

                    elif cmd == "/unblock":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            continue
                        if await unblock_user(conn, parts[1].strip()):
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u2705 Unblocked: <code>" + escape_html(parts[1]) + "</code>",
                                "parse_mode": "HTML",
                            })

            except Exception as error:
                logger.error("Command error: " + str(error))

            await asyncio.sleep(1)
    finally:
        await conn.close()


# ═══════════════════════════════════════════════════════
# STATUS / ANALYTICS / EXPORT BUILDERS
# ═══════════════════════════════════════════════════════

async def build_status_text(conn, last_error):
    state_icon = E_GREEN if not last_error else E_RED
    state_label = "Running" if not last_error else "Error"
    err_label = last_error or "none"
    active_key = get_current_api_key()[:20]
    last_dt = await state_value(conn, "last_sms_dt") or "-"
    now_label = pkt_time()
    api_count = len(api_keys)

    total_msgs = 0
    try:
        async with conn.execute(
            "SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NOT NULL"
        ) as c:
            total_msgs = (await c.fetchone())["c"]
    except Exception:
        pass

    lines = [
        E_CHART + " <b>Bot Status</b>",
        DIVIDER,
        state_icon + " <b>State:</b> " + state_label,
        E_KEY + " <b>APIs:</b> " + str(api_count),
        E_OLDKEY + " <b>Active:</b> <code>" + escape_html(active_key) + "...</code>",
        E_MEGA + " <b>Group:</b> <code>" + escape_html(TELEGRAM_GROUP_ID) + "</code>",
        E_CLOCK + " <b>Poll:</b> " + str(POLL_SECONDS) + "s",
        E_TIME + " <b>Last DT:</b> <code>" + escape_html(last_dt) + "</code>",
        E_OUT + " <b>Forwarded:</b> " + str(total_msgs),
        E_USER + " <b>Owner:</b> <code>" + str(TELEGRAM_OWNER_ID) + "</code>",
        E_CLOCK + " <b>Now:</b> " + now_label + " PKT",
        E_CROSS + " <b>Error:</b> <code>" + escape_html(err_label) + "</code>",
    ]
    return "\n".join(lines)


async def build_stats_text(conn):
    try:
        db_stats = await get_db_stats(conn)
    except Exception:
        db_stats = {"sent": 0, "pending": 0, "total": 0, "by_app": []}

    lines = [
        E_CHART + " <b>Statistics</b>",
        DIVIDER,
        E_OUT + " <b>Sent:</b> " + str(db_stats["sent"]),
        E_HOUR + " <b>Pending:</b> " + str(db_stats["pending"]),
        E_FILE + " <b>Total:</b> " + str(db_stats["total"]),
        "",
        E_MSG + " <b>Top Apps:</b>",
    ]
    by_app = db_stats.get("by_app", [])
    if not by_app:
        lines.append("   <i>None yet</i>")
    else:
        for row in by_app[:5]:
            app = row.get("app") or "unknown"
            logo = APP_LOGOS.get(app, APP_LOGOS["default"])
            lines.append("   " + logo + " " + str(app).upper() + ": <b>" + str(row.get("c", 0)) + "</b>")

    lines.append("")
    lines.append(E_DB + " <code>" + escape_html(DATABASE_FILE) + "</code>")
    return "\n".join(lines)


async def build_analytics_text(conn):
    try:
        async with conn.execute(
            "SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NOT NULL"
        ) as c:
            total_sent = (await c.fetchone())["c"]

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        async with conn.execute(
            "SELECT COUNT(*) AS c FROM forwarded_messages "
            "WHERE sent_at IS NOT NULL AND dt LIKE ?", (today + "%",)
        ) as c:
            today_sent = (await c.fetchone())["c"]

        async with conn.execute(
            "SELECT country, COUNT(*) AS c FROM forwarded_messages "
            "WHERE sent_at IS NOT NULL AND country IS NOT NULL "
            "GROUP BY country ORDER BY c DESC LIMIT 5"
        ) as c:
            countries = await c.fetchall()

        async with conn.execute(
            "SELECT COALESCE(app,'unknown') AS app, COUNT(*) AS c "
            "FROM forwarded_messages WHERE sent_at IS NOT NULL "
            "GROUP BY COALESCE(app,'unknown') ORDER BY c DESC LIMIT 5"
        ) as c:
            apps = await c.fetchall()

        async with conn.execute(
            "SELECT COUNT(*) AS c FROM forwarded_messages "
            "WHERE sent_at IS NOT NULL AND otp != 'N/A' AND otp IS NOT NULL"
        ) as c:
            otp_count = (await c.fetchone())["c"]

        try:
            async with conn.execute("SELECT COUNT(*) AS c FROM intruders") as c:
                intruder_count = (await c.fetchone())["c"]
        except Exception:
            intruder_count = 0

        lines = [
            E_CHART + " <b>Analytics</b>",
            DIVIDER,
            E_OUT + " <b>Total:</b> " + str(total_sent),
            E_CAL + " <b>Today:</b> " + str(today_sent),
            E_KEY + " <b>OTPs:</b> " + str(otp_count),
            "\U0001F6A8 <b>Intruders:</b> " + str(intruder_count),
            "",
            E_GLOBE + " <b>Top Countries:</b>",
        ]
        if countries:
            for row in countries:
                code = row["country"] or "UNKNOWN"
                flag, name = COUNTRIES.get(code, (E_GLOBE, code))
                lines.append("   " + flag + " " + name + ": <b>" + str(row["c"]) + "</b>")
        else:
            lines.append("   <i>None</i>")

        lines.append("")
        lines.append(E_MSG + " <b>Top Apps:</b>")
        if apps:
            for row in apps:
                app = row["app"] or "unknown"
                logo = APP_LOGOS.get(app, APP_LOGOS["default"])
                lines.append("   " + logo + " " + str(app).upper() + ": <b>" + str(row["c"]) + "</b>")
        else:
            lines.append("   <i>None</i>")

        return "\n".join(lines)
    except Exception as e:
        return "\u274C Analytics error: " + str(e)


async def export_csv(conn):
    try:
        async with conn.execute(
            "SELECT dt, raw_num, country, app, otp, payout, message_text "
            "FROM forwarded_messages WHERE sent_at IS NOT NULL "
            "ORDER BY dt DESC LIMIT 5000"
        ) as c:
            rows = await c.fetchall()
        if not rows:
            return None

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date/Time", "Number", "Country", "App", "OTP", "Payout", "Message"])
        for r in rows:
            writer.writerow([
                r["dt"] or "", r["raw_num"] or "", r["country"] or "",
                r["app"] or "", r["otp"] or "", r["payout"] or "",
                (r["message_text"] or "").replace("\n", " "),
            ])
        return output.getvalue().encode("utf-8")
    except Exception as e:
        logger.error("CSV export error: " + str(e))
        return None


# ═══════════════════════════════════════════════════════
# SETUP + MAIN
# ═══════════════════════════════════════════════════════

async def load_bot_username():
    global BOT_USERNAME
    try:
        response = await telegram_call("getMe", {})
        if response.get("ok"):
            BOT_USERNAME = response["result"]["username"]
            logger.info("Bot: @" + BOT_USERNAME)
    except Exception as e:
        logger.error("getMe failed: " + str(e))


async def main() -> None:
    global http_client

    print("=" * 60)
    print("Ultra SMS -> Telegram Forwarder Bot v18 - Final Premium")
    print("=" * 60)

    forward_event = asyncio.Event()
    http_client = httpx.AsyncClient(
        http2=False,
        limits=httpx.Limits(max_connections=10),
    )

    conn = await init_db()
    try:
        await load_api_keys(conn)
        await load_blocked_users(conn)
        await load_bot_username()
        last_dt = await state_value(conn, "last_sms_dt")

        logger.info("Bot: @" + BOT_USERNAME)
        logger.info("Owner: " + str(TELEGRAM_OWNER_ID))
        logger.info("Group: " + TELEGRAM_GROUP_ID)
        logger.info("Last DT: " + (last_dt or "None"))
        logger.info("APIs: " + str(len(api_keys)))
        logger.info("=" * 60)
        logger.info("Started - Owner Commands | Public Buttons")
        logger.info("=" * 60)

        try:
            startup_lines = [
                E_CROWN + " <b>Bot Started</b>",
                DIV_SHORT,
                E_GREEN + " <b>Status:</b> Online",
                E_LOCK + " <b>Mode:</b> Owner-Only Commands",
                E_MEGA + " <b>Group:</b> Buttons public",
                E_CLOCK + " <b>PKT:</b> " + pkt_time(),
            ]
            await telegram_call("sendMessage", {
                "chat_id": TELEGRAM_OWNER_ID,
                "text": "\n".join(startup_lines),
                "parse_mode": "HTML",
            })
        except Exception as e:
            logger.warning("Startup msg failed: " + str(e))

        await asyncio.gather(
            forward_loop(forward_event),
            command_loop(forward_event),
        )

    except KeyboardInterrupt:
        logger.info("Stopped")
    except Exception as e:
        logger.error("Fatal: " + str(e))
    finally:
        await conn.close()
        if http_client:
            await http_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
