import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = "7708286324:AAHmtv15lEf0TAVMT0nBiJq8nvAuT9ymK4U"
ADMIN_ID = 8372285180

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- RENDER UCHUN FLASK SERVER ---
app = Flask('')


@app.route('/')
def home():
    return "UserInfoBot ishlayapti!"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


# --- BAZA BILAN ISHLASH ---
def db_connect():
    return sqlite3.connect("userinfo_bot.db", check_same_thread=False)


def init_db():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users
                   (
                       user_id
                       INTEGER
                       PRIMARY
                       KEY,
                       username
                       TEXT,
                       full_name
                       TEXT,
                       language_code
                       TEXT
                   )
                   """)
    conn.commit()
    conn.close()


init_db()


# --- START VA MA'LUMOT BERISH ---
@bot.message_handler(commands=['start', 'id', 'info'])
def send_user_info(message):
    user = message.from_user
    chat = message.chat

    # Foydalanuvchini bazaga saqlash
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, language_code) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.first_name, user.language_code)
    )
    conn.commit()
    conn.close()

    first_name = user.first_name or "Ko'rsatilmagan"
    last_name = user.last_name or "Yo'q"
    username = f"@{user.username}" if user.username else "Username mavjud emas"
    lang = user.language_code or "Noma'lum"

    info_text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 <b>ID raqami:</b> <code>{user.id}</code>\n"
        f"🏷 <b>Ismi:</b> {first_name}\n"
        f"💬 <b>Familyasi:</b> {last_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🌐 <b>Til kodi:</b> {lang}\n\n"
        f"📌 <b>Chat ma'lumotlari:</b>\n"
        f"💬 <b>Chat ID:</b> <code>{chat.id}</code>\n"
        f"📂 <b>Chat turi:</b> {chat.type}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="📋 ID ni nusxalash", callback_data=f"copy_id_{user.id}"))

    # Agar admin yozayotgan bo'lsa, Admin panel tugmasini ham qo'shamiz
    if user.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_panel"))

    bot.send_message(chat.id, info_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_id_"))
def callback_copy_id(call):
    user_id = call.data.split("_")[2]
    bot.answer_callback_query(call.id, text=f"Sizning ID raqamingiz: {user_id}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def callback_admin_panel(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Siz admin emassiz!", show_alert=True)
        return

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()

    admin_text = (
        f"⚙️ <b>Admin Panel</b>\n\n"
        f"📊 Botdagi jami foydalanuvchilar: <b>{count} ta</b>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="👥 Foydalanuvchilar ro'yxati", callback_data="admin_users_list"))

    try:
        bot.edit_message_text(admin_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, admin_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_users_list")
def callback_users_list(call):
    if call.from_user.id != ADMIN_ID:
        return

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, username FROM users LIMIT 20")
    users = cursor.fetchall()
    conn.close()

    text = "👥 <b>So'nggi foydalanuvchilar (20 ta):</b>\n\n"
    for u in users:
        uname = f"@{u[2]}" if u[2] else "yo'q"
        text += f"• {u[1]} | ID: <code>{u[0]}</code> | {uname}\n"

    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)


# Boshqa xabarlar uchun ham ID chiqarib berish
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user = message.from_user

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, language_code) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.first_name, user.language_code)
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"👤 <b>Sizning ma'lumotlaringiz:</b>\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🏷 Ism: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'yoq'}"
    )


if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()

    print("UserInfoBot ishga tushdi...")
    bot.infinity_polling()