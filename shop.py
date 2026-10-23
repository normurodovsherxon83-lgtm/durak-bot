import os, json, hmac, hashlib, random
from urllib.parse import parse_qsl
import requests
from flask import Blueprint, request, jsonify
from db import db, get_player, add_balance

TOKEN = os.environ["BOT_TOKEN"]
shop = Blueprint("shop", __name__)

PACKS = {"s25": (25, 250), "s50": (50, 550), "s100": (100, 1200),
         "s250": (250, 3250), "s500": (500, 7000), "s1000": (1000, 15000)}

ITEMS = {}


def add(t, rows):
    for i, n, p, c, r, v in rows:
        ITEMS[i] = dict(id=i, t=t, n=n, p=p, c=c, r=r, v=v)


add("bg", [
    ("b1", "Yashil sukno", 500, "coin", "common", "#14532d,#22c55e"),
    ("b2", "Ko'k tun", 700, "coin", "common", "#0c1a4d,#1d4ed8"),
    ("b3", "Qizil baxmal", 900, "coin", "common", "#450a0a,#dc2626"),
    ("b4", "Binafsha", 1100, "coin", "common", "#3b0764,#9333ea"),
    ("b5", "Qora fon", 1300, "coin", "common", "#000000,#374151"),
    ("b6", "Yog'och", 1500, "coin", "common", "#451a03,#a16207"),
    ("b7", "Oltin chiziq", 3000, "coin", "rare", "#422006,#facc15"),
    ("b8", "Okean", 4000, "coin", "rare", "#083344,#06b6d4"),
    ("b9", "Shimol nuri", 5000, "coin", "rare", "#052e16,#34d399"),
    ("b10", "Neon shahar", 6000, "coin", "rare", "#4a044e,#22d3ee"),
    ("b11", "Olov", 150, "star", "legend", "#7f1d1d,#f97316"),
    ("b12", "Kosmos", 250, "star", "legend", "#020617,#7c3aed"),
])
add("av", [
    ("a1", "Tulki", 2000, "coin", "common", "🦊"),
    ("a2", "Bo'ri", 2400, "coin", "common", "🐺"),
    ("a3", "Sher", 2800, "coin", "common", "🦁"),
    ("a4", "Yo'lbars", 3200, "coin", "common", "🐯"),
    ("a5", "Ayiq", 3600, "coin", "common", "🐻"),
    ("a6", "Burgut", 4000, "coin", "common", "🦅"),
    ("a7", "Ajdaho", 8000, "coin", "rare", "🐉"),
    ("a8", "Yakkashox", 10000, "coin", "rare", "🦄"),
    ("a9", "Ninja", 12000, "coin", "rare", "🥷"),
    ("a10", "Shoh", 15000, "coin", "rare", "🤴"),
    ("a11", "Feniks", 100, "star", "legend", "🔥"),
    ("a12", "Olmos shoh", 300, "star", "legend", "💎"),
])

CHESTS = {
    "c_common": dict(n="Oddiy", e="🟤", p=100, c="coin", rng=(20, 150), ch=0, rar=()),
    "c_silver": dict(n="Kumush", e="🔵", p=500, c="coin", rng=(100, 800), ch=.1, rar=("common",)),
    "c_gold": dict(n="Oltin", e="🟡", p=1500, c="coin", rng=(400, 2400), ch=.3, rar=("common", "rare")),
    "c_diamond": dict(n="Olmos", e="💎", p=50, c="star", rng=(2000, 10000), ch=1, rar=("rare", "legend")),
}


def verify(init):
    try:
        d = dict(parse_qsl(init, keep_blank_values=True))
        h = d.pop("hash", "")
        s = "\n".join(f"{k}={v}" for k, v in sorted(d.items()))
        key = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
        ok = hmac.new(key, s.encode(), hashlib.sha256).hexdigest()
        return json.loads(d["user"])["id"] if hmac.compare_digest(ok, h) else None
    except Exception:
        return None


def pts(it):
    return it["p"] * (12 if it["c"] == "star" else 1) / 20


def give(uid, iid, points=0):
    p = get_player(uid)
    own = p.get("owned") or []
    if iid in own:
        return False
    db().table("players").update({
        "owned": own + [iid],
        "points": float(p["points"]) + points}).eq("tg_id", uid).execute()
    return True


def open_chest(uid, cid):
    c = CHESTS[cid]
    coins = random.randint(*c["rng"])
    got = None
    if random.random() < c["ch"]:
        own = get_player(uid).get("owned") or []
        pool = [i for i in ITEMS.values()
                if i["r"] in c["rar"] and i["id"] not in own]
        if pool:
            got = random.choice(pool)
            give(uid, got["id"])
    new = add_balance(uid, coins)
    return coins, got, new


def deliver(uid, key):
    """Stars to'lovidan keyin chaqiriladi."""
    if key in PACKS:
        new = add_balance(uid, PACKS[key][1])
        return f"✅ +{PACKS[key][1]} pul. Balans: {new}"
    if key in ITEMS:
        it = ITEMS[key]
        give(uid, key, pts(it))
        return f"✅ {it['n']} sizniki!"
    if key == "c_diamond":
        coins, got, new = open_chest(uid, key)
        return f"💎 +{coins} pul" + (f"\n🎉 {got['n']}" if got else "")
    return "✅ To'lov qabul qilindi"


@shop.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r


def who():
    d = request.get_json(silent=True) or {}
    return verify(d.get("initData", "")), d


def err(m, code=400):
    return jsonify(error=m), code


@shop.route("/api/shop/me", methods=["POST"])
def me():
    u, d = who()
    if not u:
        return err("Kirish xatosi", 401)
    p = get_player(u)
    return jsonify(
        balance=int(p["balance"]), points=float(p["points"]),
        owned=p.get("owned") or [], avatar=p.get("avatar") or "",
        bg=p.get("bg") or "", items=list(ITEMS.values()),
        chests=[dict(id=k, **v) for k, v in CHESTS.items()],
        packs=[dict(id=k, stars=v[0], coins=v[1]) for k, v in PACKS.items()])


@shop.route("/api/shop/buy", methods=["POST"])
def buy():
    u, d = who()
    if not u:
        return err("Kirish xatosi", 401)
    it = ITEMS.get(d.get("id"))
    if not it or it["c"] != "coin":
        return err("Xato")
    p = get_player(u)
    own = p.get("owned") or []
    if it["id"] in own:
        return err("Sizda bor")
    if int(p["balance"]) < it["p"]:
        return err("Pul yetmaydi")
    db().table("players").update({
        "balance": int(p["balance"]) - it["p"],
        "owned": own + [it["id"]],
        "points": float(p["points"]) + pts(it)}).eq("tg_id", u).execute()
    return jsonify(ok=True)


@shop.route("/api/shop/equip", methods=["POST"])
def equip():
    u, d = who()
    if not u:
        return err("Kirish xatosi", 401)
    it = ITEMS.get(d.get("id"))
    if not it or it["id"] not in (get_player(u).get("owned") or []):
        return err("Sizda yo'q")
    col = "avatar" if it["t"] == "av" else "bg"
    db().table("players").update({col: it["id"]}).eq("tg_id", u).execute()
    return jsonify(ok=True)


@shop.route("/api/shop/chest", methods=["POST"])
def chest():
    u, d = who()
    if not u:
        return err("Kirish xatosi", 401)
    c = CHESTS.get(d.get("id"))
    if not c or c["c"] != "coin":
        return err("Xato")
    p = get_player(u)
    if int(p["balance"]) < c["p"]:
        return err("Pul yetmaydi")
    db().table("players").update(
        {"balance": int(p["balance"]) - c["p"]}).eq("tg_id", u).execute()
    coins, got, new = open_chest(u, d["id"])
    return jsonify(coins=coins, item=got["n"] if got else None, balance=new)


@shop.route("/api/shop/invoice", methods=["POST"])
def invoice():
    u, d = who()
    if not u:
        return err("Kirish xatosi", 401)
    k = d.get("id")
    if k in PACKS:
        stars, title = PACKS[k][0], f"{PACKS[k][1]} pul"
    elif k in ITEMS and ITEMS[k]["c"] == "star":
        if k in (get_player(u).get("owned") or []):
            return err("Sizda bor")
        stars, title = ITEMS[k]["p"], ITEMS[k]["n"]
    elif k == "c_diamond":
        stars, title = CHESTS[k]["p"], "Olmos sandiq"
    else:
        return err("Xato")
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/createInvoiceLink",
        json={"title": title, "description": title + " - Durak X",
              "payload": k, "provider_token": "", "currency": "XTR",
              "prices": [{"label": title, "amount": stars}]},
        timeout=15).json()
    return jsonify(url=r.get("result")) if r.get("ok") else err("Invoice xato")
