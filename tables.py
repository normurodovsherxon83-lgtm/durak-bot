import random
import string
import time

from durak import Game, can_join, settle, MIN_STAKE


def new_code():
    return "".join(random.choice(string.ascii_uppercase + string.digits)
                   for _ in range(5))


class Table:
    def __init__(self, size=36, stake=MIN_STAKE, max_players=2, public=False):
        self.code = new_code()
        self.size = size
        self.stake = stake
        self.max_players = max_players
        self.public = public          # True = tasodifiy o'yinchilar uchun
        self.players = []             # [{"id", "name", "balance", "bot"}]
        self.status = "waiting"       # waiting / playing / done
        self.game = None
        self.result = None
        self.created = time.time()

    # ---------- kirish ----------
    def index_of(self, tg_id):
        for i, p in enumerate(self.players):
            if p["id"] == tg_id:
                return i
        return None

    def join(self, tg_id, name, balance, bot=False):
        if self.status != "waiting":
            return False, "O'yin boshlangan"
        if self.index_of(tg_id) is not None:
            return True, "Allaqachon stoldasiz"
        if len(self.players) >= self.max_players:
            return False, "Stol to'lgan"
        if not bot and not can_join(balance, self.stake):
            return False, "Balans yetarli emas"
        self.players.append({"id": tg_id, "name": name,
                             "balance": balance, "bot": bot})
        return True, "OK"

    def leave(self, tg_id):
        i = self.index_of(tg_id)
        if i is not None and self.status == "waiting":
            self.players.pop(i)
            return True
        return False

    def start(self):
        if self.status != "waiting" or len(self.players) < 2:
            return False
        self.game = Game(self.size, len(self.players))
        self.status = "playing"
        return True

    # ---------- yurishlar ----------
    def act(self, tg_id, action, card=None, target=None):
        if self.status != "playing":
            return False, "O'yin faol emas"
        me = self.index_of(tg_id)
        if me is None:
            return False, "Siz bu stolda emassiz"
        g = self.game
        ok = False
        if action == "attack":
            ok = g.attack(me, card)
        elif action == "defend":
            ok = me == g.defender and g.defend(target, card)
        elif action == "take":
            if me == g.defender and g.table:
                g.take()
                ok = True
        elif action == "end":
            if me != g.defender:
                ok = g.end_turn()
        else:
            return False, "Noma'lum amal"
        if not ok:
            return False, "Bu yurish mumkin emas"
        self._check_over()
        return True, "OK"

    def _check_over(self):
        g = self.game
        if not g.is_over():
            return
        self.status = "done"
        balances = [p["balance"] for p in self.players]
        new_bal, points = settle(self.stake, balances, g.durak())
        self.result = {
            "durak": g.durak(),
            "ids": [p["id"] for p in self.players],
            "balances": new_bal,
            "points": points,
            "bots": [p["bot"] for p in self.players],
        }

    # ---------- holat (o'yinchiga ko'rinadigani) ----------
    def state_for(self, tg_id):
        me = self.index_of(tg_id)
        s = {
            "code": self.code, "status": self.status, "size": self.size,
            "stake": self.stake, "max_players": self.max_players,
            "players": [{"name": p["name"], "bot": p["bot"]}
                        for p in self.players],
            "me": me,
        }
        if self.game:
            g = self.game
            s.update({
                "trump": g.trump, "trump_card": g.trump_card,
                "deck_count": len(g.deck),
                "table": g.table,
                "attacker": g.attacker, "defender": g.defender,
                "counts": [len(h) for h in g.hands],
                "out": sorted(g.out),
                "hand": list(g.hands[me]) if me is not None else [],
            })
        if self.result:
            s["result"] = {"durak": self.result["durak"],
                           "points": self.result["points"],
                           "balances": self.result["balances"]}
        return s


class Lobby:
    def __init__(self):
        self.tables = {}

    def create(self, size=36, stake=MIN_STAKE, max_players=2, public=False):
        t = Table(size, stake, max_players, public)
        self.tables[t.code] = t
        return t

    def get(self, code):
        return self.tables.get(code.upper())

    def find_random(self, size, stake, max_players=2):
        """Tasodifiy o'yin: mos ochiq stol bo'lsa shunga, bo'lmasa yangisi."""
        for t in self.tables.values():
            if (t.public and t.status == "waiting" and t.size == size
                    and t.stake == stake and t.max_players == max_players
                    and len(t.players) < t.max_players):
                return t
        return self.create(size, stake, max_players, public=True)

    def cleanup(self, max_age=3 * 3600):
        now = time.time()
        for code in [c for c, t in self.tables.items()
                     if now - t.created > max_age]:
            del self.tables[code]


if __name__ == "__main__":
    # sinov: 2 o'yinchi, tasodifiy yurishlar
    from durak import can_beat
    lobby = Lobby()
    t = lobby.create(36, 10, 2)
    print(t.join(1, "Ali", 100), t.join(2, "Vali", 100), t.join(3, "Sami", 100))
    print("start:", t.start())
    steps = 0
    while t.status == "playing" and steps < 2000:
        steps += 1
        g = t.game
        a, d = g.attacker, g.defender
        aid, did = t.players[a]["id"], t.players[d]["id"]
        if not g.table:
            t.act(aid, "attack", card=g.hands[a][0])
            continue
        open_cards = [x for x, y in g.table if y is None]
        if open_cards:
            att = open_cards[0]
            opts = [c for c in g.hands[d] if can_beat(att, c, g.trump, t.size)]
            if opts:
                t.act(did, "defend", card=opts[0], target=att)
            else:
                t.act(did, "take")
        else:
            thrown = False
            for p in range(len(t.players)):
                for c in list(g.hands[p]):
                    if t.act(t.players[p]["id"], "attack", card=c)[0]:
                        thrown = True
                        break
                if thrown:
                    break
            if not thrown:
                t.act(aid, "end")
    print("holat:", t.status, "| yurishlar:", steps)
    print("natija:", t.result)
    print("Ali ko'radi:", {k: v for k, v in t.state_for(1).items()
                           if k in ("me", "hand", "counts", "status")})
