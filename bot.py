from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)
from datetime import datetime, timedelta
import sqlite3

# ================== الإعدادات ==================
TOKEN = "8137604284:AAF_qkKxOrtOzfhr6JyE0TYZcynwgA8mUFw"
OWNER_ID = 1251617149
DB_NAME = "data.db"

user_state = {}

# ================== قاعدة البيانات ==================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        password TEXT,
        line_type TEXT,
        price INTEGER,
        owner_name TEXT,
        notes TEXT,
        renew_date TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ================== أدوات ==================
def calc_renew(line_type):
    days = 31 if line_type == "اونر" else 28
    return (datetime.now() + timedelta(days=days)).strftime("%d-%m-%Y")

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["➕ تسجيل رقم", "🔍 بحث"],
            ["📊 إحصائيات"]
        ],
        resize_keyboard=True
    )

# ================== أوامر ==================
def start(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("❌ غير مصرح")
        return
    update.message.reply_text("👋 أهلاً بيك", reply_markup=main_menu())

# ================== التسجيل ==================
def register_start(update: Update, context: CallbackContext):
    user_state[update.effective_chat.id] = {"step": "phone"}
    update.message.reply_text("📱 ابعت رقم الموبايل:")

def register_handler(update: Update, context: CallbackContext):
    cid = update.effective_chat.id
    text = update.message.text

    if cid not in user_state:
        return

    step = user_state[cid]["step"]

    if step == "phone":
        user_state[cid]["phone"] = text
        user_state[cid]["step"] = "password"
        update.message.reply_text("🔑 ابعت كلمة السر:")

    elif step == "password":
        user_state[cid]["password"] = text
        user_state[cid]["step"] = "type"
        update.message.reply_text(
            "📶 اختر نوع الخط:",
            reply_markup=ReplyKeyboardMarkup(
                [["فردي", "اونر"]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    elif step == "type":
        user_state[cid]["type"] = text
        user_state[cid]["step"] = "price"
        update.message.reply_text("💰 ابعت السعر:")

    elif step == "price":
        user_state[cid]["price"] = int(text)
        user_state[cid]["step"] = "name"
        update.message.reply_text(
            "👑 اسم الأونر (اختياري):",
            reply_markup=ReplyKeyboardMarkup(
                [["⏭ تخطي"]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    elif step == "name":
        user_state[cid]["owner_name"] = "" if text == "⏭ تخطي" else text
        user_state[cid]["step"] = "notes"
        update.message.reply_text("📝 ملاحظات (او ⏭ تخطي):")

    elif step == "notes":
        notes = "" if "تخطي" in text else text
        data = user_state[cid]

        renew = calc_renew(data["type"])
        now = datetime.now().strftime("%d-%m-%Y %H:%M")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("""
            INSERT INTO numbers
            (phone,password,line_type,price,owner_name,notes,renew_date,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """, (
                data["phone"],
                data["password"],
                data["type"],
                data["price"],
                data["owner_name"],
                notes,
                renew,
                now
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            update.message.reply_text("⚠️ الرقم مسجل قبل كده")
            conn.close()
            user_state.pop(cid)
            return

        conn.close()
        user_state.pop(cid)

        update.message.reply_text(
            f"✅ تم الحفظ\n\n"
            f"📱 {data['phone']}\n"
            f"📶 {data['type']}\n"
            f"💰 {data['price']}\n"
            f"📅 التجديد: {renew}",
            reply_markup=main_menu()
        )

# ================== البحث ==================
def search_start(update: Update, context: CallbackContext):
    update.message.reply_text("🔍 ابعت رقم الموبايل:")

def search_handler(update: Update, context: CallbackContext):
    phone = update.message.text
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM numbers WHERE phone=?", (phone,))
    row = c.fetchone()
    conn.close()

    if not row:
        update.message.reply_text("❌ الرقم مش موجود")
        return

    update.message.reply_text(
        f"📱 {row[1]}\n"
        f"🔑 {row[2]}\n"
        f"📶 {row[3]}\n"
        f"💰 {row[4]}\n"
        f"👑 {row[5]}\n"
        f"📝 {row[6]}\n"
        f"📅 التجديد: {row[7]}"
    )

# ================== الإحصائيات ==================
def stats(update: Update, context: CallbackContext):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(price) FROM numbers")
    total, money = c.fetchone()
    conn.close()

    update.message.reply_text(
        f"📊 الإحصائيات\n"
        f"📦 عدد الخطوط: {total}\n"
        f"💰 إجمالي الفلوس: {money or 0}"
    )

# ================== الرسائل ==================
def text_router(update: Update, context: CallbackContext):
    text = update.message.text

    if text == "➕ تسجيل رقم":
        register_start(update, context)
    elif text == "🔍 بحث":
        search_start(update, context)
    elif text == "📊 إحصائيات":
        stats(update, context)
    else:
        register_handler(update, context)

# ================== التشغيل ==================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_router))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
