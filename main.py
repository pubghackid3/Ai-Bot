# ==========================================================
#   👑 PROFESSIONAL TELEGRAM BOT — FULL FIXED
#   Owner: @Ghost_Code_404  |  Channel: @ToolsByRehan
#   No animations — instant response
# ==========================================================
import sys, subprocess, importlib

for _pkg in ["aiogram==3.7.0", "telethon==1.36.0", "cryptography==42.0.8"]:
    _mod = _pkg.split("==")[0]
    try:
        importlib.import_module(_mod)
    except ImportError:
        print(f"📦 Installing {_pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", _pkg])

import os, io, csv, sqlite3, datetime, logging, time, asyncio
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup as IKM,
    InlineKeyboardButton as IKB,
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
CHANNEL_LINK     = "https://t.me/ToolsByRehan"
CHANNEL_USERNAME = "@ToolsByRehan"
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

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
        logging.warning(f"FERNET_KEY: {FERNET_KEY.decode()}")
cipher = Fernet(FERNET_KEY)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher(storage=MemoryStorage())
CLIENTS: dict = {}

# ==========================================================
#                    🌐 TRANSLATIONS
# ==========================================================
WELCOME = {
"en": ("✨ <b>Welcome to ToolsByRehan Bot</b>\n"
       "━━━━━━━━━━━━━━━━━━━━\n\n"
       "👋 <b>Hello, {name}!</b>\n\n"
       "Your complete Telegram Manager.\n\n"
       "💎 Link unlimited accounts\n"
       "🎯 Set target groups\n"
       "💰 Earn points and get members\n"
       "💳 Buy members anytime\n\n"
       "━━━━━━━━━━━━━━━━━━━━\n"
       "👇 Get started below"),
"ur": ("✨ <b>ToolsByRehan بوٹ میں خوش آمدید</b>\n"
       "━━━━━━━━━━━━━━━━━━━━\n\n"
       "👋 <b>السلام علیکم، {name}!</b>\n\n"
       "آپ کا مکمل ٹیلیگرام منیجر۔\n\n"
       "💎 لا محدود اکاؤنٹس\n"
       "🎯 ٹارگٹ گروپ سیٹنگ\n"
       "💰 پوائنٹس اور فری ممبرز\n"
       "💳 ممبرز خریدیں\n\n"
       "━━━━━━━━━━━━━━━━━━━━\n"
       "👇 نیچے سے شروع کریں"),
"hi": ("✨ <b>ToolsByRehan बॉट में स्वागत</b>\n"
       "━━━━━━━━━━━━━━━━━━━━\n\n"
       "👋 <b>नमस्ते, {name}!</b>\n\n"
       "आपका पूरा Telegram Manager।\n\n"
       "💎 असीमित अकाउंट\n"
       "🎯 आसान टार्गेट\n"
       "💰 पॉइंट्स और फ्री मेंबर\n"
       "💳 मेंबर खरीदें\n\n"
       "━━━━━━━━━━━━━━━━━━━━\n"
       "👇 शुरू करें"),
"rom_ur": ("✨ <b>ToolsByRehan Bot mein Khush Aamdeed</b>\n"
       "━━━━━━━━━━━━━━━━━━━━\n\n"
       "👋 <b>Assalam-o-Alaikum, {name}!</b>\n\n"
       "Aap ka complete Telegram Manager.\n\n"
       "💎 Unlimited accounts\n"
       "🎯 Aasan target setting\n"
       "💰 Points aur free members\n"
       "💳 Buy members\n\n"
       "━━━━━━━━━━━━━━━━━━━━\n"
       "👇 Shuru karein"),
"ar": ("✨ <b>مرحباً بك في بوت ToolsByRehan</b>\n"
       "━━━━━━━━━━━━━━━━━━━━\n\n"
       "👋 <b>مرحباً، {name}!</b>\n\n"
       "مدير تيليجرام الكامل.\n\n"
       "💎 اربط حسابات\n"
       "🎯 عيّن الأهداف\n"
       "💰 نقاط وأعضاء مجاناً\n"
       "💳 شراء أعضاء\n\n"
       "━━━━━━━━━━━━━━━━━━━━\n"
       "👇 ابدأ الآن"),
}

TEXTS = {
"en": {
 "menu_title":"🏠 <b>DASHBOARD</b>\n━━━━━━━━━━━━━━━━━━━━\n👇 Choose an option",
 "language_set":"✅ Language set to English",
 "choose_language":"🌐 <b>Select Language</b>\n👇 Pick one:",
 "btn_back":"🔙  Back","btn_cancel":"❌  Cancel","btn_menu":"🏠  Dashboard",
 "add_title":"➕ <b>ADD ACCOUNT</b>",
 "add_guide":"📖 Send your Telegram phone number with country code.\n✍️ Example: <code>+923001234567</code>\n⚠️ Each number once.",
 "otp_guide":"📩 <b>Code sent!</b>\n✍️ Enter the code Telegram sent you.",
 "pwd_guide":"🔐 <b>2FA Password</b>\n✍️ Send your password.",
 "linked_ok":"✅ <b>Account Added</b>\n📱 <code>{phone}</code>",
 "phone_used":"❌ <b>Number Already Linked</b>\n<code>{phone}</code>",
 "target_title":"🎯 <b>SET TARGET GROUP</b>","target_guide":"📖 Send group link where members should be added.\n✍️ <code>https://t.me/yourgroup</code>",
 "target_saved":"✅ <b>Target Saved</b>\n🎯 {link}",
 "own_title":"🏠 <b>SET YOUR GROUP</b>","own_guide":"📖 Send your own group link.\n✍️ <code>https://t.me/mygroups</code>",
 "own_saved":"✅ <b>Own Group Saved</b>\n🏠 {link}",
 "my_title":"📊 <b>MY ACCOUNTS</b>","no_accounts":"❌ No accounts yet.",
 "submit_title":"📦 <b>SUBMIT ORDER</b>","submit_no_acc":"❌ No accounts linked.",
 "submit_incomplete":"⚠️ <b>Not Ready</b>\n\nSome accounts need target.",
 "history_title":"📜 <b>HISTORY</b>","history_empty":"❌ No orders yet.",
 "status_pending":"⏳ Pending","status_process":"🔄 Processing",
 "status_complete":"✅ Complete","status_rejected":"❌ Rejected",
 "members_title":"👥 <b>MEMBER INFO</b>",
 "members_body":"📊 <b>Rates:</b>\n• Paid: <b>1 acc = {rate} members</b>\n• Free: <b>{ppm} pts = 1 member</b>\n\n📱 Accounts: <b>{accounts}</b>\n💰 Points: <b>{points}</b>",
 "help_title":"📖 <b>HOW TO USE</b>",
 "help_body":("📖 <b>Step-by-Step Guide</b>\n"
              "━━━━━━━━━━━━━━━━━━━━\n\n"
              "<b>1. Add Account</b>\n"
              "My Accounts → Add New Account\n"
              "Send phone number with country code.\n\n"
              "<b>2. Set Target Group</b>\n"
              "My Accounts → Set Target Group\n"
              "Send the group link where you want members.\n\n"
              "<b>3. Set Your Group</b>\n"
              "My Accounts → Set Your Own Group\n"
              "For receiving reports.\n\n"
              "<b>4. Submit Order</b>\n"
              "Orders → Submit New Order\n"
              "Delivery in 24–48 hours.\n\n"
              "<b>Free Members</b>\n"
              "• Refer friends → 100 points each\n"
              "• 2 points = 1 member\n"
              "• Orders → Free Order\n\n"
              "━━━━━━━━━━━━━━━━━━━━\n"
              "🛎 Support: @{support}"),
 "invalid_link":"❌ Invalid link.","invalid_phone":"❌ Invalid number.",
 "cancelled":"❌ <b>Cancelled</b>","banned":"🚫 Banned","rate_limited":"⏳ Slow down.",
 "ref_title":"🎁 <b>REFER & EARN</b>",
 "ref_body":"🔗 <code>{link}</code>\n\n💰 Points: <b>{points}</b>\n👥 Referrals: <b>{refs}</b>\n\n💡 Friend links first account → <b>+{reward} pts</b>",
 "ref_reward":"🎉 <b>+{pts} Points!</b>\n{name} linked first account.\n💰 Total: <b>{total}</b>",
 "new_ref_notice":"👋 Welcome! Referrer will get <b>{pts} pts</b> once you link your first account.",
 "points_title":"💰 <b>MY POINTS</b>",
 "points_body":"💰 Points: <b>{points}</b>\n💎 {ppm} pts = 1 member\n👥 Can order: <b>{members} members</b>",
 "free_title":"💎 <b>FREE ORDER</b>","free_intro":"📖 Send target group link:",
 "free_own":"✅ Now send your own group link:",
 "free_amount":"✅ How many members?\n💎 {ppm} pts per member\n💰 Your balance: <b>{points}</b>\n✍️ Example: <code>25</code>",
 "free_no_points":"❌ Not Enough Points\n💰 You have: {points}\n💎 Need: {need}",
 "free_invalid_num":"❌ Send a number ≥ 1.",
 "free_confirm":"💎 <b>Confirm Order</b>\n👥 Members: {members}\n💰 Cost: {cost} pts\n💰 Remaining: {remaining}\n🎯 Target: {target}\n🏠 Own: {own}",
 "free_done":"🎉 <b>Order Placed!</b>\n👥 {members}\n💰 Used: {cost} pts\n💰 Left: {remaining}\n⏱ {time}",
 "btn_confirm":"✅  Confirm","btn_edit":"❌  Cancel",
 "ticket_title":"🎫 <b>NEW TICKET</b>","ticket_guide":"✍️ Describe your issue.",
 "ticket_sent":"✅ Ticket <b>#{id}</b> sent.",
 "coupon_prompt":"🎟 <b>Redeem Coupon</b>\n\nSend: <code>/redeem YOURCODE</code>",
 "buy_title":"💳 <b>BUY MEMBERS</b>",
 "buy_body":"💎 <b>How to buy:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n1️⃣ Contact our support\n2️⃣ Send payment\n3️⃣ Points added to your account\n4️⃣ Order members instantly\n\n💰 Rate: <b>{ppm} pts = 1 member</b>\n\n🎯 <b>You receive:</b>\n• Real Telegram members\n• Fast delivery\n• 100% safe\n\n🛎 Support: @{support}",
 "owner_msg_status":"📢 <b>Order Update</b>\n#{id}: <b>{status}</b>\n💬 {note}",
 "owner_msg_custom":"📩 <b>Message from Support</b>\n\n{msg}",
},
"ur": {
 "menu_title":"🏠 <b>ڈیش بورڈ</b>\n━━━━━━━━━━━━━━━━━━━━\n👇 آپشن منتخب کریں",
 "language_set":"✅ زبان اردو",
 "choose_language":"🌐 <b>زبان منتخب کریں</b>",
 "btn_back":"🔙  واپس","btn_cancel":"❌  منسوخ","btn_menu":"🏠  ڈیش بورڈ",
 "add_title":"➕ <b>اکاؤنٹ شامل کریں</b>",
 "add_guide":"📖 اپنا ٹیلیگرام نمبر کنٹری کوڈ کے ساتھ بھیجیں۔\n✍️ مثال: <code>+923001234567</code>",
 "otp_guide":"📩 <b>کوڈ بھیج دیا!</b>\n✍️ وہ کوڈ ڈالیں جو ٹیلیگرام نے بھیجا۔",
 "pwd_guide":"🔐 <b>2FA پاس ورڈ</b>\n✍️ اپنا پاس ورڈ بھیجیں۔",
 "linked_ok":"✅ <b>اکاؤنٹ شامل ہو گیا</b>\n📱 <code>{phone}</code>",
 "phone_used":"❌ <b>نمبر پہلے سے لنک ہے</b>\n<code>{phone}</code>",
 "target_title":"🎯 <b>ٹارگٹ گروپ سیٹ کریں</b>","target_guide":"📖 وہ گروپ لنک بھیجیں جہاں ممبرز چاہیے۔\n✍️ <code>https://t.me/yourgroup</code>",
 "target_saved":"✅ <b>ٹارگٹ محفوظ</b>\n🎯 {link}",
 "own_title":"🏠 <b>اپنا گروپ سیٹ کریں</b>","own_guide":"📖 اپنا گروپ لنک بھیجیں۔\n✍️ <code>https://t.me/mygroups</code>",
 "own_saved":"✅ <b>محفوظ</b>\n🏠 {link}",
 "my_title":"📊 <b>میرے اکاؤنٹس</b>","no_accounts":"❌ کوئی اکاؤنٹ نہیں۔",
 "submit_title":"📦 <b>آرڈر بھیجیں</b>","submit_no_acc":"❌ کوئی اکاؤنٹ لنک نہیں۔",
 "submit_incomplete":"⚠️ <b>آرڈر مکمل نہیں</b>\n\nکچھ اکاؤنٹس کا ٹارگٹ سیٹ نہیں۔",
 "history_title":"📜 <b>ہسٹری</b>","history_empty":"❌ کوئی آرڈر نہیں۔",
 "status_pending":"⏳ زیر التوا","status_process":"🔄 پروسیسنگ",
 "status_complete":"✅ مکمل","status_rejected":"❌ مسترد",
 "members_title":"👥 <b>ممبرز</b>",
 "members_body":"📊 1 اکاؤنٹ = {rate} ممبرز\n💎 {ppm} پوائنٹس = 1 ممبر\n📱 {accounts}\n💰 {points}",
 "help_title":"📖 <b>استعمال کا طریقہ</b>",
 "help_body":("📖 <b>قدم بہ قدم</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
              "<b>1. اکاؤنٹ شامل</b>\nMy Accounts → Add New Account\n\n"
              "<b>2. ٹارگٹ سیٹ</b>\nMy Accounts → Set Target Group\n\n"
              "<b>3. اپنا گروپ</b>\nMy Accounts → Set Your Own Group\n\n"
              "<b>4. آرڈر</b>\nOrders → Submit New Order\n\n"
              "🎁 ریفرل → 100 پوائنٹس\n💎 2 = 1 ممبر\n\n"
              "🛎 @{support}"),
 "invalid_link":"❌ غلط لنک","invalid_phone":"❌ غلط نمبر",
 "cancelled":"❌ <b>منسوخ</b>","banned":"🚫 بلاک","rate_limited":"⏳",
 "ref_title":"🎁 <b>ریفر اور کمائیں</b>",
 "ref_body":"🔗 <code>{link}</code>\n\n💰 پوائنٹس: {points}\n👥 ریفرلز: {refs}\n\n💡 دوست پہلا اکاؤنٹ → +{reward}",
 "ref_reward":"🎉 <b>+{pts} پوائنٹس!</b>\n{name}\n💰 کل: {total}",
 "new_ref_notice":"👋 ریفرر کو {pts} پوائنٹس ملیں گے۔",
 "points_title":"💰 <b>میرے پوائنٹس</b>",
 "points_body":"💰 {points}\n💎 {ppm} = 1\n👥 {members}",
 "free_title":"💎 <b>فری آرڈر</b>","free_intro":"📖 ٹارگٹ لنک:",
 "free_own":"✅ اپنا گروپ لنک:",
 "free_amount":"👥 کتنے؟\n💎 {ppm}/ممبر\n💰 {points}",
 "free_no_points":"❌ کم\n💰 {points}\n💎 چاہیے: {need}","free_invalid_num":"❌",
 "free_confirm":"💎 تصدیق\n👥 {members}\n💰 {cost}\nباقی: {remaining}\n🎯 {target}\n🏠 {own}",
 "free_done":"🎉 آرڈر بھیج دیا!\n👥 {members}\n💰 {cost}\nباقی: {remaining}\n⏱ {time}",
 "btn_confirm":"✅ تصدیق","btn_edit":"❌ منسوخ",
 "ticket_title":"🎫 <b>ٹکٹ</b>","ticket_guide":"✍️ مسئلہ لکھیں۔","ticket_sent":"✅ #{id}",
 "coupon_prompt":"🎟 <code>/redeem CODE</code>",
 "buy_title":"💳 <b>ممبرز خریدیں</b>",
 "buy_body":"💎 کیسے:\n1️⃣ سپورٹ\n2️⃣ پیمنٹ\n3️⃣ پوائنٹس\n4️⃣ ممبرز\n\n💰 {ppm} = 1\n\n🛎 @{support}",
 "owner_msg_status":"📢 #{id}: {status}\n{note}","owner_msg_custom":"📩 {msg}",
},
"hi": {
 "menu_title":"🏠 <b>डैशबोर्ड</b>\n👇 चुनें","language_set":"✅ हिंदी","choose_language":"🌐 <b>भाषा चुनें</b>",
 "btn_back":"🔙  वापस","btn_cancel":"❌  रद्द","btn_menu":"🏠  डैशबोर्ड",
 "add_title":"➕","add_guide":"📖 नंबर भेजें।","otp_guide":"📩 कोड!","pwd_guide":"🔐 2FA",
 "linked_ok":"✅ {phone}","phone_used":"❌ लिंक है",
 "target_title":"🎯","target_guide":"📖 t.me/...","target_saved":"✅ {link}",
 "own_title":"🏠","own_guide":"📖 t.me/...","own_saved":"✅ {link}",
 "my_title":"📊","no_accounts":"❌","submit_title":"📦","submit_no_acc":"❌",
 "submit_incomplete":"⚠️","history_title":"📜","history_empty":"❌",
 "status_pending":"⏳","status_process":"🔄","status_complete":"✅","status_rejected":"❌",
 "members_title":"👥","members_body":"1={rate}\n{ppm}=1\n{accounts}\n{points}",
 "help_title":"📖","help_body":"1️⃣ 2️⃣ 3️⃣ 4️⃣\n+100 pts\n🛎 @{support}",
 "invalid_link":"❌","invalid_phone":"❌","cancelled":"❌","banned":"🚫","rate_limited":"⏳",
 "ref_title":"🎁","ref_body":"{link}\n💰{points}\n👥{refs}\n+{reward}",
 "ref_reward":"🎉+{pts}\n{name}\n{total}","new_ref_notice":"👋 +{pts}",
 "points_title":"💰","points_body":"💰{points}\n{ppm}=1\n👥{members}",
 "free_title":"💎","free_intro":"📖 target:","free_own":"📖 own:",
 "free_amount":"?{ppm}/{points}","free_no_points":"❌ {points}/{need}","free_invalid_num":"❌",
 "free_confirm":"{members}/{cost}/{remaining}","free_done":"🎉{members}/{cost}/{remaining}",
 "btn_confirm":"✅","btn_edit":"❌","ticket_title":"🎫","ticket_guide":"✍️",
 "ticket_sent":"✅#{id}","coupon_prompt":"🎟 /redeem CODE",
 "buy_title":"💳","buy_body":"💎\n{ppm}=1\n🛎 @{support}",
 "owner_msg_status":"📢{id}:{status}","owner_msg_custom":"📩{msg}",
},
"rom_ur": {
 "menu_title":"🏠 <b>DASHBOARD</b>\n👇 Chunein","language_set":"✅ Roman Urdu","choose_language":"🌐 <b>Zaban chunein</b>",
 "btn_back":"🔙  Wapas","btn_cancel":"❌  Cancel","btn_menu":"🏠  Dashboard",
 "add_title":"➕","add_guide":"📖 Number bhejein.","otp_guide":"📩 Code!","pwd_guide":"🔐 2FA",
 "linked_ok":"✅ {phone}","phone_used":"❌ Linked",
 "target_title":"🎯","target_guide":"📖 t.me/...","target_saved":"✅ {link}",
 "own_title":"🏠","own_guide":"📖 t.me/...","own_saved":"✅ {link}",
 "my_title":"📊","no_accounts":"❌","submit_title":"📦","submit_no_acc":"❌",
 "submit_incomplete":"⚠️","history_title":"📜","history_empty":"❌",
 "status_pending":"⏳","status_process":"🔄","status_complete":"✅","status_rejected":"❌",
 "members_title":"👥","members_body":"1={rate}\n{ppm}=1\n{accounts}\n{points}",
 "help_title":"📖","help_body":"1️⃣2️⃣3️⃣4️⃣\n+100\n🛎 @{support}",
 "invalid_link":"❌","invalid_phone":"❌","cancelled":"❌","banned":"🚫","rate_limited":"⏳",
 "ref_title":"🎁","ref_body":"{link}\n{points}\n{refs}\n+{reward}",
 "ref_reward":"🎉+{pts}\n{name}\n{total}","new_ref_notice":"👋 +{pts}",
 "points_title":"💰","points_body":"💰{points}\n{ppm}=1\n{members}",
 "free_title":"💎","free_intro":"📖 Target:","free_own":"📖 Own:",
 "free_amount":"?{ppm}/{points}","free_no_points":"❌ {points}/{need}","free_invalid_num":"❌",
 "free_confirm":"{members}/{cost}/{remaining}","free_done":"🎉{members}/{cost}/{remaining}",
 "btn_confirm":"✅","btn_edit":"❌","ticket_title":"🎫","ticket_guide":"✍️",
 "ticket_sent":"✅#{id}","coupon_prompt":"🎟 /redeem CODE",
 "buy_title":"💳","buy_body":"💎\n{ppm}=1\n🛎 @{support}",
 "owner_msg_status":"📢{id}:{status}","owner_msg_custom":"📩{msg}",
},
"ar": {
 "menu_title":"🏠 <b>القائمة</b>","language_set":"✅ العربية","choose_language":"🌐 <b>اختر اللغة</b>",
 "btn_back":"🔙  رجوع","btn_cancel":"❌  إلغاء","btn_menu":"🏠  القائمة",
 "add_title":"➕","add_guide":"📖 أرسل رقمك.","otp_guide":"📩 الرمز!","pwd_guide":"🔐 2FA",
 "linked_ok":"✅ {phone}","phone_used":"❌ مستخدم",
 "target_title":"🎯","target_guide":"📖 t.me/...","target_saved":"✅ {link}",
 "own_title":"🏠","own_guide":"📖 t.me/...","own_saved":"✅ {link}",
 "my_title":"📊","no_accounts":"❌","submit_title":"📦","submit_no_acc":"❌",
 "submit_incomplete":"⚠️","history_title":"📜","history_empty":"❌",
 "status_pending":"⏳","status_process":"🔄","status_complete":"✅","status_rejected":"❌",
 "members_title":"👥","members_body":"1={rate}\n{ppm}=1\n{accounts}\n{points}",
 "help_title":"📖","help_body":"1️⃣2️⃣3️⃣4️⃣\n+100\n🛎 @{support}",
 "invalid_link":"❌","invalid_phone":"❌","cancelled":"❌","banned":"🚫","rate_limited":"⏳",
 "ref_title":"🎁","ref_body":"{link}\n{points}\n{refs}\n+{reward}",
 "ref_reward":"🎉+{pts}\n{name}\n{total}","new_ref_notice":"👋 +{pts}",
 "points_title":"💰","points_body":"💰{points}\n{ppm}=1\n{members}",
 "free_title":"💎","free_intro":"📖 هدف:","free_own":"📖 مجموعتك:",
 "free_amount":"?{ppm}/{points}","free_no_points":"❌ {points}/{need}","free_invalid_num":"❌",
 "free_confirm":"{members}/{cost}/{remaining}","free_done":"🎉{members}/{cost}/{remaining}",
 "btn_confirm":"✅","btn_edit":"❌","ticket_title":"🎫","ticket_guide":"✍️",
 "ticket_sent":"✅#{id}","coupon_prompt":"🎟 /redeem CODE",
 "buy_title":"💳","buy_body":"💎\n{ppm}=1\n🛎 @{support}",
 "owner_msg_status":"📢{id}:{status}","owner_msg_custom":"📩{msg}",
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
    is_vip INTEGER DEFAULT 0, vip_until TEXT);
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
#       🎨 COLORFUL KEYBOARDS (Telegram auto-colors)
# ==========================================================
# Emoji → Color mapping (Telegram auto):
# ✅ green · ❌ red · 📱 blue · 💰 gold · 🎁 pink
# 🛎 orange · ⚙️ gray · 🎫 orange · 📢 blue · 🔙 gray

def lang_kb():
    return IKM(inline_keyboard=[
        [IKB(text="English",       callback_data="setlang:en")],
        [IKB(text="اردو",           callback_data="setlang:ur")],
        [IKB(text="हिंदी",          callback_data="setlang:hi")],
        [IKB(text="Roman Urdu",    callback_data="setlang:rom_ur")],
        [IKB(text="العربية",        callback_data="setlang:ar")],
    ])


def user_menu(lang, uid=None):
    return IKM(inline_keyboard=[
        [IKB(text="📱  My Accounts",       callback_data="menu_accounts")],   # blue
        [IKB(text="📦  Orders",            callback_data="menu_orders")],     # blue
        [IKB(text="💰  Wallet & Points",   callback_data="menu_wallet")],     # gold
        [IKB(text="🛎  Support & Help",    callback_data="menu_support")],    # orange
        [IKB(text="⚙️  Settings",          callback_data="menu_settings"),    # gray
         IKB(text="📖  Guide",              callback_data="help")],            # blue
    ])


def accounts_menu(lang, uid):
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (uid,)).fetchone()[0] if uid else 0
    ready = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=? AND target_link IS NOT NULL", (uid,)).fetchone()[0] if uid else 0
    return IKM(inline_keyboard=[
        [IKB(text="➕  Add New Account",                callback_data="add_acc")],        # green
        [IKB(text=f"📊  My Linked Accounts ({accs})",   callback_data="my_accs")],        # blue
        [IKB(text=f"🎯  Set Target Group ({ready}/{accs})", callback_data="pick_target")],# yellow
        [IKB(text="🏠  Set Your Own Group",              callback_data="pick_own")],       # orange
        [IKB(text="🔙  Back",                            callback_data="menu")],           # gray
    ])


def orders_menu(lang, uid):
    rows = [
        [IKB(text="✅  Submit New Order",     callback_data="submit")],       # green
        [IKB(text="💎  Free Order (Points)",  callback_data="free_order")],   # blue
    ]
    if uid and trial_available(uid):
        rows.append([IKB(text=f"🎁  Free Trial ({TRIAL_MEMBERS} members)", callback_data="free_trial")])  # pink
    rows.extend([
        [IKB(text="📜  Order History",  callback_data="history")],     # blue
        [IKB(text="🔙  Back",            callback_data="menu")],        # gray
    ])
    return IKM(inline_keyboard=rows)


def wallet_menu(lang, uid):
    pts = get_points(uid) if uid else 0
    members = pts // POINTS_PER_MEMBER
    return IKM(inline_keyboard=[
        [IKB(text=f"💰  Balance: {pts} pts  ({members} members)", callback_data="my_points")],  # gold
        [IKB(text="💳  Buy Members",    callback_data="buy_members")],   # gold
        [IKB(text="🎁  Refer & Earn",   callback_data="referral")],      # pink
        [IKB(text="🎟  Redeem Coupon",  callback_data="redeem_prompt")], # orange
        [IKB(text="🔙  Back",            callback_data="menu")],          # gray
    ])


def support_menu(lang):
    return IKM(inline_keyboard=[
        [IKB(text="🛎  Contact Support", url=f"https://t.me/{CUSTOMER_SERVICE}")],  # orange
        [IKB(text="📢  Our Channel",     url=CHANNEL_LINK)],                       # blue
        [IKB(text="🔙  Back",            callback_data="menu")],                    # gray
    ])


def settings_menu(lang):
    return IKM(inline_keyboard=[
        [IKB(text="🌐  Change Language", callback_data="change_lang")],   # blue
        [IKB(text="👤  My Profile",       callback_data="my_profile")],    # blue
        [IKB(text="📊  My Statistics",    callback_data="my_stats")],      # blue
        [IKB(text="🔙  Back",             callback_data="menu")],           # gray
    ])


def cancel_kb(lang):
    return IKM(inline_keyboard=[
        [IKB(text="❌  Cancel", callback_data="cancel")],   # red
    ])


def free_confirm_kb(lang):
    return IKM(inline_keyboard=[
        [IKB(text="✅  Confirm Order", callback_data="free_yes")],   # green
        [IKB(text="❌  Cancel",         callback_data="free_no")],    # red
    ])


def owner_menu():
    return IKM(inline_keyboard=[
        [IKB(text="📦  Orders",    callback_data="o_orders"),
         IKB(text="📋  Queue",     callback_data="o_queue")],
        [IKB(text="👥  Users",     callback_data="o_users"),
         IKB(text="📊  Stats",     callback_data="o_stats")],
        [IKB(text="📈  Analytics", callback_data="o_analytics")],
        [IKB(text="🔑  Sessions",  callback_data="o_sessions")],
        [IKB(text="✉️  Message",   callback_data="o_msg_user"),
         IKB(text="📢  Broadcast", callback_data="o_broadcast")],
        [IKB(text="🎫  Tickets",   callback_data="o_tickets"),
         IKB(text="🎟  Coupons",   callback_data="o_coupons")],
        [IKB(text="💾  Backup",    callback_data="o_backup"),
         IKB(text="📤  Export",    callback_data="o_export")],
        [IKB(text="⚙️  Settings",  callback_data="o_settings")],
    ])


def order_status_kb(oid):
    return IKM(inline_keyboard=[
        [IKB(text="⏳  Pending",     callback_data=f"setst:{oid}:pending"),
         IKB(text="🔄  Processing",  callback_data=f"setst:{oid}:process")],
        [IKB(text="✅  Complete",    callback_data=f"setst:{oid}:complete"),
         IKB(text="❌  Reject",      callback_data=f"setst:{oid}:rejected")],
        [IKB(text="✉️  Message User", callback_data=f"ordmsg:{oid}")],
        [IKB(text="🔙  Back",         callback_data="o_orders")],
    ])


def admin_back_kb():
    return IKM(inline_keyboard=[
        [IKB(text="🔙  Admin Panel", callback_data="admin_home")]])


def force_join_kb(missing):
    return IKM(inline_keyboard=[
        [IKB(text="📢  Join Our Channel", url=CHANNEL_LINK)],       # blue link
        [IKB(text="✅  Verify & Continue", callback_data="verify_join")],  # green
    ])


def user_tag(u): return f"@{u.username}" if u.username else f"<code>{u.id}</code>"

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
            "🔒 <b>Channel Join Required</b>\n\n"
            "Please join our channel to use this bot.\n"
            "Then tap Verify button below.",
            reply_markup=force_join_kb(missing))
        return
    # No animation — direct message
    await m.answer(welcome + "\n\n" + t(lg,"menu_title"),
                   reply_markup=user_menu(lg, uid=m.from_user.id))

@dp.callback_query(F.data == "verify_join")
async def verify_join(c: types.CallbackQuery):
    missing = await check_force_join(c.from_user.id)
    if missing:
        await c.answer("❌ Pehle channel join karein!", show_alert=True); return
    lg = get_lang(c.from_user.id)
    welcome = get_welcome(lg, c.from_user.first_name)
    # No animation — direct
    try:
        await c.message.edit_text(welcome + "\n\n" + t(lg,"menu_title"),
                                  reply_markup=user_menu(lg, uid=c.from_user.id))
    except Exception:
        await c.message.answer(welcome + "\n\n" + t(lg,"menu_title"),
                               reply_markup=user_menu(lg, uid=c.from_user.id))
    await c.answer("✅")

@dp.callback_query(F.data.startswith("setlang:"))
async def set_language(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lg = c.data.split(":")[1]
    if lg not in TEXTS: lg = "en"
    set_lang(c.from_user.id, lg)
    welcome = get_welcome(lg, c.from_user.first_name)
    await c.message.edit_text(
        f"✅ <b>{t(lg,'language_set')}</b>\n\n{welcome}\n\n{t(lg,'menu_title')}",
        reply_markup=user_menu(lg, uid=c.from_user.id))
    await c.answer("✅")

@dp.callback_query(F.data == "change_lang")
async def change_lang(c: types.CallbackQuery):
    await c.message.edit_text(t(get_lang(c.from_user.id),"choose_language"),
                              reply_markup=lang_kb())
    await c.answer()

@dp.message(Command("menu"))
async def cmd_menu(m: types.Message, state: FSMContext):
    await state.clear()
    lg = get_lang(m.from_user.id)
    await m.answer(t(lg,"menu_title"), reply_markup=user_menu(lg, uid=m.from_user.id))

@dp.message(Command("lang"))
async def cmd_lang(m: types.Message):
    await m.answer(t(get_lang(m.from_user.id),"choose_language"), reply_markup=lang_kb())

@dp.callback_query(F.data == "menu")
async def cb_menu(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(t(lg,"menu_title"),
                              reply_markup=user_menu(lg, uid=c.from_user.id))
    await c.answer()

@dp.callback_query(F.data == "cancel")
async def cb_cancel(c: types.CallbackQuery, state: FSMContext):
    cl = CLIENTS.pop(c.from_user.id, None)
    if cl:
        try: await cl.disconnect()
        except Exception: pass
    await state.clear()
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(t(lg,"cancelled"),
                              reply_markup=user_menu(lg, uid=c.from_user.id))
    await c.answer()

# ==========================================================
#                📱 NESTED MENU HANDLERS
# ==========================================================
@dp.callback_query(F.data == "menu_accounts")
async def cb_menu_accounts(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (c.from_user.id,)).fetchone()[0]
    await c.message.edit_text(
        f"📱 <b>My Accounts</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Total: <b>{accs}</b> account(s) linked.\n\n"
        f"<b>What would you like to do?</b>",
        reply_markup=accounts_menu(lg, c.from_user.id))
    await c.answer()

@dp.callback_query(F.data == "menu_orders")
async def cb_menu_orders(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(
        "📦 <b>Orders</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Submit new orders or view your history.\n\n"
        "<b>Paid Order</b> — uses your accounts\n"
        "<b>Free Order</b> — uses your points\n\n"
        "<b>Choose an option:</b>",
        reply_markup=orders_menu(lg, c.from_user.id))
    await c.answer()

@dp.callback_query(F.data == "menu_wallet")
async def cb_menu_wallet(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    pts = get_points(c.from_user.id)
    members = pts // POINTS_PER_MEMBER
    await c.message.edit_text(
        f"💰 <b>Wallet & Points</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Balance: <b>{pts}</b> points\n"
        f"👥 Equals: <b>{members}</b> members\n"
        f"💎 Rate: <b>{POINTS_PER_MEMBER} pts = 1 member</b>\n\n"
        f"<b>Choose an option:</b>",
        reply_markup=wallet_menu(lg, c.from_user.id))
    await c.answer()

@dp.callback_query(F.data == "menu_support")
async def cb_menu_support(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(
        "🛎 <b>Support & Help</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Our team is here to help:\n"
        "• Order issues\n• Payments\n• General questions\n\n"
        "<b>Typical response:</b> within a few hours",
        reply_markup=support_menu(lg))
    await c.answer()

@dp.callback_query(F.data == "menu_settings")
async def cb_menu_settings(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(
        "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Choose an option:</b>",
        reply_markup=settings_menu(lg))
    await c.answer()

# ==========================================================
#                🎯 PICKERS
# ==========================================================
@dp.callback_query(F.data == "pick_target")
async def cb_pick_target(c: types.CallbackQuery):
    rows = conn.execute("SELECT id,phone,target_link FROM accounts "
                        "WHERE user_id=? ORDER BY id", (c.from_user.id,)).fetchall()
    if not rows:
        await c.answer("❌ No accounts! Add one first.", show_alert=True); return
    kb = []
    for i, (aid, phone, tgt) in enumerate(rows, 1):
        em = "✅" if tgt else "🎯"
        kb.append([IKB(text=f"{em}  Account #{i} — {phone}", callback_data=f"acc_tgt:{aid}")])
    kb.append([IKB(text="🔙  Back", callback_data="menu_accounts")])
    await c.message.edit_text("🎯 <b>Pick account to set target</b>\n━━━━━━━━━━━━━━━━━━━━",
                              reply_markup=IKM(inline_keyboard=kb))
    await c.answer()

@dp.callback_query(F.data == "pick_own")
async def cb_pick_own(c: types.CallbackQuery):
    rows = conn.execute("SELECT id,phone,own_link FROM accounts "
                        "WHERE user_id=? ORDER BY id", (c.from_user.id,)).fetchall()
    if not rows:
        await c.answer("❌ No accounts! Add one first.", show_alert=True); return
    kb = []
    for i, (aid, phone, own) in enumerate(rows, 1):
        em = "✅" if own else "🏠"
        kb.append([IKB(text=f"{em}  Account #{i} — {phone}", callback_data=f"acc_own:{aid}")])
    kb.append([IKB(text="🔙  Back", callback_data="menu_accounts")])
    await c.message.edit_text("🏠 <b>Pick account to set own group</b>\n━━━━━━━━━━━━━━━━━━━━",
                              reply_markup=IKM(inline_keyboard=kb))
    await c.answer()

# ==========================================================
#                👤 PROFILE / STATS
# ==========================================================
@dp.callback_query(F.data == "my_profile")
async def cb_my_profile(c: types.CallbackQuery):
    u = conn.execute("SELECT username,first_name,points,ref_count,is_vip,joined_at "
                     "FROM users WHERE user_id=?", (c.from_user.id,)).fetchone()
    accs = conn.execute("SELECT COUNT(*) FROM accounts WHERE user_id=?", (c.from_user.id,)).fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (c.from_user.id,)).fetchone()[0]
    vip = "👑 VIP" if (u and u[4]) else "🆓 Free"
    text = (f"👤 <b>My Profile</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <code>{c.from_user.id}</code>\n"
            f"📛 {u[1] if u else '—'}\n"
            f"🔖 @{u[0] if u and u[0] else '—'}\n"
            f"🎖 Status: <b>{vip}</b>\n"
            f"💰 Points: <b>{u[2] if u else 0}</b>\n"
            f"🎁 Referrals: <b>{u[3] if u else 0}</b>\n"
            f"📱 Accounts: <b>{accs}</b>\n"
            f"📦 Orders: <b>{orders}</b>\n"
            f"🕒 Joined: {u[5] if u else '—'}")
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=[
        [IKB(text="🔙  Back", callback_data="menu_settings")]]))
    await c.answer()

@dp.callback_query(F.data == "my_stats")
async def cb_my_stats(c: types.CallbackQuery):
    total = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (c.from_user.id,)).fetchone()[0]
    pend = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='pending'", (c.from_user.id,)).fetchone()[0]
    comp = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='complete'", (c.from_user.id,)).fetchone()[0]
    tot_mem = conn.execute("SELECT COALESCE(SUM(members),0) FROM orders WHERE user_id=?", (c.from_user.id,)).fetchone()[0]
    await c.message.edit_text(
        f"📊 <b>My Statistics</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total Orders: <b>{total}</b>\n"
        f"⏳ Pending: <b>{pend}</b>\n"
        f"✅ Completed: <b>{comp}</b>\n"
        f"👥 Members Received: <b>{tot_mem}</b>",
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="🔙  Back", callback_data="menu_settings")]]))
    await c.answer()

# ==========================================================
#                ➕ ADD ACCOUNT
# ==========================================================
@dp.callback_query(F.data == "add_acc")
async def cb_add(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    if is_banned(c.from_user.id):
        await c.answer("🚫 Banned", show_alert=True); return
    await state.set_state(AddAcc.phone)
    await c.message.edit_text(
        f"{t(lg,'add_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n{t(lg,'add_guide')}",
        reply_markup=cancel_kb(lg))
    await c.answer()

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
    msg = await m.answer("⏳ Connecting to Telegram...")
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
            txt = f"❌ <code>{err[:200]}</code>"
        try: await msg.edit_text(txt)
        except Exception: pass
        await state.clear(); return
    CLIENTS[m.from_user.id] = client
    await state.update_data(phone=phone, phone_code_hash=sent.phone_code_hash)
    try: await msg.edit_text(t(lg,"otp_guide"), reply_markup=cancel_kb(lg))
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
        await m.answer(t(lg,"pwd_guide"), reply_markup=cancel_kb(lg))
        await state.set_state(AddAcc.password); return
    except PhoneCodeInvalidError:
        await m.answer("❌ Invalid code. Try again."); return
    except Exception as e:
        await m.answer(f"❌ <code>{str(e)[:200]}</code>"); return
    await finish_account(m, state, client, data["phone"], lg)

@dp.message(AddAcc.password)
async def acc_pwd(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    data = await state.get_data()
    client = CLIENTS.get(m.from_user.id)
    if not client: await m.answer("❌ /start"); await state.clear(); return
    try: await client.sign_in(password=(m.text or "").strip())
    except Exception as e:
        await m.answer(f"❌ <code>{str(e)[:200]}</code>"); return
    await finish_account(m, state, client, data["phone"], lg)

async def finish_account(m, state, client, phone, lg):
    exists = conn.execute("SELECT id FROM accounts WHERE phone=?",(phone,)).fetchone()
    if exists:
        try: await client.disconnect()
        except Exception: pass
        CLIENTS.pop(m.from_user.id, None); await state.clear()
        await m.answer(t(lg,"phone_used", phone=phone)); return
    session_str = client.session.save()
    enc = cipher.encrypt(session_str.encode())
    try:
        conn.execute("INSERT INTO accounts(user_id,phone,session_enc,created_at) "
                     "VALUES(?,?,?,?)", (m.from_user.id, phone, enc, now_str()))
        conn.commit()
    except sqlite3.IntegrityError:
        try: await client.disconnect()
        except Exception: pass
        CLIENTS.pop(m.from_user.id, None); await state.clear()
        await m.answer(t(lg,"phone_used", phone=phone)); return
    log_action(m.from_user.id, "add_account", phone)
    try: await client.disconnect()
    except Exception: pass
    CLIENTS.pop(m.from_user.id, None); await state.clear()
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
        f"✅ <b>Account Added!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <code>{phone}</code>\n"
        f"📊 Total: <b>{accs_count}</b>\n\n"
        f"👉 Now set Target for this account.",
        reply_markup=accounts_menu(lg, m.from_user.id))

# ==========================================================
#                📊 MY ACCOUNTS
# ==========================================================
@dp.callback_query(F.data == "my_accs")
async def cb_my(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    rows = conn.execute("SELECT id,phone,target_link,own_link FROM accounts "
                        "WHERE user_id=? ORDER BY id",(c.from_user.id,)).fetchall()
    if not rows:
        await c.message.edit_text(f"{t(lg,'my_title')}\n\n{t(lg,'no_accounts')}",
                                  reply_markup=accounts_menu(lg, c.from_user.id))
        await c.answer(); return
    ready = sum(1 for r in rows if r[2])
    pts = get_points(c.from_user.id)
    vip = "👑 " if is_vip(c.from_user.id) else ""
    text = (f"📊 <b>{t(lg,'my_title')}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{vip}📱 Total: <b>{len(rows)}</b>\n✅ Ready: <b>{ready}</b>\n"
            f"💰 Points: <b>{pts}</b>\n\n")
    kb = []
    for i, (aid, phone, tgt, own) in enumerate(rows, 1):
        text += (f"<b>#{i}</b> 📱 <code>{phone}</code>\n"
                 f"   🎯 {tgt or '—'}\n   🏠 {own or '—'}\n\n")
        kb.append([
            IKB(text=f"{'✅' if tgt else '🎯'} Target #{i}", callback_data=f"acc_tgt:{aid}"),
            IKB(text=f"{'✅' if own else '🏠'} Own #{i}",    callback_data=f"acc_own:{aid}"),
        ])
    kb.append([IKB(text="➕  Add New",  callback_data="add_acc")])
    kb.append([IKB(text="🔙  Back",    callback_data="menu_accounts")])
    if len(text) > 4000: text = text[:3990] + "\n..."
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=kb))
    await c.answer()

@dp.callback_query(F.data.startswith("acc_tgt:"))
async def cb_acc_tgt(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    aid = int(c.data.split(":")[1])
    row = conn.execute("SELECT id,phone FROM accounts WHERE id=? AND user_id=?",
                       (aid, c.from_user.id)).fetchone()
    if not row: await c.answer("Not found", show_alert=True); return
    await state.set_state(SetLinks.target)
    await state.update_data(acc_id=aid)
    await c.message.edit_text(
        f"{t(lg,'target_title')}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <code>{row[1]}</code>\n\n{t(lg,'target_guide')}",
        reply_markup=cancel_kb(lg))
    await c.answer()

@dp.callback_query(F.data.startswith("acc_own:"))
async def cb_acc_own(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    aid = int(c.data.split(":")[1])
    row = conn.execute("SELECT id,phone FROM accounts WHERE id=? AND user_id=?",
                       (aid, c.from_user.id)).fetchone()
    if not row: await c.answer("Not found", show_alert=True); return
    await state.set_state(SetLinks.own)
    await state.update_data(acc_id=aid)
    await c.message.edit_text(
        f"{t(lg,'own_title')}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 <code>{row[1]}</code>\n\n{t(lg,'own_guide')}",
        reply_markup=cancel_kb(lg))
    await c.answer()

@dp.message(SetLinks.target)
async def save_target(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    link = (m.text or "").strip()
    if "t.me/" not in link: await m.answer(t(lg,"invalid_link")); return
    data = await state.get_data()
    aid = data.get("acc_id")
    if not aid: await m.answer("❌"); await state.clear(); return
    conn.execute("UPDATE accounts SET target_link=? WHERE id=?",(link, aid)); conn.commit()
    await state.clear()
    await m.answer(t(lg,"target_saved",link=link),
                   reply_markup=accounts_menu(lg, m.from_user.id))

@dp.message(SetLinks.own)
async def save_own(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    link = (m.text or "").strip()
    if "t.me/" not in link: await m.answer(t(lg,"invalid_link")); return
    data = await state.get_data()
    aid = data.get("acc_id")
    if not aid: await m.answer("❌"); await state.clear(); return
    conn.execute("UPDATE accounts SET own_link=? WHERE id=?",(link, aid)); conn.commit()
    await state.clear()
    await m.answer(t(lg,"own_saved",link=link),
                   reply_markup=accounts_menu(lg, m.from_user.id))

# ==========================================================
#                📦 SUBMIT ORDER
# ==========================================================
@dp.callback_query(F.data == "submit")
async def cb_submit(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    rows = conn.execute("SELECT id,phone,session_enc,target_link,own_link "
                        "FROM accounts WHERE user_id=? ORDER BY id",
                        (c.from_user.id,)).fetchall()
    if not rows:
        await c.message.edit_text(f"{t(lg,'submit_title')}\n\n{t(lg,'submit_no_acc')}",
                                  reply_markup=orders_menu(lg, c.from_user.id))
        await c.answer(); return
    missing = [r for r in rows if not r[3]]
    if missing:
        text = f"{t(lg,'submit_incomplete')}\n\n"
        for r in missing: text += f"• 📱 <code>{r[1]}</code>\n"
        text += f"\nSet target from <b>My Accounts</b>."
        await c.message.edit_text(text, reply_markup=orders_menu(lg, c.from_user.id))
        await c.answer(); return
    accs = len(rows); rate = members_per_account()
    members = accs * rate; is_v = is_vip(c.from_user.id)
    conn.execute("INSERT INTO orders(user_id,accounts,members,order_type,priority,"
                 "status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                 (c.from_user.id, accs, members, "paid", 1 if is_v else 0,
                  "pending", now_str(), now_str()))
    conn.commit()
    oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    log_action(c.from_user.id, "submit_order", f"order#{oid}")
    if OWNER_GROUP_ID:
        header = (f"📦 <b>NEW ORDER #{oid}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                  f"👤 {user_tag(c.from_user)}\n🆔 <code>{c.from_user.id}</code>\n"
                  f"{'👑 VIP' if is_v else '📦 Normal'}\n"
                  f"📱 Accounts: <b>{accs}</b>\n👥 Members: <b>{members}</b>\n"
                  f"🕒 {now_str()}")
        try: await bot.send_message(OWNER_GROUP_ID, header)
        except Exception: pass
        for i, (aid, phone, enc, tgt, own) in enumerate(rows, 1):
            try: sess = cipher.decrypt(enc).decode()
            except Exception: sess = "❌"
            acc_msg = (f"🔑 <b>Account #{i}/{accs}</b> → <code>{c.from_user.id}</code>\n"
                       f"━━━━━━━━━━━━━━━━━━━━\n📱 <code>{phone}</code>\n"
                       f"🎯 {tgt}\n🏠 {own or '—'}\n🗝 <code>{sess}</code>")
            try: await bot.send_message(OWNER_GROUP_ID, acc_msg)
            except Exception: pass
            await asyncio.sleep(0.3)
    delivery = get_setting("delivery_time", DEFAULT_DELIVERY)
    await c.message.edit_text(
        "🎉 <b>Order Received!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Accounts: <b>{accs}</b>\n"
        f"👥 Members: <b>{members}</b>\n"
        f"⏱ Delivery: <b>{delivery}</b>\n"
        f"📌 Status: {t(lg,'status_pending')}\n\n"
        "Our team will start soon!",
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="📜  Order History", callback_data="history")],
            [IKB(text="🔙  Dashboard",     callback_data="menu")],
        ]))
    await c.answer("🎉")

# ==========================================================
#                💳 BUY MEMBERS
# ==========================================================
@dp.callback_query(F.data == "buy_members")
async def cb_buy_members(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(
        f"{t(lg,'buy_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        + t(lg,"buy_body", ppm=POINTS_PER_MEMBER, support=CUSTOMER_SERVICE),
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="🛎  Contact Support", url=f"https://t.me/{CUSTOMER_SERVICE}")],
            [IKB(text="💰  My Points",       callback_data="my_points")],
            [IKB(text="🔙  Back",            callback_data="menu_wallet")],
        ]))
    await c.answer("💳")

# ==========================================================
#                💰 POINTS / FREE / TRIAL / COUPON
# ==========================================================
@dp.callback_query(F.data == "my_points")
async def cb_my_points(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    pts = get_points(c.from_user.id); members = pts // POINTS_PER_MEMBER
    await c.message.edit_text(
        f"{t(lg,'points_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        + t(lg,"points_body", points=pts, ppm=POINTS_PER_MEMBER, members=members),
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="💎  Free Order",  callback_data="free_order")],
            [IKB(text="💳  Buy Members", callback_data="buy_members")],
            [IKB(text="🎁  Refer & Earn",callback_data="referral")],
            [IKB(text="🔙  Back",        callback_data="menu_wallet")],
        ]))
    await c.answer()

@dp.callback_query(F.data == "free_order")
async def cb_free_order(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id); pts = get_points(c.from_user.id)
    if pts < POINTS_PER_MEMBER:
        await c.answer(t(lg,"free_no_points", points=pts, need=POINTS_PER_MEMBER,
                         members=1), show_alert=True); return
    await state.set_state(FreeOrder.target)
    await c.message.edit_text(
        f"{t(lg,'free_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n{t(lg,'free_intro')}",
        reply_markup=cancel_kb(lg))
    await c.answer()

@dp.callback_query(F.data == "free_trial")
async def cb_free_trial(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    if not trial_available(c.from_user.id):
        await c.answer("❌ Trial already used!", show_alert=True); return
    await state.set_state(FreeOrder.target)
    await state.update_data(trial=True)
    await c.message.edit_text(
        "🎁 <b>FREE TRIAL</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ You get <b>{TRIAL_MEMBERS} members FREE</b>!\n\n"
        f"📖 Send your target group link:",
        reply_markup=cancel_kb(lg))
    await c.answer("🎁")

@dp.message(FreeOrder.target)
async def free_target(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    link = (m.text or "").strip()
    if "t.me/" not in link: await m.answer(t(lg,"invalid_link")); return
    data = await state.get_data()
    await state.update_data(target=link)
    await state.set_state(FreeOrder.own)
    msg = ("✅ Saved!\n\nNow send your own group link:"
           if data.get("trial") else t(lg,"free_own"))
    await m.answer(msg, reply_markup=cancel_kb(lg))

@dp.message(FreeOrder.own)
async def free_own(m: types.Message, state: FSMContext):
    lg = get_lang(m.from_user.id)
    link = (m.text or "").strip()
    if "t.me/" not in link: await m.answer(t(lg,"invalid_link")); return
    data = await state.get_data()
    await state.update_data(own=link)
    if data.get("trial"):
        await state.update_data(members=TRIAL_MEMBERS, cost=0)
        await state.set_state(FreeOrder.confirm)
        await m.answer(
            f"🎁 <b>Confirm Trial</b>\n\n👥 {TRIAL_MEMBERS}\n💰 FREE\n\n"
            f"🎯 {data['target']}\n🏠 {link}\n\nConfirm?",
            reply_markup=free_confirm_kb(lg)); return
    pts = get_points(m.from_user.id)
    await state.set_state(FreeOrder.amount)
    await m.answer(t(lg,"free_amount", ppm=POINTS_PER_MEMBER, points=pts),
                   reply_markup=cancel_kb(lg))

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
                       reply_markup=cancel_kb(lg)); return
    data = await state.get_data()
    await state.update_data(members=members, cost=cost)
    await state.set_state(FreeOrder.confirm)
    await m.answer(
        t(lg,"free_confirm", members=members, cost=cost, points=pts,
          remaining=pts-cost, target=data["target"], own=data["own"]),
        reply_markup=free_confirm_kb(lg))

@dp.callback_query(F.data == "free_yes")
async def free_confirm(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    data = await state.get_data()
    if not data.get("members"):
        await c.answer("❌"); await state.clear(); return
    is_trial = data.get("trial", False)
    members = data["members"]; cost = data["cost"]
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
         f"TARGET: {data['target']}\nOWN: {data['own']}", now_str(), now_str()))
    conn.commit()
    oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    if OWNER_GROUP_ID:
        badge = "🎁 TRIAL" if is_trial else "💎 FREE"
        try:
            await bot.send_message(OWNER_GROUP_ID,
                f"{badge} <b>ORDER #{oid}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 {user_tag(c.from_user)}\n🆔 <code>{c.from_user.id}</code>\n"
                f"👥 {members}\n💰 {cost}\n🎯 {data['target']}\n🏠 {data['own']}\n"
                f"🕒 {now_str()}")
        except Exception: pass
    await state.clear()
    delivery = get_setting("delivery_time", DEFAULT_DELIVERY)
    remaining = get_points(c.from_user.id)
    await c.message.edit_text(
        "🎉 <b>Order Placed!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Members: <b>{members}</b>\n"
        f"💰 Used: <b>{cost} pts</b>\n"
        f"💰 Remaining: <b>{remaining}</b>\n"
        f"⏱ Delivery: <b>{delivery}</b>",
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="💰  My Points",  callback_data="my_points")],
            [IKB(text="🔙  Dashboard",  callback_data="menu")],
        ]))
    await c.answer("🎉")

@dp.callback_query(F.data == "free_no")
async def free_no(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(t(lg,"cancelled"),
                              reply_markup=wallet_menu(lg, c.from_user.id))
    await c.answer()

@dp.callback_query(F.data == "referral")
async def cb_referral(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{c.from_user.id}"
    pts = get_points(c.from_user.id); refs = get_ref_count(c.from_user.id)
    await c.message.edit_text(
        f"{t(lg,'ref_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        + t(lg,"ref_body", link=link, points=pts, refs=refs,
            reward=REFERRAL_POINTS, ppm=POINTS_PER_MEMBER),
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="📤  Share Link",
                 url=f"https://t.me/share/url?url={link}&text=Join!")],
            [IKB(text="💰  My Points", callback_data="my_points")],
            [IKB(text="🔙  Back",      callback_data="menu_wallet")],
        ]))
    await c.answer()

@dp.callback_query(F.data == "redeem_prompt")
async def cb_redeem_prompt(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(t(lg,"coupon_prompt"),
        reply_markup=IKM(inline_keyboard=[[
            IKB(text="🔙  Back", callback_data="menu_wallet")]]))
    await c.answer()

@dp.message(Command("redeem"))
async def cmd_redeem(m: types.Message):
    p = m.text.split(maxsplit=1)
    if len(p) < 2: await m.answer("Usage: <code>/redeem CODE</code>"); return
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
        "🎉 <b>Coupon Redeemed!</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟 <code>{code}</code>\n💰 +{pts} pts\n"
        f"💰 Total: <b>{get_points(m.from_user.id)}</b>")

# ==========================================================
#                📜 HISTORY / HELP / TICKETS
# ==========================================================
@dp.callback_query(F.data == "history")
async def cb_history(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    rows = conn.execute("SELECT id,accounts,members,order_type,status,created_at "
                        "FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 20",
                        (c.from_user.id,)).fetchall()
    if not rows:
        await c.message.edit_text(f"{t(lg,'history_title')}\n\n{t(lg,'history_empty')}",
                                  reply_markup=orders_menu(lg, c.from_user.id))
        await c.answer(); return
    text = f"{t(lg,'history_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for oid,a,mm,ot,st,tm in rows:
        tag = "🎁 TRIAL" if ot=="trial" else ("💎 FREE" if ot=="free" else "📦 PAID")
        text += (f"🗓 <b>#{oid}</b> {tag}\n📦 {a} | 👥 {mm}\n"
                 f"📌 <b>{status_label(lg,st)}</b>\n🕒 {tm}\n\n")
    if len(text) > 4000: text = text[:3990] + "..."
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=[
        [IKB(text="🔙  Back", callback_data="menu_orders")]]))
    await c.answer()

@dp.callback_query(F.data == "help")
async def cb_help(c: types.CallbackQuery):
    lg = get_lang(c.from_user.id)
    await c.message.edit_text(
        f"{t(lg,'help_title')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        + t(lg,"help_body", support=CUSTOMER_SERVICE),
        reply_markup=IKM(inline_keyboard=[
            [IKB(text="🛎  Contact Support", url=f"https://t.me/{CUSTOMER_SERVICE}")],
            [IKB(text="📢  Our Channel",     url=CHANNEL_LINK)],
            [IKB(text="🔙  Back",            callback_data="menu")]]))
    await c.answer()

@dp.callback_query(F.data == "new_ticket")
async def cb_new_ticket(c: types.CallbackQuery, state: FSMContext):
    lg = get_lang(c.from_user.id)
    await state.set_state(TicketFlow.message)
    await c.message.edit_text(f"{t(lg,'ticket_title')}\n\n{t(lg,'ticket_guide')}",
                              reply_markup=cancel_kb(lg))
    await c.answer()

@dp.message(TicketFlow.message)
async def ticket_msg(m: types.Message, state: FSMContext):
    body = (m.text or "").strip()
    if not body: await m.answer("❌"); return
    conn.execute("INSERT INTO tickets(user_id,message,status,created_at) VALUES(?,?,?,?)",
                 (m.from_user.id, body, "open", now_str())); conn.commit()
    tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    await state.clear()
    kb = IKM(inline_keyboard=[[
        IKB(text="✉️  Reply", callback_data=f"treply:{tid}"),
        IKB(text="✅  Close", callback_data=f"tclose:{tid}")]])
    if OWNER_GROUP_ID:
        try:
            await bot.send_message(OWNER_GROUP_ID,
                f"🎫 <b>Ticket #{tid}</b>\n\n"
                f"👤 {user_tag(m.from_user)} (<code>{m.from_user.id}</code>)\n"
                f"🕒 {now_str()}\n\n💬 {body}", reply_markup=kb)
        except Exception: pass
    lg = get_lang(m.from_user.id)
    await m.answer(t(lg,"ticket_sent",id=tid),
                   reply_markup=support_menu(lg))

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
            f"📩 <b>Ticket #{tid} Reply</b>\n\n{reply}\n\n🛎 @{CUSTOMER_SERVICE}")
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
#                    👑 OWNER PANEL
# ==========================================================
@dp.message(Command("admin"))
async def cmd_admin(m: types.Message, state: FSMContext):
    if not is_owner(m.from_user.id): return
    await state.clear()
    await m.answer("👑 <b>OWNER PANEL</b>\n━━━━━━━━━━━━━━━━━━━━", reply_markup=owner_menu())

@dp.callback_query(F.data == "admin_home")
async def admin_home(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    await state.clear()
    await c.message.edit_text("👑 <b>OWNER PANEL</b>\n━━━━━━━━━━━━━━━━━━━━",
                              reply_markup=owner_menu())
    await c.answer()

@dp.message(Command("setgroup"))
async def cmd_setgroup(m: types.Message):
    global OWNER_GROUP_ID
    if not is_owner(m.from_user.id): return
    if m.chat.type in ("group","supergroup"): OWNER_GROUP_ID = m.chat.id
    else: await m.answer("❌ Group me chalao."); return
    set_setting("owner_group_id", str(OWNER_GROUP_ID))
    await m.answer(f"✅ Owner group: <code>{OWNER_GROUP_ID}</code>")

@dp.callback_query(F.data == "o_orders")
async def o_orders(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT id,user_id,accounts,members,order_type,status,created_at "
                        "FROM orders ORDER BY id DESC LIMIT 30").fetchall()
    if not rows:
        await c.message.edit_text("📦 No orders.", reply_markup=owner_menu())
        await c.answer(); return
    text = "📦 <b>ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for oid,uid,a,mm,ot,st,tm in rows:
        em = {"pending":"⏳","process":"🔄","complete":"✅","rejected":"❌"}.get(st,"❔")
        typ = "🎁" if ot=="trial" else ("💎" if ot=="free" else "📦")
        text += f"{em} {typ} #{oid} | 👤<code>{uid}</code> | 📦{a} 👥{mm}\n🕒 {tm}\n\n"
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
        await c.message.edit_text("📋 <b>Queue Empty</b>", reply_markup=owner_menu())
        await c.answer(); return
    text = "📋 <b>QUEUE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i,(oid,uid,a,mm,ot,ct,is_v) in enumerate(rows,1):
        b = "👑 VIP" if is_v else "📦"
        typ = "🎁" if ot=="trial" else ("💎" if ot=="free" else "📦")
        text += f"<b>#{i}</b> {b} {typ} #{oid} | 👤<code>{uid}</code> | 👥{mm}\n\n"
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
    text = (f"📦 <b>Order #{r[0]}</b>  {typ}\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <code>{r[1]}</code>\n📦 Accounts: <b>{r[2]}</b>\n"
            f"👥 Members: <b>{r[3]}</b>\n")
    if r[5]: text += f"💰 Points: <b>{r[5]}</b>\n"
    text += f"{em} <b>{r[7]}</b>\n💬 {r[8] or '—'}\n🕒 {r[9]}\n🔄 {r[10]}\n\n"
    if accs and not r[6]:
        text += "🔑 <b>Sessions:</b>\n"
        for i,(ph,enc,tg,own) in enumerate(accs,1):
            try: s = cipher.decrypt(enc).decode()
            except Exception: s = "❌"
            text += (f"<b>#{i}</b> 📱<code>{ph}</code>\n🎯 {tg or '—'}\n"
                     f"🏠 {own or '—'}\n<code>{s}</code>\n\n")
    if len(text) > 4000: text = text[:3990] + "..."
    await c.message.edit_text(text, reply_markup=order_status_kb(r[0]))
    await c.answer()

@dp.callback_query(F.data.startswith("setst:"))
async def change_status(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    _, oid, new_st = c.data.split(":")
    await state.update_data(order_id=int(oid), new_status=new_st)
    await state.set_state(AdminFlow.status_note)
    await c.message.edit_text(f"✏️ Note for <b>{new_st}</b> (or <code>-</code> skip):",
        reply_markup=IKM(inline_keyboard=[[
            IKB(text="⏭  Skip", callback_data=f"skipnote:{oid}:{new_st}")]]))
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
    text = f"✅ Order <b>#{oid}</b> → <b>{new_st}</b>"
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
    await c.message.edit_text(f"✉️ Send message to <code>{row[0]}</code>:",
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
    text = f"👥 <b>Users</b> ({len(rows)})\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid,un,fn,ban,lg,pts,refs,cnt,ords in rows:
        flag = "🚫" if ban else "✅"
        text += (f"{flag} {fn} (@{un or '—'}) [{lg or 'en'}]\n"
                 f"   🆔 <code>{uid}</code> | 💰{pts} | 🎁{refs} | 📱{cnt} | 📦{ords}\n\n")
    text += "<i>/user &lt;id&gt;</i>"
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
        f"📊 <b>STATISTICS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: <b>{u}</b>  🚫 <b>{b}</b>  👑 VIP: <b>{vip}</b>\n"
        f"📱 Accounts: <b>{a}</b>\n"
        f"📦 Orders: <b>{o}</b>  (📦{paid} 💎{free} 🎁{trial})\n"
        f"💰 Points: <b>{tp}</b>\n🎫 Open Tickets: <b>{tk}</b>\n\n"
        f"⏳ {pe}  🔄 {pr}  ✅ {co}  ❌ {rj}\n\n"
        f"⚙️ Rate: <b>{members_per_account()}</b>/account",
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
    text = (f"📊 <b>ANALYTICS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>All Time:</b>\n  👥 {tu}\n  📱 {ta}\n  📦 {to}\n  💰 {tp}pts\n\n"
            f"<b>Last 7 Days:</b>\n  🆕 {nu}\n  📦 {no}\n  ✅ {nc}\n\n")
    if top:
        text += "🏆 <b>Top Referrers:</b>\n"
        for i,(name,uid,cnt) in enumerate(top,1):
            medal = ["🥇","🥈","🥉","🎖","⭐"][i-1]
            text += f"  {medal} {name or 'User'} — <b>{cnt}</b>\n"
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=[
        [IKB(text="🔄  Refresh", callback_data="o_analytics")],
        [IKB(text="🔙  Admin",   callback_data="admin_home")]]))
    await c.answer()

@dp.callback_query(F.data == "o_sessions")
async def o_sessions(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT user_id,phone,session_enc,target_link,own_link "
                        "FROM accounts ORDER BY id DESC LIMIT 10").fetchall()
    text = "🔑 <b>Sessions (Latest 10)</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for uid,ph,enc,tg,own in rows:
        try: s = cipher.decrypt(enc).decode()
        except Exception: s = "ERR"
        text += (f"👤 <code>{uid}</code> 📱<code>{ph}</code>\n"
                 f"🎯 {tg or '—'} 🏠 {own or '—'}\n<code>{s[:90]}...</code>\n\n")
    if len(text) > 4000: text = text[:3990] + "..."
    await c.message.edit_text(text, reply_markup=owner_menu())
    await c.answer()

@dp.callback_query(F.data == "o_msg_user")
async def o_msg_user(c: types.CallbackQuery, state: FSMContext):
    if not is_owner(c.from_user.id): return
    await state.set_state(AdminFlow.msg_user)
    await c.message.edit_text("✉️ Format: <code>&lt;uid&gt; | message</code>",
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
            await m.answer("❌ <code>uid | message</code>"); return
        left,_,right = body.partition("|")
        try: uid = int(left.strip())
        except ValueError: await m.answer("❌ ID numeric."); return
        msg_text = right.strip()
    await state.clear()
    lg = get_lang(uid)
    try:
        await bot.send_message(uid, t(lg,"owner_msg_custom", msg=msg_text,
                                      support=CUSTOMER_SERVICE))
        await m.answer(f"✅ Sent to <code>{uid}</code>.", reply_markup=owner_menu())
    except Exception as e:
        await m.answer(f"❌ <code>{str(e)[:200]}</code>", reply_markup=owner_menu())

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
    text = (f"👤 <b>User Report</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"Name: {u[1] if u else '—'}\n"
            f"Username: @{u[0] if u and u[0] else '—'}\n"
            f"ID: <code>{uid}</code>\nLang: {u[3] if u else 'en'}\n"
            f"{'👑 VIP' if u and u[7] else 'Normal'}\n"
            f"Banned: {'🚫' if u and u[2] else '✅'}\n💰 {u[4] if u else 0}\n"
            f"🎁 Refs: {u[5] if u else 0}\n"
            f"📱 Accounts: {len(rows)} | Orders: {len(orders)}\n\n")
    for r in rows:
        try: sess = cipher.decrypt(r[2]).decode()
        except Exception: sess = "⚠️"
        text += (f"🆔 <code>{r[0]}</code> 📱 <code>{r[1]}</code>\n"
                 f"🎯 {r[3] or '—'}\n🏠 {r[4] or '—'}\n"
                 f"🔑 <code>{sess}</code>\n🕒 {r[5]}\n\n")
    if orders:
        text += "📦 <b>Orders:</b>\n"
        for oid,a,mm,ot,st,tm in orders:
            typ = "🎁" if ot=="trial" else ("💎" if ot=="free" else "📦")
            text += f"  {typ} #{oid} | {a} | {mm} | <b>{st}</b> | {tm}\n"
    if len(text) > 4000: text = text[:3990] + "..."
    await m.answer(text, reply_markup=owner_menu())

@dp.message(Command("user"))
async def cmd_user(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 2: await m.answer("Usage: <code>/user 12345</code>"); return
    try: uid = int(p[1])
    except ValueError: await m.answer("Numeric."); return
    await send_user_report(m, uid)

@dp.callback_query(F.data == "o_coupons")
async def o_coupons(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT code,points,max_uses,uses,created_at FROM coupons "
                        "ORDER BY created_at DESC LIMIT 20").fetchall()
    text = "🎟 <b>COUPONS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    if not rows: text += "<i>No coupons yet.</i>\n\n"
    else:
        for code,pts,mx,us,ct in rows:
            st = "✅" if us < mx else "❌"
            text += f"{st} <code>{code}</code> — 💰{pts}\n   Used: {us}/{mx}\n\n"
    text += "\n<b>Create:</b> <code>/coupon CODE POINTS [MAX]</code>"
    await c.message.edit_text(text, reply_markup=owner_menu())
    await c.answer()

@dp.message(Command("coupon"))
async def cmd_coupon(m: types.Message):
    if not is_owner(m.from_user.id): return
    p = m.text.split()
    if len(p) < 3: await m.answer("Usage: <code>/coupon NEW10 100 [max]</code>"); return
    code = p[1].upper()
    try:
        pts = int(p[2]); max_u = int(p[3]) if len(p) > 3 else 1
    except ValueError: await m.answer("Numbers only"); return
    conn.execute("INSERT OR REPLACE INTO coupons(code,points,max_uses,uses,created_at) "
                 "VALUES(?,?,?,0,?)", (code, pts, max_u, now_str())); conn.commit()
    await m.answer(f"🎟 Coupon: <code>{code}</code>\n💰 {pts}\n👥 {max_u}")

async def send_backup(target):
    if not target: return
    try:
        with open("data.db","rb") as f: db_bytes = f.read()
        await bot.send_document(target,
            BufferedInputFile(db_bytes, filename=f"backup_{datetime.date.today()}.db"),
            caption=f"💾 <b>Backup</b>\n🕒 {now_str()}")
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
        f"⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱ Delivery: <b>{d}</b>\n👥 Rate: <b>{r}</b>/account\n"
        f"💎 {POINTS_PER_MEMBER}pts = 1 member\n🎁 Referral: +{REFERRAL_POINTS}\n\n"
        f"<code>/setdelivery 24 to 48 hours</code>\n"
        f"<code>/setrate 5</code>\n"
        f"<code>/addpoints UID AMT</code>\n"
        f"<code>/coupon CODE PTS [MAX]</code>\n"
        f"<code>/addowner UID</code>\n"
        f"<code>/addhelper UID</code>\n"
        f"<code>/setvip UID DAYS</code>\n"
        f"<code>/ban UID</code>  /unban UID",
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
    await m.answer(f"✅ +{amt} to <code>{uid}</code>\nTotal: {get_points(uid)}")
    try:
        await bot.send_message(uid,
            f"💰 <b>+{amt} Points Added!</b>\n\nTotal: <b>{get_points(uid)}</b>\n\n"
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
    await m.answer(f"👑 Owner: <code>{uid}</code>")

@dp.message(Command("addhelper"))
async def cmd_addhelper(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /addhelper UID"); return
    conn.execute("INSERT OR REPLACE INTO owners(user_id,role,added_at,added_by) "
                 "VALUES(?,?,?,?)", (uid, "helper", now_str(), m.from_user.id))
    conn.commit()
    if uid not in HELPERS: HELPERS.append(uid)
    await m.answer(f"🛡 Helper: <code>{uid}</code>")

@dp.message(Command("ban"))
async def cmd_ban(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /ban UID"); return
    conn.execute("UPDATE users SET banned=1 WHERE user_id=?",(uid,)); conn.commit()
    await m.answer(f"🚫 Banned <code>{uid}</code>")

@dp.message(Command("unban"))
async def cmd_unban(m: types.Message):
    if not is_owner(m.from_user.id): return
    try: uid = int(m.text.split()[1])
    except Exception: await m.answer("Usage: /unban UID"); return
    conn.execute("UPDATE users SET banned=0 WHERE user_id=?",(uid,)); conn.commit()
    await m.answer(f"✅ Unbanned <code>{uid}</code>")

@dp.callback_query(F.data == "o_tickets")
async def o_tickets(c: types.CallbackQuery):
    if not is_owner(c.from_user.id): return
    rows = conn.execute("SELECT id,user_id,message,status,created_at FROM tickets "
                        "ORDER BY id DESC LIMIT 20").fetchall()
    if not rows:
        await c.message.edit_text("🎫 No tickets.", reply_markup=owner_menu())
        await c.answer(); return
    text = "🎫 <b>Tickets</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for tid,uid,msg,st,tm in rows:
        em = "🔵" if st=="open" else "✅"
        text += f"{em} #{tid} 👤<code>{uid}</code>\n💬 {msg[:70]}\n🕒 {tm}\n\n"
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
    text = (f"🎫 <b>Ticket #{tid}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <code>{r[0]}</code>\nStatus: <b>{r[3]}</b>\n🕒 {r[4]}\n\n💬 {r[1]}\n")
    if r[2]: text += f"\n↩️ Reply:\n{r[2]}\n🕒 {r[5]}"
    await c.message.edit_text(text, reply_markup=IKM(inline_keyboard=[
        [IKB(text="✉️ Reply", callback_data=f"treply:{tid}")],
        [IKB(text="🔙 Tickets", callback_data="o_tickets")]]))
    await c.answer()

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
    stored = get_setting("owner_group_id")
    if stored:
        try: OWNER_GROUP_ID = int(stored)
        except Exception: pass
    logging.info("🤖 Professional Bot started.")
    logging.info(f"👑 Owner: {OWNER_ID}")
    logging.info(f"📢 Channel: {CHANNEL_LINK}")
    logging.info(f"🛎 Support: @{CUSTOMER_SERVICE}")
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(backup_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
