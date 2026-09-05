import os
import logging
import requests
import json
import asyncio
import aiohttp
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ---------- CONFIG ----------
BOT_TOKEN = "8956990017:AAFS07sAXyckqUN5GNkQHwXAiNZYPCVtKdM"
OWNER_ID = 8762845215
HF_TOKEN = "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"
DAILY_LIMIT = 20
MAX_USER_HISTORY = 5

# ---------- MODELS (7) ----------
MODELS = [
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    "codellama/CodeLlama-7b-Python-hf",
    "bigcode/starcoder",
    "microsoft/phi-1_5",
    "google/flan-t5-base",
    "mistralai/Mistral-7B-Instruct-v0.1",
    "HuggingFaceH4/zephyr-7b-beta"
]
HF_API_URL = "https://api-inference.huggingface.co/models/{}"
PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

# ---------- FILES ----------
HISTORY_FILE = "history.json"
SNIPPETS_FILE = "snippets.json"
FEEDBACK_FILE = "feedback.json"
BOOKMARKS_FILE = "bookmarks.json"
CHALLENGES_FILE = "challenges.json"
LEADERBOARD_FILE = "leaderboard.json"
BADGES_FILE = "badges.json"
ANALYTICS_FILE = "analytics.json"
NOTIFICATIONS_FILE = "notifications.json"
FILES_DIR = "user_files"
os.makedirs(FILES_DIR, exist_ok=True)

# ---------- STATES ----------
ASK_AI, WAIT_SAVE_NAME, WAIT_EXPLAIN, WAIT_RUN, WAIT_BROADCAST, WAIT_LANG, \
WAIT_FORMAT, WAIT_CONVERT, WAIT_REVIEW, WAIT_COMPLEXITY, WAIT_TESTS, WAIT_DOCS = range(12)

# ---------- LOGGING ----------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ---------- HTTP HEALTH CHECK SERVER ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()
threading.Thread(target=run_health_server, daemon=True).start()

# ---------- JSON HELPERS ----------
def load_json(f):
    return json.load(open(f)) if os.path.exists(f) else {}
def save_json(f, d):
    with open(f, "w") as j: json.dump(d, j, indent=2)

def load_history(): return load_json(HISTORY_FILE)
def save_history(d): save_json(HISTORY_FILE, d)
def load_snippets(): return load_json(SNIPPETS_FILE)
def save_snippets(d): save_json(SNIPPETS_FILE, d)
def load_feedback(): return load_json(FEEDBACK_FILE)
def save_feedback(d): save_json(FEEDBACK_FILE, d)
def load_bookmarks(): return load_json(BOOKMARKS_FILE)
def save_bookmarks(d): save_json(BOOKMARKS_FILE, d)
def load_challenges(): return load_json(CHALLENGES_FILE)
def save_challenges(d): save_json(CHALLENGES_FILE, d)
def load_leaderboard(): return load_json(LEADERBOARD_FILE)
def save_leaderboard(d): save_json(LEADERBOARD_FILE, d)
def load_badges(): return load_json(BADGES_FILE)
def save_badges(d): save_json(BADGES_FILE, d)
def load_analytics(): return load_json(ANALYTICS_FILE)
def save_analytics(d): save_json(ANALYTICS_FILE, d)
def load_notifications(): return load_json(NOTIFICATIONS_FILE)
def save_notifications(d): save_json(NOTIFICATIONS_FILE, d)

# ---------- HISTORY ----------
def get_user_history(user_id):
    h = load_history()
    return h.get(str(user_id), [])
def add_to_history(user_id, role, content):
    h = load_history()
    u = str(user_id)
    if u not in h: h[u] = []
    h[u].append({"role": role, "content": content})
    if user_id != OWNER_ID and len(h[u]) > MAX_USER_HISTORY*2:
        h[u] = h[u][-MAX_USER_HISTORY*2:]
    save_history(h)
def clear_user_history(user_id):
    h = load_history()
    if str(user_id) in h:
        del h[str(user_id)]
        save_history(h)
def format_history(h):
    if not h: return "📭 Koi history nahi."
    return "\n".join(f"{'👤' if e['role']=='user' else '🤖'} {e['content']}" for e in h)

# ---------- SNIPPETS ----------
def save_snippet(user_id, name, code):
    s = load_snippets()
    u = str(user_id)
    if u not in s: s[u] = {}
    s[u][name] = code
    save_snippets(s)
def get_snippets(user_id):
    return load_snippets().get(str(user_id), {})
def delete_snippet(user_id, name):
    s = load_snippets()
    u = str(user_id)
    if u in s and name in s[u]:
        del s[u][name]
        save_snippets(s)
        return True
    return False

# ---------- BOOKMARKS ----------
def add_bookmark(user_id, q, r):
    b = load_bookmarks()
    u = str(user_id)
    if u not in b: b[u] = []
    b[u].append({"query": q, "response": r[:200], "timestamp": str(datetime.now())})
    save_bookmarks(b)
def get_bookmarks(user_id):
    return load_bookmarks().get(str(user_id), [])

# ---------- CHALLENGES ----------
def get_current_challenge():
    c = load_challenges()
    return c.get(max(c.keys())) if c else None
def set_challenge(q, a):
    c = load_challenges()
    c[datetime.now().strftime("%Y-%m-%d")] = {"question": q, "answer": a.strip().lower()}
    save_challenges(c)
def submit_challenge(user_id, answer):
    lb = load_leaderboard()
    u = str(user_id)
    if u not in lb: lb[u] = {"points": 0, "solved": 0, "history": []}
    ch = get_current_challenge()
    if not ch: return "No active challenge."
    if ch["answer"] == answer.strip().lower():
        lb[u]["points"] += 10; lb[u]["solved"] += 1
        lb[u]["history"].append({"date": datetime.now().strftime("%Y-%m-%d"), "status": "solved"})
        save_leaderboard(lb)
        check_achievements(user_id)
        return "✅ Correct! +10 points."
    else:
        lb[u]["history"].append({"date": datetime.now().strftime("%Y-%m-%d"), "status": "wrong"})
        save_leaderboard(lb)
        return "❌ Wrong answer."
def get_leaderboard():
    return sorted(load_leaderboard().items(), key=lambda x: x[1]["points"], reverse=True)

# ---------- BADGES ----------
def get_badges(user_id):
    return load_badges().get(str(user_id), [])
def award_badge(user_id, badge):
    b = load_badges()
    u = str(user_id)
    if u not in b: b[u] = []
    if badge not in b[u]:
        b[u].append(badge)
        save_badges(b)
        return True
    return False
def check_achievements(user_id):
    hist = get_user_history(user_id)
    g = sum(1 for h in hist if "Gmail" in h.get("content",""))
    if g >= 10: award_badge(user_id, "🥉 Bronze")
    if g >= 50: award_badge(user_id, "🥈 Silver")
    if g >= 100: award_badge(user_id, "🥇 Gold")
    lb = load_leaderboard()
    if str(user_id) in lb and lb[str(user_id)].get("solved",0) >= 10:
        award_badge(user_id, "🏆 Challenge Champion")
    if len(hist) >= 50:
        award_badge(user_id, "🧠 AI Master")

# ---------- ANALYTICS ----------
def update_analytics(user_id, action, amt=0):
    a = load_analytics()
    u = str(user_id)
    if u not in a: a[u] = {"days": {}}
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in a[u]["days"]:
        a[u]["days"][today] = {"earnings": 0, "queries": 0, "snippets": 0}
    if action == "earn": a[u]["days"][today]["earnings"] += amt
    elif action == "query": a[u]["days"][today]["queries"] += 1
    elif action == "snippet": a[u]["days"][today]["snippets"] += 1
    save_analytics(a)
def get_analytics(user_id):
    a = load_analytics().get(str(user_id), {})
    return a.get("days", {})

# ---------- EXPORT ----------
def export_user_data(user_id):
    return json.dumps({
        "history": get_user_history(user_id),
        "snippets": get_snippets(user_id),
        "bookmarks": get_bookmarks(user_id),
        "badges": get_badges(user_id),
        "analytics": get_analytics(user_id)
    }, indent=2)

# ---------- ANTI-SPAM ----------
last_msg = {}
def check_spam(uid):
    if uid == OWNER_ID: return True
    now = datetime.now()
    if uid not in last_msg or (now - last_msg[uid]).total_seconds() >= 5:
        last_msg[uid] = now
        return True
    return False

# ---------- FEEDBACK ----------
def add_feedback(uid, mid, rating):
    f = load_feedback()
    f[str(mid)] = {"user": uid, "rating": rating, "timestamp": str(datetime.now())}
    save_feedback(f)
def get_feedback_stats():
    f = load_feedback().values()
    likes = sum(1 for x in f if x["rating"]=="like")
    return len(f), likes, len(f)-likes

# ---------- USER LIMIT ----------
reqs = {}
def check_limit(uid):
    if uid == OWNER_ID: return True
    today = datetime.now().date()
    if uid not in reqs or reqs[uid][1] != today:
        reqs[uid] = [0, today]
    if reqs[uid][0] >= DAILY_LIMIT:
        return False
    return True
def inc_limit(uid):
    if uid == OWNER_ID: return
    today = datetime.now().date()
    if uid not in reqs or reqs[uid][1] != today:
        reqs[uid] = [0, today]
    reqs[uid][0] += 1
def get_user_stats():
    h = load_history()
    return len(h), sum(len(v) for v in h.values())

# ---------- AI HELPERS ----------
async def call_hf_model(model, prompt):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    url = HF_API_URL.format(model)
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 500, "temperature": 0.2}}
    for attempt in range(2):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=25) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            return data[0].get("generated_text", "").replace(prompt, "").strip()
                        return data.get("generated_text", "").replace(prompt, "").strip()
                    elif resp.status == 429:
                        await asyncio.sleep(3)
                        continue
        except:
            pass
    return ""

async def ask_multiple_ai(user_id, prompt):
    tasks = [call_hf_model(m, prompt) for m in MODELS[:5]]  # Use first 5 for speed
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in responses if isinstance(r, str) and len(r) > 10]
    if not valid:
        return "❌ All AI models are busy. Please try later."
    if len(valid) == 1:
        return valid[0]
    # Synthesize using deepseek
    combined = "I got multiple responses. Synthesize them:\n" + "\n".join(f"Resp{i+1}: {r}" for i,r in enumerate(valid[:3]))
    final = await call_hf_model("deepseek-ai/deepseek-coder-6.7b-instruct", f"Combine these into a single best answer:\n{combined}")
    return final if final else valid[0]

async def ask_single_ai(user_id, prompt):
    return await call_hf_model("deepseek-ai/deepseek-coder-6.7b-instruct", prompt)

def run_code(lang, code):
    try:
        r = requests.post(PISTON_API_URL, json={"language": lang, "source": code}, timeout=15)
        if r.status_code == 200:
            return r.json().get("output", "✅ No output.").strip()
        return f"⚠️ Error: {r.text}"
    except Exception as e:
        return f"❌ {str(e)}"

# ---------- KEYBOARDS (CLEAN DASHBOARD) ----------
MAIN_MENU = [
    [InlineKeyboardButton("🤖 AI Services", callback_data="menu_ai")],
    [InlineKeyboardButton("🛠️ Code Tools", callback_data="menu_code")],
    [InlineKeyboardButton("📁 My Data", callback_data="menu_data")],
    [InlineKeyboardButton("🏆 Challenges", callback_data="menu_challenge")],
]
AI_MENU = [
    [InlineKeyboardButton("💬 Ask AI (Single)", callback_data="ask_ai")],
    [InlineKeyboardButton("🚀 Super AI (Multi)", callback_data="super_ai")],
    [InlineKeyboardButton("🔍 Explain Code", callback_data="explain_code")],
    [InlineKeyboardButton("🧪 Generate Tests", callback_data="generate_tests")],
    [InlineKeyboardButton("📝 Generate Docs", callback_data="generate_docs")],
    [InlineKeyboardButton("🔙 Main", callback_data="main_menu")],
]
CODE_MENU = [
    [InlineKeyboardButton("▶️ Run Code", callback_data="run_code")],
    [InlineKeyboardButton("🎨 Format Code", callback_data="format_code")],
    [InlineKeyboardButton("🔄 Convert Code", callback_data="convert_code")],
    [InlineKeyboardButton("🧐 Review Code", callback_data="review_code")],
    [InlineKeyboardButton("📊 Complexity", callback_data="complexity")],
    [InlineKeyboardButton("🔙 Main", callback_data="main_menu")],
]
DATA_MENU = [
    [InlineKeyboardButton("📚 My History", callback_data="my_history")],
    [InlineKeyboardButton("📌 Bookmarks", callback_data="my_bookmarks")],
    [InlineKeyboardButton("💾 Save Snippet", callback_data="save_snippet")],
    [InlineKeyboardButton("📂 My Snippets", callback_data="my_snippets")],
    [InlineKeyboardButton("🏅 My Badges", callback_data="my_badges")],
    [InlineKeyboardButton("📈 Analytics", callback_data="analytics")],
    [InlineKeyboardButton("📋 Export Data", callback_data="export")],
    [InlineKeyboardButton("🗑️ Clear History", callback_data="clear_history")],
    [InlineKeyboardButton("🔙 Main", callback_data="main_menu")],
]
CHALLENGE_MENU = [
    [InlineKeyboardButton("🏆 Daily Challenge", callback_data="daily_challenge")],
    [InlineKeyboardButton("📊 Leaderboard", callback_data="leaderboard")],
    [InlineKeyboardButton("🔙 Main", callback_data="main_menu")],
]
ADMIN_MENU = [
    [InlineKeyboardButton("👥 Users List", callback_data="admin_users")],
    [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
    [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
    [InlineKeyboardButton("🏆 Set Challenge", callback_data="admin_set_challenge")],
    [InlineKeyboardButton("⚙️ Set Daily Limit", callback_data="admin_set_limit")],
    [InlineKeyboardButton("🗑️ Clear User History", callback_data="admin_clear_user")],
    [InlineKeyboardButton("🔙 Main", callback_data="main_menu")],
]
BACK_BUTTON = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]

# ---------- BOT HANDLERS ----------
async def start(update, context):
    await show_main(update, is_new=True)

async def show_main(update, is_new=False):
    user_id = update.effective_user.id
    menu = MAIN_MENU.copy()
    if user_id == OWNER_ID:
        menu.append([InlineKeyboardButton("🔐 Admin", callback_data="admin_panel")])
    text = "🤖 **AI Coding Bot**\n\nSelect a category:"
    if is_new and hasattr(update, 'message'):
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(menu), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(menu), parse_mode="Markdown")

async def button_handler(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = update.effective_user.id

    def go(menu, text):
        return q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(menu), parse_mode="Markdown")

    if data == "main_menu":
        await show_main(update); return

    # ---- Main menu navigation ----
    if data == "menu_ai":
        await go(AI_MENU, "🤖 **AI Services**\n\nSelect an option:")
    elif data == "menu_code":
        await go(CODE_MENU, "🛠️ **Code Tools**\n\nSelect an option:")
    elif data == "menu_data":
        await go(DATA_MENU, "📁 **My Data**\n\nSelect an option:")
    elif data == "menu_challenge":
        await go(CHALLENGE_MENU, "🏆 **Challenges**\n\nSelect an option:")

    # ---- AI Services ----
    elif data == "ask_ai":
        context.user_data['multi'] = False
        context.user_data['state'] = ASK_AI
        await q.edit_message_text("💬 **Ask AI (Single)**\n\nType your coding question:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "super_ai":
        context.user_data['multi'] = True
        context.user_data['state'] = ASK_AI
        await q.edit_message_text("🚀 **Super AI (Multi)**\n\nType your question (7 models):", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "explain_code":
        context.user_data['state'] = WAIT_EXPLAIN
        await q.edit_message_text("🔍 **Explain Code**\n\nPaste your code:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "generate_tests":
        context.user_data['state'] = WAIT_TESTS
        await q.edit_message_text("🧪 **Generate Tests**\n\nPaste your function/class:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "generate_docs":
        context.user_data['state'] = WAIT_DOCS
        await q.edit_message_text("📝 **Generate Docs**\n\nPaste your code:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")

    # ---- Code Tools ----
    elif data == "run_code":
        context.user_data['state'] = WAIT_RUN
        await q.edit_message_text("▶️ **Run Code**\n\nPaste your code (Python, Java, C++, JS, Go, Rust):", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "format_code":
        context.user_data['state'] = WAIT_FORMAT
        await q.edit_message_text("🎨 **Format Code**\n\nPaste your code:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "convert_code":
        context.user_data['state'] = WAIT_CONVERT
        await q.edit_message_text("🔄 **Convert Code**\n\nSend code and target language (e.g., 'Python to Java ...')", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "review_code":
        context.user_data['state'] = WAIT_REVIEW
        await q.edit_message_text("🧐 **Review Code**\n\nPaste your code:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "complexity":
        context.user_data['state'] = WAIT_COMPLEXITY
        await q.edit_message_text("📊 **Complexity**\n\nPaste your code:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")

    # ---- Data ----
    elif data == "my_history":
        h = get_user_history(uid)
        text = "📚 **History**\n\n" + format_history(h) if h else "📭 No history."
        if len(text) > 4000:
            await q.message.reply_text(text[:4000])
            await q.message.reply_text("🔙 Back", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]))
        else:
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]), parse_mode="Markdown")
    elif data == "my_bookmarks":
        b = get_bookmarks(uid)
        if not b:
            text = "📌 No bookmarks."
        else:
            text = "📌 **Bookmarks**\n\n" + "\n".join(f"{i+1}. {x['query'][:40]}..." for i,x in enumerate(b))
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]), parse_mode="Markdown")
    elif data == "save_snippet":
        context.user_data['state'] = WAIT_SAVE_NAME
        context.user_data['saving_code'] = None
        await q.edit_message_text("💾 **Save Snippet**\n\nSend code first, then name.", reply_markup=InlineKeyboardMarkup(BACK_BUTTON), parse_mode="Markdown")
    elif data == "my_snippets":
        s = get_snippets(uid)
        if not s:
            await q.edit_message_text("📂 No snippets.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]))
            return
        kb = []
        for name in s:
            kb.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"snippet_{name}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="menu_data")])
        await q.edit_message_text("📂 **Snippets**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif data.startswith("snippet_"):
        name = data[8:]
        code = get_snippets(uid).get(name)
        if code:
            await q.edit_message_text(f"📄 **{name}**\n\n```\n{code}\n```", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{name}"), InlineKeyboardButton("🔙 Back", callback_data="my_snippets")]]), parse_mode="Markdown")
        else:
            await q.edit_message_text("❌ Not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="my_snippets")]]))
    elif data.startswith("del_"):
        name = data[4:]
        if delete_snippet(uid, name):
            await q.edit_message_text(f"✅ Deleted '{name}'.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="my_snippets")]]))
        else:
            await q.edit_message_text("❌ Failed.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="my_snippets")]]))
    elif data == "my_badges":
        b = get_badges(uid)
        text = "🏅 **Badges**\n\n" + ("\n".join(b) if b else "No badges yet.")
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]), parse_mode="Markdown")
    elif data == "analytics":
        a = get_analytics(uid)
        if not a:
            text = "📈 No data."
        else:
            text = "📈 **Analytics (last 7 days)**\n\n"
            for day, vals in sorted(a.items(), reverse=True)[:7]:
                text += f"📅 {day}: Earned {vals.get('earnings',0)} PKR, Queries {vals.get('queries',0)}, Snippets {vals.get('snippets',0)}\n"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]), parse_mode="Markdown")
    elif data == "export":
        data = export_user_data(uid)
        fpath = f"export_{uid}.json"
        with open(fpath, "w") as f: f.write(data)
        await q.message.reply_document(open(fpath, "rb"), caption="📋 Your data")
        os.remove(fpath)
    elif data == "clear_history":
        await q.edit_message_text("🗑️ Clear all history?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yes", callback_data="clear_confirm"), InlineKeyboardButton("❌ No", callback_data="menu_data")]]), parse_mode="Markdown")
    elif data == "clear_confirm":
        clear_user_history(uid)
        await q.edit_message_text("✅ History cleared.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_data")]]))

    # ---- Challenge ----
    elif data == "daily_challenge":
        ch = get_current_challenge()
        text = f"🏆 **Daily Challenge**\n\n{ch['question']}\n\nUse /submit <answer>" if ch else "🏆 No challenge today."
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_challenge")]]), parse_mode="Markdown")
    elif data == "leaderboard":
        lb = get_leaderboard()
        if not lb:
            text = "📊 No one solved yet."
        else:
            text = "📊 **Leaderboard**\n\n" + "\n".join(f"{i+1}. {uid[:6]} – {x['points']}pts" for i,(uid,x) in enumerate(lb[:10]))
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu_challenge")]]), parse_mode="Markdown")

    # ---- Admin ----
    elif data == "admin_panel":
        if uid != OWNER_ID: await q.edit_message_text("❌ Access Denied."); return
        await q.edit_message_text("🔐 **Admin Panel**", reply_markup=InlineKeyboardMarkup(ADMIN_MENU), parse_mode="Markdown")
    elif data == "admin_users":
        if uid != OWNER_ID: return
        h = load_history()
        text = "👥 **Users**\n\n" + "\n".join(f"{u}: {len(v)} msgs" for u,v in h.items())
        await q.edit_message_text(text[:4000], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_stats":
        if uid != OWNER_ID: return
        users, msgs = get_user_stats()
        fb_total, likes, dislikes = get_feedback_stats()
        await q.edit_message_text(f"📊 **Stats**\n\n👥 Users: {users}\n💬 Messages: {msgs}\n📝 Daily Limit: {DAILY_LIMIT}\n👍 Likes: {likes}\n👎 Dislikes: {dislikes}\n👑 Owner: {OWNER_ID}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_broadcast":
        context.user_data['state'] = WAIT_BROADCAST
        await q.edit_message_text("📢 **Broadcast**\n\nSend message:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_set_challenge":
        context.user_data['state'] = WAIT_CHALLENGE_SET
        await q.edit_message_text("🏆 **Set Challenge**\n\nSend: `Question | Answer`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_set_limit":
        context.user_data['state'] = 'waiting_set_limit'
        await q.edit_message_text("⚙️ **Set Daily Limit**\n\nSend number:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_clear_user":
        context.user_data['state'] = 'waiting_clear_user'
        await q.edit_message_text("🗑️ **Clear User History**\n\nSend user ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")

# ---------- MESSAGE HANDLER ----------
async def handle_message(update, context):
    uid = update.effective_user.id
    msg = update.message.text
    state = context.user_data.get('state')

    if not check_spam(uid):
        await update.message.reply_text("⏳ Slow down!")
        return

    async def process(prompt, hint=""):
        if not check_limit(uid):
            await update.message.reply_text(f"❌ Daily limit {DAILY_LIMIT} reached.")
            return
        multi = context.user_data.get('multi', False)
        await update.message.reply_text("⏳ Thinking..." + (" (7 models)" if multi else ""))
        if multi:
            reply = await ask_multiple_ai(uid, prompt)
        else:
            reply = await call_hf_model("deepseek-ai/deepseek-coder-6.7b-instruct", prompt)
        if not reply:
            reply = "⚠️ No response."
        inc_limit(uid)
        update_analytics(uid, "query")
        await update.message.reply_text(reply[:4000])
        context.user_data['state'] = None
        await update.message.reply_text("🔙 Back", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main", callback_data="main_menu")]]))

    if state == ASK_AI:
        await process(msg)
    elif state == WAIT_EXPLAIN:
        await process(f"Explain line by line:\n{msg}")
    elif state == WAIT_FORMAT:
        await process(f"Format properly:\n{msg}")
    elif state == WAIT_CONVERT:
        if "to" in msg.lower():
            parts = msg.lower().split("to", 1)
            lang = parts[0].strip().split()[-1]
            code = parts[1].strip()
            await process(f"Convert to {lang}:\n{code}")
        else:
            await update.message.reply_text("❌ Use 'language to target' format.", reply_markup=InlineKeyboardMarkup(BACK_BUTTON))
    elif state == WAIT_REVIEW:
        await process(f"Review code:\n{msg}")
    elif state == WAIT_COMPLEXITY:
        await process(f"Complexity of:\n{msg}")
    elif state == WAIT_TESTS:
        await process(f"Generate tests for:\n{msg}")
    elif state == WAIT_DOCS:
        await process(f"Generate docs for:\n{msg}")
    elif state == WAIT_RUN:
        lang = "python"
        code = msg
        if "public class" in code or "System.out.println" in code: lang = "java"
        elif "int main" in code or "std::cout" in code: lang = "cpp"
        elif "function" in code or "console.log" in code: lang = "javascript"
        elif "package main" in code or "fmt.Println" in code: lang = "go"
        elif "fn main" in code or "println!" in code: lang = "rust"
        await update.message.reply_text(f"⏳ Running {lang}...")
        out = run_code(lang, code)
        await update.message.reply_text(f"```\n{out}\n```", parse_mode="Markdown")
        context.user_data['state'] = None
    elif state == WAIT_SAVE_NAME:
        if context.user_data.get('saving_code') is None:
            context.user_data['saving_code'] = msg
            await update.message.reply_text("✅ Code received. Now send a name:", reply_markup=InlineKeyboardMarkup(BACK_BUTTON))
        else:
            code = context.user_data['saving_code']
            name = msg.strip()
            if name:
                save_snippet(uid, name, code)
                update_analytics(uid, "snippet")
                await update.message.reply_text(f"✅ Snippet '{name}' saved!")
            else:
                await update.message.reply_text("❌ Invalid name.")
            context.user_data['saving_code'] = None
            context.user_data['state'] = None
            await update.message.reply_text("🔙 Main", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main", callback_data="main_menu")]]))
    elif state == WAIT_BROADCAST:
        if uid != OWNER_ID: return
        h = load_history()
        users = list(h.keys())
        sent, failed = 0, 0
        for uid2 in users:
            try:
                await context.bot.send_message(int(uid2), f"📢 Broadcast:\n{msg}")
                sent += 1
            except:
                failed += 1
        await update.message.reply_text(f"✅ Broadcast done.\nSent: {sent}\nFailed: {failed}")
        context.user_data['state'] = None
    elif state == WAIT_CHALLENGE_SET:
        if uid != OWNER_ID: return
        try:
            q, a = msg.split('|', 1)
            set_challenge(q.strip(), a.strip())
            await update.message.reply_text("🏆 Challenge set!")
        except:
            await update.message.reply_text("❌ Use: Question | Answer")
        context.user_data['state'] = None
    elif state == 'waiting_set_limit':
        if uid != OWNER_ID: return
        try:
            global DAILY_LIMIT
            DAILY_LIMIT = int(msg)
            await update.message.reply_text(f"✅ Limit set to {DAILY_LIMIT}")
        except:
            await update.message.reply_text("❌ Invalid number.")
        context.user_data['state'] = None
    elif state == 'waiting_clear_user':
        if uid != OWNER_ID: return
        try:
            target = int(msg)
            clear_user_history(target)
            await update.message.reply_text(f"✅ User {target} history cleared.")
        except:
            await update.message.reply_text("❌ Invalid ID.")
        context.user_data['state'] = None
    else:
        await update.message.reply_text("Use buttons below.", reply_markup=InlineKeyboardMarkup(MAIN_MENU))

async def submit_challenge(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /submit <answer>")
        return
    ans = ' '.join(context.args)
    result = submit_challenge(update.effective_user.id, ans)
    await update.message.reply_text(result)

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelled.", reply_markup=InlineKeyboardMarkup(MAIN_MENU))

# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("submit", submit_challenge))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot is running with 7 models (multi-AI) – Clean dashboard.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
