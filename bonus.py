import os
from datetime import datetime, timezone, timedelta
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
DAILY = 100
INVITE = 100


def _row(tg_id):
    r = sb.table("players").select("*").eq("tg_id", tg_id).execute()
    return r.data[0] if r.data else None


def exists(tg_id):
    return _row(tg_id) is not None


def claim_daily(tg_id):
    p = _row(tg_id)
    if not p:
        return False, "O'yinchi topilmadi", 0
    now = datetime.now(timezone.utc)
    last = p.get("last_daily")
    if last:
        try:
            dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            left = timedelta(hours=24) - (now - dt)
            if left.total_seconds() > 0:
                h = int(left.total_seconds() // 3600) + 1
                return False, f"Keyingi bonus ~{h} soatdan keyin", p["balance"]
        except ValueError:
            pass
    bal = float(p["balance"]) + DAILY
    sb.table("players").update(
        {"balance": bal, "last_daily": now.isoformat()}
    ).eq("tg_id", tg_id).execute()
    return True, f"+{DAILY} pul olindi", bal


def add_referral(new_id, inviter_id):
    if new_id == inviter_id:
        return False
    inviter, me = _row(inviter_id), _row(new_id)
    if not inviter or not me or me.get("referred_by"):
        return False
    sb.table("players").update({"referred_by": inviter_id}).eq("tg_id", new_id).execute()
    sb.table("players").update(
        {"balance": float(inviter["balance"]) + INVITE}
    ).eq("tg_id", inviter_id).execute()
    return True


def top(by="points", n=20):
    r = (sb.table("players").select("name,balance,points")
         .order(by, desc=True).limit(n).execute())
    return r.data
