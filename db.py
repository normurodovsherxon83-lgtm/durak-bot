import os
from supabase import create_client

_client = None


def db():
    global _client
    if _client is None:
        _client = create_client(os.environ["SUPABASE_URL"],
                                os.environ["SUPABASE_KEY"])
    return _client


def get_player(tg_id, name=""):
    """O'yinchini oladi; yo'q bo'lsa 100 balans bilan yaratadi."""
    res = db().table("players").select("*").eq("tg_id", tg_id).execute()
    if res.data:
        return res.data[0]
    new = {"tg_id": tg_id, "name": name}
    return db().table("players").insert(new).execute().data[0]


def save_result(tg_ids, balances, points):
    """O'yin oxirida yangi balans va ochkolarni saqlaydi."""
    for tg_id, bal, pts in zip(tg_ids, balances, points):
        p = get_player(tg_id)
        db().table("players").update({
            "balance": bal,
            "points": float(p["points"]) + pts,
        }).eq("tg_id", tg_id).execute()


def top(by="points", limit=10):
    """Reyting: by='points' (ochko) yoki by='balance' (valyuta)."""
    return (db().table("players").select("name,balance,points")
            .order(by, desc=True).limit(limit).execute().data)


def add_balance(tg_id, amount):
    """Balansga pul qo'shadi (Stars to'lovi uchun)."""
    p = get_player(tg_id)
    new = int(p["balance"]) + amount
    db().table("players").update({"balance": new}).eq("tg_id", tg_id).execute()
    return new
