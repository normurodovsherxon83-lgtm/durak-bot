import os, threading
import telebot
from flask import Flask
from telebot.types import (ReplyKeyboardMarkup, KeyboardButton,
                           MenuButtonWebApp, WebAppInfo,
                           InlineKeyboardMarkup, InlineKeyboardButton,
                           LabeledPrice)
from db import get_player
from bonus import exists, add_referral, INVITE
from api import api
from shop import shop, PACKS, deliver

SITE = "https://normurodovsherxon83-lgtm.github.io/durak-app/"
ADMIN = "@axrtge"
BOT_USER = "durak_xbot"

bot = telebot.TeleBot(os.environ["BOT_TOKEN"])
app = Flask(__name__)
app.register_blueprint(api)
app.register_blueprint(shop)

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
    kb.row(KeyboardButton("🎁 Do'st taklif qilish"),
           KeyboardButton("💰 Pul sotib olish"))
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


# ---------- Telegram Stars orqali pul sotib olish ----------

@bot.message_handler(func=lambda m: m.text == "💰 Pul sotib olish")
def shop_menu(m):
    kb = InlineKeyboardMarkup()
    for key, (stars, coins) in PACKS.items():
        kb.add(InlineKeyboardButton(f"⭐ {stars} Stars → {coins} pul",
                                    callback_data=f"buy_{key}"))
    bot.send_message(m.chat.id,
                     "💰 O'yin pulini Telegram Stars bilan sotib oling:",
                     reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy(c):
    key = c.data[4:]
    if key not in PACKS:
        bot.answer_callback_query(c.id, "Xato paket")
        return
    stars, coins = PACKS[key]
    bot.answer_callback_query(c.id)
    bot.send_invoice(
        chat_id=c.message.chat.id,
        title=f"{coins} o'yin puli",
        description=f"Durak X uchun {coins} pul",
        invoice_payload=key,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{coins} pul", amount=stars)],
    )


@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def paid(m):
    try:
        bot.send_message(
            m.chat.id,
            deliver(m.from_user.id, m.successful_payment.invoice_payload),
            reply_markup=menu())
    except Exception as e:
        print("To'lov xato:", e)
        bot.send_message(
            m.chat.id,
            f"⚠️ To'lov o'tdi, lekin yetkazilmadi. Adminga yozing: {ADMIN}")


threading.Thread(target=bot.infinity_polling, daemon=True).start()
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
