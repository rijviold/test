import os
import json
import re
import imaplib
import email
from datetime import datetime
import telebot
import pandas as pd
from telebot.types import ReplyKeyboardMarkup, BotCommand

# Set your new Telegram bot token in the BOT_TOKEN environment variable.
# Do not reuse the token pasted into chat; regenerate it with @BotFather first.
TOKEN = os.getenv("BOT_TOKEN", "8688332157:AAFQ5uFC8s9W4E8wsg65OIILTp8W4XLepUY")
ADMIN_IDS = ["8907546487"]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
DB_FILE = "database.json"
TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

try: BOT_USERNAME = bot.get_me().username
except: BOT_USERNAME = "tppshopbot"

state = {}

db = {
    "users": {}, "products": {}, "deposits": [], "orders": [],
    "usedTxnIds": [], "pendingOrders": [], "validMails": [], "vouchers": {},
    "settings": {
        "bot_name": "TPP Shop Bot",
        "welcome_msg": "👋 <b>Welcome to {bot_name}</b>\n━━━━━━━━━━━━━━━━━━\n💰 Balance: <b>{bal:.2f} BDT</b>\n━━━━━━━━━━━━━━━━━━\n📌 <i>নিচের মেনু থেকে আপনার প্রয়োজনীয় সার্ভিসটি বেছে নিন 👇</i>",
        "paymentMethods": {
            "bkash": {"name": "Bkash", "number": "01833878871", "style": "success"},
            "nagad": {"name": "Nagad", "number": "017XXXXXXXX", "style": "primary"},
            "rocket": {"name": "Rocket", "number": "019XXXXXXXX", "style": "danger"},
            "binance": {"name": "Binance", "number": "Not Set", "style": "primary"}
        },
        "dollarRate": 120, "supportLink": "http://t.me/rifat_raisul",
        "adminIds": ADMIN_IDS, "isBotAsleep": False,
        "force_channels": {},
        "resellers": []
    }
}

def load_db():
    global db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, dict) and isinstance(db.get(k), dict):
                        db[k].update(v)
                    else:
                        db[k] = v
        except Exception as e:
            print(f"⚠️ Error loading database: {e}")

def save_db():
    try:
        temp_file = DB_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
        if os.path.exists(DB_FILE):
            os.replace(temp_file, DB_FILE)
        else:
            os.rename(temp_file, DB_FILE)
    except Exception as e:
        print(f"⚠️ Error saving database: {e}")

load_db()

def is_admin(user_id):
    return str(user_id) in db["settings"]["adminIds"]

def ensure_user(message):
    uid = str(message.chat.id)
    if uid not in db["users"]:
        db["users"][uid] = {"id": uid, "name": message.from_user.first_name or "User", "username": message.from_user.username or "none", "balance": 0.0, "joined": datetime.now().isoformat(), "orders": 0, "banned": False}
        save_db()
    return db["users"][uid]

def check_ban(chat_id):
    if str(chat_id) in db["users"] and db["users"][str(chat_id)].get("banned"):
        bot.send_message(chat_id, '⛔ <b>আপনি এই বট থেকে নিষিদ্ধ (Banned) হয়েছেন।</b>')
        return True
    return False

def user_menu(chat_id):
    keyboard = [
        [{"text": "Buy Products"}],
        [{"text": "My Profile"}, {"text": "Deposit"}],
        [{"text": "Get Code"}, {"text": "Support"}],
        [{"text": "Tutorial"}]
    ]
    if is_admin(chat_id): keyboard.append([{"text": "Admin Panel"}])
    return json.dumps({"keyboard": keyboard, "resize_keyboard": True})

def admin_menu():
    keyboard = [
        [{"text": "Product Management"}, {"text": "Add Stock"}],
        [{"text": "Live Stock"}, {"text": "User Management"}],
        [{"text": "Deposit Requests"}, {"text": "Deposit History"}],
        [{"text": "Broadcast"}, {"text": "Voucher Management"}],
        [{"text": "Force Join Setup"}, {"text": "Support Setup"}],
        [{"text": "Admin Management"}, {"text": "Payment Settings"}],
        [{"text": "Reseller Management"}, {"text": "Tutorial Setup"}],
        [{"text": "Download Database"}],
        [{"text": "User Menu"}]
    ]
    return json.dumps({"keyboard": keyboard, "resize_keyboard": True})

CATEGORIES = {
    "hotmail": {"name": "Hotmail"},
    "outlook": {"name": "Outlook"},
    "froutlook": {"name": "FR_Outlook"},
    "vpn": {"name": "VPN"},
    "proxy": {"name": "Proxy~IP"}
}

def get_category_keyboard(prefix, exclude=None):
    if exclude is None: exclude = []
    kb, row = [], []
    for cat_id, data in CATEGORIES.items():
        if cat_id in exclude: continue
        row.append({"text": data["name"], "callback_data": f"{prefix}_{cat_id}"})
        if len(row) == 2: kb.append(row); row = []
    if row: kb.append(row)
    return kb

def complete_purchase(chat_id, prod_name, qty, call_id=None):
    if prod_name not in db["products"]:
        if call_id: bot.answer_callback_query(call_id, "প্রোডাক্ট পাওয়া যায়নি!", show_alert=True)
        else: bot.send_message(chat_id, "❌ প্রোডাক্ট পাওয়া যায়নি!")
        return

    product = db["products"][prod_name]
    user = db["users"][chat_id]
    cat_id = product.get("category", "")

    is_reseller = chat_id in db["settings"].get("resellers", [])
    actual_price = product.get("reseller_price", product["price"]) if is_reseller else product["price"]

    if cat_id != "vpn" and len(product.get("stock", [])) < qty:
        msg = f"স্টক অপর্যাপ্ত! স্টকে আছে: {len(product.get('stock', []))} টি"
        if call_id: bot.answer_callback_query(call_id, msg, show_alert=True)
        else: bot.send_message(chat_id, f"❌ {msg}")
        return

    total_price = actual_price * qty
    if user["balance"] < total_price:
        msg = f"ব্যালেন্স অপর্যাপ্ত! আপনার ব্যালেন্স: {user['balance']} BDT"
        if call_id: bot.answer_callback_query(call_id, msg, show_alert=True)
        else: bot.send_message(chat_id, f"❌ {msg}")
        return

    user["balance"] -= total_price
    user["orders"] += qty

    if call_id: bot.answer_callback_query(call_id, "প্রসেস হচ্ছে...")

    if cat_id == "vpn":
        order_id = int(datetime.now().timestamp() * 1000)
        db["pendingOrders"].append({"id": order_id, "userId": chat_id, "product": prod_name, "price": product["price"], "time": datetime.now().isoformat()}); save_db()
        bot.send_message(chat_id, '⏳ <b>অর্ডার রিকোয়েস্ট পাঠানো হয়েছে</b>\nএডমিন খুব শীঘ্রই আপনার সাথে যোগাযোগ করবেন।')
        admin_msg = f'📦 <b>NEW MANUAL ORDER (VPN)</b>\nUser: <b>{user["name"]}</b>\nPackage: <b>{prod_name}</b>\nPrice: {actual_price}৳'
        markup = json.dumps({"inline_keyboard": [[{"text": "Approve", "callback_data": f"vpnapp_{order_id}"}, {"text": "Reject", "callback_data": f"vpnrej_{order_id}"}]]})
        for admin_id in db["settings"]["adminIds"]:
            try: bot.send_message(admin_id, admin_msg, reply_markup=markup)
            except: pass
    else:
        items = [product["stock"].pop(0) for _ in range(qty)]
        db["orders"].append({"userId": chat_id, "product": prod_name, "item": items[0] if qty == 1 else items, "price": total_price, "time": datetime.now().isoformat()}); save_db()

        kb = json.dumps({"inline_keyboard": [[{"text": "আবার কিনুন", "callback_data": f"buyagain_{cat_id}"}]]})

        if qty == 1:
            item = items[0].rstrip("|")
            email_only = re.split(r'[|:]', item)[0]
            msg = f'✅ <b>অর্ডার সম্পন্ন</b>\n\n✉️ <b>মেইল:</b>\n<code>{email_only}</code>\n\n✏️ <b>ডিটেইলস:</b>\n<code>{item}</code>'
            bot.send_message(chat_id, msg, reply_markup=kb)
        else:
            file_path = os.path.join(TMP_DIR, f"order_{chat_id}_{int(datetime.now().timestamp())}.xlsx")
            pd.DataFrame(items, columns=["Accounts"]).to_excel(file_path, index=False, header=False)
            with open(file_path, "rb") as f:
                bot.send_document(chat_id, f, caption=f'✅ <b>বাল্ক অর্ডার সম্পন্ন ({qty} pcs)</b>', reply_markup=kb)
            os.remove(file_path)

@bot.message_handler(commands=['start'])
def start_handler(message):
    chat_id = str(message.chat.id)
    if db["settings"]["isBotAsleep"]: return
    ensure_user(message)
    state[chat_id] = None
    if check_ban(chat_id): return

    u = db["users"][chat_id]
    msg = db["settings"]["welcome_msg"].format(bot_name=db["settings"]["bot_name"], bal=u["balance"])
    bot.send_message(chat_id, msg, reply_markup=user_menu(chat_id))

def fetch_hotmail_code(email_addr, password):
    try:
        mail = imaplib.IMAP4_SSL("outlook.office365.com", 993)
        mail.login(email_addr, password)
        mail.select("inbox")

        status, messages = mail.search(None, "ALL")
        if status != "OK" or not messages[0].split():
            mail.select("Junk")
            status, messages = mail.search(None, "ALL")
            if status != "OK" or not messages[0].split():
                mail.logout()
                return "❌ ইনবক্সে কোনো মেইল পাওয়া যায়নি।"

        latest_num = messages[0].split()[-1]
        status, msg_data = mail.fetch(latest_num, "(RFC822)")
        if status != "OK":
            mail.logout()
            return "❌ মেইল ফেচ করা যায়নি।"

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if "attachment" not in str(part.get("Content-Disposition")):
                            try:
                                payload = part.get_payload(decode=True)
                                if payload: body += payload.decode("utf-8", errors="ignore")
                            except: pass
                else:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload: body = payload.decode("utf-8", errors="ignore")
                    except: pass

                code_match = re.search(r'\b(\d{4,8})\b', body)
                if code_match:
                    mail.logout()
                    return f"✅ <b>ভেরিফিকেশন কোড:</b>\n👉 <code>{code_match.group(1)}</code> 👈"
        mail.logout()
        return "❌ ওটিপি কোড খুঁজে পাওয়া যায়নি।"
    except Exception as e:
        return f"❌ IMAP কানেকশন ফেইল্ড!\nত্রুটি: {str(e)}"

@bot.message_handler(func=lambda msg: True, content_types=['text', 'document'])
def main_handler(message):
    chat_id = str(message.chat.id)
    text = message.text or message.caption or ""

    if db["settings"]["isBotAsleep"]: return
    if check_ban(chat_id): return
    ensure_user(message)

    if chat_id in state and state[chat_id] is not None:
        handle_state(message, chat_id, text)
        return

    if text == "My Profile":
        u = db["users"][chat_id]
        bot.send_message(chat_id, f'👤 <b>My Profile</b>\n\nName: <b>{u["name"]}</b>\nBalance: <b>{u["balance"]:.2f} BDT</b>\nOrders: <b>{u["orders"]}</b>')
    elif text == "Buy Products":
        bot.send_message(chat_id, '📦 <b>প্যাকেজ সিলেক্ট করুন</b>', reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("cat")}))
    elif text == "Deposit":
        keyboard = [[{"text": m_data["name"], "callback_data": f"deposit_{m_id}"}] for m_id, m_data in db["settings"]["paymentMethods"].items()]
        bot.send_message(chat_id, '💳 <b>পেমেন্ট মেথড সিলেক্ট করুন</b>', reply_markup=json.dumps({"inline_keyboard": keyboard}))
    elif text == "Get Code":
        kb = json.dumps({"inline_keyboard": [[{"text": "Hotmail Code", "callback_data": "menu_hotmail_code"}], [{"text": "2FA Code", "callback_data": "menu_2fa_code"}]]})
        bot.send_message(chat_id, '📌 <b>সার্ভিস সিলেক্ট করুন:</b>', reply_markup=kb)
    elif text == "Support":
        state[chat_id] = {"type": "wait_support_msg"}
        bot.send_message(chat_id, '💬 <b>আপনার সমস্যা বা প্রশ্ন লিখুন:</b>')
    elif text == "Admin Panel" and is_admin(chat_id):
        bot.send_message(chat_id, '🛡️ <b>Admin Panel</b>', reply_markup=admin_menu())
    elif text == "Download Database" and is_admin(chat_id):
        save_db()
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                bot.send_document(chat_id, f, caption='✅ <b>database.json ফাইলটি ডাউনলোড করা হলো।</b>')
        else:
            bot.send_message(chat_id, '❌ database.json ফাইলটি পাওয়া যায়নি!')
    elif text == "Product Management" and is_admin(chat_id):
        kb = json.dumps({"inline_keyboard": [[{"text": "Add Product", "callback_data": "admin_pm_add"}], [{"text": "Delete Product", "callback_data": "admin_pm_del_prod"}]]})
        bot.send_message(chat_id, '⚙️ <b>Product Management:</b>', reply_markup=kb)
    elif text == "Add Stock" and is_admin(chat_id):
        bot.send_message(chat_id, '📦 <b>স্টক অ্যাড করতে ক্যাটাগরি সিলেক্ট করুন:</b>', reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("admin_stock", exclude=["vpn"])}))
    elif text == "User Menu":
        bot.send_message(chat_id, '✅ <b>মূল মেনু:</b>', reply_markup=user_menu(chat_id))

def handle_state(message, chat_id, text):
    st = state[chat_id]

    if st["type"] == "wait_support_msg":
        for admin_id in db["settings"]["adminIds"]:
            try: bot.send_message(admin_id, f'💬 <b>Support Request from {chat_id}:</b>\n\n{text}')
            except: pass
        bot.send_message(chat_id, '✅ আপনার মেসেজটি পাঠানো হয়েছে।')
        state[chat_id] = None

    elif st["type"] == "wait_hotmail_input":
        parts = re.split(r'[|:]', text.strip())
        if len(parts) < 2: return bot.send_message(chat_id, '❌ ফরম্যাট: <code>email|password</code>')
        bot.send_message(chat_id, '⏳ ইনবক্স চেক করা হচ্ছে...')
        bot.send_message(chat_id, fetch_hotmail_code(parts[0].strip(), parts[1].strip()))
        state[chat_id] = None

    elif st["type"] == "add_product_name":
        state[chat_id] = {"type": "add_product_price", "cat": st["cat"], "name": text.strip()}
        bot.send_message(chat_id, 'Normal Price দিন:')
    elif st["type"] == "add_product_price":
        try: price = float(text.strip())
        except: return bot.send_message(chat_id, '❌ সঠিক প্রাইস দিন:')
        state[chat_id] = {"type": "add_product_reseller_price", "cat": st["cat"], "name": st["name"], "price": price}
        bot.send_message(chat_id, 'Reseller Price দিন:')
    elif st["type"] == "add_product_reseller_price":
        try: reseller_price = float(text.strip())
        except: return bot.send_message(chat_id, '❌ সঠিক প্রাইস দিন:')
        db["products"][st["name"]] = {"name": st["name"], "category": st["cat"], "price": st["price"], "reseller_price": reseller_price, "stock": []}
        save_db()
        bot.send_message(chat_id, '✅ প্রোডাক্ট যোগ করা হয়েছে!')
        state[chat_id] = None

    elif st["type"] == "stockUpload" and is_admin(chat_id) and message.document:
        try:
            file_path = os.path.join(TMP_DIR, message.document.file_name)
            with open(file_path, "wb") as f: f.write(bot.download_file(bot.get_file(message.document.file_id).file_path))
            new_stock = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip(): new_stock.append(line.strip())
            if new_stock:
                db["products"][st["product"]]["stock"].extend(new_stock); save_db()
                bot.send_message(chat_id, f'✅ Stock Added ({len(new_stock)} pcs).')
            if os.path.exists(file_path): os.remove(file_path)
        except Exception as e: bot.send_message(chat_id, f'❌ Error: {e}')
        state[chat_id] = None

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id, data = str(call.message.chat.id), call.data

    if data == "menu_hotmail_code":
        state[chat_id] = {"type": "wait_hotmail_input"}
        bot.send_message(chat_id, '✉️ <b>হটমেইল দিন:</b>\n<code>email|password</code>')
    elif data == "admin_pm_add" and is_admin(chat_id):
        bot.edit_message_text('📦 ক্যাটাগরি সিলেক্ট করুন:', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("admin_add")}))
    elif data.startswith("admin_add_") and is_admin(chat_id):
        state[chat_id] = {"type": "add_product_name", "cat": data.replace("admin_add_", "")}
        bot.send_message(chat_id, 'প্রোডাক্টের নাম লিখুন:')
    elif data.startswith("admin_stock_") and is_admin(chat_id):
        cat_id = data.replace("admin_stock_", "")
        products = [p for p in db["products"].values() if p.get("category") == cat_id]
        if not products: return bot.answer_callback_query(call.id, "কোনো প্রোডাক্ট নেই!", show_alert=True)
        bot.edit_message_text('📦 প্রোডাক্ট সিলেক্ট করুন:', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": [[{"text": p["name"], "callback_data": f"stkupload_{p['name']}"}] for p in products]}))
    elif data.startswith("stkupload_") and is_admin(chat_id):
        state[chat_id] = {"type": "stockUpload", "product": data.replace("stkupload_", "")}
        bot.send_message(chat_id, '📦 স্টক ফাইল (.txt) আপলোড করুন:')
    elif data.startswith("cat_"):
        cat_id = data.replace("cat_", "")
        products = [p for p in db["products"].values() if p.get("category") == cat_id]
        if not products: return bot.answer_callback_query(call.id, "কোনো প্রোডাক্ট নেই!", show_alert=True)
        is_reseller = chat_id in db["settings"].get("resellers", [])
        kb = []
        for p in products:
            price = p.get("reseller_price", p["price"]) if is_reseller else p["price"]
            kb.append([{"text": f"{p['name']} | {price}৳", "callback_data": f"buy_{p['name']}"}])
        bot.edit_message_text('📦 প্রোডাক্টস:', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))
    elif data.startswith("buy_"):
        complete_purchase(chat_id, data.replace("buy_", ""), 1, call.id)

print("🚀 TPP Shop Bot is Running!")
bot.set_my_commands([BotCommand("start", "Start")])
bot.infinity_polling(skip_pending=True)
