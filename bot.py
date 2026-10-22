import hashlib
import hmac
import json
import os
import time
from functools import wraps
from urllib.parse import parse_qsl

from flask import Blueprint, jsonify, request

from db import get_player, save_result
from durak import MIN_STAKE
from tables import Lobby

api = Blueprint("api", __name__)
lobby = Lobby()
saved = set()
ORIGIN = "https://normurodovsherxon83-lgtm.github.io"


# ---------- CORS (Mini App GitHub Pages'dan so'raydi) ----------
@api.before_request
def preflight():
    if request.method == "OPTIONS":
        return "", 204


@api.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = ORIGIN
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return resp


# ---------- Telegram initData tekshiruvi ----------
def check_init_data(init_data):
    data = dict(parse_qsl(init_data or "", keep_blank_values=True))
    their_hash = data.pop("hash", None)
    if not their_hash or "user" not in data:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", os.environ["BOT_TOKEN"].encode(),
                      hashlib.sha256).digest()
    mine = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mine, their_hash):
        return None
    if time.time() - int(data.get("auth_date", 0)) > 86400:
        return None
    return json.loads(data["user"])


def auth(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        body = request.get_json(silent=True) or {}
        user = check_init_data(body.get("initData"))
        if not user:
            return jsonify(ok=False, error="Ruxsat yo'q"), 401
        return fn(user, body, *a, **kw)
    return wrapper


def err(msg, code=400):
    return jsonify(ok=False, error=msg), code


def clean_params(body):
    try:
        size = int(body.get("size", 36))
        stake = int(body.get("stake", MIN_STAKE))
        mx = int(body.get("max_players", 2))
    except (TypeError, ValueError):
        return None
    if size not in (24, 36, 54) or stake < MIN_STAKE or not 2 <= mx <= 6:
        return None
    return size, stake, mx


def join_table(t, user):
    p = get_player(user["id"], user.get("first_name", ""))
    return t.join(user["id"], user.get("first_name", "") or "Nomsiz",
                  float(p["balance"]))


def finish_if_done(t):
    if t.status == "done" and t.code not in saved and t.result:
        saved.add(t.code)
        r = t.result
        humans = [(i, b, p) for i, (b, p, bot) in
                  enumerate(zip(r["balances"], r["points"], r["bots"]))
                  if not bot]
        try:
            save_result([r["ids"][i] for i, _, _ in humans],
                        [b for _, b, _ in humans],
                        [p for _, _, p in humans])
        except Exception as e:
            print("Natijani saqlashda xato:", e)


# ---------- manzillar ----------
@api.route("/api/me", methods=["POST", "OPTIONS"])
@auth
def me(user, body):
    p = get_player(user["id"], user.get("first_name", ""))
    return jsonify(ok=True, balance=p["balance"], points=p["points"])


@api.route("/api/create", methods=["POST", "OPTIONS"])
@auth
def create(user, body):
    prm = clean_params(body)
    if not prm:
        return err("Noto'g'ri sozlama")
    t = lobby.create(*prm, public=False)
    ok, msg = join_table(t, user)
    if not ok:
        return err(msg)
    return jsonify(ok=True, state=t.state_for(user["id"]))


@api.route("/api/random", methods=["POST", "OPTIONS"])
@auth
def random_table(user, body):
    prm = clean_params(body)
    if not prm:
        return err("Noto'g'ri sozlama")
    t = lobby.find_random(*prm)
    ok, msg = join_table(t, user)
    if not ok:
        return err(msg)
    if len(t.players) >= t.max_players:
        t.start()
    return jsonify(ok=True, state=t.state_for(user["id"]))


@api.route("/api/join", methods=["POST", "OPTIONS"])
@auth
def join(user, body):
    t = lobby.get(str(body.get("code", "")))
    if not t:
        return err("Stol topilmadi", 404)
    ok, msg = join_table(t, user)
    if not ok:
        return err(msg)
    return jsonify(ok=True, state=t.state_for(user["id"]))


@api.route("/api/start", methods=["POST", "OPTIONS"])
@auth
def start(user, body):
    t = lobby.get(str(body.get("code", "")))
    if not t:
        return err("Stol topilmadi", 404)
    if not t.players or t.players[0]["id"] != user["id"]:
        return err("Faqat stol egasi boshlaydi")
    if not t.start():
        return err("Kamida 2 o'yinchi kerak")
    return jsonify(ok=True, state=t.state_for(user["id"]))


@api.route("/api/state", methods=["POST", "OPTIONS"])
@auth
def state(user, body):
    t = lobby.get(str(body.get("code", "")))
    if not t or t.index_of(user["id"]) is None:
        return err("Stol topilmadi", 404)
    return jsonify(ok=True, state=t.state_for(user["id"]))


@api.route("/api/act", methods=["POST", "OPTIONS"])
@auth
def act(user, body):
    t = lobby.get(str(body.get("code", "")))
    if not t:
        return err("Stol topilmadi", 404)
    ok, msg = t.act(user["id"], body.get("action"),
                    card=body.get("card"), target=body.get("target"))
    finish_if_done(t)
    if not ok:
        return err(msg)
    return jsonify(ok=True, state=t.state_for(user["id"]))
