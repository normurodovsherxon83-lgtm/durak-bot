import os, threading
import telebot
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

bot = telebot.TeleBot(os.environ["8671616808:AAHXsTvOKEyA_qYdGpaRTgVZsj-Ry9gzqHs"])
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

@bot.message_handler(commands=["start"])
def start(m):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Join game", web_app=WebAppInfo("https://normurodovsherxon83-lgtm.github.io/durak-app/")))
    bot.send_message(m.chat.id, "Durak o'yiniga xush kelibsiz!", reply_markup=kb)

threading.Thread(target=bot.infinity_polling, daemon=True).start()
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
