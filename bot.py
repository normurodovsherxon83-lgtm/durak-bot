import os, threading
import telebot
from flask import Flask
from telebot.types import (ReplyKeyboardMarkup, KeyboardButton,
                           MenuButtonWebApp, WebAppInfo)
from db import get_player
from bonus import exists, add_referral, INVITE
from api import api

SITE = "https://normurodovsherxon83-lgtm.github.io/durak-app/"
ADMIN = "@axrtge"
BOT_USER = "durak_xbot"

bot = telebot.TeleBot(os.environ["BOT_TOKEN"])
app = Flask(__name__)
app.register_blueprint(api)

# "Open" tugmasi (xabar yozish joyining yonida) saytni ochadi
try:
    bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="🎮 O'ynash",
                                     web_app=WebAppInfo(SITE)))
except Exception as e:
    print("Menu tugma xato:", e)

RULES = (
    "📖 Durak qoidalari\n\n"
    "• Karta to'plami: 24, 36 yoki 54 talik\n"
    "• Stolda ko'pi bilan 6 o'yinchi\n"
    "• O'yin oldidan stavka tanlanadi (kamida 10)\n"
    "• Durak (kartasi qolgan) stavkani to'laydi, "
    "pul yutganlarga teng bo'linadi\n"
    "• Ochko: olgan pul ulushining 1/10 qismi\n"
    "• Do'stlar yoki tasodifiy odamlar bilan, "
    "odam kelmasa 10 soniyadan keyin botlar qo'shiladi\n\n"
    "O'ynash uchun pastdagi 🎮 tugmani bosing."
)


def menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📖 Qoidalar"), KeyboardButton("📞 Murojaat"))
    kb.row(KeyboardButton("🎁 Do'st taklif qilish"))
    return kb


@app.route("/")
def home():
    return "OK"


@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    inviter = None
    parts = (m.text or "").split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            inviter = int(parts[1][4:])
        except ValueError:
            inviter = None
    try:
        is_new = not exists(uid)
        get_player(uid, m.from_user.first_name or "")
        if inviter and is_new and add_referral(uid, inviter):
            try:
                bot.send_message(
                    inviter,
                    f"🎉 Do'stingiz qo'shildi! +{INVITE} pul berildi.")
            except Exception as e:
                print("Taklif xabari xato:", e)
    except Exception as e:
        print("DB xato:", e)
    bot.send_message(m.chat.id,
                     "Durak X o'yiniga xush kelibsiz! 🎴\n"
                     "O'ynash uchun pastdagi 🎮 tugmani bosing.",
                     reply_markup=menu())


@bot.message_handler(func=lambda m: m.text == "📖 Qoidalar")
def rules(m):
    bot.send_message(m.chat.id, RULES, reply_markup=menu())


@bot.message_handler(func=lambda m: m.text == "📞 Murojaat")
def contact(m):
    bot.send_message(m.chat.id,
                     f"✉️ Savol, taklif yoki shikoyat uchun adminga yozing: {ADMIN}",
                     reply_markup=menu())


@bot.message_handler(func=lambda m: m.text == "🎁 Do'st taklif qilish")
def invite(m):
    link = f"https://t.me/{BOT_USER}?start=ref_{m.from_user.id}"
    bot.send_message(m.chat.id,
                     f"🎁 Do'stingizni taklif qiling, u birinchi marta "
                     f"kirsa sizga +{INVITE} pul beriladi.\n\n"
                     f"Sizning havolangiz:\n{link}",
                     reply_markup=menu())


threading.Thread(target=bot.infinity_polling, daemon=True).start()
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
