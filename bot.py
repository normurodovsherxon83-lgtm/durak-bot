import os, threading
import telebot
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from db import get_player, top

bot = telebot.TeleBot(os.environ["BOT_TOKEN"])
app = Flask(__name__)


@app.route("/")
def home():
    return "OK"


@bot.message_handler(commands=["start"])
def start(m):
    try:
        get_player(m.from_user.id, m.from_user.first_name or "")
    except Exception as e:
        print("DB xato:", e)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(
        "Join game",
        web_app=WebAppInfo("https://normurodovsherxon83-lgtm.github.io/durak-app/")))
    bot.send_message(m.chat.id, "Durak o'yiniga xush kelibsiz!", reply_markup=kb)


@bot.message_handler(commands=["profil"])
def profil(m):
    try:
        p = get_player(m.from_user.id, m.from_user.first_name or "")
        bot.send_message(m.chat.id,
                         f"💰 Balans: {p['balance']}\n⭐ Ochko: {p['points']}")
    except Exception as e:
        print("DB xato:", e)
        bot.send_message(m.chat.id, f"Baza xatosi: {type(e).__name__}: {str(e)[:300]}")


def reyting_matni(by, sarlavha):
    rows = top(by, 10)
    if not rows:
        return "Hozircha reyting bo'sh."
    qatorlar = [f"{i}. {r['name'] or 'Nomsiz'} — {r[by]}"
                for i, r in enumerate(rows, 1)]
    return sarlavha + "\n" + "\n".join(qatorlar)


@bot.message_handler(commands=["reyting"])
def reyting(m):
    try:
        bot.send_message(m.chat.id, reyting_matni("points", "⭐ Ochko reytingi"))
    except Exception as e:
        print("DB xato:", e)
        bot.send_message(m.chat.id, f"Baza xatosi: {type(e).__name__}: {str(e)[:300]}")


@bot.message_handler(commands=["valyuta"])
def valyuta(m):
    try:
        bot.send_message(m.chat.id, reyting_matni("balance", "💰 Valyuta reytingi"))
    except Exception as e:
        print("DB xato:", e)
        bot.send_message(m.chat.id, f"Baza xatosi: {type(e).__name__}: {str(e)[:300]}")


threading.Thread(target=bot.infinity_polling, daemon=True).start()
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
