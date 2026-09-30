import os
import json
import re
import pyotp
import threading
import time
import requests
from datetime import datetime
import telebot
import pandas as pd
from telebot.types import ReplyKeyboardMarkup, BotCommand

# ====== BOT CREDENTIALS ======
TOKEN = "8285219805:AAECK_oYoxzzxwlOz1mKDcIPtSpy3LxcSGw"
ADMIN_IDS = ["6034658132"]

# ====== 3RD PARTY API SETTINGS ======
API_PANEL_URL = "https://vpn.sajeebtechonline.top/api.php"
API_PANEL_KEY = "YOUR_API_KEY" # এখানে আপনার API KEY দিবেন

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
DB_FILE = "database.json"
TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

try: BOT_USERNAME = bot.get_me().username
except: BOT_USERNAME = "tppshopbot"

state = {}

# ====== 100% NEW PREMIUM EMOJI IDs ======
EMOJI = {
    "success": "6266827283135207188",   
    "danger": "6267000941547885720",    
    "primary": "5465205795211721259",   
    "money": "6267068789146260253",     
    "mail": "5307843983102204243",      
    "2fa": "5195240845523044099",       
    "buy": "5440841102871517055",       
    "dashboard": "5203993413346680064", 
    "support": "5237988788164107500",   
    "box": "6266794310671275367",       
    "stock": "6267152480878990865",     
    "person": "5465553786346945697",    
    "sparkle": "6266995104687330978",   
    "banned": "6264989883241076562",    
    "pending": "6267144651153609853",   
    "heart": "6267032805910254913",     
    "deposit_btn": "6156613307013797495", 
    "shield": "6267128480601741166",    
    "bell": "5465400086647290249",      
    "link": "5336972142066047577",      
    "clock": "5336983442125001376",     
    "pin": "6267172559851099903",       
    "wallet": "5190576863226933563",    
    "pencil": "5193071182663947673",    
    "refresh": "5462915533965901712",   
    "dev_boss": "6267019543051244106",  
    "admin_badge": "6267097569722111582",
    "off_badge": "6266797059450347770"  
}

CATEGORIES = {
    "hotmail": {"name": "Hotmail", "emoji": "6237502556403144574", "style": "success"},
    "outlook": {"name": "Outlook", "emoji": "6237502556403144574", "style": "primary"},
    "froutlook": {"name": "FR_Outlook", "emoji": "6237502556403144574", "style": "danger"},
    "vpn": {"name": "VPN", "emoji": "6217595563374810170", "style": "success"},
    "proxy": {"name": "Proxy~IP", "emoji": "6233460206198591939", "style": "primary"}
}

PAYMENT_EMOJIS = {
    "bkash": "6237975191784266396",   
    "nagad": "6235336389647407554",   
    "rocket": "6235655011796261649",  
    "binance": "6237610939902858402"  
}

db = {
    "users": {}, "products": {}, "deposits": [], "orders": [],
    "usedTxnIds": [], "pendingOrders": [], "validMails": [], "vouchers": {},
    "settings": {
        "bot_name": "Proxy Market",
        "welcome_msg": '<tg-emoji emoji-id="6266995104687330978">✨</tg-emoji> <b>Welcome to {bot_name}</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id="6267068789146260253">💰</tg-emoji> Balance: <b>{bal:.2f} BDT / {usdt:.4f} USDT</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id="6267172559851099903">📌</tg-emoji> <i>নিচের মেনু থেকে আপনার প্রয়োজনীয় সার্ভিসটি বেছে নিন 👇</i>',
        "ui_overrides": {},
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
                db.update(json.load(f))
        except: pass

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
    except: pass

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
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["banned"]}">⛔</tg-emoji> <b>আপনি এই বট থেকে নিষিদ্ধ (Banned) হয়েছেন।</b>')
        return True
    return False

# ====== DYNAMIC BUTTON HELPER ======
def btn_prop(orig_text, default_emoji, default_style):
    if "ui_overrides" not in db["settings"]: db["settings"]["ui_overrides"] = {}
    if orig_text not in db["settings"]["ui_overrides"]:
        db["settings"]["ui_overrides"][orig_text] = {"text": orig_text, "emoji": default_emoji, "style": default_style}
        save_db()
    ov = db["settings"]["ui_overrides"][orig_text]
    return {"text": ov.get("text", orig_text), "icon_custom_emoji_id": ov.get("emoji", default_emoji), "style": ov.get("style", default_style)}

# ====== FORCE JOIN HELPERS ======
def get_unjoined_channels(user_id):
    if is_admin(user_id): return []
    unjoined = []
    for cid, data in db["settings"].get("force_channels", {}).items():
        try:
            member = bot.get_chat_member(cid, user_id)
            if member.status not in ['member', 'administrator', 'creator']: unjoined.append(data)
        except: unjoined.append(data)
    return unjoined

def send_force_join_msg(chat_id, unjoined):
    msg = (f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>ACCESS RESTRICTED</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n'
           f'━━━━━━━━━━━━━━━━━━\n'
           f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> প্রিয় ইউজার, আমাদের বটের সম্পূর্ণ সার্ভিস এবং সিকিউর ট্রানজেকশন উপভোগ করতে আমাদের অফিসিয়াল কমিউনিটিতে যুক্ত হওয়া বাধ্যতামূলক।\n\n'
           f'<tg-emoji emoji-id="{EMOJI["bell"]}">🔔</tg-emoji> <b>নিচের চ্যানেলগুলোতে জয়েন করে আপনার এক্সেস আনলক করুন:</b>\n\n'
           f'━━━━━━━━━━━━━━━━━━\n'
           f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <i>জয়েন করা সম্পন্ন হলে নিচের \'Verify Access\' বাটনে ক্লিক করুন।</i>')

    kb = []
    for ch in unjoined: kb.append([{"text": ch["name"], "url": ch["url"], "icon_custom_emoji_id": EMOJI["bell"], "style": "primary"}])
    kb.append([{"text": "Verify Access", "callback_data": "verify_join", "icon_custom_emoji_id": EMOJI["shield"], "style": "success"}])
    bot.send_message(chat_id, msg, reply_markup=json.dumps({"inline_keyboard": kb}))

def user_menu(chat_id):
    keyboard = [
        [btn_prop("Buy Products", EMOJI["buy"], "success")],
        [btn_prop("My Profile", EMOJI["dashboard"], "primary"), btn_prop("Deposit", EMOJI["deposit_btn"], "primary")],
        [btn_prop("Get Code", EMOJI["2fa"], "primary"), btn_prop("Support", EMOJI["support"], "primary")],
        [btn_prop("Tutorial", EMOJI["sparkle"], "success")]
    ]
    if is_admin(chat_id): keyboard.append([btn_prop("Admin Panel", EMOJI["shield"], "primary")])
    return json.dumps({"keyboard": keyboard, "resize_keyboard": True})

def admin_menu():
    keyboard = [
        [btn_prop("Product Management", EMOJI["box"], "primary"), btn_prop("Add Stock", EMOJI["stock"], "success")],
        [btn_prop("Live Stock", EMOJI["dashboard"], "primary"), btn_prop("User Management", EMOJI["person"], "danger")],
        [btn_prop("Deposit Requests", EMOJI["pending"], "success"), btn_prop("Deposit History", EMOJI["primary"], "primary")],
        [btn_prop("Broadcast", EMOJI["bell"], "danger"), btn_prop("Voucher Management", EMOJI["buy"], "success")],
        [btn_prop("Force Join Setup", EMOJI["shield"], "primary"), btn_prop("Support Setup", EMOJI["support"], "danger")],
        [btn_prop("Admin Management", EMOJI["shield"], "primary"), btn_prop("Payment Settings", EMOJI["deposit_btn"], "success")],
        [btn_prop("Reseller Management", EMOJI["dev_boss"], "primary"), btn_prop("Tutorial Setup", EMOJI["link"], "success")],
        [btn_prop("User Menu", EMOJI["success"], "success")]
    ]
    return json.dumps({"keyboard": keyboard, "resize_keyboard": True})

def get_category_keyboard(prefix, exclude=None):
    if exclude is None: exclude = []
    kb, row = [], []
    for cat_id, data in CATEGORIES.items():
        if cat_id in exclude: continue
        row.append({"text": data["name"], "callback_data": f"{prefix}_{cat_id}", "icon_custom_emoji_id": data["emoji"], "style": data["style"]})
        if len(row) == 2: kb.append(row); row = []
    if row: kb.append(row)
    return kb

def get_user_profile(uid):
    u = db["users"].get(uid)
    if not u: return None, None
    status = f'<tg-emoji emoji-id="{EMOJI["banned"]}">⛔</tg-emoji> <b>Banned</b>' if u.get("banned") else f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Active</b>'
    msg = (f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> <b>USER PROFILE</b>\n'
           f'━━━━━━━━━━━━━━━━━━\n'
           f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> Name: <b>{u["name"]}</b>\n'
           f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> ID: <code>{uid}</code>\n'
           f'<tg-emoji emoji-id="{EMOJI["link"]}">🔗</tg-emoji> Username: @{u.get("username", "none")}\n'
           f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> Balance: <b>{u["balance"]} BDT ({u["balance"]/db["settings"]["dollarRate"]:.2f} USD)</b>\n'
           f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> Orders: <b>{u["orders"]}</b>\n'
           f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> Status: {status}\n'
           f'━━━━━━━━━━━━━━━━━━')
    kb = [
        [{"text": "Unban" if u.get("banned") else "Ban", "callback_data": f"toggle_ban_{uid}", "icon_custom_emoji_id": EMOJI["success"] if u.get("banned") else EMOJI["banned"], "style": "success" if u.get("banned") else "danger"}],
        [{"text": "Add Balance", "callback_data": f"addbal_{uid}", "icon_custom_emoji_id": EMOJI["money"], "style": "primary"}, 
         {"text": "Cut Balance", "callback_data": f"cutbal_{uid}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}],
        [{"text": "Send Message", "callback_data": f"sendmsg_{uid}", "icon_custom_emoji_id": EMOJI["mail"], "style": "primary"}]
    ]
    return msg, json.dumps({"inline_keyboard": kb})

def get_dep_req_kb(page=0):
    reqs = [d for d in db["deposits"] if d.get("status") == "pending"]
    if not reqs: return None, None
    per_page = 10
    total_pages = (len(reqs) + per_page - 1) // per_page
    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0
    start, end = page * per_page, page * per_page + per_page
    kb = []
    for dep in reqs[start:end]:
        u_name = db["users"].get(dep["userId"], {}).get("name", "Unknown")
        kb.append([{"text": f"{u_name} | {dep['amount']} BDT ({dep['amount']/db['settings']['dollarRate']:.2f} USD)", "callback_data": f"viewdep_{dep['id']}", "icon_custom_emoji_id": EMOJI["money"], "style": "primary"}])
    nav_row = []
    if page > 0: nav_row.append({"text": "< Prev", "callback_data": f"deppage_{page-1}", "style": "primary"})
    if page < total_pages - 1: nav_row.append({"text": "Next >", "callback_data": f"deppage_{page+1}", "style": "primary"})
    if nav_row: kb.append(nav_row)
    msg = f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>পেন্ডিং ডিপোজিট (Page {page+1}/{total_pages}):</b>'
    return msg, json.dumps({"inline_keyboard": kb})

# ====== PURCHASE EXECUTION HELPER ======
def complete_purchase(chat_id, prod_name, qty, call_id=None):
    if prod_name not in db["products"]:
        msg = f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> প্রোডাক্ট পাওয়া যায়নি!'
        if call_id: bot.answer_callback_query(call_id, "প্রোডাক্ট পাওয়া যায়নি!", show_alert=True)
        else: bot.send_message(chat_id, msg)
        return
        
    product = db["products"][prod_name]
    user = db["users"][chat_id]
    cat_id = product.get("category", "")
    is_api = product.get("is_api", False)
    
    is_reseller = chat_id in db["settings"].get("resellers", [])
    actual_price = product.get("reseller_price", product["price"]) if is_reseller else product["price"]
    
    # Check local stock only if it's NOT an API product
    if not is_api and cat_id != "vpn" and len(product.get("stock", [])) < qty:
        msg = f"স্টক অপর্যাপ্ত! স্টকে আছে: {len(product.get('stock', []))} টি"
        if call_id: bot.answer_callback_query(call_id, msg, show_alert=True)
        else: bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> {msg}')
        return
        
    total_price = actual_price * qty
    if user["balance"] < total_price:
        msg = f"ব্যালেন্স অপর্যাপ্ত! আপনার ব্যালেন্স: {user['balance']} BDT ({user['balance']/db['settings']['dollarRate']:.2f} USD)"
        if call_id: bot.answer_callback_query(call_id, msg, show_alert=True)
        else: bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> {msg}')
        return
        
    user["balance"] -= total_price
    user["orders"] += qty
    
    if call_id: bot.answer_callback_query(call_id, "প্রসেস হচ্ছে...")
    
    curr_time = datetime.now().strftime("%d-%m-%Y , %I:%M %p")
    cat_name = CATEGORIES.get(cat_id, {}).get("name", "Unknown Category")
    
    # --- API DELIVERY LOGIC ---
    if is_api:
        try:
            payload = {"action": "order", "key": API_PANEL_KEY, "service": product["api_service_id"], "quantity": qty}
            res = requests.post(API_PANEL_URL, data=payload).json()
            
            if "order" in res:
                order_id = res["order"]
                db["orders"].append({"userId": chat_id, "product": prod_name, "api_order_id": order_id, "price": total_price, "time": datetime.now().isoformat()})
                save_db()
                
                # Check status right away to fetch details
                st_payload = {"action": "status", "key": API_PANEL_KEY, "order": order_id}
                st_res = requests.post(API_PANEL_URL, data=st_payload).json()
                
                msg = (f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>অর্ডার সম্পন্ন (API)</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <b>Delivery Time:</b> {curr_time}\n'
                       f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>Order ID:</b> <code>{order_id}</code>\n'
                       f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Package:</b> {cat_name} ➔ {prod_name}\n\n')
                
                if "status" in st_res:
                    msg += f"<b>Status:</b> {st_res['status']}\n"
                
                accs = st_res.get("accounts", st_res.get("data", st_res.get("mails", "")))
                if accs:
                    msg += f"\n<tg-emoji emoji-id='{EMOJI['box']}'>📦</tg-emoji> <b>আপনার প্রোডাক্টস:</b>\n<code>{accs}</code>"
                else:
                    msg += f"\n<i>(মেইল সাথে সাথে না আসলে অর্ডারটি API-তে প্রসেসিং এ আছে। বিস্তারিত জানতে অ্যাডমিনের সাথে যোগাযোগ করুন।)</i>"
                
                bot.send_message(chat_id, msg)
            else:
                user["balance"] += total_price
                user["orders"] -= qty
                save_db()
                err = res.get("error", "Unknown API Error")
                bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>API Error:</b> {err}\nআপনার ব্যালেন্স রিফান্ড করা হয়েছে।')
        except Exception as e:
            user["balance"] += total_price
            user["orders"] -= qty
            save_db()
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>API Connection Error:</b> কানেকশন ফেইল্ড!\nআপনার ব্যালেন্স রিফান্ড করা হয়েছে।')
        return

    # --- MANUAL VPN LOGIC ---
    if cat_id == "vpn":
        order_id = int(datetime.now().timestamp() * 1000)
        db["pendingOrders"].append({"id": order_id, "userId": chat_id, "product": prod_name, "price": product["price"], "time": datetime.now().isoformat()}); save_db()
        msg = (f'<tg-emoji emoji-id="{EMOJI["pending"]}">⏳</tg-emoji> <b>অর্ডার রিকোয়েস্ট পাঠানো হয়েছে</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
               f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Package:</b> {cat_name} ➔ {prod_name}\n\n'
               f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <i>ভিপিএন ম্যানুয়াল ডেলিভারি হয়। এডমিন খুব শীঘ্রই আপনার সাথে যোগাযোগ করে সার্ভিস ডেলিভারি সম্পন্ন করবেন।</i>')
        bot.send_message(chat_id, msg)
        admin_msg = (f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>NEW MANUAL ORDER (VPN)</b>\n━━━━━━━━━━━━━━━━━━\n'
                     f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> User: <b>{user["name"]}</b> (<code>{chat_id}</code>)\n'
                     f'<tg-emoji emoji-id="{EMOJI["link"]}">🔗</tg-emoji> Username: @{user.get("username", "none")}\n'
                     f'<tg-emoji emoji-id="{EMOJI["buy"]}">💎</tg-emoji> Package: <b>{prod_name}</b>\n'
                     f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> Price: <b>{actual_price} BDT ({actual_price/db["settings"]["dollarRate"]:.2f} USD)</b>\n━━━━━━━━━━━━━━━━━━\n'
                     f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <i>Please Approve to manually deliver details.</i>')
        markup = json.dumps({"inline_keyboard": [
            [{"text": "Approve", "callback_data": f"vpnapp_{order_id}", "icon_custom_emoji_id": EMOJI["success"], "style": "success"},
             {"text": "Reject", "callback_data": f"vpnrej_{order_id}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}]
        ]})
        for admin_id in db["settings"]["adminIds"]:
            try: bot.send_message(admin_id, admin_msg, reply_markup=markup)
            except: pass
    
    # --- NORMAL LOCAL DELIVERY LOGIC ---
    else:
        items = []
        for _ in range(qty):
            items.append(product["stock"].pop(0))
        db["orders"].append({"userId": chat_id, "product": prod_name, "item": items[0] if qty == 1 else items, "price": total_price, "time": datetime.now().isoformat()}); save_db()
        
        kb = json.dumps({"inline_keyboard": [[{"text": "আবার কিনুন", "callback_data": f"buyagain_{cat_id}", "icon_custom_emoji_id": EMOJI["buy"], "style": "success"}]]})
        
        if qty == 1:
            item = items[0].rstrip("|")
            if cat_id == "proxy":
                parts = item.split(":")
                host, port, u_name, pwd = (parts + ["N/A"] * 4)[:4]
                msg = (f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>অর্ডার সম্পন্ন</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <b>Delivery Time:</b> {curr_time}\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Package:</b> {cat_name} ➔ {prod_name}\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>আপনার প্রক্সি ডিটেইলস:</b>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <b>Host:</b> <code>{host}</code>\n'
                       f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Port:</b> <code>{port}</code>\n'
                       f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> <b>Username:</b> <code>{u_name}</code>\n'
                       f'<tg-emoji emoji-id="{EMOJI["2fa"]}">🔐</tg-emoji> <b>Password:</b> <code>{pwd}</code>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <i>Full Details:</i>\n<code>{item}</code>')
            else:
                email_only = re.split(r'[|:]', item)[0]
                msg = (f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>অর্ডার সম্পন্ন</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <b>Delivery Time:</b> {curr_time}\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Package:</b> {cat_name} ➔ {prod_name}\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>আপনার প্রোডাক্ট:</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>মেইল:</b>\n<code>{email_only}</code>\n<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                       f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>ডিটেইলস</b> <tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji>\n<code>{item}</code>')
            bot.send_message(chat_id, msg, reply_markup=kb)
        else:
            safe_prod_name = re.sub(r'[\\/*?:"<>|]', "_", prod_name)
            file_path = os.path.join(TMP_DIR, f"{safe_prod_name}_{chat_id}_{int(datetime.now().timestamp())}.xlsx")
            
            df = pd.DataFrame(items, columns=["Accounts"])
            df.to_excel(file_path, index=False, header=False)
            
            msg = (f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>বাল্ক অর্ডার সম্পন্ন</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                   f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <b>Delivery Time:</b> {curr_time}\n\n'
                   f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Package:</b> {cat_name} ➔ {prod_name}\n'
                   f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>Quantity:</b> {qty} pcs\n'
                   f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>Total Price:</b> {total_price} BDT ({total_price/db["settings"]["dollarRate"]:.2f} USD)\n\n'
                   f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <i>আপনার অ্যাকাউন্টগুলো নিচের ফাইলে দেওয়া হলো।</i>')
                   
            try:
                with open(file_path, "rb") as f:
                    bot.send_document(chat_id, f, caption=msg, reply_markup=kb)
                os.remove(file_path)
            except Exception as e:
                bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> ফাইল তৈরিতে সমস্যা হয়েছে: {e}')
        
        stock_left = len(product["stock"])
        if stock_left < 5:
            for admin_id in db["settings"]["adminIds"]:
                try: bot.send_message(admin_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>Low Stock Alert!</b>\n<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> প্রোডাক্ট: <b>{prod_name}</b>\n<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> মাত্র {stock_left} টি বাকি আছে!')
                except: pass

@bot.message_handler(commands=['start'])
def start_handler(message):
    chat_id = str(message.chat.id)
    if db["settings"]["isBotAsleep"]: return
    
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None
    is_new_user = chat_id not in db["users"]
    
    ensure_user(message)
    state[chat_id] = None
    if check_ban(chat_id): return
    
    if is_new_user and referrer_id and referrer_id != chat_id and referrer_id in db["users"]:
        db["users"][referrer_id]["balance"] += 0.0
        save_db()
        try: bot.send_message(referrer_id, f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>New Referral Bonus!</b>\nআপনার লিংকে একজন জয়েন করেছে। <tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> 0 BDT ({0/db["settings"]["dollarRate"]:.2f} USD) যোগ হয়েছে।')
        except: pass

    unjoined = get_unjoined_channels(chat_id)
    if unjoined:
        send_force_join_msg(chat_id, unjoined)
        return

    u = db["users"][chat_id]
    usdt_bal = u["balance"] / db["settings"]["dollarRate"]
    
    bot_name = db["settings"].get("bot_name", "New Proxy Market")
    msg_template = db["settings"].get("welcome_msg", "👋 <b>{bot_name}</b>\n\n💰 Balance: <b>{bal:.2f} BDT / {usdt:.4f} USDT</b>")
    try: msg = msg_template.format(bot_name=bot_name, bal=u["balance"], usdt=usdt_bal)
    except: msg = f"👋 <b>{bot_name}</b>\n\n💰 Balance: <b>{u['balance']:.2f} BDT / {usdt_bal:.4f} USDT</b>"

    bot.send_message(chat_id, msg, reply_markup=user_menu(chat_id))

# ====== ADMIN API COMMAND ======
@bot.message_handler(commands=['api_balance'])
def api_balance_handler(message):
    chat_id = str(message.chat.id)
    if is_admin(chat_id):
        try:
            payload = {"action": "balance", "key": API_PANEL_KEY}
            res = requests.post(API_PANEL_URL, data=payload).json()
            bal = res.get("balance", "Unknown")
            currency = res.get("currency", "BDT")
            bot.reply_to(message, f'🌐 <b>API Panel Balance:</b> {bal} {currency}')
        except Exception as e:
            bot.reply_to(message, f'❌ Error checking API balance: {e}')

@bot.message_handler(func=lambda msg: True, content_types=['text', 'photo', 'video', 'document', 'animation', 'sticker', 'voice', 'audio'])
def main_handler(message):
    chat_id = str(message.chat.id)
    text = message.text or message.caption or ""
    
    if db["settings"]["isBotAsleep"]: return
    if check_ban(chat_id): return
    ensure_user(message)

    actual_text = text
    for orig, data in db["settings"].get("ui_overrides", {}).items():
        if text == data.get("text", orig):
            actual_text = orig
            break

    menu_buttons = ["My Profile", "Buy Products", "Deposit", "Get Code", "Support", "Tutorial", "Admin Panel", "Live Stock", "User Menu", "Product Management", "Add Stock", "User Management", "Deposit Requests", "Deposit History", "Broadcast", "Voucher Management", "Force Join Setup", "Support Setup", "Tutorial Setup", "Admin Management", "Payment Settings", "Reseller Management"]
    
    if actual_text in menu_buttons:
        state[chat_id] = None
        unjoined = get_unjoined_channels(chat_id)
        if unjoined:
            send_force_join_msg(chat_id, unjoined)
            return

    if chat_id in state and state[chat_id] is not None:
        unjoined = get_unjoined_channels(chat_id)
        if unjoined:
            send_force_join_msg(chat_id, unjoined)
            state[chat_id] = None
            return
        handle_state(message, chat_id, text)
        return

    # ====== USER MENU ======
    if actual_text == "My Profile":
        u = db["users"][chat_id]
        msg = (f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> <b>My Profile</b>\n\n'
               f'━━━━━━━━━━━━━━━━━━\n'
               f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> Name: <b>{u["name"]}</b>\n'
               f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> User ID: <code>{u["id"]}</code>\n'
               f'<tg-emoji emoji-id="{EMOJI["link"]}">🔗</tg-emoji> Username: @{u.get("username", "none")}\n'
               f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> Balance: <b>{u["balance"]:.2f} BDT ({u["balance"]/db["settings"]["dollarRate"]:.2f} USD)</b>\n'
               f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> Total Orders: <b>{u["orders"]}</b>\n'
               f'━━━━━━━━━━━━━━━━━━\n'
               f'<tg-emoji emoji-id="{EMOJI["dashboard"]}">📊</tg-emoji> <b>Referral Link:</b>\n<code>https://t.me/{BOT_USERNAME}?start={u["id"]}</code>\n')
        
        kb = json.dumps({"inline_keyboard": [[{"text": "Apply Voucher", "callback_data": "apply_voucher", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "primary"}]]})
        bot.send_message(chat_id, msg, reply_markup=kb)

    elif actual_text == "Buy Products":
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>প্যাকেজ সিলেক্ট করুন</b>', reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("cat")}))
    
    elif actual_text == "Deposit":
        keyboard = [[{"text": m_data["name"], "callback_data": f"deposit_{m_id}", "icon_custom_emoji_id": PAYMENT_EMOJIS.get(m_id, EMOJI["money"]), "style": m_data.get("style", "primary")}] for m_id, m_data in db["settings"]["paymentMethods"].items()]
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["deposit_btn"]}">💳</tg-emoji> <b>প্রথমে পেমেন্ট মেথড সিলেক্ট করুন</b>', reply_markup=json.dumps({"inline_keyboard": keyboard}))
    
    elif actual_text == "Get Code":
        kb = json.dumps({"inline_keyboard": [
            [{"text": "Mail Code", "callback_data": "menu_mail_code", "icon_custom_emoji_id": EMOJI["mail"], "style": "primary"}],
            [{"text": "2FA Code", "callback_data": "menu_2fa_code", "icon_custom_emoji_id": EMOJI["2fa"], "style": "primary"}]
        ]})
        bot.send_message(chat_id, f'📌 <b>কোন সার্ভিসটি প্রয়োজন?</b>', reply_markup=kb)
        
    elif actual_text == "Support":
        state[chat_id] = {"type": "wait_support_msg"}
        msg = (f'<tg-emoji emoji-id="{EMOJI["support"]}">💬</tg-emoji> <b>Support Center</b>\n'
               f'━━━━━━━━━━━━━━━━━━\n'
               f'আপনার সমস্যা বা প্রশ্ন @nextproxybd বিস্তারিত লিখে মেসেজ করুন। অ্যাডমিনরা শীঘ্রই বটের মাধ্যমে আপনাকে রিপ্লে দেবেন।')
        bot.send_message(chat_id, msg)
        
    elif actual_text == "Tutorial":
        tuts = db["settings"].get("tutorials", [])
        if not tuts:
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>দুঃখিত! বর্তমানে কোনো টিউটোরিয়াল ভিডিও অ্যাড করা নেই।</b>')
        else:
            kb = []
            for t in tuts:
                kb.append([{"text": t["name"], "url": t["url"], "icon_custom_emoji_id": t["emoji"], "style": "primary"}])
            msg = (f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>টিউটোরিয়াল গাইডলাইন</b>\n'
                   f'━━━━━━━━━━━━━━━━━━\n'
                   f'বট ব্যবহার করতে কোনো সমস্যা হলে বা কোনো কাজ বুঝতে অসুবিধা হলে নিচের ভিডিওগুলো দেখতে পারেন। এখানে আপনার প্রয়োজনীয় সকল গাইডলাইন সুন্দরভাবে দেওয়া আছে। 👇')
            bot.send_message(chat_id, msg, reply_markup=json.dumps({"inline_keyboard": kb}))

    # ====== ADMIN MENU ======
    elif actual_text == "Admin Panel" and is_admin(chat_id):
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>Welcome Admin</b>', reply_markup=admin_menu())
    elif actual_text == "Admin Management" and is_admin(chat_id):
        kb = json.dumps({"inline_keyboard": [
            [{"text": "Add Admin", "callback_data": "admin_mgr_add", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "success"}],
            [{"text": "Delete Admin", "callback_data": "admin_mgr_del", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}]
        ]})
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>Admin Management System:</b>', reply_markup=kb)
    elif actual_text == "Reseller Management" and is_admin(chat_id):
        kb = json.dumps({"inline_keyboard": [
            [{"text": "Add Reseller", "callback_data": "reseller_mgr_add", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "success"}],
            [{"text": "Delete Reseller", "callback_data": "reseller_mgr_del", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}]
        ]})
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["dev_boss"]}">👨‍💼</tg-emoji> <b>Reseller Management System:</b>', reply_markup=kb)
    elif actual_text == "Payment Settings" and is_admin(chat_id):
        kb = []
        for m_id, m_data in db["settings"]["paymentMethods"].items():
            emoji_id = PAYMENT_EMOJIS.get(m_id, EMOJI["money"])
            kb.append([{"text": f"Edit {m_data['name']} Number", "callback_data": f"editpm_{m_id}", "icon_custom_emoji_id": emoji_id, "style": "primary"}])
        kb.append([{"text": f"Edit Dollar Rate (Current: {db['settings'].get('dollarRate', 120)} BDT)", "callback_data": "edit_dollar_rate", "icon_custom_emoji_id": EMOJI["money"], "style": "success"}])
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>কোন পেমেন্ট মেথডের নাম্বার পরিবর্তন করবেন?</b>', reply_markup=json.dumps({"inline_keyboard": kb}))
    elif actual_text == "Support Setup" and is_admin(chat_id):
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["support"]}">💬</tg-emoji> <b>Support System Updated!</b>\n\nএখন থেকে সকল ইউজার সরাসরি বটের মাধ্যমে মেসেজ করবে এবং আপনি এখানে নোটিফিকেশন পেয়ে রিপ্লে দিতে পারবেন।')
        
    elif actual_text == "Tutorial Setup" and is_admin(chat_id):
        tuts = db["settings"].get("tutorials", [])
        msg = f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Tutorial Management</b>\n\n'
        kb = [[{"text": "Add New Tutorial", "callback_data": "add_tutorial", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "success"}]]
        if not tuts:
            msg += "কোনো টিউটোরিয়াল অ্যাড করা নেই।"
        else:
            for idx, t in enumerate(tuts):
                msg += f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <b>{t["name"]}</b>\n'
                kb.append([{"text": f"Remove {t['name']}", "callback_data": f"del_tut_{idx}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
        bot.send_message(chat_id, msg, reply_markup=json.dumps({"inline_keyboard": kb}))
        
    elif actual_text == "Force Join Setup" and is_admin(chat_id):
        chans = db["settings"].get("force_channels", {})
        msg = f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>Force Join Channels:</b>\n\n'
        kb = [[{"text": "Add New Channel", "callback_data": "add_fc", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "success"}]]
        if not chans: msg += "কোনো চ্যানেল অ্যাড করা নেই।"
        else:
            for cid, data in chans.items():
                msg += f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <b>{data["name"]}</b> (<code>{cid}</code>)\n'
                kb.append([{"text": f"Remove {data['name']}", "callback_data": f"del_fc_{cid}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
        bot.send_message(chat_id, msg, reply_markup=json.dumps({"inline_keyboard": kb}))
    elif actual_text == "Voucher Management" and is_admin(chat_id):
        kb = json.dumps({"inline_keyboard": [
            [{"text": "Create Voucher", "callback_data": "create_voucher", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "success"},
             {"text": "Active Vouchers", "callback_data": "list_vouchers", "icon_custom_emoji_id": EMOJI["box"], "style": "primary"}]
        ]})
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Voucher Management System</b>', reply_markup=kb)
    elif actual_text == "Product Management" and is_admin(chat_id):
        kb = json.dumps({"inline_keyboard": [
            [{"text": "Add Normal Product", "callback_data": "admin_pm_add", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "success"},
             {"text": "Add API Product", "callback_data": "admin_pm_add_api", "icon_custom_emoji_id": EMOJI["box"], "style": "primary"}],
            [{"text": "Change Price", "callback_data": "admin_pm_change_price", "icon_custom_emoji_id": EMOJI["money"], "style": "primary"}],
            [{"text": "Delete Product", "callback_data": "admin_pm_del_prod", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}],
            [{"text": "Delete Product Stock", "callback_data": "admin_pm_del_stock", "icon_custom_emoji_id": EMOJI["pencil"], "style": "primary"}]
        ]})
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Product Management:</b>', reply_markup=kb)
    elif actual_text == "Add Stock" and is_admin(chat_id):
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>কোন ক্যাটাগরিতে স্টক অ্যাড করবেন?</b>', reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("admin_stock", exclude=["vpn"])}))
    elif actual_text == "Live Stock" and is_admin(chat_id):
        products = db["products"].values()
        if not products: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> No stock.')
        msg = f'<tg-emoji emoji-id="{EMOJI["dashboard"]}">📊</tg-emoji> <b>Live Stock</b>\n\n'
        for p in products:
            r_price = p.get("reseller_price", p["price"])
            is_api = p.get("is_api", False)
            if p.get("category") == "vpn": msg += f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>{p["name"]}</b> | Price: {p["price"]}৳ (Reseller: {r_price}৳) | [Manual Delivery]\n'
            elif is_api: msg += f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>{p["name"]}</b> | Price: {p["price"]}৳ (Reseller: {r_price}৳) | [Auto API Delivery]\n'
            else: msg += f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>{p["name"]}</b> | Price: {p["price"]}৳ (Reseller: {r_price}৳) | Stock: {len(p.get("stock", []))}\n'
        bot.send_message(chat_id, msg)
    elif actual_text == "User Management" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_user_search"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> <b>ইউজারের টেলিগ্রাম ID বা Username দিন:</b>')
    elif actual_text == "Deposit Requests" and is_admin(chat_id):
        msg, kb = get_dep_req_kb(0)
        if not kb: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>কোনো পেন্ডিং ডিপোজিট নেই।</b>')
        bot.send_message(chat_id, msg, reply_markup=kb)
    elif actual_text == "Deposit History" and is_admin(chat_id):
        deposits = db["deposits"][-20:]
        if not deposits: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>কোনো ডিপোজিট রেকর্ড নেই।</b>')
        msg = f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>ডিপোজিট হিস্টোরি:</b>\n\n'
        for dep in deposits:
            st_emoji = {"approved": f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji>', "rejected": f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji>', "pending": f'<tg-emoji emoji-id="{EMOJI["pending"]}">⏳</tg-emoji>'}.get(dep.get("status"), "")
            msg += f"{st_emoji} {dep['amount']} BDT ({dep['amount']/db['settings']['dollarRate']:.2f} USD) | User: {dep['userId']} | {dep['method']}\n"
        bot.send_message(chat_id, msg)
    elif actual_text == "Broadcast" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_broadcast"}
        msg = f'<tg-emoji emoji-id="{EMOJI["bell"]}">🔔</tg-emoji> <b>ব্রডকাস্ট মেসেজ পাঠান:</b>\n\nআপনি চাইলে Text, Photo, Video, GIF, Sticker, Bold বা Link যুক্ত মেসেজ পাঠাতে পারেন। যা পাঠাবেন, তা-ই সব ইউজারের কাছে চলে যাবে।'
        bot.send_message(chat_id, msg)
    elif actual_text == "User Menu":
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>মূল মেনু:</b>', reply_markup=user_menu(chat_id))

def handle_state(message, chat_id, text):
    st = state[chat_id]
    
    # ====== SUPPORT SYSTEM STATES ======
    if st["type"] == "wait_support_msg":
        u_name = db["users"][chat_id].get("name", "Unknown")
        admin_msg = (f'<tg-emoji emoji-id="{EMOJI["support"]}">💬</tg-emoji> <b>New Support Request</b>\n'
                     f'━━━━━━━━━━━━━━━━━━\n'
                     f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> User: <b>{u_name}</b> (<code>{chat_id}</code>)\n'
                     f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>Message:</b>\n{text}\n'
                     f'━━━━━━━━━━━━━━━━━━')
        markup = json.dumps({"inline_keyboard": [[{"text": "Reply", "callback_data": f"support_reply_{chat_id}", "icon_custom_emoji_id": EMOJI["pencil"], "style": "primary"}]]})
        for admin_id in db["settings"]["adminIds"]:
            try: bot.send_message(admin_id, admin_msg, reply_markup=markup)
            except: pass
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>আপনার মেসেজটি অ্যাডমিনদের কাছে পাঠানো হয়েছে।</b> অপেক্ষা করুন, খুব শীঘ্রই রিপ্লে পাবেন।')
        state[chat_id] = None

    elif st["type"] == "wait_support_reply":
        uid = st["uid"]
        admin_name = db["users"][chat_id].get("name", "Admin")
        try:
            reply_msg = (f'<tg-emoji emoji-id="{EMOJI["admin_badge"]}">🛡️</tg-emoji> <b>Reply from Admin ({admin_name})</b>\n'
                         f'━━━━━━━━━━━━━━━━━━\n{text}')
            bot.send_message(uid, reply_msg)
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>ইউজারকে রিপ্লে পাঠানো সফল হয়েছে!</b>')
        except:
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>রিপ্লে পাঠানো ব্যর্থ হয়েছে। ইউজার হয়তো বট ব্লক করেছে।</b>')
        state[chat_id] = None

    # ====== PAYMENT METHOD EDIT ======
    elif st["type"] == "wait_edit_pm":
        method = st["method"]
        new_number = text.strip()
        pm_name = db["settings"]["paymentMethods"][method]["name"]
        db["settings"]["paymentMethods"][method]["number"] = new_number
        save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>{pm_name} এর নাম্বার সফলভাবে আপডেট করা হয়েছে!</b>\n\nনতুন নাম্বার: <code>{new_number}</code>')
        state[chat_id] = None

    elif st["type"] == "wait_edit_dollar_rate":
        try:
            new_rate = float(text.strip())
            if new_rate <= 0: raise ValueError
        except:
            return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>ভুল ইনপুট!</b> দয়া করে সঠিক টাকার পরিমাণ (যেমন: 125.50) লিখুন:')
        
        db["settings"]["dollarRate"] = new_rate
        save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>ডলার রেট সফলভাবে আপডেট করা হয়েছে!</b>\n\nনতুন রেট: <b>1 USD = {new_rate} BDT</b>')
        state[chat_id] = None

    # ====== TUTORIAL SETUP STATES ======
    elif st["type"] == "wait_tut_name":
        state[chat_id] = {"type": "wait_tut_url", "name": text.strip()}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["link"]}">🔗</tg-emoji> <b>টিউটোরিয়াল ভিডিওর লিংক দিন (https://...):</b>')
        
    elif st["type"] == "wait_tut_url":
        state[chat_id] = {"type": "wait_tut_emoji", "name": st["name"], "url": text.strip()}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>বাটনের জন্য প্রিমিয়াম ইমোজি ID দিন:</b>\n(যেমন: 6266995104687330978 বা 5336972142066047577)')
        
    elif st["type"] == "wait_tut_emoji":
        emoji_id = text.strip()
        if not emoji_id.isdigit(): 
            emoji_id = EMOJI["link"] 
            
        if "tutorials" not in db["settings"]: db["settings"]["tutorials"] = []
        db["settings"]["tutorials"].append({"name": st["name"], "url": st["url"], "emoji": emoji_id})
        save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>টিউটোরিয়াল সফলভাবে যুক্ত করা হয়েছে!</b>')
        state[chat_id] = None

    # ====== FORCE JOIN ADD STATES ======
    elif st["type"] == "wait_fc_id":
        cid = text.strip()
        state[chat_id] = {"type": "wait_fc_name", "cid": cid}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>চ্যানেলের নাম দিন (যেমন: Official Channel):</b>')
    elif st["type"] == "wait_fc_name":
        name = text.strip()
        state[chat_id] = {"type": "wait_fc_url", "cid": st["cid"], "name": name}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["link"]}">🔗</tg-emoji> <b>চ্যানেলের ইনভাইট লিংক দিন (https://...):</b>')
    elif st["type"] == "wait_fc_url":
        url = text.strip()
        cid = st["cid"]
        if "force_channels" not in db["settings"]: db["settings"]["force_channels"] = {}
        db["settings"]["force_channels"][cid] = {"id": cid, "name": st["name"], "url": url}
        save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>চ্যানেল সফলভাবে যুক্ত করা হয়েছে!</b>')
        state[chat_id] = None

    # ====== ADMIN MANAGEMENT STATE ======
    elif st["type"] == "wait_add_admin":
        s_val = text.strip().lower().replace("@", "")
        u = next((u for u in db["users"].values() if u["id"] == s_val or u.get("username", "").lower() == s_val), None)
        if not u:
            if s_val.isdigit(): 
                new_admin_id = s_val
                admin_name = f"ID: {new_admin_id}"
            else: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> ইউজার পাওয়া যায়নি! সঠিক ID বা Username দিন।')
        else:
            new_admin_id = u["id"]
            admin_name = u["name"]

        if new_admin_id in db["settings"]["adminIds"]:
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>{admin_name}</b> আগে থেকেই অ্যাডমিন হিসেবে যুক্ত আছেন!')
        else:
            db["settings"]["adminIds"].append(new_admin_id)
            save_db()
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>{admin_name}</b> কে সফলভাবে অ্যাডমিন হিসেবে যুক্ত করা হয়েছে!')
        state[chat_id] = None

    # ====== RESELLER MANAGEMENT & CHANGE PRICE STATES ======
    elif st["type"] == "wait_add_reseller":
        s_val = text.strip().lower().replace("@", "")
        u = next((u for u in db["users"].values() if u["id"] == s_val or u.get("username", "").lower() == s_val), None)
        if not u:
            if s_val.isdigit(): 
                new_reseller_id = s_val
                r_name = f"ID: {new_reseller_id}"
            else: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> ইউজার পাওয়া যায়নি! সঠিক ID বা Username দিন।')
        else:
            new_reseller_id = u["id"]
            r_name = u["name"]

        if "resellers" not in db["settings"]: db["settings"]["resellers"] = []
        if new_reseller_id in db["settings"]["resellers"]:
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>{r_name}</b> আগে থেকেই রিসেলার হিসেবে যুক্ত আছেন!')
        else:
            db["settings"]["resellers"].append(new_reseller_id)
            save_db()
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>{r_name}</b> কে সফলভাবে রিসেলার হিসেবে যুক্ত করা হয়েছে!')
        state[chat_id] = None

    elif st["type"] == "wait_change_price_normal":
        try: price = float(text.strip())
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক প্রাইস দিন (যেমন: 50):')
        state[chat_id] = {"type": "wait_change_price_reseller", "prod": st["prod"], "price": price}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Normal Price: {price} BDT</b>\n\nএবার <b>{st["prod"]}</b> এর নতুন রিসেলার প্রাইস (Reseller Price) লিখুন:')
        
    elif st["type"] == "wait_change_price_reseller":
        try: reseller_price = float(text.strip())
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক রিসেলার প্রাইস দিন (যেমন: 40):')
        prod_name = st["prod"]
        db["products"][prod_name]["price"] = st["price"]
        db["products"][prod_name]["reseller_price"] = reseller_price
        save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>{prod_name}</b> এর প্রাইস সফলভাবে আপডেট করা হয়েছে!\n\nNormal: {st["price"]} BDT\nReseller: {reseller_price} BDT')
        state[chat_id] = None
        
    # ====== VPN ADMIN APPROVAL STATES ======
    elif st["type"] == "wait_vpn_email":
        vpn_email = text.strip()
        state[chat_id] = {"type": "wait_vpn_pass", "order": st["order"], "msg_id": st["msg_id"], "vpn_email": vpn_email}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["2fa"]}">🔐</tg-emoji> Email রিসিভ করা হয়েছে: <code>{vpn_email}</code>\n\n<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>ভিপিএনের জন্য এবার Password দিন:</b>')
        
    elif st["type"] == "wait_vpn_pass":
        vpn_pass = text.strip()
        order = st["order"]
        vpn_email = st["vpn_email"]
        if order in db["pendingOrders"]:
            db["pendingOrders"].remove(order)
            order["item"] = f"{vpn_email}|{vpn_pass}"
            db["orders"].append(order)
            save_db()
            
        curr_time = datetime.now().strftime("%d-%m-%Y , %I:%M %p")
        user_msg = (f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>আপনার ভিপিএন অর্ডারটি সফলভাবে কমপ্লিট হয়েছে!</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n\n'
                    f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <b>Delivery Time:</b> {curr_time}\n\n'
                    f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Package:</b> VPN ➔ {order["product"]}\n\n'
                    f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>আপনার অ্যাক্সেস ডিটেইলস:</b>\n\n'
                    f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>Email:</b>\n<code>{vpn_email}</code>\n'
                    f'<tg-emoji emoji-id="{EMOJI["2fa"]}">🔐</tg-emoji> <b>Password:</b>\n<code>{vpn_pass}</code>\n\n'
                    f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <i>ধন্যবাদ আমাদের সাথে থাকার জন্য!</i>')
        try: bot.send_message(order["userId"], user_msg)
        except: pass
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Thank You!</b> অর্ডারটি সফলভাবে ইউজারকে ডেলিভারি করা হয়েছে।')
        try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> Delivered to User.', chat_id, st["msg_id"])
        except: pass
        state[chat_id] = None

    elif st["type"] == "wait_user_search":
        s_val = text.strip().lower().replace("@", "")
        u = next((u for u in db["users"].values() if u["id"] == s_val or u.get("username", "").lower() == s_val), None)
        if not u: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> ইউজার পাওয়া যায়নি!')
        msg, kb = get_user_profile(u["id"])
        bot.send_message(chat_id, msg, reply_markup=kb); state[chat_id] = None
    elif st["type"] == "wait_addbal":
        try: amt = float(text)
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক টাকার পরিমাণ দিন।')
        db["users"][st["uid"]]["balance"] += amt; save_db()
        try: bot.send_message(st["uid"], f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>আপনার একাউন্টে {amt} BDT ({amt/db["settings"]["dollarRate"]:.2f} USD) যুক্ত হয়েছে।</b>')
        except: pass
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>{amt} BDT ({amt/db["settings"]["dollarRate"]:.2f} USD) অ্যাড করা হয়েছে।</b>'); state[chat_id] = None
    elif st["type"] == "wait_cutbal":
        try: amt = float(text)
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক টাকার পরিমাণ দিন।')
        db["users"][st["uid"]]["balance"] = max(0, db["users"][st["uid"]]["balance"] - amt); save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>{amt} BDT ({amt/db["settings"]["dollarRate"]:.2f} USD) কেটে নেওয়া হয়েছে।</b>'); state[chat_id] = None
    elif st["type"] == "wait_sendmsg":
        try: bot.send_message(st["uid"], f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>Admin Message:</b>\n━━━━━━━━━━━━━━━━━━\n{text}')
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>মেসেজ পাঠানো ব্যর্থ হয়েছে। ইউজার হয়তো বট ব্লক করেছে।</b>')
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>মেসেজ সফলভাবে পাঠানো হয়েছে।</b>'); state[chat_id] = None
    elif st["type"] == "wait_broadcast":
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["pending"]}">⏳</tg-emoji> <b>ব্রডকাস্ট শুরু হয়েছে... ব্যাকগ্রাউন্ডে মেসেজ পাঠানো হচ্ছে।</b>\nআপনি চাইলে এখন বটের অন্য কাজ করতে পারেন।')
        
        def run_broadcast(broadcast_msg, admin_id):
            success = 0
            failed = 0
            users = list(db["users"].keys())
            total = len(users)
            
            for uid in users:
                try:
                    bot.copy_message(chat_id=uid, from_chat_id=admin_id, message_id=broadcast_msg.message_id)
                    success += 1
                    time.sleep(0.05)
                except: 
                    failed += 1
            
            try: 
                report_msg = (f'<tg-emoji emoji-id="{EMOJI["bell"]}">🔔</tg-emoji> <b>ব্রডকাস্ট সম্পন্ন হয়েছে!</b>\n'
                              f'━━━━━━━━━━━━━━━━━━\n'
                              f'<tg-emoji emoji-id="{EMOJI["person"]}">👥</tg-emoji> সর্বমোট ইউজার: <b>{total}</b> জন\n'
                              f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> সফলভাবে পাঠানো হয়েছে: <b>{success}</b> জনকে\n'
                              f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> ফেইল্ড (বট ব্লক করেছে): <b>{failed}</b> জনকে\n'
                              f'━━━━━━━━━━━━━━━━━━')
                bot.send_message(admin_id, report_msg)
            except: pass

        threading.Thread(target=run_broadcast, args=(message, chat_id)).start()
        state[chat_id] = None
    
    # ====== CUSTOM BULK QUANTITY WAIT STATE ======
    elif st["type"] == "wait_custom_qty":
        try:
            qty = int(text.strip())
            if qty <= 0: raise ValueError
        except:
            return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক সংখ্যা দিন।')
            
        prod_name = st["prod"]
        product = db["products"].get(prod_name)
        is_api = product.get("is_api", False)
        
        if not product:
            state[chat_id] = None
            return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> প্রোডাক্ট পাওয়া যায়নি।')
            
        if not is_api and len(product.get("stock", [])) < qty:
            return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> স্টক অপর্যাপ্ত! স্টকে আছে: {len(product.get("stock", []))} টি। আবার সংখ্যা দিন:')
            
        state[chat_id] = None
        complete_purchase(chat_id, prod_name, qty)

    # ====== VOUCHER STATES ======
    elif st["type"] == "wait_voucher_input":
        code = text.strip()
        if code not in db["vouchers"]: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>দুঃখিত, আপনার কোডটি ভুল!</b>')
        v = db["vouchers"][code]
        if chat_id in v["used_by"]: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>আপনি ইতিমধ্যে এই ভাউচারটি ব্যবহার করেছেন!</b>')
        if len(v["used_by"]) >= v["limit"]: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>দুঃখিত, এই কোডের লিমিট শেষ হয়ে গেছে!</b>')
        v["used_by"].append(chat_id)
        db["users"][chat_id]["balance"] += v["amount"]; save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>অভিনন্দন!</b>\nভাউচার কোড সফলভাবে যুক্ত হয়েছে।\nআপনি <b>{v["amount"]} BDT ({v["amount"]/db["settings"]["dollarRate"]:.2f} USD)</b> পেয়েছেন।')
        state[chat_id] = None

    elif st["type"] == "wait_voucher_code":
        code = text.strip()
        if code in db["vouchers"]: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>এই কোডটি ইতিমধ্যে আছে! অন্য কোড দিন:</b>')
        state[chat_id] = {"type": "wait_voucher_amount", "code": code}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> কোড: <b>{code}</b>\n\nএবার ভাউচারের টাকার পরিমাণ লিখুন (যেমন: 50):')
    
    elif st["type"] == "wait_voucher_amount":
        try: amt = float(text)
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক টাকার পরিমাণ দিন।')
        state[chat_id] = {"type": "wait_voucher_limit", "code": st["code"], "amount": amt}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> পরিমাণ: <b>{amt} BDT ({amt/db["settings"]["dollarRate"]:.2f} USD)</b>\n\nএবার ব্যবহারের লিমিট দিন (যেমন: 20):')
    
    elif st["type"] == "wait_voucher_limit":
        try: limit = int(text)
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক লিমিট সংখ্যা দিন।')
        code = st["code"]
        db["vouchers"][code] = {"amount": st["amount"], "limit": limit, "used_by": []}; save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>ভাউচার সফলভাবে তৈরি হয়েছে!</b>\n\nকোড: <code>{code}</code>\nপরিমাণ: <b>{st["amount"]} BDT ({st["amount"]/db["settings"]["dollarRate"]:.2f} USD)</b>\nলিমিট: <b>{limit} জন</b>')
        state[chat_id] = None

    elif st["type"] == "wait_mail":
        mail = text.strip().lower()
        if "@" not in mail or "." not in mail: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক মেইল এড্রেস দিন!')
        db["validMails"].append({"email": mail, "userId": chat_id, "time": datetime.now().isoformat()}); save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> মেইল কোড জেনারেট হচ্ছে...'); state[chat_id] = None
    
    elif st["type"] == "wait_2fa":
        secret = text.strip().replace(" ", "").upper()
        if len(secret) < 6: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>2FA Key অন্তত ৬ অক্ষরের হতে হবে!</b>')
        try:
            totp = pyotp.TOTP(secret)
            code = totp.now()
            msg = (f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>2FA Authenticator</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n'
                   f'━━━━━━━━━━━━━━━━━━\n'
                   f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Generated Code:</b>\n👉 <code>{code}</code> 👈\n\n'
                   f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Secret Key:</b>\n<code>{secret}</code>\n'
                   f'━━━━━━━━━━━━━━━━━━\n'
                   f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <i>কোডটি দ্রুত কপি করে ব্যবহার করুন।</i>')
            kb = json.dumps({"inline_keyboard": [[{"text": "Re-Generate", "callback_data": f"re2fa_{secret}", "icon_custom_emoji_id": EMOJI["refresh"], "style": "primary"}]]})
            bot.send_message(chat_id, msg, reply_markup=kb); state[chat_id] = None
        except Exception: bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>দুঃখিত, আপনার 2FA Key টি সঠিক নয় বা ইনভ্যালিড!</b>')

    elif st["type"] == "depositAmount":
        try: amount = float(text)
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক পরিমাণ লিখুন।')
        
        pm = db["settings"]["paymentMethods"][st["method"]]
        emoji_id = PAYMENT_EMOJIS.get(st["method"], EMOJI["money"])
        
        if st["method"] == "binance":
            if amount <= 0.19: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> পরিমাণ মিনিমাম 0.20 হতে হবে।')
            bdt_amount = amount * db["settings"]["dollarRate"]
            msg = f'<tg-emoji emoji-id="{emoji_id}">💳</tg-emoji> <b>Deposit Request</b>\n\nMethod: <b>{pm["name"]}</b>\nAmount: <b>{amount} USD ({bdt_amount} BDT)</b>\n\nএই নাম্বারে/Pay ID তে ডলার পাঠান: <code>{pm["number"]}</code>\n\nপেমেন্ট সম্পন্ন হলে নিচের বাটনে ক্লিক করুন:'
            callback_amount = bdt_amount
        else:
            if amount < 20: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সর্বনিম্ন ২০ টাকা লিখতে হবে।')
            msg = f'<tg-emoji emoji-id="{emoji_id}">💳</tg-emoji> <b>Deposit Request</b>\n\nMethod: <b>{pm["name"]}</b>\nAmount: <b>{amount} BDT ({amount/db["settings"]["dollarRate"]:.2f} USD)</b>\n\nএই নাম্বারে টাকা পাঠান: <code>{pm["number"]}</code>\n\nপেমেন্ট সম্পন্ন হলে নিচের বাটনে ক্লিক করুন:'
            callback_amount = amount
            
        bot.send_message(chat_id, msg, reply_markup=json.dumps({"inline_keyboard": [[{"text": "Payment Done", "callback_data": f"paid_{st['method']}_{callback_amount}", "icon_custom_emoji_id": EMOJI["success"], "style": "success"}]]})); state[chat_id] = None
        
    elif st["type"] == "depositTxnId":
        txn_id = text.strip().upper()
        if not txn_id:
            return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক TrxID দিন!')

        amount_needed = float(st["amount"])
        method = st["method"]

        # Manual verification: একই TrxID আগে pending/approved হয়েছে কি না যাচাই।
        if txn_id in db.get("usedTxnIds", []):
            return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> এই TrxID আগে ব্যবহার হয়েছে!')

        existing_dep = next(
            (d for d in db.get("deposits", [])
             if str(d.get("txnId", "")).upper() == txn_id
             and d.get("status") in ("pending", "approved")),
            None
        )
        if existing_dep:
            return bot.send_message(
                chat_id,
                f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> এই TrxID দিয়ে একটি Deposit Request ইতিমধ্যে জমা হয়েছে।'
            )

        # Auto SMS/API verification সম্পূর্ণ বন্ধ।
        # TrxID জমা হওয়ার পর Admin manually verify করে Approve/Reject করবেন।
        dep_id = int(datetime.now().timestamp() * 1000)
        dep = {
            "id": dep_id,
            "userId": chat_id,
            "amount": amount_needed,
            "method": method,
            "txnId": txn_id,
            "status": "pending",
            "time": datetime.now().isoformat()
        }
        db.setdefault("deposits", []).append(dep)
        save_db()

        pm_name = db["settings"]["paymentMethods"].get(method, {}).get("name", method)
        u = db["users"].get(chat_id, {})
        admin_msg = (
            f'<tg-emoji emoji-id="{EMOJI["pending"]}">⏳</tg-emoji> <b>NEW DEPOSIT REQUEST</b>\n'
            f'━━━━━━━━━━━━━━━━━━\n'
            f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> User: <b>{u.get("name", "Unknown")}</b>\n'
            f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> ID: <code>{chat_id}</code>\n'
            f'<tg-emoji emoji-id="{EMOJI["link"]}">🔗</tg-emoji> Username: @{u.get("username", "none")}\n'
            f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> Method: <b>{pm_name}</b>\n'
            f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> Amount: <b>{amount_needed:g} BDT ({amount_needed/db["settings"]["dollarRate"]:.2f} USD)</b>\n'
            f'<tg-emoji emoji-id="{EMOJI["2fa"]}">🔐</tg-emoji> TrxID: <code>{txn_id}</code>\n'
            f'━━━━━━━━━━━━━━━━━━\n'
            f'<i>Payment manually verify করে Approve/Reject করুন।</i>'
        )
        markup = json.dumps({"inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"approve_{dep_id}", "icon_custom_emoji_id": EMOJI["success"], "style": "success"},
                {"text": "Reject", "callback_data": f"reject_{dep_id}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}
            ]
        ]})

        for admin_id in db["settings"]["adminIds"]:
            try:
                bot.send_message(admin_id, admin_msg, reply_markup=markup)
            except:
                pass

        bot.send_message(
            chat_id,
            f'<tg-emoji emoji-id="{EMOJI["pending"]}">⏳</tg-emoji> <b>Deposit Request Submitted</b>\n\n'
            f'Amount: <b>{amount_needed:g} BDT</b>\n'
            f'Method: <b>{pm_name}</b>\n'
            f'TrxID: <code>{txn_id}</code>\n\n'
            f'আপনার payment এখন Admin verification-এর জন্য pending আছে। Verify হওয়ার পর balance যোগ হবে।'
        )
        state[chat_id] = None

    # ====== ADD NORMAL PRODUCT ======
    elif st["type"] == "add_product_name":
        if text.strip() in db["products"]: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> এই নামের প্রোডাক্ট আগে থেকেই আছে। অন্য নাম দিন:')
        state[chat_id] = {"type": "add_product_price", "cat": st["cat"], "name": text.strip()}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> প্রোডাক্টের নাম: <b>{text.strip()}</b>\n\nএবার প্রোডাক্টের প্রাইস (Price) লিখুন:')
    elif st["type"] == "add_product_price":
        try: price = float(text.strip())
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক প্রাইস দিন (যেমন: 50):')
        state[chat_id] = {"type": "add_product_reseller_price", "cat": st["cat"], "name": st["name"], "price": price}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Normal Price: {price} BDT</b>\n\nএবার প্রোডাক্টের রিসেলার প্রাইস (Reseller Price) লিখুন:')
    elif st["type"] == "add_product_reseller_price":
        try: reseller_price = float(text.strip())
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক রিসেলার প্রাইস দিন (যেমন: 40):')
        db["products"][st["name"]] = {"name": st["name"], "category": st["cat"], "price": st["price"], "reseller_price": reseller_price, "is_api": False, "stock": []}; save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Product Added!</b>\nName: {st["name"]}\nPrice: {st["price"]} BDT\nReseller Price: {reseller_price} BDT'); state[chat_id] = None
        
    # ====== ADD API PRODUCT ======
    elif st["type"] == "add_api_product_name":
        if text.strip() in db["products"]: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> এই নামের প্রোডাক্ট আগে থেকেই আছে। অন্য নাম দিন:')
        state[chat_id] = {"type": "add_api_product_price", "cat": st["cat"], "name": text.strip()}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> API প্রোডাক্টের নাম: <b>{text.strip()}</b>\n\nএবার প্রোডাক্টের প্রাইস (Price) লিখুন:')
    elif st["type"] == "add_api_product_price":
        try: price = float(text.strip())
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক প্রাইস দিন (যেমন: 50):')
        state[chat_id] = {"type": "add_api_product_reseller_price", "cat": st["cat"], "name": st["name"], "price": price}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Normal Price: {price} BDT</b>\n\nএবার প্রোডাক্টের রিসেলার প্রাইস (Reseller Price) লিখুন:')
    elif st["type"] == "add_api_product_reseller_price":
        try: reseller_price = float(text.strip())
        except: return bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> সঠিক রিসেলার প্রাইস দিন:')
        state[chat_id] = {"type": "add_api_product_service_id", "cat": st["cat"], "name": st["name"], "price": st["price"], "reseller_price": reseller_price}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Reseller Price: {reseller_price} BDT</b>\n\nএবার থার্ড-পার্টি প্যানেলের <b>Service Code (ID)</b> লিখুন:')
    elif st["type"] == "add_api_product_service_id":
        service_id = text.strip()
        db["products"][st["name"]] = {"name": st["name"], "category": st["cat"], "price": st["price"], "reseller_price": st["reseller_price"], "is_api": True, "api_service_id": service_id, "stock": []}
        save_db()
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>API Product Added!</b>\nName: {st["name"]}\nService ID: {service_id}')
        state[chat_id] = None

    elif st["type"] == "stockUpload" and is_admin(chat_id) and message.document:
        try:
            file_name = message.document.file_name
            file_ext = os.path.splitext(file_name)[1].lower()
            file_path = os.path.join(TMP_DIR, f"{file_name}_{datetime.now().timestamp()}{file_ext}")
            with open(file_path, "wb") as f: f.write(bot.download_file(bot.get_file(message.document.file_id).file_path))
            
            cat_id = db["products"][st["product"]].get("category", "")
            new_stock = []
            
            if file_ext == '.txt':
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        val = line.strip()
                        if val: new_stock.append(val)
            elif file_ext in ['.xls', '.xlsx']:
                df = pd.read_excel(file_path, header=None, dtype=str)
                df = df.fillna("")
                if cat_id == "proxy":
                    for _, row in df.iterrows():
                        host = str(row.iloc[0]).strip() if len(row) > 0 else ""
                        port = str(row.iloc[1]).strip() if len(row) > 1 else ""
                        user = str(row.iloc[2]).strip() if len(row) > 2 else ""
                        pwd = str(row.iloc[3]).strip() if len(row) > 3 else ""
                        
                        if host.endswith(".0") and host[:-2].isdigit(): host = host[:-2]
                        if port.endswith(".0") and port[:-2].isdigit(): port = port[:-2]
                        if user.endswith(".0") and user[:-2].isdigit(): user = user[:-2]
                        if pwd.endswith(".0") and pwd[:-2].isdigit(): pwd = pwd[:-2]
                        
                        if host and host.lower() != "nan": new_stock.append(f"{host}:{port}:{user}:{pwd}")
                else:
                    for x in df.values.flatten():
                        val = str(x).strip()
                        if val and val.lower() != "nan":
                            if val.endswith(".0") and val[:-2].isdigit(): val = val[:-2]
                            new_stock.append(val)
            
            if new_stock:
                db["products"][st["product"]]["stock"].extend(new_stock); save_db()
                bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Stock Added!</b>\nAdded {len(new_stock)} items.')
            else:
                bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>ফাইল থেকে কোনো ডেটা পাওয়া যায়নি বা ফরম্যাট ভুল!</b>')
                
            if os.path.exists(file_path): os.remove(file_path)
        except Exception as e: bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>Error:</b> {e}')
        state[chat_id] = None

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id, data = str(call.message.chat.id), call.data
    
    if data == "menu_mail_code":
        state[chat_id] = {"type": "wait_mail"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>আপনার মেইল এড্রেস দিন</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        return
        
    elif data == "menu_2fa_code":
        state[chat_id] = {"type": "wait_2fa"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["2fa"]}">🔐</tg-emoji> <b>আপনার 2FA KEY টা দিন:</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        return
        
    elif data.startswith("support_reply_") and is_admin(chat_id):
        uid = data.replace("support_reply_", "")
        state[chat_id] = {"type": "wait_support_reply", "uid": uid}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>ইউজার <code>{uid}</code> কে কি রিপ্লে দিতে চান তা নিচে লিখে সেন্ড করুন:</b>')

    # ====== ADMIN MANAGEMENT ACTIONS ======
    elif data == "admin_mgr_add" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_add_admin"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> <b>নতুন অ্যাডমিনের টেলিগ্রাম ID বা Username দিন:</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data == "admin_mgr_del" and is_admin(chat_id):
        admins = db["settings"]["adminIds"]
        if not admins: return bot.answer_callback_query(call.id, "কোনো অতিরিক্ত অ্যাডমিন নেই!", show_alert=True)
        kb = []
        for aid in admins:
            u_name = db["users"].get(aid, {}).get("name", f"ID: {aid}")
            kb.append([{"text": u_name, "callback_data": f"deladmin_{aid}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>কোন অ্যাডমিনকে রিমুভ করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))

    elif data.startswith("deladmin_") and is_admin(chat_id):
        aid = data.replace("deladmin_", "")
        if aid in db["settings"]["adminIds"]:
            db["settings"]["adminIds"].remove(aid); save_db()
            bot.answer_callback_query(call.id, "অ্যাডমিন সফলভাবে রিমুভ করা হয়েছে!", show_alert=True)
            admins = db["settings"]["adminIds"]
            if not admins:
                try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>আর কোনো অ্যাডমিন অবশিষ্ট নেই।</b>', chat_id, call.message.message_id)
                except: pass
            else:
                kb = []
                for a in admins:
                    u_name = db["users"].get(a, {}).get("name", f"ID: {a}")
                    kb.append([{"text": u_name, "callback_data": f"deladmin_{a}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
                try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>কোন অ্যাডমিনকে রিমুভ করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))
                except: pass

    # ====== RESELLER MANAGEMENT ACTIONS ======
    elif data == "reseller_mgr_add" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_add_reseller"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> <b>নতুন রিসেলারের টেলিগ্রাম ID বা Username দিন:</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data == "reseller_mgr_del" and is_admin(chat_id):
        resellers = db["settings"].get("resellers", [])
        if not resellers: return bot.answer_callback_query(call.id, "কোনো রিসেলার নেই!", show_alert=True)
        kb = []
        for rid in resellers:
            u_name = db["users"].get(rid, {}).get("name", f"ID: {rid}")
            kb.append([{"text": u_name, "callback_data": f"delreseller_{rid}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["dev_boss"]}">👨‍💼</tg-emoji> <b>কোন রিসেলারকে রিমুভ করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))

    elif data.startswith("delreseller_") and is_admin(chat_id):
        rid = data.replace("delreseller_", "")
        if rid in db["settings"].get("resellers", []):
            db["settings"]["resellers"].remove(rid); save_db()
            bot.answer_callback_query(call.id, "রিসেলার সফলভাবে রিমুভ করা হয়েছে!", show_alert=True)
            resellers = db["settings"].get("resellers", [])
            if not resellers:
                try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>আর কোনো রিসেলার অবশিষ্ট নেই।</b>', chat_id, call.message.message_id)
                except: pass
            else:
                kb = []
                for r in resellers:
                    u_name = db["users"].get(r, {}).get("name", f"ID: {r}")
                    kb.append([{"text": u_name, "callback_data": f"delreseller_{r}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
                try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["dev_boss"]}">👨‍💼</tg-emoji> <b>কোন রিসেলারকে রিমুভ করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))
                except: pass

    # ====== PAYMENT SETTINGS ACTIONS ======
    elif data.startswith("editpm_") and is_admin(chat_id):
        method = data.split("_")[1]
        pm_name = db["settings"]["paymentMethods"][method]["name"]
        current_num = db["settings"]["paymentMethods"][method]["number"]
        state[chat_id] = {"type": "wait_edit_pm", "method": method}
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>{pm_name}</b> এর নতুন নাম্বার দিন:\n\nবর্তমান নাম্বার: <code>{current_num}</code>', chat_id, call.message.message_id)

    elif data == "edit_dollar_rate" and is_admin(chat_id):
        current_rate = db["settings"].get("dollarRate", 120)
        state[chat_id] = {"type": "wait_edit_dollar_rate"}
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>নতুন ডলার রেট (1 USD = ? BDT) লিখুন:</b>\n\nবর্তমান রেট: <code>{current_rate} BDT</code>\n\n(যেমন: 120 বা 125.50 লিখে সেন্ড করুন)', chat_id, call.message.message_id)

    # ====== TUTORIAL ACTIONS ======
    elif data == "add_tutorial" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_tut_name"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>টিউটোরিয়াল বাটনের নাম লিখুন (যেমন: How to deposit):</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data.startswith("del_tut_") and is_admin(chat_id):
        idx = int(data.replace("del_tut_", ""))
        if "tutorials" in db["settings"] and len(db["settings"]["tutorials"]) > idx:
            del db["settings"]["tutorials"][idx]
            save_db()
            bot.answer_callback_query(call.id, "টিউটোরিয়াল ডিলিট করা হয়েছে!", show_alert=True)
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass

    # ====== FORCE JOIN ACTIONS ======
    elif data == "verify_join":
        unjoined = get_unjoined_channels(chat_id)
        if unjoined: bot.answer_callback_query(call.id, "দুঃখিত! আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি।", show_alert=True)
        else:
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>অ্যাক্সেস ভেরিফায়েড!</b>', reply_markup=user_menu(chat_id))
    
    elif data == "add_fc" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_fc_id"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>চ্যানেলের Username (e.g., @mychannel) অথবা Chat ID দিন:</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data.startswith("del_fc_") and is_admin(chat_id):
        cid = data.replace("del_fc_", "")
        if "force_channels" in db["settings"] and cid in db["settings"]["force_channels"]:
            del db["settings"]["force_channels"][cid]; save_db()
            bot.answer_callback_query(call.id, "চ্যানেল ডিলিট করা হয়েছে!", show_alert=True)
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass

    elif data.startswith("deppage_") and is_admin(chat_id):
        page = int(data.split("_")[1])
        msg, kb = get_dep_req_kb(page)
        if kb: bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=kb)
        else: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>কোনো পেন্ডিং ডিপোজিট নেই।</b>', chat_id, call.message.message_id)

    elif data.startswith("viewdep_") and is_admin(chat_id):
        dep_id = int(data.split("_")[1])
        dep = next((d for d in db["deposits"] if d["id"] == dep_id), None)
        if not dep or dep.get("status") != "pending": return bot.answer_callback_query(call.id, "ডিপোজিট রিকোয়েস্টটি পাওয়া যায়নি বা ইতোমধ্যে প্রসেস হয়েছে!", show_alert=True)
        u_name = db["users"].get(dep["userId"], {}).get("name", "Unknown")
        pm_name = db["settings"]["paymentMethods"].get(dep["method"], {}).get("name", dep["method"])
        try: time_str = datetime.fromtimestamp(dep["id"]).strftime("%I:%M %p | %d %b, %Y")
        except: time_str = "N/A"
        admin_msg = (f'<tg-emoji emoji-id="{EMOJI["wallet"]}">💳</tg-emoji> <b>DEPOSIT DETAILS</b>\n━━━━━━━━━━━━━━━━━━\n'
                     f'<tg-emoji emoji-id="{EMOJI["person"]}">👤</tg-emoji> User: <b>{u_name}</b>\n'
                     f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> ID: <code>{dep["userId"]}</code>\n'
                     f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> Method: <b>{pm_name}</b>\n'
                     f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> Amount: <b>{dep["amount"]} BDT ({dep["amount"]/db["settings"]["dollarRate"]:.2f} USD)</b>\n'
                     f'<tg-emoji emoji-id="{EMOJI["2fa"]}">🔐</tg-emoji> TrxID: <code>{dep["txnId"]}</code>\n'
                     f'<tg-emoji emoji-id="{EMOJI["clock"]}">🕒</tg-emoji> Time: <b>{time_str}</b>\n━━━━━━━━━━━━━━━━━━')
        markup = json.dumps({"inline_keyboard": [
            [{"text": "Approve", "callback_data": f"approve_{dep_id}", "icon_custom_emoji_id": EMOJI["success"], "style": "success"}, 
             {"text": "Reject", "callback_data": f"reject_{dep_id}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}],
            [{"text": "< Back", "callback_data": "deppage_0", "style": "primary"}]
        ]})
        bot.edit_message_text(admin_msg, chat_id, call.message.message_id, reply_markup=markup)

    elif data == "admin_pm_add" and is_admin(chat_id):
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>কোন ক্যাটাগরিতে Normal প্রোডাক্ট অ্যাড করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("admin_add")}))
    
    elif data == "admin_pm_add_api" and is_admin(chat_id):
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>কোন ক্যাটাগরিতে API প্রোডাক্ট অ্যাড করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("admin_addapi")}))
        
    elif data == "admin_pm_change_price" and is_admin(chat_id):
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>কোন ক্যাটাগরির প্রোডাক্টের প্রাইস চেঞ্জ করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("chgpricecat")}))
    
    elif data.startswith("chgpricecat_") and is_admin(chat_id):
        cat_id = data.replace("chgpricecat_", "")
        products = [p for p in db["products"].values() if p.get("category") == cat_id]
        if not products: return bot.answer_callback_query(call.id, "এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই!", show_alert=True)
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>কোন প্রোডাক্টের প্রাইস চেঞ্জ করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": [[{"text": p["name"], "callback_data": f"chgprice_{p['name']}", "icon_custom_emoji_id": EMOJI["pencil"], "style": "primary"}] for p in products]}))

    elif data.startswith("chgprice_") and is_admin(chat_id):
        prod_name = data.replace("chgprice_", "")
        if prod_name in db["products"]:
            state[chat_id] = {"type": "wait_change_price_normal", "prod": prod_name}
            current_price = db["products"][prod_name]["price"]
            current_r_price = db["products"][prod_name].get("reseller_price", current_price)
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>{prod_name}</b> এর বর্তমান প্রাইস:\nNormal: {current_price} BDT\nReseller: {current_r_price} BDT\n\n<b>নতুন Normal Price লিখে সেন্ড করুন:</b>')
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass

    elif data == "admin_pm_del_prod" and is_admin(chat_id):
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>কোন ক্যাটাগরি থেকে প্রোডাক্ট ডিলিট করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("delprodcat")}))
    elif data == "admin_pm_del_stock" and is_admin(chat_id):
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>কোন ক্যাটাগরি থেকে প্রোডাক্টের স্টক ক্লিয়ার করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": get_category_keyboard("delstockcat")}))

    elif data.startswith("delprodcat_") and is_admin(chat_id):
        cat_id = data.replace("delprodcat_", "")
        products = [p for p in db["products"].values() if p.get("category") == cat_id]
        if not products: return bot.answer_callback_query(call.id, "এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই!", show_alert=True)
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>কোন প্রোডাক্টটি ডিলিট করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": [[{"text": p["name"], "callback_data": f"delprod_{p['name']}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}] for p in products]}))

    elif data.startswith("delstockcat_") and is_admin(chat_id):
        cat_id = data.replace("delstockcat_", "")
        products = [p for p in db["products"].values() if p.get("category") == cat_id]
        if not products: return bot.answer_callback_query(call.id, "এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই!", show_alert=True)
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>কোন প্রোডাক্টের স্টক ক্লিয়ার করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": [[{"text": p["name"], "callback_data": f"delstock_{p['name']}", "icon_custom_emoji_id": EMOJI["pencil"], "style": "primary"}] for p in products]}))

    elif data.startswith("delprod_") and is_admin(chat_id):
        prod_name = data.replace("delprod_", "")
        if prod_name in db["products"]:
            del db["products"][prod_name]; save_db()
            bot.answer_callback_query(call.id, "প্রোডাক্ট সফলভাবে ডিলিট করা হয়েছে!", show_alert=True)
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass

    elif data.startswith("delstock_") and is_admin(chat_id):
        prod_name = data.replace("delstock_", "")
        if prod_name in db["products"]:
            db["products"][prod_name]["stock"] = []; save_db()
            bot.answer_callback_query(call.id, "প্রোডাক্টের সম্পূর্ণ স্টক ক্লিয়ার করা হয়েছে!", show_alert=True)
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass

    elif data.startswith("admin_add_") and is_admin(chat_id):
        cat_id = data.replace("admin_add_", "")
        state[chat_id] = {"type": "add_product_name", "cat": cat_id}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>{CATEGORIES[cat_id]["name"]}</b> ক্যাটাগরিতে নতুন প্রোডাক্টের নাম লিখুন:')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data.startswith("admin_addapi_") and is_admin(chat_id):
        cat_id = data.replace("admin_addapi_", "")
        state[chat_id] = {"type": "add_api_product_name", "cat": cat_id}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>API {CATEGORIES[cat_id]["name"]}</b> ক্যাটাগরিতে নতুন প্রোডাক্টের নাম লিখুন:')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data.startswith("admin_stock_") and is_admin(chat_id):
        cat_id = data.replace("admin_stock_", "")
        # Only local products need stock uploads
        products = [p for p in db["products"].values() if p.get("category") == cat_id and not p.get("is_api", False)]
        if not products: return bot.answer_callback_query(call.id, "আগে এই ক্যাটাগরিতে Normal প্রোডাক্ট অ্যাড করুন!", show_alert=True)
        bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>কোন প্রোডাক্টের স্টক আপলোড করবেন?</b>', chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": [[{"text": p["name"], "callback_data": f"stkupload_{p['name']}", "style": "primary"}] for p in products]}))
        
    elif data.startswith("stkupload_") and is_admin(chat_id):
        prod_name = data.replace("stkupload_", "")
        state[chat_id] = {"type": "stockUpload", "product": prod_name}
        msg = (f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>{prod_name}</b> এর জন্য Excel (.xlsx) অথবা Text (.txt) ফাইলটি পাঠান:\n\n'
               f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> <b>আপলোডের সঠিক ফরম্যাট:</b>\n'
               f'<tg-emoji emoji-id="{EMOJI["pencil"]}">📝</tg-emoji> <b>TXT ফাইল হলে:</b>\n'
               f'<code>Host:Port:Username:Password</code> (মাঝে : থাকবে)\n\n'
               f'<tg-emoji emoji-id="{EMOJI["dashboard"]}">📊</tg-emoji> <b>Excel ফাইল হলে:</b>\n'
               f'• কলাম A = Host\n'
               f'• কলাম B = Port\n'
               f'• কলাম C = Username\n'
               f'• কলাম D = Password')
        bot.send_message(chat_id, msg)
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass

    elif data.startswith("vpnapp_") and is_admin(chat_id):
        order_id = int(data.split("_")[1])
        order = next((o for o in db["pendingOrders"] if o.get("id") == order_id), None)
        if not order: return bot.answer_callback_query(call.id, "অর্ডারটি পাওয়া যায়নি বা ইতোমধ্যে সম্পন্ন হয়েছে!", show_alert=True)
        state[chat_id] = {"type": "wait_vpn_email", "order": order, "msg_id": call.message.message_id}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>{order["product"]}</b> এর জন্য নির্দিষ্ট ইমেইল দিন:')
        
    elif data.startswith("vpnrej_") and is_admin(chat_id):
        order_id = int(data.split("_")[1])
        order = next((o for o in db["pendingOrders"] if o.get("id") == order_id), None)
        if not order: return bot.answer_callback_query(call.id, "অর্ডারটি পাওয়া যায়নি বা ইতোমধ্যে সম্পন্ন হয়েছে!", show_alert=True)
        db["users"][order["userId"]]["balance"] += order["price"]
        db["pendingOrders"].remove(order); save_db()
        try: bot.send_message(order["userId"], f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>দুঃখিত!</b> কোনো কারণে আপনার <b>{order["product"]}</b> এর অর্ডারটি ক্যানসেল করা হয়েছে।\nআপনার অ্যাকাউন্টে <b>{order["price"]} BDT ({order["price"]/db["settings"]["dollarRate"]:.2f} USD)</b> রিফান্ড করা হয়েছে।')
        except: pass
        try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> Order Rejected & Refunded.', chat_id, call.message.message_id)
        except: pass

    elif data.startswith("re2fa_"):
        secret = data.replace("re2fa_", "")
        try:
            totp = pyotp.TOTP(secret)
            code = totp.now()
            msg = (f'<tg-emoji emoji-id="{EMOJI["shield"]}">🛡️</tg-emoji> <b>2FA Authenticator</b> <tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji>\n'
                   f'━━━━━━━━━━━━━━━━━━\n'
                   f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> <b>Generated Code:</b>\n👉 <code>{code}</code> 👈\n\n'
                   f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Secret Key:</b>\n<code>{secret}</code>\n'
                   f'━━━━━━━━━━━━━━━━━━\n'
                   f'<tg-emoji emoji-id="{EMOJI["clock"]}">⏳</tg-emoji> <i>কোডটি দ্রুত কপি করে ব্যবহার করুন।</i>')
            kb = json.dumps({"inline_keyboard": [[{"text": "Re-Generate", "callback_data": f"re2fa_{secret}", "icon_custom_emoji_id": EMOJI["refresh"], "style": "primary"}]]})
            bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=kb)
        except: bot.answer_callback_query(call.id, "Error generating 2FA Code!", show_alert=True)

    elif data == "apply_voucher":
        state[chat_id] = {"type": "wait_voucher_input"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>ভাউচার কোডটি নিচে লিখে সেন্ড করুন:</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
    elif data == "create_voucher" and is_admin(chat_id):
        state[chat_id] = {"type": "wait_voucher_code"}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>নতুন ভাউচার কোডটি লিখুন (যেমন: BONUS50):</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
    elif data == "list_vouchers" and is_admin(chat_id):
        if not db.get("vouchers"): return bot.answer_callback_query(call.id, "কোনো অ্যাক্টিভ ভাউচার নেই!", show_alert=True)
        msg = f'<tg-emoji emoji-id="{EMOJI["box"]}">📦</tg-emoji> <b>Active Vouchers:</b>\n\n'
        kb = []
        for code, v in db["vouchers"].items():
            used = len(v["used_by"])
            msg += f"কোড: <code>{code}</code> | {v['amount']}৳ ({v['amount']/db['settings']['dollarRate']:.2f} USD) | Limit: {used}/{v['limit']}\n"
            kb.append([{"text": f"Delete {code}", "callback_data": f"del_voucher_{code}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}])
        bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))
    elif data.startswith("del_voucher_") and is_admin(chat_id):
        code = data.replace("del_voucher_", "")
        if code in db.get("vouchers", {}):
            del db["vouchers"][code]; save_db()
            bot.answer_callback_query(call.id, "ভাউচার ডিলিট করা হয়েছে!", show_alert=True)
            bot.delete_message(chat_id, call.message.message_id)

    elif data.startswith("deposit_"):
        method = data.split("_")[1]
        state[chat_id] = {"type": "depositAmount", "method": method}
        emoji_id = PAYMENT_EMOJIS.get(method, EMOJI["money"])
        if method == "binance":
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{emoji_id}">💳</tg-emoji> <b>{method.upper()}</b>\nকত ডলার (USD) ডিপোজিট করবেন লিখুন:')
        else:
            bot.send_message(chat_id, f'<tg-emoji emoji-id="{emoji_id}">💳</tg-emoji> <b>{method.upper()}</b>\nকত টাকা ডিপোজিট করবেন লিখুন:')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
    elif data.startswith("paid_"):
        _, method, amount = data.split("_")
        state[chat_id] = {"type": "depositTxnId", "method": method, "amount": float(amount)}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["primary"]}">⚙️</tg-emoji> <b>Transaction ID (TrxID) দিন:</b>')
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        
    elif data.startswith("approve_") and is_admin(chat_id):
        dep_id = int(data.split("_")[1])
        for dep in db["deposits"]:
            if dep["id"] == dep_id and dep["status"] == "pending":
                txn_id = str(dep.get("txnId", "")).upper()
                if txn_id and txn_id in db.get("usedTxnIds", []):
                    return bot.answer_callback_query(call.id, "এই TrxID ইতিমধ্যে ব্যবহার হয়েছে!", show_alert=True)
                dep["status"] = "approved"
                dep["approvedBy"] = chat_id
                dep["approvedAt"] = datetime.now().isoformat()
                if txn_id:
                    db.setdefault("usedTxnIds", []).append(txn_id)
                db["users"][dep["userId"]]["balance"] += float(dep["amount"])
                save_db()
                try: bot.send_message(dep["userId"], f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>Deposit Approved!</b>\n\nAmount: <b>{dep["amount"]} BDT ({dep["amount"]/db["settings"]["dollarRate"]:.2f} USD)</b>\nআপনার ব্যালেন্স আপডেট হয়েছে। ধন্যবাদ!')
                except: pass
                try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["success"]}">✅</tg-emoji> Approved: {dep["amount"]} BDT ({dep["amount"]/db["settings"]["dollarRate"]:.2f} USD)', chat_id, call.message.message_id)
                except: pass
                break
    elif data.startswith("reject_") and is_admin(chat_id):
        dep_id = int(data.split("_")[1])
        for dep in db["deposits"]:
            if dep["id"] == dep_id and dep["status"] == "pending":
                dep["status"] = "rejected"; save_db()
                try: bot.send_message(dep["userId"], f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> <b>Deposit Rejected.</b>\n\nকোনো সমস্যা থাকলে সাপোর্টে যোগাযোগ করুন।')
                except: pass
                try: bot.edit_message_text(f'<tg-emoji emoji-id="{EMOJI["danger"]}">❌</tg-emoji> Rejected: {dep["amount"]} BDT ({dep["amount"]/db["settings"]["dollarRate"]:.2f} USD)', chat_id, call.message.message_id)
                except: pass
                break
    
    elif data.startswith("toggle_ban_") and is_admin(chat_id):
        uid = data.replace("toggle_ban_", "")
        if uid in db["users"]: 
            db["users"][uid]["banned"] = not db["users"][uid].get("banned"); save_db()
            msg, kb = get_user_profile(uid)
            try: bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=kb)
            except: pass
    elif data.startswith("addbal_") and is_admin(chat_id):
        state[chat_id] = {"type": "wait_addbal", "uid": data.replace("addbal_", "")}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>কত টাকা Add করবেন লিখুন:</b>')
    elif data.startswith("cutbal_") and is_admin(chat_id):
        state[chat_id] = {"type": "wait_cutbal", "uid": data.replace("cutbal_", "")}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> <b>কত টাকা Cut করবেন লিখুন:</b>')
    elif data.startswith("sendmsg_") and is_admin(chat_id):
        state[chat_id] = {"type": "wait_sendmsg", "uid": data.replace("sendmsg_", "")}
        bot.send_message(chat_id, f'<tg-emoji emoji-id="{EMOJI["mail"]}">✉️</tg-emoji> <b>ইউজারকে কী মেসেজ পাঠাতে চান তা লিখুন:</b>')
    
    elif data.startswith("cat_") or data.startswith("buyagain_"):
        is_buyagain = data.startswith("buyagain_")
        cat_id = data.replace("buyagain_", "") if is_buyagain else data.replace("cat_", "")
        cat_info = CATEGORIES[cat_id]
        products = [p for p in db["products"].values() if p.get("category") == cat_id]
        if not products: return bot.answer_callback_query(call.id, "এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই!", show_alert=True)
        
        is_reseller = chat_id in db["settings"].get("resellers", [])
        kb = []
        for p in products:
            actual_price = p.get("reseller_price", p["price"]) if is_reseller else p["price"]
            is_api = p.get("is_api", False)
            if cat_id == "vpn": 
                btn_text = f"{p['name']} | {actual_price}৳ ({actual_price/db['settings']['dollarRate']:.2f} USD)"
            elif is_api:
                btn_text = f"{p['name']} | {actual_price}৳ | [Auto API]"
            else:
                btn_text = f"{p['name']} | {actual_price}৳ | Stock: {len(p.get('stock', []))}"
            kb.append([{"text": btn_text, "callback_data": f"buy_{p['name']}", "icon_custom_emoji_id": cat_info["emoji"], "style": cat_info["style"]}])
        msg_text = f'<tg-emoji emoji-id="{cat_info["emoji"]}">📦</tg-emoji> <b>{cat_info["name"]} প্রোডাক্টস:</b>'
        msg_content = call.message.text or call.message.caption or ""
        is_product_msg = "অর্ডার সম্পন্ন" in msg_content or "অর্ডার রিকোয়েস্ট পাঠানো হয়েছে" in msg_content or "বাল্ক অর্ডার সম্পন্ন" in msg_content
        bot.answer_callback_query(call.id)
        if is_buyagain or is_product_msg: bot.send_message(chat_id, msg_text, reply_markup=json.dumps({"inline_keyboard": kb}))
        else:
            try: bot.edit_message_text(msg_text, chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))
            except: pass
    
    elif data.startswith("buy_"):
        prod_name = data.replace("buy_", "")
        if prod_name not in db["products"]: return bot.answer_callback_query(call.id, "প্রোডাক্ট পাওয়া যায়নি!", show_alert=True)
        product = db["products"][prod_name]
        cat_id = product.get("category", "")
        
        # ====== BULK MAIL MENU ======
        if cat_id in ["hotmail", "outlook", "froutlook"]:
            is_reseller = chat_id in db["settings"].get("resellers", [])
            actual_price = product.get("reseller_price", product["price"]) if is_reseller else product["price"]
            
            # API Product Notification on Buy Menu
            is_api = product.get("is_api", False)
            stock_display = "[API Auto Delivery]" if is_api else f"{len(product.get('stock', []))} pcs"
            
            msg_text = (f'<tg-emoji emoji-id="{EMOJI["sparkle"]}">✨</tg-emoji> <b>কয়টি নিতে চান</b> <tg-emoji emoji-id="{EMOJI["dev_boss"]}">👑</tg-emoji>\n'
                        f'━━━━━━━━━━━━━━━━━━\n'
                        f'<tg-emoji emoji-id="{EMOJI["pin"]}">📌</tg-emoji> Product: <b>{prod_name}</b>\n'
                        f'<tg-emoji emoji-id="{EMOJI["money"]}">💰</tg-emoji> Price: <b>{actual_price} BDT / pcs</b>\n'
                        f'<tg-emoji emoji-id="{EMOJI["stock"]}">⚙️</tg-emoji> Stock: <b>{stock_display}</b>')
            
            kb = [
                [{"text": "1 pcs", "callback_data": f"cbuy_{prod_name}_1", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "primary"},
                 {"text": "3 pcs", "callback_data": f"cbuy_{prod_name}_3", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "primary"}],
                [{"text": "5 pcs", "callback_data": f"cbuy_{prod_name}_5", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "primary"},
                 {"text": "10 pcs", "callback_data": f"cbuy_{prod_name}_10", "icon_custom_emoji_id": EMOJI["sparkle"], "style": "danger"}],
                [{"text": "Enter Quantity", "callback_data": f"cqty_{prod_name}", "icon_custom_emoji_id": EMOJI["pencil"], "style": "success"}],
                [{"text": "Back", "callback_data": f"cat_{cat_id}", "icon_custom_emoji_id": EMOJI["danger"], "style": "danger"}]
            ]
            try: bot.edit_message_text(msg_text, chat_id, call.message.message_id, reply_markup=json.dumps({"inline_keyboard": kb}))
            except: pass
        else:
            complete_purchase(chat_id, prod_name, 1, call.id)

    # ====== CUSTOM BULK HANDLERS ======
    elif data.startswith("cbuy_"):
        parts = data.split("_")
        prod_name = parts[1]
        qty = int(parts[2])
        complete_purchase(chat_id, prod_name, qty, call.id)
        
    elif data.startswith("cqty_"):
        prod_name = data.replace("cqty_", "")
        state[chat_id] = {"type": "wait_custom_qty", "prod": prod_name}
        msg = (f'<tg-emoji emoji-id="{EMOJI["pencil"]}">✏️</tg-emoji> <b>কতটি নিতে চান তা নিচে লিখে সেন্ড করুন:</b>\n'
               f'যেমন: 20')
        bot.send_message(chat_id, msg)
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass

print("🚀 TPP Shop Bot is Running with Dynamic Config, UI Editors & Premium Emojis!")
bot.set_my_commands([BotCommand("start", "Start")])
bot.infinity_polling(skip_pending=True)
