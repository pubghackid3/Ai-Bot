"""Green SMS -> Telegram Forwarder Bot - v7 (Paste-Safe)

Fixed for Railway:
- No multi-line lists (paste-safe)
- No box-drawing Unicode (paste-safe)
- No nested f-string quotes
- Simple string concatenation everywhere
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

COUNTRY_FLAGS = {
    "PK": "PK", "US": "US", "GB": "GB", "IN": "IN", "CA": "CA",
    "AU": "AU", "DE": "DE", "FR": "FR", "IT": "IT", "ES": "ES",
    "BR": "BR", "MX": "MX", "JP": "JP", "CN": "CN", "RU": "RU",
    "ZA": "ZA", "NG": "NG", "EG": "EG", "SA": "SA", "AE": "AE",
    "BD": "BD", "ID": "ID", "MY": "MY", "SG": "SG", "HK": "HK",
    "TR": "TR", "PL": "PL", "UA": "UA", "RO": "RO", "NL": "NL",
    "BE": "BE", "CH": "CH", "AT": "AT", "SE": "SE", "NO": "NO",
    "DK": "DK", "FI": "FI", "IE": "IE", "PT": "PT", "GR": "GR",
}


def escape_html(text):
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============ DATABASE ============

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
        "dt TEXT)"
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
    async with conn.execute("SELECT value FROM bot_state WHERE key = ?", (key,)) as cursor:
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


async def save_message_data(conn, sms_id, raw_num, cli, message_text, payout, dt):
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO forwarded_messages(sms_id, claimed_at, raw_num, cli, message_text, payout, dt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(sms_id) DO UPDATE SET "
        "raw_num = excluded.raw_num, "
        "cli = excluded.cli, "
        "message_text = excluded.message_text, "
        "payout = excluded.payout, "
        "dt = excluded.dt",
        (sms_id, now, raw_num, cli, message_text, payout, dt),
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


async def cleanup_old_records(conn, days=30):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with conn.execute(
        "DELETE FROM forwarded_messages WHERE sent_at < ?", (cutoff,)
    ) as cursor:
        deleted = cursor.rowcount
    await conn.commit()
    return deleted


# ============ HELPERS ============

def generate_sms_id(message):
    dt = str(message.get("dt", ""))
    num = str(message.get("num", ""))
    cli = str(message.get("cli", ""))
    msg = str(message.get("message", ""))
    content_hash = hashlib.md5((cli + ":" + msg).encode()).hexdigest()[:8]
    return dt + "_" + num + "_" + content_hash


def mask_number(number):
    if len(number) > 7:
        return number[:3] + "..." + number[-4:]
    return number or "Unknown"


def flag_for_number(value):
    if not value:
        return ""
    try:
        clean_number = re.sub(r"\D", "", str(value))
        parsed = phonenumbers.parse(clean_number, None)
        if phonenumbers.is_valid_number(parsed):
            region = phonenumbers.region_code_for_number(parsed)
            return COUNTRY_FLAGS.get(region, "")
    except Exception:
        pass
    return ""


def sms_text(message, masked=True):
    number = str(message.get("num", ""))
    flag = flag_for_number(number)
    if masked:
        display_number = mask_number(number)
    else:
        display_number = number or "Unknown"
    prefix = flag + " " if flag else ""
    return prefix + "<code>" + escape_html(display_number) + "</code>"


def otp_from_message(message_text):
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
    if m:
        return m.group(1)
    return "N/A"


def message_buttons(message_text, sms_id, fallback=False):
    otp = otp_from_message(message_text)
    keyboard = []

    row1 = []
    if otp != "N/A":
        if fallback:
            row1.append({"text": "Copy OTP: " + otp, "callback_data": "otp:" + otp})
        else:
            row1.append({"text": "Copy OTP", "copy_text": {"text": otp}})
    else:
        row1.append({"text": "No OTP Found", "callback_data": "otp:none"})
    keyboard.append(row1)

    row2 = []
    row2.append({"text": "Full SMS", "callback_data": "full:" + sms_id})
    if TELEGRAM_CHANNEL_URL and TELEGRAM_CHANNEL_URL != "https://t.me/your_channel":
        row2.append({"text": "Channel", "url": TELEGRAM_CHANNEL_URL})
    keyboard.append(row2)

    row3 = []
    if BOT_USERNAME:
        clean_username = BOT_USERNAME.lstrip("@")
        row3.append({"text": "Bot", "url": "https://t.me/" + clean_username})
        keyboard.append(row3)

    return {"inline_keyboard": keyboard}


# ============ API MANAGEMENT ============

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


# ============ API FETCH ============

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
            params = {"dt1": since_dt, "dt2": current_dt2, "records": records_limit}

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
                logger.error("HTTP " + str(response.status_code) + ": " + response.text[:200])
                break

            payload = response.json()
            if payload.get("status") == "error":
                logger.error("API error: " + str(payload.get("msg", "Unknown")))
                break

            results = payload.get("data", [])
            total = payload.get("total", 0)

            logger.info("Batch " + str(batch_count) + ": " + str(len(results)) + " msgs (total: " + str(total) + ")")

            if not results:
                break

            all_messages.extend(results)
            total_fetched += len(results)

            if len(results) < records_limit:
                logger.info("Last batch (" + str(len(results)) + " < " + str(records_limit) + ")")
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


# ============ TELEGRAM ============

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
                raise RuntimeError("TG HTTP " + str(response.status_code) + ": " + response.text[:500])

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
        bad = ("reply markup" in err) or ("button" in err) or ("parse" in err) or ("copy_text" in err)
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


# ============ STATUS (paste-safe) ============

async def status_text(conn, last_error):
    async with conn.execute(
        "SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NOT NULL"
    ) as c:
        row = await c.fetchone()
        total = row["c"]

    async with conn.execute(
        "SELECT COUNT(*) AS c FROM forwarded_messages WHERE sent_at IS NULL"
    ) as c:
        row = await c.fetchone()
        pending = row["c"]

    last_dt = await state_value(conn, "last_sms_dt")
    api_count = len(await get_all_api_keys(conn))

    if last_error:
        state_label = "Error"
    else:
        state_label = "Running"

    err_label = last_error or "none"
    active_key = get_current_api_key()[:20]
    last_dt_label = last_dt or "-"
    now_label = datetime.now(timezone.utc).strftime("%H:%M:%S")

    result = "Bot Status\n"
    result += "--------------------\n"
    result += "State: " + state_label + "\n"
    result += "APIs: " + str(api_count) + "\n"
    result += "Active: " + escape_html(active_key) + "...\n"
    result += "Group: " + escape_html(TELEGRAM_GROUP_ID) + "\n"
    result += "Poll: " + str(POLL_SECONDS) + "s\n"
    result += "Last DT: " + escape_html(last_dt_label) + "\n"
    result += "Sent: " + str(total) + "\n"
    result += "Pending: " + str(pending) + "\n"
    result += "Owner: " + str(TELEGRAM_OWNER_ID) + "\n"
    result += "Now: " + now_label + " UTC\n"
    result += "Error: " + escape_html(err_label)
    return result


# ============ LOOPS ============

async def forward_loop(forward_event):
    global runtime_last_error, runtime_last_poll
    last_error = None
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

                        await save_message_data(conn, sms_id, raw_num, cli, msg_text, payout, dt)

                        display_text = sms_text(message, masked=True)
                        markup = message_buttons(msg_text, sms_id)

                        await send_group_message(display_text, markup)
                        await mark_sent(conn, sms_id)

                        if dt:
                            await set_state(conn, "last_sms_dt", dt)

                        logger.info("Sent " + sms_id[:40])
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


async def command_loop(forward_event):
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

                    if sender.get("id") != TELEGRAM_OWNER_ID:
                        continue

                    if callback:
                        data = str(callback.get("data", ""))
                        callback_id = callback.get("id", "")
                        if not callback_id:
                            continue

                        if data.startswith("full:"):
                            sms_id = data.split(":", 1)[1]
                            msg_data = await get_message_data(conn, sms_id)
                            if msg_data:
                                alert = "Msg: " + msg_data["message_text"]
                                alert = alert[:200]
                            else:
                                alert = "Message expired."
                            try:
                                await telegram_call("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": alert,
                                    "show_alert": True,
                                })
                            except Exception as e:
                                logger.warning("Callback: " + str(e))

                        elif data.startswith("otp:"):
                            otp = data.split(":", 1)[1]
                            if otp == "none":
                                alert = "No OTP found in this message."
                            else:
                                alert = "OTP: " + otp
                            try:
                                await telegram_call("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": alert,
                                    "show_alert": True,
                                })
                            except Exception:
                                pass
                        continue

                    if chat.get("type") != "private":
                        continue

                    cmd = text.strip().split(maxsplit=1)[0].split("@")[0].lower()

                    if cmd == "/start":
                        start_text = "Green SMS Forwarder\n"
                        start_text += "--------------------\n"
                        start_text += "Online\n\n"
                        start_text += "Group: " + escape_html(TELEGRAM_GROUP_ID) + "\n"
                        start_text += "Owner: " + str(TELEGRAM_OWNER_ID) + "\n\n"
                        start_text += "API Commands:\n"
                        start_text += "/addapi KEY\n"
                        start_text += "/remapi KEY\n"
                        start_text += "/apilist\n\n"
                        start_text += "/help - all commands"
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": start_text,
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/help":
                        help_text = "Commands\n"
                        help_text += "--------------------\n"
                        help_text += "Control:\n"
                        help_text += "/start\n"
                        help_text += "/status\n"
                        help_text += "/stats\n"
                        help_text += "/reset\n"
                        help_text += "/forwardnow\n"
                        help_text += "/cleanup\n\n"
                        help_text += "API:\n"
                        help_text += "/addapi KEY\n"
                        help_text += "/remapi KEY\n"
                        help_text += "/apilist"
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": help_text,
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/status":
                        st = await status_text(conn, runtime_last_error)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": st,
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/reset":
                        await set_state(conn, "last_sms_dt", "")
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "Reset done. Bot will re-fetch all.",
                        })

                    elif cmd == "/stats":
                        async with conn.execute(
                            "SELECT COUNT(*) FROM forwarded_messages WHERE sent_at IS NOT NULL"
                        ) as c:
                            row = await c.fetchone()
                            total = row[0]
                        async with conn.execute(
                            "SELECT COUNT(*) FROM forwarded_messages WHERE sent_at IS NULL"
                        ) as c:
                            row = await c.fetchone()
                            pending = row[0]
                        async with conn.execute(
                            "SELECT COUNT(*) FROM forwarded_messages"
                        ) as c:
                            row = await c.fetchone()
                            all_recs = row[0]

                        stats_text = "Statistics\n"
                        stats_text += "--------------------\n"
                        stats_text += "Sent: " + str(total) + "\n"
                        stats_text += "Pending: " + str(pending) + "\n"
                        stats_text += "Records: " + str(all_recs) + "\n"
                        stats_text += "File: " + escape_html(DATABASE_FILE)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": stats_text,
                            "parse_mode": "HTML",
                        })

                    elif cmd == "/forwardnow":
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "Triggered.",
                        })
                        forward_event.set()

                    elif cmd == "/cleanup":
                        deleted = await cleanup_old_records(conn, CLEANUP_DAYS)
                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": "Cleaned: " + str(deleted) + " records (> " + str(CLEANUP_DAYS) + "d)",
                        })

                    elif cmd == "/addapi":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "Usage: /addapi YOUR_KEY",
                            })
                            continue
                        api_key = parts[1]
                        added = await add_api_key(conn, api_key)
                        if added:
                            await load_api_keys(conn)
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "API Added: " + escape_html(api_key[:20]) + "...",
                                "parse_mode": "HTML",
                            })
                        else:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "API key already exists.",
                            })

                    elif cmd == "/remapi":
                        parts = text.strip().split()
                        if len(parts) < 2:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "Usage: /remapi YOUR_KEY",
                            })
                            continue
                        api_key = parts[1]
                        removed = await remove_api_key(conn, api_key)
                        if removed:
                            await load_api_keys(conn)
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "API Removed: " + escape_html(api_key[:20]) + "...",
                                "parse_mode": "HTML",
                            })
                        else:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "API key not found.",
                            })

                    elif cmd == "/apilist":
                        keys = await get_all_api_keys(conn)
                        if not keys:
                            await telegram_call("sendMessage", {
                                "chat_id": chat["id"],
                                "text": "No API keys stored.",
                            })
                            continue

                        current_key = get_current_api_key()
                        list_text = "API Keys\n"
                        list_text += "--------------------\n"
                        for k in keys:
                            if k["api_key"] == current_key:
                                mark = "[ACTIVE] "
                            else:
                                mark = "[STANDBY] "
                            list_text += mark + escape_html(k["api_key"][:20]) + "...\n"

                        await telegram_call("sendMessage", {
                            "chat_id": chat["id"],
                            "text": list_text,
                            "parse_mode": "HTML",
                        })

            except Exception as error:
                logger.error("Command error: " + str(error))

            await asyncio.sleep(1)
    finally:
        await conn.close()


async def load_bot_username():
    global BOT_USERNAME
    try:
        response = await telegram_call("getMe", {})
        if response.get("ok"):
            BOT_USERNAME = response["result"]["username"]
            logger.info("Bot: @" + BOT_USERNAME)
    except Exception as e:
        logger.error("getMe failed: " + str(e))


async def main():
    global http_client

    print("=" * 60)
    print("Green SMS -> Telegram Forwarder")
    print("v7 - Paste-Safe")
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
        logger.info("Group: " + TELEGRAM_GROUP_ID)
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
