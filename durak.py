import random

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = {
    24: ["9", "10", "J", "Q", "K", "A"],
    36: ["6", "7", "8", "9", "10", "J", "Q", "K", "A"],
    54: ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"],
}

def make_deck(size=36):
    deck = [r + s for s in SUITS for r in RANKS[size]]
    if size == 54:
        deck += ["🃏1", "🃏2"]
    random.shuffle(deck)
    return deck

def new_game(size=36, players=2):
    deck = make_deck(size)
    while deck[-1].startswith("🃏"):
        random.shuffle(deck)
    trump_card = deck[-1]
    n = min(6, (len(deck) - 1) // players)
    hands = [[deck.pop(0) for _ in range(n)] for _ in range(players)]
    return {"deck": deck, "trump": trump_card[-1],
            "trump_card": trump_card, "hands": hands}
    def power(card, size=36):
    return RANKS[size].index(card[:-1])

def can_beat(att, dfn, trump, size=36):
    aj = att.startswith("🃏")
    dj = dfn.startswith("🃏")
    if aj:
        return dj and dfn > att
    if dj:
        return True
    if dfn[-1] == att[-1]:
        return power(dfn, size) > power(att, size)
    return dfn[-1] == trump and att[-1] != trump
