import os, threading
import telebot
from flask import Flask
from telebot.types import (ReplyKeyboardMarkup, KeyboardButton,
                           MenuButtonWebApp, WebAppInfo)
from db import get_player
from api import api

SITE = "https://normurodovsherxon83-lgtm.github.io/durak-app/"
ADMIN = "@axrtge"

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
    return kb


@app.route("/")
def home():
    return "OK"


@bot.message_handler(commands=["start"])
def start(m):
    try:
        get_player(m.from_user.id, m.from_user.first_name or "")
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


threading.Thread(target=bot.infinity_polling, daemon=True).start()
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
