"""Ultra SMS Forwarder Bot v13 - Smart OTP + App Detection + Animation"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite
import httpx
import phonenumbers

# ═══════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════
GREEN_SMS_API = "http://143.110.245.86/api/partner/v1/messages/"
GREEN_SMS_API_KEY = "gsp_5735fa94_Ufmcr2_GNpht0AqpKZLK5Lt6MQxBavnavSUwx3zw-hs"
TELEGRAM_GROUP_ID = "-1004330079864"
TELEGRAM_OWNER_ID = 8762845215
TELEGRAM_CHANNEL_URL = "https://t.me/RN_OTP_1"
BOT_USERNAME = "RN_OTP_bot"
BUTTON_BOT_USERNAME = "RN_OTP1_bot"
BOT_TOKEN = "8354696843:AAEq3AUqSUSBToIf_tWA9UdtsMOjVMSTc-E"

POLL_SECONDS = 5
DATABASE_FILE = "sms_telegram_bot.sqlite3"
MAX_RECORDS = 200
MAX_BATCHES = 100
CLEANUP_DAYS = 30
ANIMATION_ENABLED = True
# ========================================

runtime_last_error = None
runtime_last_poll = None
http_client = None
current_api_index = 0
api_keys = []

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("greensms_bot")

# ═══════════════════════════════════════════════════════
# EMOJI CONSTANTS
# ═══════════════════════════════════════════════════════
E_CLIP = "\U0001F4CB"
E_EYES = "\U0001F440"
E_MEGA = "\U0001F4E2"
E_BOT = "\U0001F916"
E_CROSS = "\u274C"
E_CHECK = "\u2705"
E_GREEN = "\U0001F7E2"
E_RED = "\U0001F534"
E_KEY = "\U0001F511"
E_CHART = "\U0001F4CA"
E_CAL = "\U0001F4C5"
E_OUT = "\U0001F4E4"
E_HOUR = "\u23F3"
E_USER = "\U0001F464"
E_CLOCK = "\U0001F550"
E_MSG = "\U0001F4AC"
E_ROCKET = "\U0001F680"
E_GEAR = "\u2699"
E_FILE = "\U0001F4C1"
E_DB = "\U0001F5C4"
E_BOLT = "\u26A1"
E_GLOBE = "\U0001F310"
E_INFO = "\u2139"
E_INBOX = "\U0001F4E9"
E_FIRE = "\U0001F525"
E_STAR = "\u2B50"
E_LOCK = "\U0001F512"

# Animation frames
FRAMES = ["\u25B0", "\u25B1", "\u25B2", "\u25B3", "\u25B4", "\u25B5", "\u25B6", "\u25B7"]
PROGRESS_BLOCKS = ["\u2596", "\u2597", "\u2598", "\u259D", "\u2599", "\u259F", "\u259A", "\u259C"]

DIVIDER = "\u2501" * 14
DOT = "\u2022"

# ═══════════════════════════════════════════════════════
# APP LOGOS & DETECTION
# ═══════════════════════════════════════════════════════
APP_LOGOS = {
    "whatsapp":  "\U0001F4F1",        # 📱
    "telegram":  "\u2708\uFE0F",       # ✈️
    "instagram": "\U0001F4F8",        # 📸
    "facebook":  "\U0001F535",        # 🔵
    "twitter":   "\U0001F426",        # 🐦
    "tiktok":    "\U0001F3B5",        # 🎵
    "snapchat":  "\U0001F47B",        # 👻
    "discord":   "\U0001F3AE",        # 🎮
    "youtube":   "\U0001F4FA",        # 📺
    "linkedin":  "\U0001F4BC",        # 💼
    "google":    "\U0001F50D",        # 🔍
    "gmail":     "\U0001F4E7",        # 📧
    "microsoft": "\U0001F7EA",        # 🟪
    "apple":     "\U0001F34E",        # 🍎
    "amazon":    "\U0001F4E6",        # 📦
    "netflix":   "\U0001F3AC",        # 🎬
    "paypal":    "\U0001F4B3",        # 💳
    "binance":   "\U0001F4B0",        # 💰
    "coinbase":  "\U0001FA99",        # 🪙
    "uber":      "\U0001F697",        # 🚗
    "airbnb":    "\U0001F3E0",        # 🏠
    "reddit":    "\U0001F47D",        # 👽
    "pinterest": "\U0001F4CC",        # 📌
    "skype":     "\u260E\uFE0F",       # ☎️
    "zoom":      "\U0001F3A5",        # 🎥
    "signal":    "\U0001F512",        # 🔒
    "viber":     "\U0001F4DE",        # 📞
    "line":      "\U0001F4AC",        # 💬
    "wechat":    "\U0001F49A",        # 💚
    "imo":       "\U0001F4F2",        # 📲
    "truecaller":"\U0001F4DE",        # 📞
    "bank":      "\U0001F3E6",        # 🏦
    "hdfc":      "\U0001F3E6",        # 🏦
    "icici":     "\U0001F3E6",        # 🏦
    "sbi":       "\U0001F3E6",        # 🏦
    "paytm":     "\U0001F4B8",        # 💸
    "phonepe":   "\U0001F4B8",        # 💸
    "gpay":      "\U0001F4B8",        # 💸
    "default":   "\U0001F4E9",        # 📩
}

# App detection keywords (order matters - more specific first)
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
    ("truecaller",["truecaller"]),
    ("paytm",     ["paytm"]),
    ("phonepe",   ["phonepe", "phone pe"]),
    ("gpay",      ["google pay", "gpay"]),
    ("hdfc",      ["hdfc"]),
    ("icici",     ["icici"]),
    ("sbi",       ["sbi ", "sbi-", "state bank"]),
    ("bank",      ["bank", "otp for transaction", "transaction"]),
]

# ═══════════════════════════════════════════════════════
# COUNTRY FLAGS
# ═══════════════════════════════════════════════════════
COUNTRY_FLAGS = {
    "PK": "\U0001F1F5\U0001F1F0", "US": "\U0001F1FA\U0001F1F8",
    "GB": "\U0001F1EC\U0001F1E7", "IN": "\U0001F1EE\U0001F1F3",
    "CA": "\U0001F1E8\U0001F1E6", "AU": "\U0001F1E6\U0001F1FA",
    "DE": "\U0001F1E9\U0001F1EA", "FR": "\U0001F1EB\U0001F1F7",
    "IT": "\U0001F1EE\U0001F1F9", "ES": "\U0001F1EA\U0001F1F8",
    "BR": "\U0001F1E7\U0001F1F7", "MX": "\U0001F1F2\U0001F1FD",
    "JP": "\U0001F1EF\U0001F1F5", "CN": "\U0001F1E8\U0001F1F3",
    "RU": "\U0001F1F7\U0001F1FA", "ZA": "\U0001F1FF\U0001F1E6",
    "NG": "\U0001F1F3\U0001F1EC", "EG": "\U0001F1EA\U0001F1EC",
    "SA": "\U0001F1F8\U0001F1E6", "AE": "\U0001F1E6\U0001F1EA",
    "BD": "\U0001F1E7\U0001F1E9", "ID": "\U0001F1EE\U0001F1E9",
    "MY": "\U0001F1F2\U0001F1FE", "SG": "\U0001F1F8\U0001F1EC",
    "HK": "\U0001F1ED\U0001F1F0", "TR": "\U0001F1F9\U0001F1F7",
    "PL": "\U0001F1F5\U0001F1F1", "UA": "\U0001F1FA\U0001F1E6",
    "RO": "\U0001F1F7\U0001F1F4", "NL": "\U0001F1F3\U0001F1F1",
    "BE": "\U0001F1E7\U0001F1EA", "CH": "\U0001F1E8\U0001F1ED",
    "AT": "\U0001F1E6\U0001F1F9", "SE": "\U0001F1F8\U0001F1EA",
    "NO": "\U0001F1F3\U0001F1F4", "DK": "\U0001F1E9\U0001F1F0",
    "FI": "\U0001F1EB\U0001F1EE", "IE": "\U0001F1EE\U0001F1EA",
    "PT": "\U0001F1F5\U0001F1F9", "GR": "\U0001F1EC\U0001F1F7",
    "KR": "\U0001F1F0\U0001F1F7", "NZ": "\U0001F1F3\U0001F1FF",
    "TW": "\U0001F1F9\U0001F1FC", "TH": "\U0001F1F9\U0001F1ED",
    "VN": "\U0001F1FB\U0001F1F3", "PH": "\U0001F1F5\U0001F1ED",
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


def escape_html(text):
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mask_number(number):
    if len(number) > 7:
        return number[:3] + "\u2022\u2022\u2022" + number[-4:]
    return number or "Unknown"


def detect_country_code(value):
    """Return country code like PK, US"""
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


def flag_for_number(value):
    code = detect_country_code(value)
    return COUNTRY_FLAGS.get(code, E_GLOBE)


def detect_app(message_text):
    """Detect app from message. Returns (app_name, logo)"""
    if not message_text:
        return "unknown", APP_LOGOS["default"]

    low = message_text.lower()
    for app_name, keywords in APP_KEYWORDS:
        for kw in keywords:
            if kw in low:
                return app_name, APP_LOGOS.get(app_name, APP_LOGOS["default"])

    return "unknown", APP_LOGOS["default"]


def extract_otp(message_text):
    """
    ULTRA OTP Extraction - Handles:
    - 123-456 (with dash) → returns 123-456
    - 123 456 (with space) → returns 123-456
    - 12345 → returns 12345
    - WhatsApp-style codes
    """
    if not message_text:
        return "N/A"

    # ═══ Priority 1: Formatted OTP with dash/space (e.g., 123-456, 123 456) ═══
    # This catches WhatsApp/Telegram style "123-456"
    m = re.search(r"(?<!\d)(\d{3,4}[\s\-]\d{3,4})(?!\d)", message_text)
    if m:
        # Normalize space to dash
        raw = m.group(1)
        clean = re.sub(r"\s+", "-", raw)
        return clean

    # ═══ Priority 2: OTP near keywords (multi-language) ═══
    keyword_patterns = [
        r"(?:otp|code|pin|verify|verification|password|passcode)[^\d]{0,15}(\d{3,9})",
        r"(?:کوڈ|پاس کوڈ)[^\d]{0,15}(\d{3,9})",
        r"(?:कोड|ओटीपी|पिन)[^\d]{0,15}(\d{3,9})",
        r"(?:رمز|كود)[^\d]{0,15}(\d{3,9})",
        r"(?:কোড|ওটিপি)[^\d]{0,15}(\d{3,9})",
        r"(?:kode|verifikasi)[^\d]{0,15}(\d{3,9})",
        r"(?:kod|şifre)[^\d]{0,15}(\d{3,9})",
        r"(?:code|vérification)[^\d]{0,15}(\d{3,9})",
    ]
    for pattern in keyword_patterns:
        m = re.search(pattern, message_text, re.IGNORECASE)
        if m:
            return m.group(1)

    # ═══ Priority 3: 4-8 digit standalone ═══
    m = re.search(r"(?<!\d)(\d{4,8})(?!\d)", message_text)
    if m:
        return m.group(1)

    # ═══ Priority 4: 3-9 digit standalone ═══
    m = re.search(r"(?<!\d)(\d{3,9})(?!\d)", message_text)
    if m:
        return m.group(1)

    return "N/A"


def generate_sms_id(message):
    dt = str(message.get("dt", ""))
    num = str(message.get("num", ""))
    cli = str(message.get("cli", ""))
    msg = str(message.get("message", ""))
    content_hash = hashlib.md5((cli + ":" + msg).encode()).hexdigest()[:8]
    return dt + "_" + num + "_" + content_hash


# ═══════════════════════════════════════════════════════
# MESSAGE BUILDERS
# ═══════════════════════════════════════════════════════

def sms_text(message, masked=True):
    """
    Beautiful SMS message with app logo + country flag.

    Example:
        📩 ɴᴇᴡ sᴍs

        📱 ᴡʜᴀᴛsᴀᴘᴘ • 🇵🇰 ᴘᴀᴋɪsᴛᴀɴ

        📞 923•••4567
    """
    number = str(message.get("num", ""))
    text = str(message.get("message", ""))

    # Detect app + country
    app_name, app_logo = detect_app(text)
    country_code = detect_country_code(number)
    flag = COUNTRY_FLAGS.get(country_code, E_GLOBE)
    country_name = country_code if country_code != "UNKNOWN" else "Unknown"

    if masked:
        display_number = mask_number(number)
    else:
        display_number = number or "Unknown"

    # Build message
    lines = []
    lines.append(E_INBOX + " <b>New SMS</b>")
    lines.append("")

    if app_name != "unknown":
        lines.append(app_logo + " <b>" + app_name.upper() + "</b> " + DOT + " " + flag + " " + country_name)
    else:
        lines.append(E_MSG + " <b>SMS</b> " + DOT + " " + flag + " " + country_name)

    lines.append("")
    lines.append(E_BOLT + " <code>" + escape_html(display_number) + "</code>")

    return "\n".join(lines)


def message_buttons(message_text, sms_id, fallback=False):
    """
    Ultra buttons:
    [📋 Copy OTP: 123-456]
    [👁 Full Message] [📢 Channel]
    [🤖 Open Bot]
    """
    otp = extract_otp(message_text)
    keyboard = []

    # Row 1: OTP Copy
    row1 = []
    if otp != "N/A":
        # Show the FULL OTP in button text
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

    # Row 2: Full + Channel
    row2 = [
        {"text": E_EYES + " Full Message", "callback_data": "full:" + sms_id}
    ]
    if TELEGRAM_CHANNEL_URL:
        row2.append({
            "text": E_MEGA + " Channel",
            "url": TELEGRAM_CHANNEL_URL
        })
    keyboard.append(row2)

    # Row 3: Bot
    clean_username = BUTTON_BOT_USERNAME.lstrip("@")
    keyboard.append([
        {"text": E_BOT + " Open Bot", "url": "https://t.me/" + clean_username}
    ])

    return {"inline_keyboard": keyboard}


def build_full_message_alert(message_text, otp="N/A", app_name="unknown",
                              country_code="UNKNOWN", number=""):
    """
    Full message alert format:
    ━━━━━━━━━━━━━━━
    📱 WHATSAPP • 🇵🇰 PK
    📞 923•••4567
    ━━━━━━━━━━━━━━━
    🔑 OTP: 123-456
    ━━━━━━━━━━━━━━━
    💬 Full Message:
    [original text]
    """
    flag = COUNTRY_FLAGS.get(country_code, E_GLOBE)
    app_logo = APP_LOGOS.get(app_name, APP_LOGOS["default"])

    lines = []
    lines.append(DIVIDER)
    if app_name != "unknown":
        lines.append(app_logo + " " + app_name.upper() + " " + DOT + " " + flag + " " + country_code)
    else:
        lines.append(E_MSG + " SMS " + DOT + " " + flag + " " + country_code)

    if number:
        lines.append(E_BOLT + " " + number)

    if otp != "N/A":
        lines.append(DIVIDER)
        lines.append(E_KEY + " OTP: " + otp)

    lines.append(DIVIDER)
    lines.append(E_MSG + " " + message_text)

    return "\n".join(lines)
            # ═══════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════

async def init_db():
    conn = await aiosqlite.connect(DATABASE_FILE)
    conn.row_factory = aiosqlite.Row
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS forwarded_messages ("
        "sms_id TEXT PRIMARY KEY, "
        "claimed_at TEXT NOT NULL, "
        "sent_at TEXT, "
        "raw_num TEXT, "
        "cli TEXT, "
        "message_text TEXT, "
        "payout TEXT, "
        "dt TEXT, "
        "app TEXT, "
        "country TEXT, "
        "otp TEXT)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sent_at ON forwarded_messages(sent_at)"
    )
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS bot_state ("
        "key TEXT PRIMARY KEY, "
        "value TEXT NOT NULL)"
    )
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS api_keys ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "api_key TEXT UNIQUE NOT NULL, "
        "is_active BOOLEAN DEFAULT 1, "
        "added_at TEXT NOT NULL)"
    )
    await conn.commit()
    return conn


async def state_value(conn, key, default=""):
    async with conn.execute(
        "SELECT value FROM bot_state WHERE key = ?", (key,)
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            return str(row["value"])
        return default


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
        "sms_id, claimed_at, raw_num, cli, message_text, payout, dt, "
        "app, country, otp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(sms_id) DO UPDATE SET "
        "raw_num = excluded.raw_num, "
        "cli = excluded.cli, "
        "message_text = excluded.message_text, "
        "payout = excluded.payout, "
        "dt = excluded.dt, "
        "app = excluded.app, "
        "country = excluded.country, "
        "otp = excluded.otp",
        (sms_id, now, raw_num, cli, message_text, payout, dt,
         app, country, otp),
    )
    await conn.commit()


async def claim_message(conn, sms_id):
    async with conn.execute(
        "SELECT sent_at FROM forwarded_messages WHERE sms_id = ?", (sms_id,)
    ) as cursor:
        existing = await cursor.fetchone()
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
    ) as cursor:
        row = await cursor.fetchone()
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
        "FROM forwarded_messages WHERE sms_id = ?",
        (sms_id,),
    ) as cursor:
        row = await cursor.fetchone()
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
    ) as cursor:
        deleted = cursor.rowcount
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
    async with conn.execute(
        "SELECT COUNT(*) AS c FROM forwarded_messages"
    ) as c:
        total = (await c.fetchone())["c"]
    async with conn.execute(
        "SELECT app, COUNT(*) AS c FROM forwarded_messages "
        "WHERE sent_at IS NOT NULL GROUP BY app "
        "ORDER BY c DESC LIMIT 10"
    ) as c:
        by_app = await c.fetchall()
    return {
        "sent": sent,
        "pending": pending,
        "total": total,
        "by_app": [dict(r) for r in by_app],
    }


# ═══════════════════════════════════════════════════════
# API MANAGEMENT
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
    ) as cursor:
        deleted = cursor.rowcount
    await conn.commit()
    return deleted > 0


async def get_all_api_keys(conn):
    async with conn.execute(
        "SELECT api_key, is_active, added_at FROM api_keys ORDER BY id"
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def load_api_keys(conn):
    global api_keys, current_api_index, GREEN_SMS_API_KEY
    keys = await get_all_api_keys(conn)
    active = []
    for k in keys:
        if k["is_active"]:
            active.append(k["api_key"])
    api_keys = active

    if api_keys:
        current_api_index = 0
        GREEN_SMS_API_KEY = api_keys[0]
        logger.info("Loaded " + str(len(api_keys)) + " API keys")
    else:
        if GREEN_SMS_API_KEY:
            api_keys = [GREEN_SMS_API_KEY]
            current_api_index = 0
            logger.info("No API keys in DB, using hardcoded key")
        else:
            logger.error("No API keys available!")

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
    global current_api_index, GREEN_SMS_API_KEY

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
    logger.info("API: " + api_key[:20] + "...")

    while True:
        try:
            batch_count += 1
            params = {
                "dt1": since_dt,
                "dt2": current_dt2,
                "records": records_limit,
            }

            response = await http_client.get(
                GREEN_SMS_API,
                headers={"Authorization": "Bearer " + api_key},
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited. Waiting " + str(retry_after) + "s")
                await asyncio.sleep(retry_after)
                continue

            if response.status_code == 503:
                new_limit = max(10, records_limit // 2)
                if new_limit < records_limit:
                    records_limit = new_limit
                    logger.warning("503 -> reducing records to " + str(records_limit))
                    continue
                logger.error("503 with minimum records. Stop.")
                break

            if response.status_code == 401:
                logger.error("401 Unauthorized: " + api_key[:20] + "...")
                conn = await init_db()
                try:
                    new_key = await rotate_api_key(conn)
                    if new_key and new_key != api_key:
                        logger.info("Rotated API key")
                        api_key = new_key
                        continue
                finally:
                    await conn.close()
                raise RuntimeError("API 401 - check your API key")

            if response.status_code != 200:
                logger.error(
                    "HTTP " + str(response.status_code) + ": " + response.text[:200]
                )
                break

            payload = response.json()
            if payload.get("status") == "error":
                logger.error("API error: " + str(payload.get("msg", "Unknown")))
                break

            results = payload.get("data", [])
            total = payload.get("total", 0)

            logger.info(
                "Batch " + str(batch_count) + ": " + str(len(results)) +
                " msgs (total: " + str(total) + ")"
            )

            if not results:
                break

            all_messages.extend(results)
            total_fetched += len(results)

            if len(results) < records_limit:
                logger.info(
                    "Last batch (" + str(len(results)) + " < " +
                    str(records_limit) + ")"
                )
                break

            oldest_dt_str = results[-1].get("dt", "")
            if not oldest_dt_str:
                break

            if oldest_dt_str == last_used_dt2:
                logger.info("Same dt2 - done")
                break

            last_used_dt2 = current_dt2
            current_dt2 = oldest_dt_str
            logger.info("Next until " + current_dt2)

            if batch_count >= MAX_BATCHES:
                logger.warning("Safety limit " + str(MAX_BATCHES) + " batches")
                break

        except httpx.TimeoutException:
            logger.error("API timeout")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            logger.error("Fetch error: " + str(e))
            break

    logger.info("Fetched " + str(total_fetched) + " messages")
    all_messages.reverse()
    return all_messages


# ═══════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════

async def telegram_call(method, payload, retries=3):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/" + method

    for attempt in range(retries):
        try:
            response = await http_client.post(url, json=payload, timeout=30)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning("TG rate limit. Wait " + str(retry_after) + "s")
                await asyncio.sleep(retry_after)
                continue

            if not response.is_success:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(
                    "TG HTTP " + str(response.status_code) + ": " +
                    response.text[:500]
                )

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
        bad = (
            ("reply markup" in err) or ("button" in err) or
            ("parse" in err) or ("copy_text" in err)
        )
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


async def animate_send(cid, frames_list, duration_each=0.3):
    """Send an animated message with frames"""
    if not ANIMATION_ENABLED:
        return None
    try:
        first = await telegram_call("sendMessage", {
            "chat_id": cid,
            "text": frames_list[0],
            "parse_mode": "HTML",
        })
        mid = first.get("result", {}).get("message_id")
        if not mid:
            return None
        for frame in frames_list[1:]:
            await asyncio.sleep(duration_each)
            try:
                await telegram_call("editMessageText", {
                    "chat_id": cid,
                    "message_id": mid,
                    "text": frame,
                    "parse_mode": "HTML",
                })
            except Exception:
                pass
        return mid
    except Exception:
        return None


# ═══════════════════════════════════════════════════════
# MESSAGE HANDLER HELPERS
# ═══════════════════════════════════════════════════════

async def get_full_message_alert(conn, sms_id):
    """Build full message alert with app + country + OTP"""
    msg = await get_message_data(conn, sms_id)
    if not msg:
        return None

    otp = extract_otp(msg["message_text"])
    app_name, _ = detect_app(msg["message_text"])
    country = msg.get("country", "UNKNOWN")
    number = msg.get("raw_num", "")

    # Mask the number
    masked_num = mask_number(number) if number else ""

    return build_full_message_alert(
        message_text=msg["message_text"],
        otp=otp,
        app_name=app_name,
        country_code=country,
        number=masked_num,
)                    
# ═══════════════════════════════════════════════════════
# FORWARD LOOP
# ═══════════════════════════════════════════════════════

async def forward_loop(forward_event: asyncio.Event) -> None:
    global runtime_last_error, runtime_last_poll
    last_error: str | None = None
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

                if not messages:
                    logger.info("No new SMS")
                else:
                    logger.info("Processing " + str(len(messages)) + " messages")

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

                        # Detect app + country + OTP
                        app_name, _ = detect_app(msg_text)
                        country_code = detect_country_code(raw_num)
                        otp = extract_otp(msg_text)

                        # Save to DB
                        await save_message_data(
                            conn, sms_id, raw_num, cli, msg_text,
                            payout, dt, app_name, country_code, otp,
                        )

                        # Build display message
                        display_text = sms_text(message, masked=True)
                        markup = message_buttons(msg_text, sms_id)

                        # Send to group with animation
                        try:
                            await send_group_message(display_text, markup)
                            await mark_sent(conn, sms_id)
                            logger.info("Sent " + sms_id[:40])
                        except Exception as send_err:
                            logger.error("Send failed: " + str(send_err))
                            continue

                        if dt:
                            await set_state(conn, "last_sms_dt", dt)

                        await asyncio.sleep(0.5)

                last_error = None
                runtime_last_error = None

            except Exception as error:
                last_error = str(error)
                runtime_last_error = last_error
                logger.error("Forward error: " + last_error)

            try:
                await asyncio.wait_for(forward_event.wait(), timeout=POLL_SECONDS)
                forward_event.clear()
                logger.info("Manual trigger")
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

                    if callback:
                        sender = callback.get("from", {})
                    else:
                        sender = message.get("from", {})

                    text = str(message.get("text", ""))

                    # ═══ OWNER ONLY ═══
                    if sender.get("id") != TELEGRAM_OWNER_ID:
                        continue

                    # ═══ CALLBACK (button presses) ═══
                    if callback:
                        data = str(callback.get("data", ""))
                        callback_id = callback.get("id", "")
                        if not callback_id:
                            continue

                        # ═══ FULL MESSAGE ═══
                        if data.startswith("full:"):
                            sms_id = data.split(":", 1)[1]
                            alert = await get_full_message_alert(conn, sms_id)
                            if not alert:
                                alert = "❌ Message expired."
                            try:
                                await telegram_call("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": alert[:200],
                                    "show_alert": True,
                                })
                            except Exception as e:
                                logger.warning("Callback failed: " + str(e))

                        # ═══ OTP (fallback) ═══
                        elif data.startswith("otp:"):
                            otp = data.split(":", 1)[1]
                            if otp == "none":
                                alert = "❌ No OTP found in this message."
                            else:
                                alert = "\U0001F4CB OTP: " + otp
                            try:
                                await telegram_call("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": alert,
                                    "show_alert": True,
                                })
                            except Exception:
                                pass

                        continue

                    # ═══ OWNER PRIVATE COMMANDS ═══
                    if chat.get("type") != "private":
                        continue

                    cmd = text.strip().split(maxsplit=1)[0].split("@")[0].lower()

                    if cmd == "/start":
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": (
                                "\U0001F916 <b>SMS Forwarder Bot</b>\n"
                                "\u2501" * 14 + "\n"
                                "\u2705 <b>Online</b>\n\n"
                                "\U0001F4E2 <b>Group:</b> <code>" +
                                escape_html(TELEGRAM_GROUP_ID) + "</code>\n"
                                "\U0001F464 <b>Owner:</b> <code>" +
                                str(TELEGRAM_OWNER_ID) + "</code>\n\n"
                                "\U0001F511 <b>Commands</b>\n"
                                "\u2022 /status - Bot status\n"
                                "\u2022 /stats - Statistics\n"
                                "\u2022 /reset - Reset cursor\n"
                                "\u2022 /forwardnow - Force poll\n"
                                "\u2022 /cleanup - Delete old records\n"
                                "\u2022 /addapi KEY - Add API\n"
                                "\u2022 /remapi KEY - Remove API\n"
                                "\u2022 /apilist - List APIs"
                            ),
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/help":
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": (
                                "\U0001F4CB <b>Commands</b>\n"
                                "\u2501" * 14 + "\n"
                                "\u2699 <b>Control</b>\n"
                                "\u2022 /start\n"
                                "\u2022 /status\n"
                                "\u2022 /stats\n"
                                "\u2022 /reset\n"
                                "\u2022 /forwardnow\n"
                                "\u2022 /cleanup\n\n"
                                "\U0001F511 <b>API</b>\n"
                                "\u2022 /addapi <code>KEY</code>\n"
                                "\u2022 /remapi <code>KEY</code>\n"
                                "\u2022 /apilist"
                            ),
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/status":
                        status = await build_status_text(conn, runtime_last_error)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": status,
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/stats":
                        stats_text = await build_stats_text(conn)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": stats_text,
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/reset":
                        await set_state(conn, "last_sms_dt", "")
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\u2705 <b>Reset done</b>\nBot will re-fetch all.",
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/forwardnow":
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\U0001F680 <b>Triggered</b>",
                            "parse_mode": "HTML",
                        })
                        forward_event.set()

                    elif cmd == "/cleanup":
                        deleted = await cleanup_old_records(conn, CLEANUP_DAYS)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\U0001F9F9 <b>Cleaned:</b> " + str(deleted) +
                                    " records (> " + str(CLEANUP_DAYS) + "d)",
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/addapi":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u274C <b>Usage:</b>\n<code>/addapi YOUR_KEY</code>",
                                "parse_mode": "HTML",
                            })
                            continue
                        api_key = parts[1]
                        if await add_api_key(conn, api_key):
                            await load_api_keys(conn)
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": (
                                    "\u2705 <b>API Added</b>\n"
                                    "\U0001F511 <code>" +
                                    escape_html(api_key[:20]) + "...</code>"
                                ),
                                "parse_mode": "HTML",
                            })
                        else:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u274C API key already exists.",
                            })

                    elif cmd == "/remapi":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u274C <b>Usage:</b>\n<code>/remapi YOUR_KEY</code>",
                                "parse_mode": "HTML",
                            })
                            continue
                        api_key = parts[1]
                        if await remove_api_key(conn, api_key):
                            await load_api_keys(conn)
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": (
                                    "\u2705 <b>API Removed</b>\n"
                                    "\U0001F511 <code>" +
                                    escape_html(api_key[:20]) + "...</code>"
                                ),
                                "parse_mode": "HTML",
                            })
                        else:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\u274C API key not found.",
                            })

                    elif cmd == "/apilist":
                        keys = await get_all_api_keys(conn)
                        if not keys:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "\U0001F4CB No API keys stored.",
                            })
                            continue
                        current_key = get_current_api_key()
                        lines = [
                            "\U0001F511 <b>API Keys</b>",
                            "\u2501" * 14,
                        ]
                        for k in keys:
                            if k["api_key"] == current_key:
                                mark = "\U0001F7E2 <b>ACTIVE</b>"
                            else:
                                mark = "\U0001F310 standby"
                            lines.append(
                                mark + "\n   <code>" +
                                escape_html(k["api_key"][:20]) + "...</code>"
                            )
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "\n".join(lines),
                            "parse_mode": "HTML",
                        })

            except Exception as error:
                logger.error("Command error: " + str(error))

            await asyncio.sleep(1)
    finally:
        await conn.close()


# ═══════════════════════════════════════════════════════
# STATUS BUILDERS
# ═══════════════════════════════════════════════════════

async def build_status_text(conn, last_error):
    """Full status card"""
    if last_error:
        state_icon = E_RED
        state_label = "Error"
    else:
        state_icon = E_GREEN
        state_label = "Running"

    err_label = last_error or "none"
    active_key = get_current_api_key()[:20]
    last_dt = await state_value(conn, "last_sms_dt") or "-"
    now_label = datetime.now(timezone.utc).strftime("%H:%M:%S")
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
        E_CAL + " <b>Last DT:</b> <code>" + escape_html(last_dt) + "</code>",
        E_OUT + " <b>Forwarded:</b> " + str(total_msgs),
        E_USER + " <b>Owner:</b> <code>" + str(TELEGRAM_OWNER_ID) + "</code>",
        E_BOLT + " <b>Now:</b> " + now_label + " UTC",
        E_CROSS + " <b>Error:</b> <code>" + escape_html(err_label) + "</code>",
    ]
    return "\n".join(lines)


async def build_stats_text(conn):
    """Full statistics card"""
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
            cnt = row.get("c", 0)
            lines.append("   " + logo + " " + app.upper() + ": <b>" + str(cnt) + "</b>")

    lines.append("")
    lines.append(E_DB + " <code>" + escape_html(DATABASE_FILE) + "</code>")
    return "\n".join(lines)


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
    print("Ultra SMS -> Telegram Forwarder Bot v13")
    print("Smart OTP + App Detection + Country Flags")
    print("=" * 60)

    forward_event = asyncio.Event()
    http_client = httpx.AsyncClient(
        http2=False,
        limits=httpx.Limits(max_connections=10),
    )

    conn = await init_db()
    try:
        await load_api_keys(conn)
        await load_bot_username()
        last_dt = await state_value(conn, "last_sms_dt")

        logger.info("Bot: @" + BOT_USERNAME)
        logger.info("Button bot: @" + BUTTON_BOT_USERNAME)
        logger.info("Group: " + TELEGRAM_GROUP_ID)
        logger.info("Channel: " + TELEGRAM_CHANNEL_URL)
        logger.info("Owner: " + str(TELEGRAM_OWNER_ID))
        logger.info("Last DT: " + (last_dt or "None"))
        logger.info("Poll: " + str(POLL_SECONDS) + "s | Batch: " + str(MAX_RECORDS))
        logger.info("APIs: " + str(len(api_keys)))
        logger.info("=" * 60)
        logger.info("Started")
        logger.info("=" * 60)

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
