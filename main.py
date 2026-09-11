"""Green SMS -> Telegram Forwarder Bot - v5 (Professional UI)

Features:
- Clean & professional button layout
- Minimal text, maximum emoji
- Unlimited messages (1000+)
- Non-owner users completely ignored
- HTML parse_mode (no Markdown crash)
- Same-timestamp safe pagination
- 503 retry with reduced batch size
- FIXED: OTP regex + smart OTP extraction
"""

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

# ============ CONFIGURATION ============
GREEN_SMS_API = "http://143.110.245.86/api/partner/v1/messages/"
GREEN_SMS_API_KEY = "gsp_5735fa94_Ufmcr2_GNpht0AqpKZLK5Lt6MQxBavnavSUwx3zw-hs"
TELEGRAM_GROUP_ID = "-1004330079864"
TELEGRAM_OWNER_ID = 8762845215
TELEGRAM_CHANNEL_URL = "https://t.me/ToolsByRehan"
BOT_USERNAME = "@RN_OTP_bot"
BOT_TOKEN = "8354696843:AAEq3AUqSUSBToIf_tWA9UdtsMOjVMSTc-E"
POLL_SECONDS = 5
DATABASE_FILE = "sms_telegram_bot.sqlite3"
MAX_RECORDS = 200
MAX_BATCHES = 100
CLEANUP_DAYS = 30
# ========================================

runtime_last_error: str | None = None
runtime_last_poll: str | None = None
http_client: httpx.AsyncClient | None = None
current_api_index: int = 0
api_keys: list[str] = []

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("greensms_bot")

COUNTRY_FLAGS = {
    "PK": "🇵🇰", "US": "🇺🇸", "GB": "🇬🇧", "IN": "🇮🇳", "CA": "🇨🇦",
    "AU": "🇦🇺", "DE": "🇩🇪", "FR": "🇫🇷", "IT": "🇮🇹", "ES": "🇪🇸",
    "BR": "🇧🇷", "MX": "🇲🇽", "JP": "🇯🇵", "CN": "🇨🇳", "RU": "🇷🇺",
    "ZA": "🇿🇦", "NG": "🇳🇬", "EG": "🇪🇬", "SA": "🇸🇦", "AE": "🇦🇪",
    "BD": "🇧🇩", "ID": "🇮🇩", "MY": "🇲🇾", "SG": "🇸🇬", "HK": "🇭🇰",
    "TR": "🇹🇷", "PL": "🇵🇱", "UA": "🇺🇦", "RO": "🇷🇴", "NL": "🇳🇱",
    "BE": "🇧🇪", "CH": "🇨🇭", "AT": "🇦🇹", "SE": "🇸🇪", "NO": "🇳🇴",
    "DK": "🇩🇰", "FI": "🇫🇮", "IE": "🇮🇪", "PT": "🇵🇹", "GR": "🇬🇷",
}


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============ DATABASE ============

async def init_db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DATABASE_FILE)
    conn.row_factory = aiosqlite.Row
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS forwarded_messages (
            sms_id TEXT PRIMARY KEY,
            claimed_at TEXT NOT NULL,
            sent_at TEXT,
            raw_num TEXT,
            cli TEXT,
            message_text TEXT,
            payout TEXT,
            dt TEXT
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_sent_at ON forwarded_messages(sent_at)")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            added_at TEXT NOT NULL
        )
    """)
    await conn.commit()
    return conn


async def state_value(conn, key: str, default: str = "") -> str:
    async with conn.execute("SELECT value FROM bot_state WHERE key = ?", (key,)) as cursor:
        row = await cursor.fetchone()
        return str(row["value"]) if row else default


async def set_state(conn, key: str, value: str) -> None:
    await conn.execute("""
        INSERT INTO bot_state(key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    await conn.commit()


async def save_message_data(conn, sms_id, raw_num, cli, message_text, payout, dt):
    await conn.execute("""
        INSERT INTO forwarded_messages(sms_id, claimed_at, raw_num, cli, message_text, payout, dt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(sms_id) DO UPDATE SET
            raw_num = excluded.raw_num,
            cli = excluded.cli,
            message_text = excluded.message_text,
            payout = excluded.payout,
            dt = excluded.dt
    """, (sms_id, datetime.now(timezone.utc).isoformat(), raw_num, cli, message_text, payout, dt))
    await conn.commit()


async def claim_message(conn, sms_id: str) -> bool:
    async with conn.execute("SELECT sent_at FROM forwarded_messages WHERE sms_id = ?", (sms_id,)) as cursor:
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
    async with conn.execute("SELECT 1 FROM forwarded_messages WHERE sms_id = ?", (sms_id,)) as cursor:
        return await cursor.fetchone() is not None


async def mark_sent(conn, sms_id: str) -> None:
    await conn.execute(
        "UPDATE forwarded_messages SET sent_at = ? WHERE sms_id = ?",
        (datetime.now(timezone.utc).isoformat(), sms_id),
    )
    await conn.commit()


async def get_message_data(conn, sms_id: str) -> dict[str, Any] | None:
    async with conn.execute(
        "SELECT raw_num, cli, message_text, payout, dt FROM forwarded_messages WHERE sms_id = ?",
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
    }


async def cleanup_old_records(conn, days: int = 30) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with conn.execute("DELETE FROM forwarded_messages WHERE sent_at < ?", (cutoff,)) as cursor:
        deleted = cursor.rowcount
    await conn.commit()
    return deleted


# ============ HELPERS ============

def generate_sms_id(message: dict[str, Any]) -> str:
    dt = str(message.get("dt", ""))
    num = str(message.get("num", ""))
    cli = str(message.get("cli", ""))
    msg = str(message.get("message", ""))
    content_hash = hashlib.md5(f"{cli}:{msg}".encode()).hexdigest()[:8]
    return f"{dt}_{num}_{content_hash}"


def mask_number(number: str) -> str:
    if len(number) > 7:
        return f"{number[:3]}•••{number[-4:]}"
    return number or "Unknown"


def flag_for_number(value: str | None) -> str:
    if not value:
        return "🌐"
    try:
        clean_number = re.sub(r"\D", "", str(value))
        parsed = phonenumbers.parse(clean_number, None)
        if phonenumbers.is_valid_number(parsed):
            region = phonenumbers.region_code_for_number(parsed)
            return COUNTRY_FLAGS.get(region, "🌐")
    except Exception:
        pass
    return "🌐"


def sms_text(message: dict[str, Any], masked: bool = True) -> str:
    """Compact, professional message line."""
    number = str(message.get("num", ""))
    flag = flag_for_number(number)
    display_number = mask_number(number) if masked else (number or "Unknown")
    return f"{flag} <code>{escape_html(display_number)}</code>"


def otp_from_message(message_text: str) -> str:
    """
    Smart OTP extraction:
      1. Near keyword (OTP / code / PIN / verify / password)
      2. First 4-8 digit standalone number
      3. First 3-9 digit standalone number
    """
    if not message_text:
        return "N/A"

    keyword_match = re.search(
        r"(?:otp|code|pin|verify|verification|password)[^\d]{0,15}(\d{3,9})",
        message_text,
        re.IGNORECASE,
    )
    if keyword_match:
        return keyword_match.group(1)

    m = re.search(r"(?<!\d)(\d{4,8})(?!\d)", message_text)
    if m:
        return m.group(1)

    m = re.search(r"(?<!\d)(\d{3,9})(?!\d)", message_text)
    return m.group(1) if m else "N/A"


def message_buttons(message_text: str, sms_id: str, fallback: bool = False) -> dict[str, Any]:
    """
    Professional, compact button layout:

        [ 📋 Copy OTP ]
        [ 👁 Full SMS ]  [ 📢 Channel ]
        [ 🤖 Bot ]
    """
    otp = otp_from_message(message_text)

    # --- Row 1: OTP ---
    row1 = []
    if fallback:
        # Fallback: show OTP in button text and copy via callback alert
        if otp != "N/A":
            row1.append({"text": f"📋 OTP: {otp}", "callback_data": f"otp:{otp}"})
        else:
            row1.append({"text": "❌ No OTP Found", "callback_data": "otp:none"})
    else:
        if otp != "N/A":
            row1.append({"text": "📋 Copy OTP", "copy_text": {"text": otp}})
        else:
            row1.append({"text": "❌ No OTP Found", "callback_data": "otp:none"})

    # --- Row 2: Full SMS + Channel ---
    row2 = []
    row2.append({"text": "👁 Full SMS", "callback_data": f"full:{sms_id}"})
    if TELEGRAM_CHANNEL_URL and TELEGRAM_CHANNEL_URL != "https://t.me/your_channel":
        row2.append({"text": "📢 Channel", "url": TELEGRAM_CHANNEL_URL})

    # --- Row 3: Bot ---
    row3 = []
    if BOT_USERNAME:
        clean_username = BOT_USERNAME.lstrip("@")
        row3.append({"text": "🤖 Bot", "url": f"https://t.me/{clean_username}"})

    keyboard = []
    if row1:
        keyboard.append(row1)
    if row2:
        keyboard.append(row2)
    if row3:
        keyboard.append(row3)

    return {"inline_keyboard": keyboard}


# ============ API MANAGEMENT ============

async def add_api_key(conn, api_key: str) -> bool:
    try:
        await conn.execute(
            "INSERT INTO api_keys (api_key, added_at) VALUES (?, ?)",
            (api_key, datetime.now(timezone.utc).isoformat()),
        )
        await conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


async def remove_api_key(conn, api_key: str) -> bool:
    async with conn.execute("DELETE FROM api_keys WHERE api_key = ?", (api_key,)) as cursor:
        deleted = cursor.rowcount
    await conn.commit()
    return deleted > 0


async def get_all_api_keys(conn) -> list[dict[str, Any]]:
    async with conn.execute("SELECT api_key, is_active, added_at FROM api_keys ORDER BY id") as cursor:
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def load_api_keys(conn) -> list[str]:
    global api_keys, current_api_index, GREEN_SMS_API_KEY
    keys = await get_all_api_keys(conn)
    api_keys = [k["api_key"] for k in keys if k["is_active"]]

    if api_keys:
        current_api_index = 0
        GREEN_SMS_API_KEY = api_keys[0]
        logger.info(f"✅ Loaded {len(api_keys)} API keys")
    else:
        if GREEN_SMS_API_KEY:
            api_keys = [GREEN_SMS_API_KEY]
            current_api_index = 0
            logger.info("⚠️ No API keys in DB, using hardcoded key")
        else:
            logger.error("❌ No API keys available!")

    return api_keys


def get_current_api_key() -> str:
    global api_keys, current_api_index
    if api_keys and current_api_index < len(api_keys):
        return api_keys[current_api_index]
    return GREEN_SMS_API_KEY


async def rotate_api_key(conn) -> str | None:
    global current_api_index, GREEN_SMS_API_KEY
    if not api_keys:
        return None
    current_api_index = (current_api_index + 1) % len(api_keys)
    GREEN_SMS_API_KEY = api_keys[current_api_index]
    logger.info(f"🔄 Rotated to API key #{current_api_index + 1}")
    return GREEN_SMS_API_KEY


# ============ API FETCH ============

async def fetch_all_messages(since_dt: str = "") -> list[dict[str, Any]]:
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
    last_used_dt2: str | None = None
    records_limit = MAX_RECORDS

    logger.info(f"🔍 Fetching: {since_dt} → {current_dt2}")
    logger.info(f"🔑 API: {api_key[:20]}...")

    while True:
        try:
            batch_count += 1
            params = {"dt1": since_dt, "dt2": current_dt2, "records": records_limit}

            response = await http_client.get(
                GREEN_SMS_API,
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"⏳ Rate limited. Waiting {retry_after}s...")
                await asyncio.sleep(retry_after)
                continue

            if response.status_code == 503:
                new_limit = max(10, records_limit // 2)
                if new_limit < records_limit:
                    records_limit = new_limit
                    logger.warning(f"⚠️ 503 → reducing records to {records_limit}")
                    continue
                logger.error("❌ 503 with minimum records. Stop.")
                break

            if response.status_code == 401:
                logger.error(f"❌ 401 Unauthorized: {api_key[:20]}...")
                conn = await init_db()
                try:
                    new_key = await rotate_api_key(conn)
                    if new_key and new_key != api_key:
                        logger.info("🔄 Rotated API key")
                        api_key = new_key
                        continue
                finally:
                    await conn.close()
                raise RuntimeError("API 401 - check your API key")

            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                break

            payload = response.json()
            if payload.get("status") == "error":
                logger.error(f"❌ API error: {payload.get('msg', 'Unknown')}")
                break

            results = payload.get("data", [])
            total = payload.get("total", 0)

            logger.info(f"📄 Batch {batch_count}: {len(results)} msgs (total: {total})")

            if not results:
                break

            all_messages.extend(results)
            total_fetched += len(results)

            if len(results) < records_limit:
                logger.info(f"📌 Last batch ({len(results)} < {records_limit})")
                break

            oldest_dt_str = results[-1].get("dt", "")
            if not oldest_dt_str:
                break

            if oldest_dt_str == last_used_dt2:
                logger.info("📌 Same dt2 — done")
                break

            last_used_dt2 = current_dt2
            current_dt2 = oldest_dt_str
            logger.info(f"➡️ Next until {current_dt2}")

            if batch_count >= MAX_BATCHES:
                logger.warning(f"⚠️ Safety limit {MAX_BATCHES} batches")
                break

        except httpx.TimeoutException:
            logger.error("❌ API timeout")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            logger.error(f"❌ Fetch error: {e}")
            break

    logger.info(f"📨 Fetched {total_fetched} messages")
    all_messages.reverse()
    return all_messages


# ============ TELEGRAM ============

async def telegram_call(method: str, payload: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    for attempt in range(retries):
        try:
            response = await http_client.post(url, json=payload, timeout=30)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning(f"⏳ TG rate limit. Wait {retry_after}s")
                await asyncio.sleep(retry_after)
                continue

            if not response.is_success:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(f"TG HTTP {response.status_code}: {response.text[:500]}")

            result = response.json()
            if not result.get("ok"):
                desc = result.get("description", "Unknown")
                d = desc.lower()
                if any(k in d for k in ("reply markup", "button", "parse", "copy_text")):
                    raise RuntimeError(f"TG markup error: {desc}")
                if result.get("error_code") == 429 and attempt < retries - 1:
                    await asyncio.sleep(result.get("parameters", {}).get("retry_after", 1))
                    continue
                raise RuntimeError(f"TG error: {desc}")
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
            raise RuntimeError(f"TG request failed: {e}")


async def send_group_message(text: str, reply_markup: dict[str, Any]) -> dict[str, Any]:
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
        if any(k in err for k in ("reply markup", "button", "parse", "copy_text")):
            logger.warning("⚠️ copy_text unsupported → fallback")
            sms_id = ""
            for row in reply_markup.get("inline_keyboard", []):
                for btn in row:
                    if btn.get("callback_data", "").startswith("full:"):
                        sms_id = btn["callback_data"].split(":", 1)[1]
                        break
            # Rebuild fallback buttons using full text (retrieve from DB is safer, but
            # text here is masked — use it as-is; OTP extraction from masked text still works
            # because OTP digits are not masked).
            fallback_markup = message_buttons(text, sms_id, fallback=True)
            payload["reply_markup"] = fallback_markup
            return await telegram_call("sendMessage", payload)
        raise


async def telegram_updates(offset: int) -> list[dict[str, Any]]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
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
        logger.error(f"❌ Updates error: {e}")
        return []


# ============ STATUS ============

async def status_text(conn, last_error: str | None) -> str:
    async with conn.execute("SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NOT NULL") as c:
        total = (await c.fetchone())["c"]
    async with conn.execute("SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NULL") as c:
        pending = (await c.fetchone())["c"]
    last_dt = await state_value(conn, "last_sms_dt")
    api_count = len(await get_all_api_keys(conn))

    state_icon = "🟢" if not last_error else "🔴"

    return (
        "📊 <b>Bot Status</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{state_icon} <b>State:</b> {'Running' if not last_error
