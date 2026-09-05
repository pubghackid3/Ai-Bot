import os
import logging
import requests
import json
import shutil
import asyncio
import aiohttp
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ---------- CONFIG ----------
BOT_TOKEN = "8956990017:AAFS07sAXyckqUN5GNkQHwXAiNZYPCVtKdM"
OWNER_ID = 8762845215
HF_TOKEN = "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"
DAILY_LIMIT = 20
MAX_USER_HISTORY = 5

# ---------- 7 FREE MODELS ----------
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
WAIT_FORMAT, WAIT_CONVERT, WAIT_REVIEW, WAIT_COMPLEXITY, WAIT_TESTS, WAIT_DOCS, \
WAIT_BOOKMARK, WAIT_CHALLENGE_ANSWER, WAIT_CHALLENGE_SET, WAIT_MODEL_SELECT = range(16)

# ---------- LOGGING ----------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ---------- FILE HELPERS ----------
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_history():
    return load_json(HISTORY_FILE)
def save_history(data):
    save_json(HISTORY_FILE, data)
def load_snippets():
    return load_json(SNIPPETS_FILE)
def save_snippets(data):
    save_json(SNIPPETS_FILE, data)
def load_feedback():
    return load_json(FEEDBACK_FILE)
def save_feedback(data):
    save_json(FEEDBACK_FILE, data)
def load_bookmarks():
    return load_json(BOOKMARKS_FILE)
def save_bookmarks(data):
    save_json(BOOKMARKS_FILE, data)
def load_challenges():
    return load_json(CHALLENGES_FILE)
def save_challenges(data):
    save_json(CHALLENGES_FILE, data)
def load_leaderboard():
    return load_json(LEADERBOARD_FILE)
def save_leaderboard(data):
    save_json(LEADERBOARD_FILE, data)
def load_badges():
    return load_json(BADGES_FILE)
def save_badges(data):
    save_json(BADGES_FILE, data)
def load_analytics():
    return load_json(ANALYTICS_FILE)
def save_analytics(data):
    save_json(ANALYTICS_FILE, data)
def load_notifications():
    return load_json(NOTIFICATIONS_FILE)
def save_notifications(data):
    save_json(NOTIFICATIONS_FILE, data)

# ---------- HISTORY ----------
def get_user_history(user_id):
    history = load_history()
    return history.get(str(user_id), [])
def add_to_history(user_id, role, content):
    history = load_history()
    u = str(user_id)
    if u not in history:
        history[u] = []
    history[u].append({"role": role, "content": content})
    if user_id != OWNER_ID:
        if len(history[u]) > MAX_USER_HISTORY * 2:
            history[u] = history[u][-MAX_USER_HISTORY * 2:]
    save_history(history)
def clear_user_history(user_id):
    history = load_history()
    if str(user_id) in history:
        del history[str(user_id)]
        save_history(history)
def format_history(history):
    if not history:
        return "📭 Koi history nahi mili."
    text = ""
    for entry in history:
        role = "👤 User" if entry["role"] == "user" else "🤖 Assistant"
        text += f"{role}: {entry['content']}\n\n"
    return text.strip()

# ---------- SNIPPETS ----------
def save_snippet(user_id, name, code):
    snippets = load_snippets()
    u = str(user_id)
    if u not in snippets:
        snippets[u] = {}
    snippets[u][name] = code
    save_snippets(snippets)
def get_snippets(user_id):
    snippets = load_snippets()
    return snippets.get(str(user_id), {})
def delete_snippet(user_id, name):
    snippets = load_snippets()
    u = str(user_id)
    if u in snippets and name in snippets[u]:
        del snippets[u][name]
        save_snippets(snippets)
        return True
    return False

# ---------- BOOKMARKS ----------
def add_bookmark(user_id, query, response):
    bookmarks = load_bookmarks()
    u = str(user_id)
    if u not in bookmarks:
        bookmarks[u] = []
    bookmarks[u].append({"query": query, "response": response[:200], "timestamp": str(datetime.now())})
    save_bookmarks(bookmarks)
def get_bookmarks(user_id):
    bookmarks = load_bookmarks()
    return bookmarks.get(str(user_id), [])

# ---------- CHALLENGES ----------
def get_current_challenge():
    challenges = load_challenges()
    if not challenges:
        return None
    latest = max(challenges.keys()) if challenges else None
    return challenges.get(latest)
def set_challenge(question, answer):
    challenges = load_challenges()
    date_str = datetime.now().strftime("%Y-%m-%d")
    challenges[date_str] = {"question": question, "answer": answer.strip().lower()}
    save_challenges(challenges)
def submit_challenge(user_id, answer):
    lb = load_leaderboard()
    u = str(user_id)
    if u not in lb:
        lb[u] = {"points": 0, "solved": 0, "history": []}
    challenge = get_current_challenge()
    if not challenge:
        return "No active challenge."
    if challenge["answer"] == answer.strip().lower():
        lb[u]["points"] += 10
        lb[u]["solved"] += 1
        lb[u]["history"].append({"date": datetime.now().strftime("%Y-%m-%d"), "status": "solved"})
        save_leaderboard(lb)
        check_achievements(user_id)
        return "✅ Correct! You earned 10 points."
    else:
        lb[u]["history"].append({"date": datetime.now().strftime("%Y-%m-%d"), "status": "wrong"})
        save_leaderboard(lb)
        return "❌ Wrong answer. Try again tomorrow!"
def get_leaderboard():
    lb = load_leaderboard()
    sorted_users = sorted(lb.items(), key=lambda x: x[1]["points"], reverse=True)
    return sorted_users

# ---------- BADGES ----------
def get_badges(user_id):
    badges = load_badges()
    u = str(user_id)
    if u not in badges:
        badges[u] = []
    return badges[u]

def award_badge(user_id, badge):
    badges = load_badges()
    u = str(user_id)
    if u not in badges:
        badges[u] = []
    if badge not in badges[u]:
        badges[u].append(badge)
        save_badges(badges)
        return True
    return False

def check_achievements(user_id):
    history = get_user_history(user_id)
    gmail_submissions = sum(1 for h in history if "Gmail submitted" in h.get("content", ""))
    if gmail_submissions >= 10:
        award_badge(user_id, "🥉 Bronze (10 Gmails)")
    if gmail_submissions >= 50:
        award_badge(user_id, "🥈 Silver (50 Gmails)")
    if gmail_submissions >= 100:
        award_badge(user_id, "🥇 Gold (100 Gmails)")
    lb = load_leaderboard()
    u = str(user_id)
    if u in lb and lb[u].get("solved", 0) >= 10:
        award_badge(user_id, "🏆 Challenge Champion")
    ai_queries = sum(1 for h in history if h.get("role") == "user")
    if ai_queries >= 50:
        award_badge(user_id, "🧠 AI Master")

# ---------- ANALYTICS ----------
def update_analytics(user_id, action, amount=0):
    analytics = load_analytics()
    u = str(user_id)
    if u not in analytics:
        analytics[u] = {"days": {}}
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in analytics[u]["days"]:
        analytics[u]["days"][today] = {"earnings": 0, "queries": 0, "snippets": 0}
    if action == "earn":
        analytics[u]["days"][today]["earnings"] += amount
    elif action == "query":
        analytics[u]["days"][today]["queries"] += 1
    elif action == "snippet":
        analytics[u]["days"][today]["snippets"] += 1
    save_analytics(analytics)

def get_analytics(user_id, days=7):
    analytics = load_analytics()
    u = str(user_id)
    if u not in analytics:
        return None
    days_data = analytics[u]["days"]
    sorted_days = sorted(days_data.keys(), reverse=True)[:days]
    result = {}
    for d in sorted_days:
        result[d] = days_data[d]
    return result

# ---------- NOTIFICATIONS ----------
def add_notification(user_id, message):
    notifs = load_notifications()
    u = str(user_id)
    if u not in notifs:
        notifs[u] = []
    notifs[u].append({"message": message, "timestamp": str(datetime.now())})
    save_notifications(notifs)

def get_notifications(user_id):
    notifs = load_notifications()
    return notifs.get(str(user_id), [])

# ---------- EXPORT ----------
def export_user_data(user_id):
    data = {
        "history": get_user_history(user_id),
        "snippets": get_snippets(user_id),
        "bookmarks": get_bookmarks(user_id),
        "badges": get_badges(user_id),
        "analytics": get_analytics(user_id, 30)
    }
    return json.dumps(data, indent=2)

# ---------- ANTI-SPAM ----------
user_last_message = {}
def check_spam(user_id):
    if user_id == OWNER_ID:
        return True
    now = datetime.now()
    if user_id not in user_last_message:
        user_last_message[user_id] = now
        return True
    diff = (now - user_last_message[user_id]).total_seconds()
    if diff < 5:
        return False
    user_last_message[user_id] = now
    return True

# ---------- FEEDBACK ----------
def add_feedback(user_id, message_id, rating):
    feedback = load_feedback()
    if str(message_id) not in feedback:
        feedback[str(message_id)] = {"user": user_id, "rating": rating, "timestamp": str(datetime.now())}
    else:
        feedback[str(message_id)]["rating"] = rating
    save_feedback(feedback)
def get_feedback_stats():
    feedback = load_feedback()
    total = len(feedback)
    likes = sum(1 for f in feedback.values() if f["rating"] == "like")
    dislikes = total - likes
    return total, likes, dislikes

# ---------- USER LIMIT ----------
user_requests = {}
def check_limit(user_id):
    if user_id == OWNER_ID:
        return True
    today = datetime.now().date()
    if user_id not in user_requests:
        user_requests[user_id] = [0, today]
        return True
    count, date = user_requests[user_id]
    if date != today:
        user_requests[user_id] = [0, today]
        return True
    if count >= DAILY_LIMIT:
        return False
    return True
def increment_limit(user_id):
    if user_id == OWNER_ID:
        return
    today = datetime.now().date()
    if user_id not in user_requests:
        user_requests[user_id] = [0, today]
    count, date = user_requests[user_id]
    if date != today:
        user_requests[user_id] = [0, today]
    else:
        user_requests[user_id] = [count + 1, date]
def get_user_stats():
    history = load_history()
    total_users = len(history)
    total_messages = sum(len(h) for h in history.values())
    return total_users, total_messages

# ---------- MULTI-AI SYSTEM (7 MODELS) ----------
async def call_hf_model(model, prompt):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    url = HF_API_URL.format(model)
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 500, "temperature": 0.2}}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if isinstance(result, list):
                        return result[0].get("generated_text", "").replace(prompt, "").strip()
                    elif isinstance(result, dict):
                        return result.get("generated_text", "").replace(prompt, "").strip()
                    else:
                        return ""
                else:
                    # If rate limit (429), wait and retry once
                    if resp.status == 429:
                        await asyncio.sleep(2)
                        async with session.post(url, headers=headers, json=payload, timeout=20) as retry_resp:
                            if retry_resp.status == 200:
                                result = await retry_resp.json()
                                if isinstance(result, list):
                                    return result[0].get("generated_text", "").replace(prompt, "").strip()
                                elif isinstance(result, dict):
                                    return result.get("generated_text", "").replace(prompt, "").strip()
                    return ""
    except:
        return ""

async def ask_multiple_ai(user_id, prompt):
    # Use all 7 models, but limit to first 5 that respond
    tasks = [call_hf_model(model, prompt) for model in MODELS]
    responses = await asyncio.gather(*tasks)
    valid = [r for r in responses if r and len(r) > 10]
    if not valid:
        return "❌ All AI models failed. Please try again later."
    # If only one valid, return it
    if len(valid) == 1:
        return valid[0]
    # Use first 3 valid responses for synthesis (or all if less than 3)
    selected = valid[:3] if len(valid) >= 3 else valid
    # Synthesize using deepseek
    combined = "I got multiple responses. Synthesize them into one answer:\n\n"
    for i, resp in enumerate(selected):
        combined += f"Response {i+1}: {resp}\n"
    final = await call_hf_model("deepseek-ai/deepseek-coder-6.7b-instruct", 
        f"Combine these into a single best answer: {combined}")
    if not final or len(final) < 10:
        # If synthesis fails, return the first valid response
        return valid[0]
    # Add note about models
    final += f"\n\n🤖 (Combined from {len(selected)} AI models)"
    return final

async def ask_single_ai(user_id, prompt):
    return await call_hf_model("deepseek-ai/deepseek-coder-6.7b-instruct", prompt)

def run_code(language, code):
    try:
        payload = {"language": language, "source": code}
        response = requests.post(PISTON_API_URL, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            output = result.get("output", "").strip()
            if not output:
                output = "✅ Code ran successfully (no output)."
            return output
        else:
            return f"⚠️ Execution error: {response.text}"
    except Exception as e:
        return f"❌ Execution failed: {str(e)}"

# ---------- KEYBOARDS ----------
MAIN_MENU = [
    [InlineKeyboardButton("💬 Ask AI (Single)", callback_data="ask_ai")],
    [InlineKeyboardButton("🚀 Super AI (Multi)", callback_data="super_ai")],
    [InlineKeyboardButton("🔍 Explain Code", callback_data="explain_code")],
    [InlineKeyboardButton("▶️ Run Code", callback_data="run_code")],
    [InlineKeyboardButton("🎨 Format Code", callback_data="format_code")],
    [InlineKeyboardButton("🔄 Convert Code", callback_data="convert_code")],
    [InlineKeyboardButton("🧐 Review Code", callback_data="review_code")],
    [InlineKeyboardButton("📊 Complexity", callback_data="complexity")],
    [InlineKeyboardButton("🧪 Generate Tests", callback_data="generate_tests")],
    [InlineKeyboardButton("📝 Generate Docs", callback_data="generate_docs")],
    [InlineKeyboardButton("💾 Save Snippet", callback_data="save_snippet")],
    [InlineKeyboardButton("📂 My Snippets", callback_data="my_snippets")],
    [InlineKeyboardButton("📤 Upload File", callback_data="upload_file")],
    [InlineKeyboardButton("📸 Upload Image", callback_data="upload_image")],
    [InlineKeyboardButton("🏆 Daily Challenge", callback_data="daily_challenge")],
    [InlineKeyboardButton("📊 Leaderboard", callback_data="leaderboard")],
    [InlineKeyboardButton("📚 My History", callback_data="my_history")],
    [InlineKeyboardButton("📌 Bookmarks", callback_data="my_bookmarks")],
    [InlineKeyboardButton("🏅 My Badges", callback_data="my_badges")],
    [InlineKeyboardButton("📈 Analytics", callback_data="analytics")],
    [InlineKeyboardButton("📋 Export Data", callback_data="export")],
    [InlineKeyboardButton("🗑️ Clear History", callback_data="clear_history")],
    [InlineKeyboardButton("ℹ️ About / Help", callback_data="about")],
]

ADMIN_MENU = [
    [InlineKeyboardButton("👥 Users List", callback_data="admin_users")],
    [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
    [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
    [InlineKeyboardButton("🏆 Set Challenge", callback_data="admin_set_challenge")],
    [InlineKeyboardButton("⚙️ Set Daily Limit", callback_data="admin_set_limit")],
    [InlineKeyboardButton("🗑️ Clear User History", callback_data="admin_clear_user")],
    [InlineKeyboardButton("🔙 Back to Main", callback_data="main_menu")],
]

BACK_MENU = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]

# ---------- BOT HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, is_new=True)

async def show_main_menu(update: Update, is_new=False):
    user_id = update.effective_user.id
    menu = MAIN_MENU.copy()
    if user_id == OWNER_ID:
        menu.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")])

    text = "🤖 **Universal AI Coding Bot**\n\n"
    if user_id == OWNER_ID:
        text += "👑 Owner Access – Unlimited\n"
    else:
        text += f"📝 Daily limit: {DAILY_LIMIT}\n"
    text += "\nUpload files, images, solve challenges, earn badges & more!\n🚀 Use **Super AI** for best results with 7 models."

    if is_new and hasattr(update, 'message'):
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(menu), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(menu), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "main_menu":
        await show_main_menu(update)
        return

    def set_state(state, prompt_text):
        context.user_data['state'] = state
        return query.edit_message_text(prompt_text, reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")

    if data == "ask_ai":
        context.user_data['multi'] = False
        await set_state(ASK_AI, "💬 **Ask AI (Single)**\n\nType your coding question below.")
    elif data == "super_ai":
        context.user_data['multi'] = True
        await set_state(ASK_AI, "🚀 **Super AI (7 Models)**\n\nType your question. I'll combine responses from multiple AI models.\n\nModels: DeepSeek, CodeLlama, StarCoder, Phi, Flan-T5, Mistral, Zephyr")
    elif data == "explain_code":
        await set_state(WAIT_EXPLAIN, "🔍 **Explain Code**\n\nPaste your code. I'll explain line-by-line.")
    elif data == "format_code":
        await set_state(WAIT_FORMAT, "🎨 **Format Code**\n\nPaste your code. I'll format it properly.")
    elif data == "convert_code":
        await set_state(WAIT_CONVERT, "🔄 **Convert Code**\n\nPaste your code and specify target language.\nExample: 'Python to Java' then the code.")
    elif data == "review_code":
        await set_state(WAIT_REVIEW, "🧐 **Review Code**\n\nPaste your code. I'll review for bugs and improvements.")
    elif data == "complexity":
        await set_state(WAIT_COMPLEXITY, "📊 **Analyze Complexity**\n\nPaste your code. I'll analyze time/space complexity.")
    elif data == "generate_tests":
        await set_state(WAIT_TESTS, "🧪 **Generate Tests**\n\nPaste your function/class. I'll generate unit tests.")
    elif data == "generate_docs":
        await set_state(WAIT_DOCS, "📝 **Generate Docs**\n\nPaste your code. I'll generate docstrings.")
    elif data == "run_code":
        await set_state(WAIT_RUN, "▶️ **Run Code**\n\nPaste your code. Supported: Python, Java, C++, JS, Go, Rust.")
    elif data == "save_snippet":
        context.user_data['state'] = WAIT_SAVE_NAME
        context.user_data['saving_code'] = None
        await query.edit_message_text("💾 **Save Snippet**\n\nSend me the code you want to save.\nAfter that, I'll ask for a name.", reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "my_snippets":
        snippets = get_snippets(user_id)
        if not snippets:
            await query.edit_message_text("📂 **My Snippets**\n\nYou have no saved snippets.", reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
            return
        keyboard = []
        for name in snippets.keys():
            keyboard.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"snippet_{name}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("📂 **My Snippets**\n\nSelect a snippet:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data.startswith("snippet_"):
        name = data[8:]
        snippets = get_snippets(user_id)
        code = snippets.get(name)
        if code:
            await query.edit_message_text(
                f"📄 **{name}**\n\n```\n{code}\n```",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{name}")],
                    [InlineKeyboardButton("🔙 Back to Snippets", callback_data="my_snippets")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
                ]),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Snippet not found.", reply_markup=InlineKeyboardMarkup(BACK_MENU))
    elif data.startswith("delete_"):
        name = data[7:]
        if delete_snippet(user_id, name):
            await query.edit_message_text(f"✅ Snippet '{name}' deleted.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="my_snippets")]]))
        else:
            await query.edit_message_text("❌ Could not delete.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="my_snippets")]]))
    elif data == "upload_file":
        context.user_data['state'] = 'waiting_file'
        await query.edit_message_text("📤 **Upload File**\n\nSend me any file (document, PDF, zip, etc.). I'll store it and can analyze text content.", reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "upload_image":
        context.user_data['state'] = 'waiting_image'
        await query.edit_message_text("📸 **Upload Image**\n\nSend me an image. I'll generate a caption for it.", reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "daily_challenge":
        challenge = get_current_challenge()
        if not challenge:
            text = "🏆 **No active challenge today.** Check back later."
        else:
            text = f"🏆 **Daily Challenge**\n\n{challenge['question']}\n\nSubmit your answer using /submit <answer>"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "leaderboard":
        lb = get_leaderboard()
        if not lb:
            text = "📊 **Leaderboard**\n\nNo one has solved any challenge yet."
        else:
            text = "📊 **Leaderboard**\n\n"
            for i, (uid, data) in enumerate(lb[:10]):
                text += f"{i+1}. User {uid[:6]} – {data['points']} pts ({data['solved']} solved)\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "my_badges":
        badges = get_badges(user_id)
        if not badges:
            text = "🏅 **My Badges**\n\nYou have no badges yet. Keep using the bot to earn badges!"
        else:
            text = "🏅 **My Badges**\n\n" + "\n".join(badges)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "analytics":
        analytics = get_analytics(user_id, 7)
        if not analytics:
            text = "📈 **Analytics**\n\nNo data available yet."
        else:
            text = "📈 **Analytics (Last 7 Days)**\n\n"
            for day, vals in sorted(analytics.items(), reverse=True):
                text += f"📅 {day}: Earned {vals.get('earnings', 0)} PKR, Queries {vals.get('queries', 0)}, Snippets {vals.get('snippets', 0)}\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "export":
        data = export_user_data(user_id)
        file_path = f"export_{user_id}.json"
        with open(file_path, "w") as f:
            f.write(data)
        await query.message.reply_document(open(file_path, "rb"), caption="📋 Your exported data.")
        os.remove(file_path)
    elif data == "my_history":
        history = get_user_history(user_id)
        if not history:
            text = "📭 Aapki koi history nahi hai."
        else:
            text = "📚 **Your Conversation History**\n\n" + format_history(history)
        if len(text) > 4000:
            await query.message.reply_text(text[:4000])
            await query.message.reply_text("🔙 Back", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
    elif data == "my_bookmarks":
        bookmarks = get_bookmarks(user_id)
        if not bookmarks:
            await query.edit_message_text("📌 **Bookmarks**\n\nYou have no bookmarks.", reply_markup=InlineKeyboardMarkup(BACK_MENU), parse_mode="Markdown")
            return
        text = "📌 **Your Bookmarks**\n\n"
        for i, bm in enumerate(bookmarks):
            text += f"{i+1}. {bm['query'][:40]}...\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]), parse_mode="Markdown")
    elif data == "clear_history":
        await query.edit_message_text(
            "🗑️ **Clear History**\n\nAre you sure?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes", callback_data="clear_confirm")],
                [InlineKeyboardButton("❌ No", callback_data="main_menu")]
            ]),
            parse_mode="Markdown"
        )
    elif data == "clear_confirm":
        clear_user_history(user_id)
        await query.edit_message_text("✅ History cleared.", reply_markup=InlineKeyboardMarkup(BACK_MENU))
    elif data == "about":
        await query.edit_message_text(
            "ℹ️ **Universal AI Coding Bot**\n\n"
            "• All languages\n• Explain, Run, Format, Convert\n• Review, Complexity, Tests, Docs\n• Snippets, Bookmarks\n• File & Image upload\n• Daily challenges & Leaderboard\n• Badges & Achievements\n• Earning Analytics\n• Export Data\n• 🚀 Super AI with 7 models\n"
            f"• Owner: @AF3463\n• Daily limit: {DAILY_LIMIT}\n• Unlimited for owner\n\n"
            "Commands: /start - Main menu, /cancel - Cancel",
            reply_markup=InlineKeyboardMarkup(BACK_MENU),
            parse_mode="Markdown"
        )
    elif data == "admin_panel":
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ Access Denied!")
            return
        await query.edit_message_text("🔐 **Admin Panel**", reply_markup=InlineKeyboardMarkup(ADMIN_MENU), parse_mode="Markdown")
    elif data == "admin_users":
        if user_id != OWNER_ID:
            return
        history = load_history()
        if not history:
            text = "📭 No users."
        else:
            text = "👥 **Users**\n\n"
            for uid, msgs in history.items():
                text += f"🆔 {uid} – {len(msgs)} msgs\n"
        await query.edit_message_text(text[:4000], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_stats":
        if user_id != OWNER_ID:
            return
        total_users, total_messages = get_user_stats()
        total_fb, likes, dislikes = get_feedback_stats()
        lb = get_leaderboard()
        total_challenge_solvers = len(lb)
        await query.edit_message_text(
            f"📊 **Stats**\n\n👥 Users: {total_users}\n💬 Messages: {total_messages}\n📝 Daily Limit: {DAILY_LIMIT}\n👍 Likes: {likes}\n👎 Dislikes: {dislikes}\n🏆 Challenge Solvers: {total_challenge_solvers}\n👑 Owner: {OWNER_ID}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
            parse_mode="Markdown"
        )
    elif data == "admin_broadcast":
        if user_id != OWNER_ID:
            return
        context.user_data['state'] = WAIT_BROADCAST
        await query.edit_message_text("📢 **Broadcast**\n\nSend message to all users.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_set_challenge":
        if user_id != OWNER_ID:
            return
        context.user_data['state'] = WAIT_CHALLENGE_SET
        await query.edit_message_text("🏆 **Set Challenge**\n\nSend the challenge question and answer separated by '|'.\nExample: 'What is 2+2? | 4'", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_set_limit":
        if user_id != OWNER_ID:
            return
        context.user_data['state'] = 'waiting_set_limit'
        await query.edit_message_text("⚙️ **Set Daily Limit**\n\nEnter new limit (number):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")
    elif data == "admin_clear_user":
        if user_id != OWNER_ID:
            return
        context.user_data['state'] = 'waiting_clear_user'
        await query.edit_message_text("🗑️ **Clear User History**\n\nEnter user ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]), parse_mode="Markdown")

# ---------- MESSAGE HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    msg = update.message

    if not check_spam(user_id):
        await update.message.reply_text("⏳ Please wait a few seconds before sending another message.")
        return

    async def process_ai_with_options(prompt, hint=""):
        if not check_limit(user_id):
            await update.message.reply_text(f"❌ Daily limit {DAILY_LIMIT} reached.")
            return
        multi = context.user_data.get('multi', False)
        await update.message.reply_text("⏳ Thinking... (using 7 AI models)" if multi else "⏳ Thinking...")
        if multi:
            reply = await ask_multiple_ai(user_id, prompt)
        else:
            reply = await call_hf_model("deepseek-ai/deepseek-coder-6.7b-instruct", prompt)
        if not reply:
            reply = "⚠️ No response from AI. Please try again."
        increment_limit(user_id)
        update_analytics(user_id, "query")
        await update.message.reply_text(reply[:4000])
        context.user_data['last_query'] = prompt[:100]
        context.user_data['last_response'] = reply[:200]
        await update.message.reply_text(
            "💡 Save this as bookmark?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📌 Save", callback_data="bookmark_yes"),
                 InlineKeyboardButton("🚫 No", callback_data="bookmark_no")]
            ])
        )
        context.user_data['state'] = None
        await update.message.reply_text("🔙 Back", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]))

    if state == 'waiting_file' and msg.document:
        file = msg.document
        file_obj = await context.bot.get_file(file.file_id)
        file_path = os.path.join(FILES_DIR, f"{user_id}_{file.file_name}")
        await file_obj.download_to_drive(file_path)
        await update.message.reply_text(f"📤 **File uploaded!**\n\nName: {file.file_name}\nSize: {file.file_size} bytes")
        ext = file.file_name.split('.')[-1].lower()
        if ext in ['txt', 'py', 'java', 'cpp', 'c', 'js', 'go', 'rs', 'html', 'css', 'json', 'xml', 'md', 'csv']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()[:2000]
            await update.message.reply_text(f"📄 **File content:**\n\n```\n{content}\n```")
        context.user_data['state'] = None
    elif state == 'waiting_image' and msg.photo:
        photo = msg.photo[-1]
        file_obj = await context.bot.get_file(photo.file_id)
        file_path = os.path.join(FILES_DIR, f"{user_id}_image_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        await file_obj.download_to_drive(file_path)
        await update.message.reply_text("📸 **Image received!**")
        # Simple caption generation (could be improved)
        caption = await call_hf_model("Salesforce/blip-image-captioning-base", "")
        await update.message.reply_text(f"🖼️ **Caption:**\n\n{caption if caption else 'Image received successfully.'}")
        context.user_data['state'] = None
    elif state == ASK_AI:
        await process_ai_with_options(msg.text)
    elif state == WAIT_EXPLAIN:
        await process_ai_with_options(f"Explain the following code line by line:\n\n{msg.text}")
    elif state == WAIT_FORMAT:
        await process_ai_with_options(f"Format the following code properly with correct indentation and style:\n\n{msg.text}")
    elif state == WAIT_CONVERT:
        if "to" in msg.text.lower():
            parts = msg.text.split("to", 1)
            lang = parts[0].strip().split()[-1]
            code = parts[1].strip()
            await process_ai_with_options(f"Convert the following code to {lang}:\n\n{code}")
        else:
            context.user_data['convert_code'] = msg.text
            await update.message.reply_text("Please specify target language (e.g., Java, Python, C++):", reply_markup=InlineKeyboardMarkup(BACK_MENU))
            context.user_data['state'] = 'waiting_convert_target'
    elif state == 'waiting_convert_target':
        target = msg.text.strip()
        code = context.user_data.get('convert_code', '')
        if code and target:
            await process_ai_with_options(f"Convert the following code to {target}:\n\n{code}")
            context.user_data['convert_code'] = None
        else:
            await update.message.reply_text("❌ Please send code first, then target language.")
    elif state == WAIT_REVIEW:
        await process_ai_with_options(f"Review the following code for bugs, improvements, and best practices:\n\n{msg.text}")
    elif state == WAIT_COMPLEXITY:
        await process_ai_with_options(f"Analyze time and space complexity (Big-O) of the following code:\n\n{msg.text}")
    elif state == WAIT_TESTS:
        await process_ai_with_options(f"Generate unit tests for the following code:\n\n{msg.text}")
    elif state == WAIT_DOCS:
        await process_ai_with_options(f"Generate docstrings and comments for the following code:\n\n{msg.text}")
    elif state == WAIT_RUN:
        code = msg.text
        lang = "python"
        if "public class" in code or "System.out.println" in code:
            lang = "java"
        elif "int main" in code or "std::cout" in code:
            lang = "cpp"
        elif "function" in code or "console.log" in code:
            lang = "javascript"
        elif "package main" in code or "fmt.Println" in code:
            lang = "go"
        elif "fn main" in code or "println!" in code:
            lang = "rust"
        await update.message.reply_text(f"⏳ Running code ({lang})...")
        output = run_code(lang, code)
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
        context.user_data['state'] = None
    elif state == WAIT_SAVE_NAME:
        if context.user_data.get('saving_code') is None:
            context.user_data['saving_code'] = msg.text
            await update.message.reply_text("✅ Code received. Now send a name for this snippet.", reply_markup=InlineKeyboardMarkup(BACK_MENU))
        else:
            code = context.user_data['saving_code']
            name = msg.text.strip()
            if not name:
                await update.message.reply_text("❌ Please enter a valid name.")
                return
            save_snippet(user_id, name, code)
            await update.message.reply_text(f"✅ Snippet '{name}' saved!")
            update_analytics(user_id, "snippet")
            context.user_data['saving_code'] = None
            context.user_data['state'] = None
    elif state == WAIT_CHALLENGE_SET:
        if user_id != OWNER_ID:
            return
        try:
            question, answer = msg.text.split('|', 1)
            set_challenge(question.strip(), answer.strip())
            await update.message.reply_text("🏆 **Challenge set successfully!**")
            history = load_history()
            for uid in list(history.keys()):
                try:
                    await context.bot.send_message(int(uid), f"📢 **New Daily Challenge!**\n\n{question.strip()}\n\nSubmit using /submit <answer>", parse_mode="Markdown")
                except:
                    pass
        except:
            await update.message.reply_text("❌ Invalid format. Use: 'Question | Answer'")
        context.user_data['state'] = None
    elif state == 'waiting_set_limit':
        if user_id != OWNER_ID:
            return
        try:
            new_limit = int(msg.text)
            global DAILY_LIMIT
            DAILY_LIMIT = new_limit
            await update.message.reply_text(f"✅ Daily limit set to {DAILY_LIMIT}")
        except:
            await update.message.reply_text("❌ Invalid number.")
        context.user_data['state'] = None
    elif state == 'waiting_clear_user':
        if user_id != OWNER_ID:
            return
        try:
            target_id = int(msg.text)
            clear_user_history(target_id)
            await update.message.reply_text(f"✅ User {target_id} history cleared.")
        except:
            await update.message.reply_text("❌ Invalid user ID.")
        context.user_data['state'] = None
    elif state == WAIT_BROADCAST:
        if user_id != OWNER_ID:
            return
        history = load_history()
        user_ids = list(history.keys())
        await update.message.reply_text(f"⏳ Broadcasting to {len(user_ids)} users...")
        sent, failed = 0, 0
        for uid in user_ids:
            try:
                await context.bot.send_message(int(uid), f"📢 **Broadcast from Owner:**\n\n{msg.text}", parse_mode="Markdown")
                sent += 1
            except:
                failed += 1
        await update.message.reply_text(f"✅ Broadcast complete!\nSent: {sent}\nFailed: {failed}")
        context.user_data['state'] = None
    else:
        await update.message.reply_text("Please use the buttons below.", reply_markup=InlineKeyboardMarkup(MAIN_MENU))

# ---------- COMMANDS ----------
async def submit_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /submit <answer>")
        return
    answer = ' '.join(context.args)
    result = submit_challenge(user_id, answer)
    await update.message.reply_text(result)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Action cancelled.", reply_markup=InlineKeyboardMarkup(MAIN_MENU))

# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("submit", submit_challenge))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    print("🚀 Advanced AI Coding Bot is running with 7 models...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
