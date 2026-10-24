import random

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = {
    24: ["9", "10", "J", "Q", "K", "A"],
    36: ["6", "7", "8", "9", "10", "J", "Q", "K", "A"],
    54: ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"],
}


def is_joker(card):
    return card.startswith("🃏")


def rank(card):
    return "🃏" if is_joker(card) else card[:-1]


def make_deck(size=36):
    deck = [r + s for s in SUITS for r in RANKS[size]]
    if size == 54:
        deck += ["🃏1", "🃏2"]
    random.shuffle(deck)
    return deck


def power(card, size=36):
    return RANKS[size].index(card[:-1])


def can_beat(att, dfn, trump, size=36):
    aj, dj = is_joker(att), is_joker(dfn)
    if aj:
        return dj and dfn > att
    if dj:
        return True
    if dfn[-1] == att[-1]:
        return power(dfn, size) > power(att, size)
    return dfn[-1] == trump and att[-1] != trump


class Game:
    def __init__(self, size=36, players=2):
        self.size = size
        deck = make_deck(size)
        while is_joker(deck[-1]):
            random.shuffle(deck)
        self.trump_card = deck[-1]
        self.trump = self.trump_card[-1]
        n = min(6, (len(deck) - 1) // players)
        self.hands = [[deck.pop(0) for _ in range(n)] for _ in range(players)]
        self.deck = deck
        self.table = []  # [[hujum, himoya yoki None], ...]
        self.out = set()  # o'yindan chiqqan (kartasi tugagan) o'yinchilar
        self.attacker = self.first_attacker()
        self.defender = self.next_player(self.attacker)

    # ---------- yordamchi ----------
    def first_attacker(self):
        best, who = None, None
        for p, hand in enumerate(self.hands):
            for c in hand:
                if not is_joker(c) and c[-1] == self.trump:
                    pw = power(c, self.size)
                    if best is None or pw < best:
                        best, who = pw, p
        return who if who is not None else random.randrange(len(self.hands))

    def next_player(self, i):
        n = len(self.hands)
        for k in range(1, n + 1):
            j = (i + k) % n
            if j not in self.out:
                return j
        return i

    def refill(self):
        n = len(self.hands)
        order = [(self.attacker + k) % n for k in range(n)]
        order.remove(self.defender)
        order.append(self.defender)  # himoyachi oxirida oladi
        for p in order:
            while len(self.hands[p]) < 6 and self.deck:
                self.hands[p].append(self.deck.pop(0))
        if not self.deck:
            for p in range(n):
                if not self.hands[p]:
                    self.out.add(p)

    # ---------- yurishlar ----------
    def can_attack(self, p, card):
        if p in self.out or p == self.defender or card not in self.hands[p]:
            return False
        if not self.table:
            return p == self.attacker
        if len(self.table) >= 6:
            return False
        open_cards = sum(1 for _, d in self.table if d is None)
        if open_cards + 1 > len(self.hands[self.defender]):
            return False
        ranks = {rank(c) for pair in self.table for c in pair if c}
        return rank(card) in ranks

    def attack(self, p, card):
        if not self.can_attack(p, card):
            return False
        self.hands[p].remove(card)
        self.table.append([card, None])
        return True

    def defend(self, att_card, card):
        hand = self.hands[self.defender]
        if card not in hand:
            return False
        for pair in self.table:
            if pair[0] == att_card and pair[1] is None:
                if can_beat(att_card, card, self.trump, self.size):
                    hand.remove(card)
                    pair[1] = card
                    return True
                return False
        return False

    def take(self):
        """Himoyachi olomadi: stoldagi hamma kartani oladi."""
        for a, d in self.table:
            self.hands[self.defender].append(a)
            if d:
                self.hands[self.defender].append(d)
        self.table = []
        self.refill()
        self.attacker = self.next_player(self.defender)
        self.defender = self.next_player(self.attacker)

    def end_turn(self):
        """Bito: hamma hujum qaytarildi."""
        if not self.table or any(d is None for _, d in self.table):
            return False
        self.table = []
        self.refill()
        if self.defender in self.out:
            self.attacker = self.next_player(self.defender)
        else:
            self.attacker = self.defender
        self.defender = self.next_player(self.attacker)
        return True

    # ---------- natija ----------
    def is_over(self):
        return len(self.out) >= len(self.hands) - 1

    def durak(self):
        """Durak o'yinchi raqami; durang bo'lsa None."""
        if not self.is_over():
            return None
        left = [p for p in range(len(self.hands)) if p not in self.out]
        return left[0] if left else None


# Standart qiymatlar (admin paneldagi sozlama bo'lmasa shular ishlaydi)
MIN_STAKE = 100
MAX_STAKE = 100000
POINTS_DIV = 10


def _cfg(key, default):
    """Admin paneldagi sozlamani oladi, bo'lmasa standart qiymat."""
    try:
        from admin import cfg
        return int(cfg(key, default))
    except Exception:
        return default


def min_stake():
    return _cfg("min_stake", MIN_STAKE)


def max_stake():
    return _cfg("max_stake", MAX_STAKE)


def points_div():
    return _cfg("points_div", POINTS_DIV) or POINTS_DIV


def can_join(balance, stake):
    """Stavka eng kam va eng ko'p chegara oralig'ida bo'lishi va balans yetarli bo'lishi kerak."""
    return min_stake() <= stake <= max_stake() and balance >= stake


def settle(stake, balances, durak_index):
    """
    O'yin oxiridagi hisob-kitob.
    Durak stavka miqdorini yo'qotadi, yutganlar uni teng bo'lishadi.
    Ochko = olingan pul ulushi / ochko bo'luvchi (standart 10).
    Qaytaradi: (yangi balanslar, ochkolar ro'yxati).
    Durang bo'lsa (durak_index None) hech narsa o'zgarmaydi.
    """
    n = len(balances)
    new = list(balances)
    points = [0.0] * n
    if durak_index is None:
        return new, points
    winners = [p for p in range(n) if p != durak_index]
    share = round(stake / len(winners), 2)
    new[durak_index] -= stake
    div = points_div()
    for p in winners:
        new[p] += share
        points[p] = round(share / div, 2)
    return new, points


if __name__ == "__main__":
    # tez sinov: tasodifiy o'ynaydigan o'yin
    for size in (24, 36, 54):
        g = Game(size, 3)
        steps = 0
        while not g.is_over() and steps < 2000:
            steps += 1
            a = g.attacker
            if not g.table:
                g.attack(a, random.choice(g.hands[a]))
            moved = False
            for att, d in g.table:
                if d is None:
                    opts = [c for c in g.hands[g.defender]
                            if can_beat(att, c, g.trump, size)]
                    if opts:
                        g.defend(att, opts[0])
                        moved = True
                    else:
                        g.take()
                        moved = None
                        break
            if moved is None:
                continue
            for p in range(len(g.hands)):
                for c in list(g.hands[p]):
                    if g.attack(p, c):
                        break
            if all(d for _, d in g.table):
                g.end_turn()
        print(size, "talik: durak =", g.durak(), "| yurishlar:", steps)
