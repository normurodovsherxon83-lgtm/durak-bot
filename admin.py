import os, time, threading
import requests
from flask import Blueprint, request, jsonify
from db import db, get_player
import shop as S

admin = Blueprint("admin", __name__)

ADMINS = set()
for x in os.environ.get("ADMIN_IDS", "").replace(" ", "").split(","):
    if x.lstrip("-").isdigit():
        ADMINS.add(int(x))

DEFAULT_CFG = dict(daily_bonus=1000, referral_bonus=100, start_balance=100,
                   min_stake=100, max_stake=100000, points_div=10)
CONFIG = dict(DEFAULT_CFG)


def cfg(key, default=None):
    """Boshqa fayllar sozlamani shu orqali oladi: from admin import cfg"""
    return CONFIG.get(key, DEFAULT_CFG.get(key, default))


# ---------- Supabase 'settings' jadvali ----------
def kv_get(k):
    try:
        r = db().table("settings").select("value").eq("key", k).execute().data
        return r[0]["value"] if r else None
    except Exception:
        return None


def kv_set(k, v):
    db().table("settings").upsert({"key": k, "value": v}).execute()


def save_items():
    kv_set("items", S.ITEMS)


def save_chests():
    kv_set("chests", {k: {**v, "rng": list(v["rng"]), "rar": list(v["rar"])}
                      for k, v in S.CHESTS.items()})


def save_packs():
    kv_set("packs", {k: list(v) for k, v in S.PACKS.items()})


def load():
    try:
        c = kv_get("config")
        if c:
            CONFIG.update(c)
        it = kv_get("items")
        if it is not None:
            S.ITEMS.clear()
            S.ITEMS.update(it)
        ch = kv_get("chests")
        if ch is not None:
            S.CHESTS.clear()
            for k, v in ch.items():
                v["rng"] = tuple(v["rng"])
                v["rar"] = tuple(v["rar"])
                S.CHESTS[k] = v
        pk = kv_get("packs")
        if pk is not None:
            S.PACKS.clear()
            for k, v in pk.items():
                S.PACKS[k] = (int(v[0]), int(v[1]))
    except Exception as e:
        print("admin load xato:", e)


admin.record_once(lambda state: load())


@admin.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r


def who():
    d = request.get_json(silent=True) or {}
    u = S.verify(d.get("initData", ""))
    return (u if u in ADMINS else None), d


def deny():
    return S.err("Ruxsat yo'q", 403)


# ---------- Holat ----------
@admin.route("/api/admin/state", methods=["POST"])
def state():
    u, d = who()
    if not u:
        return deny()
    res = db().table("players").select("balance,points", count="exact").limit(1000).execute()
    rows = res.data or []
    stats = dict(players=res.count if res.count is not None else len(rows),
                 balance=sum(float(r.get("balance") or 0) for r in rows),
                 points=sum(float(r.get("points") or 0) for r in rows))
    return jsonify(
        items=list(S.ITEMS.values()),
        chests=[dict(id=k, **v) for k, v in S.CHESTS.items()],
        packs=[dict(id=k, stars=v[0], coins=v[1]) for k, v in S.PACKS.items()],
        config=CONFIG, stats=stats)


# ---------- Sozlamalar ----------
@admin.route("/api/admin/config", methods=["POST"])
def config():
    u, d = who()
    if not u:
        return deny()
    new = d.get("config") or {}
    for k in DEFAULT_CFG:
        if k in new:
            try:
                CONFIG[k] = int(float(new[k]))
            except Exception:
                return S.err("Son kiriting: " + k)
    kv_set("config", CONFIG)
    return jsonify(ok=True)


# ---------- Avatar / fon ----------
@admin.route("/api/admin/item", methods=["POST"])
def item():
    u, d = who()
    if not u:
        return deny()
    it = d.get("item") or {}
    iid = str(it.get("id", "")).strip()
    if not iid or it.get("t") not in ("av", "bg") or it.get("c") not in ("coin", "star"):
        return S.err("Xato ma'lumot")
    try:
        p = int(it.get("p", 0))
    except Exception:
        return S.err("Narx son bo'lsin")
    S.ITEMS[iid] = dict(id=iid, t=it["t"], n=str(it.get("n", ""))[:40], p=p, c=it["c"],
                        r=it.get("r", "common"), v=str(it.get("v", "")))
    save_items()
    return jsonify(ok=True)


@admin.route("/api/admin/item_del", methods=["POST"])
def item_del():
    u, d = who()
    if not u:
        return deny()
    S.ITEMS.pop(d.get("id"), None)
    save_items()
    return jsonify(ok=True)


# ---------- Sandiqlar ----------
@admin.route("/api/admin/chest", methods=["POST"])
def chest():
    u, d = who()
    if not u:
        return deny()
    c = d.get("chest") or {}
    cid = str(c.get("id", "")).strip()
    if not cid.startswith("c_"):
        return S.err("ID 'c_' bilan boshlansin")
    try:
        lo, hi = int(c["rng"][0]), int(c["rng"][1])
        S.CHESTS[cid] = dict(
            n=str(c.get("n", ""))[:30], e=str(c.get("e", "🎁"))[:4], p=int(c["p"]),
            c="star" if cid == "c_diamond" else "coin", rng=(min(lo, hi), max(lo, hi)),
            ch=max(0.0, min(1.0, float(c.get("ch", 0)))),
            rar=tuple(x for x in c.get("rar", []) if x in ("common", "rare", "epic", "legend")))
    except Exception:
        return S.err("Xato ma'lumot")
    save_chests()
    return jsonify(ok=True)


@admin.route("/api/admin/chest_del", methods=["POST"])
def chest_del():
    u, d = who()
    if not u:
        return deny()
    if d.get("id") != "c_diamond":
        S.CHESTS.pop(d.get("id"), None)
        save_chests()
    return jsonify(ok=True)


# ---------- Pul paketlari ----------
@admin.route("/api/admin/pack", methods=["POST"])
def pack():
    u, d = who()
    if not u:
        return deny()
    p = d.get("pack") or {}
    pid = str(p.get("id", "")).strip()
    try:
        stars, coins = int(p["stars"]), int(p["coins"])
    except Exception:
        return S.err("Son kiriting")
    if not pid or stars < 1 or coins < 1:
        return S.err("Xato ma'lumot")
    S.PACKS[pid] = (stars, coins)
    save_packs()
    return jsonify(ok=True)


@admin.route("/api/admin/pack_del", methods=["POST"])
def pack_del():
    u, d = who()
    if not u:
        return deny()
    S.PACKS.pop(d.get("id"), None)
    save_packs()
    return jsonify(ok=True)


# ---------- O'yinchilar ----------
def pub(p):
    return dict(tg_id=p["tg_id"], name=p.get("name"), balance=int(p.get("balance") or 0),
                points=float(p.get("points") or 0), owned=p.get("owned") or [],
                avatar=p.get("avatar") or "", bg=p.get("bg") or "")


@admin.route("/api/admin/find", methods=["POST"])
def find():
    u, d = who()
    if not u:
        return deny()
    q = str(d.get("q", "")).strip()
    t = db().table("players").select("tg_id,name,balance,points,owned,avatar,bg")
    if q.isdigit():
        t = t.eq("tg_id", int(q))
    elif q:
        t = t.ilike("name", f"%{q}%")
    else:
        t = t.order("points", desc=True)
    return jsonify(players=[pub(p) for p in (t.limit(20).execute().data or [])])


@admin.route("/api/admin/player", methods=["POST"])
def player():
    u, d = who()
    if not u:
        return deny()
    try:
        tid = int(d["tg_id"])
        p = get_player(tid)
        upd = {"balance": max(0, int(p["balance"]) + int(float(d.get("balance") or 0))),
               "points": max(0.0, float(p["points"]) + float(d.get("points") or 0))}
    except Exception:
        return S.err("Xato ma'lumot")
    own = list(p.get("owned") or [])
    g, t = d.get("give"), d.get("take")
    if g in S.ITEMS and g not in own:
        own.append(g)
    if t in own:
        own.remove(t)
        if p.get("avatar") == t:
            upd["avatar"] = ""
        if p.get("bg") == t:
            upd["bg"] = ""
    upd["owned"] = own
    db().table("players").update(upd).eq("tg_id", tid).execute()
    return jsonify(ok=True, player=pub(get_player(tid)))


# ---------- E'lon ----------
def _send_all(text):
    start = 0
    while True:
        rows = db().table("players").select("tg_id").range(start, start + 999).execute().data or []
        for r in rows:
            try:
                requests.post(f"https://api.telegram.org/bot{S.TOKEN}/sendMessage",
                              json={"chat_id": r["tg_id"], "text": text}, timeout=10)
            except Exception:
                pass
            time.sleep(0.06)
        if len(rows) < 1000:
            break
        start += 1000


@admin.route("/api/admin/broadcast", methods=["POST"])
def broadcast():
    u, d = who()
    if not u:
        return deny()
    text = str(d.get("text", "")).strip()
    if not text:
        return S.err("Matn yozing")
    threading.Thread(target=_send_all, args=(text,), daemon=True).start()
    return jsonify(ok=True)
