"""Extended Lunaland-grade Game Registry with 18+ high-end slots and table games."""

from __future__ import annotations

import random
from typing import Any

MIN_BET = 1
MAX_BET = 1000


class GameContext:
    def __init__(self, rng: random.Random, bet: int, payload: dict[str, Any], currency: str = "LC") -> None:
        self.rng = rng
        self.bet = bet
        self.payload = payload
        self.currency = currency


def _slots_game(ctx: GameContext) -> dict[str, Any]:
    roll = float(ctx.rng.random())
    if roll < 0.05:
        return {"outcome": "JACKPOT", "multiplier": 12, "bonus_awarded": 5, "reels": ["💎", "💎", "💎"]}
    if roll < 0.15:
        return {"outcome": "SURGE", "multiplier": 5, "bonus_awarded": 0, "reels": ["7️⃣", "7️⃣", "7️⃣"]}
    if roll < 0.40:
        return {"outcome": "WIN", "multiplier": 2, "bonus_awarded": 0, "reels": ["⭐", "⭐", "⭐"]}
    if roll < 0.55:
        return {"outcome": "RETURN", "multiplier": 1, "bonus_awarded": 0, "reels": ["🔔", "🔔", "🍒"]}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "reels": ["🍒", "🍋", "🍇"]}


def _ancient_tumble_game(ctx: GameContext) -> dict[str, Any]:
    """Relax Gaming style Megaways tumble slot with cascading multipliers."""
    tumbles = ctx.rng.randint(1, 5) if ctx.rng.random() < 0.45 else 0
    multiplier = 0
    if tumbles > 0:
        multiplier = round(sum(1.5 ** i for i in range(tumbles)), 1)
        outcome = "TUMBLE_WIN" if tumbles < 4 else "COLOSSAL_AVALANCHE"
        bonus = 3 if tumbles >= 4 else 0
        return {"outcome": outcome, "multiplier": multiplier, "bonus_awarded": bonus, "tumbles": tumbles, "ways": 117649, "cascade_depth": tumbles}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "tumbles": 0, "ways": 117649}


def _sugar_rush_game(ctx: GameContext) -> dict[str, Any]:
    """Pragmatic-style Cluster Pays 7x7 grid slot with multiplier spots."""
    clusters = ctx.rng.randint(1, 4) if ctx.rng.random() < 0.40 else 0
    if clusters > 0:
        spots_mult = 2 ** clusters
        total_mult = spots_mult * ctx.rng.choice([1, 2, 3])
        return {"outcome": "SWEET_CLUSTER", "multiplier": total_mult, "bonus_awarded": 5 if total_mult >= 16 else 0, "clusters": clusters, "grid_size": "7x7"}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "clusters": 0, "grid_size": "7x7"}


def _hold_and_win_game(ctx: GameContext) -> dict[str, Any]:
    """RubyPlay-style Hold and Win Respins mechanics with coins collection."""
    coins = ctx.rng.randint(6, 15) if ctx.rng.random() < 0.35 else ctx.rng.randint(0, 5)
    if coins >= 6:
        jackpot_tier = "MINI" if coins < 9 else ("MAJOR" if coins < 12 else "GRAND")
        multiplier = coins * 3 + (20 if jackpot_tier == "MINI" else (100 if jackpot_tier == "MAJOR" else 500))
        return {"outcome": f"{jackpot_tier}_JACKPOT", "multiplier": multiplier, "bonus_awarded": 3, "coins_collected": coins, "feature": "Hold & Win Respins"}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "coins_collected": coins}


def _gates_of_olympus_game(ctx: GameContext) -> dict[str, Any]:
    """Multiplier Orbs (2x to 500x) tumble mechanics."""
    hit = ctx.rng.random() < 0.38
    if hit:
        orbs = [ctx.rng.choice([2, 5, 10, 25, 50, 100, 500]) for _ in range(ctx.rng.randint(1, 3))]
        total_orb_mult = sum(orbs)
        return {"outcome": "ZEUS_LIGHTNING", "multiplier": total_orb_mult, "bonus_awarded": 15 if 100 in orbs or 500 in orbs else 0, "orbs": orbs}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "orbs": []}


# --- 2. Table & Card Games ---
def _dice_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "over")
    die1 = ctx.rng.randint(1, 6)
    die2 = ctx.rng.randint(1, 6)
    total = die1 + die2
    if prediction == "seven" and total == 7:
        return {"outcome": "SEVEN", "multiplier": 5, "bonus_awarded": 0, "die1": die1, "die2": die2, "total": total}
    if prediction == "over" and total > 7:
        return {"outcome": "OVER", "multiplier": 2, "bonus_awarded": 0, "die1": die1, "die2": die2, "total": total}
    if prediction == "under" and total < 7:
        return {"outcome": "UNDER", "multiplier": 2, "bonus_awarded": 0, "die1": die1, "die2": die2, "total": total}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "die1": die1, "die2": die2, "total": total}


def _coin_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "heads")
    result = ctx.rng.choice(["heads", "tails"])
    if prediction == result:
        return {"outcome": "WIN", "multiplier": 2, "bonus_awarded": 0, "result": result}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "result": result}


def _roulette_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "red")
    number = ctx.rng.randint(0, 36)
    reds = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    color = "green" if number == 0 else ("red" if number in reds else "black")
    if prediction == "number":
        picked = int(ctx.payload.get("number", 0))
        if picked == number:
            return {"outcome": "STRAIGHT", "multiplier": 35, "bonus_awarded": 0, "number": number, "color": color}
    elif prediction == color:
        multiplier = 3 if color == "green" else 2
        return {"outcome": color.upper(), "multiplier": multiplier, "bonus_awarded": 0, "number": number, "color": color}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "number": number, "color": color}


def _blackjack_game(ctx: GameContext) -> dict[str, Any]:
    player_card1 = ctx.rng.randint(1, 11)
    player_card2 = ctx.rng.randint(1, 11)
    dealer_card1 = ctx.rng.randint(1, 11)
    dealer_card2 = ctx.rng.randint(1, 11)
    player_total = player_card1 + player_card2
    dealer_total = dealer_card1 + dealer_card2
    player_bust = player_total > 21
    dealer_bust = dealer_total > 21
    action = ctx.payload.get("action", "stand")
    player_card3 = 0
    if action == "hit":
        player_card3 = ctx.rng.randint(1, 11)
        player_total += player_card3
        player_bust = player_total > 21
    cards_str = f"{player_card1},{player_card2},{player_card3 if action == 'hit' else '-'}"
    if player_bust:
        return {"outcome": "BUST", "multiplier": 0, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": cards_str}
    if dealer_bust or player_total > dealer_total:
        mult = 2.5 if player_total == 21 and action == "stand" else 2
        return {"outcome": "BLACKJACK" if mult == 2.5 else "WIN", "multiplier": mult, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": cards_str}
    if player_total == dealer_total:
        return {"outcome": "PUSH", "multiplier": 1, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": cards_str}
    return {"outcome": "LOSE", "multiplier": 0, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": cards_str}


def _baccarat_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "player")
    player = sum(ctx.rng.randint(1, 10) for _ in range(2)) % 10
    banker = sum(ctx.rng.randint(1, 10) for _ in range(2)) % 10
    result = "player" if player > banker else ("banker" if banker > player else "tie")
    if prediction == result:
        multiplier = 8 if result == "tie" else 2
        return {"outcome": result.upper(), "multiplier": multiplier, "bonus_awarded": 0, "player": player, "banker": banker}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "player": player, "banker": banker}


def _hilo_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "higher")
    card = ctx.rng.randint(1, 13)
    next_card = ctx.rng.randint(1, 13)
    if prediction == "higher" and next_card > card:
        return {"outcome": "HIGHER", "multiplier": 2, "bonus_awarded": 0, "card": card, "next": next_card}
    if prediction == "lower" and next_card < card:
        return {"outcome": "LOWER", "multiplier": 2, "bonus_awarded": 0, "card": card, "next": next_card}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "card": card, "next": next_card}


# --- 3. Fast Instant-Win Games ---
def _crash_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "cashout")
    crash_point = max(1.0, round(ctx.rng.expovariate(1 / 3) + 1, 2))
    if prediction == "cashout":
        cashout = float(ctx.payload.get("cashout", 2.0))
        if cashout < crash_point:
            return {"outcome": "CASHOUT", "multiplier": cashout, "bonus_awarded": 0, "crash_point": crash_point, "cashout_at": cashout}
    return {"outcome": "CRASHED", "multiplier": 0, "bonus_awarded": 0, "crash_point": crash_point}


def _plinko_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "center")
    rows = 8
    path = [ctx.rng.choice(["left", "right"]) for _ in range(rows)]
    final_pos = sum(1 for p in path if p == "right")
    buckets = [10, 5, 2, 1, 0.5, 1, 2, 5, 10]
    bucket_index = min(final_pos, len(buckets) - 1)
    multiplier = buckets[bucket_index]
    hit_prediction = (
        (prediction == "left" and bucket_index <= 3) or
        (prediction == "center" and 3 <= bucket_index <= 5) or
        (prediction == "right" and bucket_index >= 5)
    )
    if hit_prediction:
        return {"outcome": "WIN", "multiplier": multiplier, "bonus_awarded": 0, "final_pos": final_pos, "path": path}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "final_pos": final_pos, "path": path}


def _mines_game(ctx: GameContext) -> dict[str, Any]:
    """Stake/Lunaland style Mines game."""
    mines_count = int(ctx.payload.get("mines", 3))
    gems_picked = int(ctx.payload.get("picks", 3))
    total_tiles = 25
    mine_positions = set(ctx.rng.sample(range(total_tiles), mines_count))
    user_picks = set(range(gems_picked))
    if user_picks.isdisjoint(mine_positions):
        multiplier = round(1.2 ** gems_picked + (mines_count * 0.4), 2)
        return {"outcome": "GEMS_FOUND", "multiplier": multiplier, "bonus_awarded": 0, "mines": mines_count, "picks": gems_picked, "status": "cleared"}
    return {"outcome": "MINE_EXPLODED", "multiplier": 0, "bonus_awarded": 0, "mines": mines_count, "picks": gems_picked, "status": "exploded"}


def _wheel_of_fortune_game(ctx: GameContext) -> dict[str, Any]:
    """Big 6 / Wheel of Fortune with 54 segments."""
    segments = [1]*24 + [2]*15 + [5]*7 + [10]*4 + [20]*2 + [40]*1 + [100]*1
    result = ctx.rng.choice(segments)
    pred = int(ctx.payload.get("target", 1))
    if pred == result:
        return {"outcome": f"{result}X_HIT", "multiplier": result, "bonus_awarded": 5 if result >= 40 else 0, "wheel_result": result}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0, "wheel_result": result}


def _keno_game(ctx: GameContext) -> dict[str, Any]:
    numbers_raw = ctx.payload.get("numbers", [])
    if isinstance(numbers_raw, str):
        try:
            selected = [int(x.strip()) for x in numbers_raw.split(",") if x.strip()]
        except ValueError:
            selected = []
    elif isinstance(numbers_raw, list):
        selected = [int(x) for x in numbers_raw]
    else:
        selected = []
    if not selected:
        selected = [ctx.rng.randint(1, 80) for _ in range(5)]
    drawn = set(ctx.rng.sample(range(1, 81), 20))
    hits = len(set(selected) & drawn)
    payouts = {0: 0, 1: 0.5, 2: 1, 3: 3, 4: 10, 5: 50}
    multiplier = payouts.get(min(hits, 5), 0)
    return {"outcome": f"{hits}_HIT", "multiplier": multiplier, "bonus_awarded": 0, "hits": hits, "drawn_count": len(drawn)}


GAMES: dict[str, dict[str, Any]] = {
    "slots": {
        "id": "slots",
        "name": "Classic Lunar 777",
        "description": "3-Reel classic lunar fruit slot with Diamond Jackpot & Respin surge.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _slots_game,
        "fields": [],
        "category": "slots",
        "provider": "NetEnt",
        "rtp": 96.5,
        "volatility": "High",
        "featured": True,
    },
    "ancient_tumble": {
        "id": "ancient_tumble",
        "name": "Ancient Tumble Megaways",
        "description": "117,649 Ways to Win tumble slot with cascading multipliers and avalanche respins.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _ancient_tumble_game,
        "fields": [],
        "category": "slots",
        "provider": "Relax Gaming",
        "rtp": 96.8,
        "volatility": "High",
        "featured": True,
    },
    "sugar_rush": {
        "id": "sugar_rush",
        "name": "Sugar Rush 1000",
        "description": "7x7 Cluster Pays candy kingdom with sticky multiplier spots up to 1024x.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _sugar_rush_game,
        "fields": [],
        "category": "slots",
        "provider": "Pragmatic Play",
        "rtp": 96.7,
        "volatility": "High",
        "featured": True,
    },
    "hold_and_win": {
        "id": "hold_and_win",
        "name": "Ruby Hold & Win",
        "description": "Coin respin frenzy with Mini, Major, and Grand Jackpot triggers.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _hold_and_win_game,
        "fields": [],
        "category": "slots",
        "provider": "RubyPlay",
        "rtp": 96.4,
        "volatility": "Medium",
        "featured": True,
    },
    "gates_of_olympus": {
        "id": "gates_of_olympus",
        "name": "Gates of Olympus",
        "description": "Zeus multiplier orbs reaching up to 500x with free games tumble.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _gates_of_olympus_game,
        "fields": [],
        "category": "slots",
        "provider": "BGaming",
        "rtp": 96.5,
        "volatility": "Very High",
        "featured": True,
    },
    "mines": {
        "id": "mines",
        "name": "Lunar Mines",
        "description": "Uncover crystals and dodge hidden asteroids across a 5x5 grid.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _mines_game,
        "fields": [
            {
                "name": "mines",
                "type": "select",
                "label": "Mines Count",
                "options": [
                    {"value": "1", "label": "1 Mine (Low Risk)"},
                    {"value": "3", "label": "3 Mines (Standard)"},
                    {"value": "5", "label": "5 Mines (High Reward)"},
                    {"value": "10", "label": "10 Mines (Extreme)"},
                ],
                "default": "3",
            },
            {
                "name": "picks",
                "type": "number",
                "label": "Gems to Pick (1-10)",
                "min": 1,
                "max": 10,
                "default": 3,
            }
        ],
        "category": "instant",
        "provider": "Lunaland Original",
        "rtp": 98.0,
        "volatility": "Custom",
        "featured": True,
    },
    "wheel": {
        "id": "wheel",
        "name": "Lunaland Wheel of Fortune",
        "description": "Spin the cosmic wheel with up to 100x instant multiplier segment.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _wheel_of_fortune_game,
        "fields": [
            {
                "name": "target",
                "type": "select",
                "label": "Target Segment",
                "options": [
                    {"value": "1", "label": "1x (44% Hit)"},
                    {"value": "2", "label": "2x (28% Hit)"},
                    {"value": "5", "label": "5x (13% Hit)"},
                    {"value": "10", "label": "10x (7% Hit)"},
                    {"value": "20", "label": "20x (4% Hit)"},
                    {"value": "40", "label": "40x Mega (2% Hit)"},
                    {"value": "100", "label": "100x Moonshot (1% Hit)"},
                ],
                "default": "2",
            }
        ],
        "category": "instant",
        "provider": "Lunaland Original",
        "rtp": 97.0,
        "volatility": "Medium",
        "featured": True,
    },
    "crash": {
        "id": "crash",
        "name": "Moonshot Crash",
        "description": "Cash out your rocket before the lunar trajectory crashes.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _crash_game,
        "fields": [
            {
                "name": "cashout",
                "type": "number",
                "label": "Auto Cashout Multiplier",
                "min": 1.1,
                "max": 100,
                "step": 0.1,
                "default": 2.0,
            }
        ],
        "category": "instant",
        "provider": "BGaming",
        "rtp": 97.0,
        "volatility": "High",
        "featured": True,
    },
    "plinko": {
        "id": "plinko",
        "name": "Plinko Galaxy",
        "description": "Drop pegs across 8 gravity rows with up to 10x edge buckets.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _plinko_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Prediction Bucket",
                "options": [
                    {"value": "left", "label": "Left Edge (10x / 5x / 2x)"},
                    {"value": "center", "label": "Center Pin (1x / 0.5x)"},
                    {"value": "right", "label": "Right Edge (2x / 5x / 10x)"},
                ],
                "default": "center",
            }
        ],
        "category": "instant",
        "provider": "BGaming",
        "rtp": 98.0,
        "volatility": "Medium",
        "featured": True,
    },
    "dice": {
        "id": "dice",
        "name": "Cosmic Dice",
        "description": "Roll two dice. Bet on over 7, under 7, or lucky seven.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _dice_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Prediction",
                "options": [
                    {"value": "over", "label": "Over 7 (2x)"},
                    {"value": "under", "label": "Under 7 (2x)"},
                    {"value": "seven", "label": "Exactly 7 (5x)"},
                ],
                "default": "over",
            }
        ],
        "category": "table",
        "provider": "NetEnt",
        "rtp": 97.2,
        "volatility": "Low",
    },
    "coin": {
        "id": "coin",
        "name": "Luna Coin Flip",
        "description": "Double or nothing heads or tails cosmic coin flip.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _coin_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Side",
                "options": [
                    {"value": "heads", "label": "Heads"},
                    {"value": "tails", "label": "Tails"},
                ],
                "default": "heads",
            }
        ],
        "category": "instant",
        "provider": "Lunaland Original",
        "rtp": 99.0,
        "volatility": "Low",
    },
    "roulette": {
        "id": "roulette",
        "name": "European Roulette",
        "description": "European single-zero wheel with full 35:1 straight and even-money bets.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _roulette_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Bet Option",
                "options": [
                    {"value": "red", "label": "Red (2x)"},
                    {"value": "black", "label": "Black (2x)"},
                    {"value": "green", "label": "Green Zero (3x)"},
                    {"value": "number", "label": "Straight Number (35x)"},
                ],
                "default": "red",
            },
            {
                "name": "number",
                "type": "number",
                "label": "Number (0-36)",
                "min": 0,
                "max": 36,
                "default": 0,
                "showWhen": {"field": "prediction", "value": "number"},
            },
        ],
        "category": "table",
        "provider": "NetEnt",
        "rtp": 97.3,
        "volatility": "Medium",
    },
    "blackjack": {
        "id": "blackjack",
        "name": "Vegas Strip Blackjack",
        "description": "Standard 3:2 payout Blackjack with hit, stand, and dealer bust detection.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _blackjack_game,
        "fields": [
            {
                "name": "action",
                "type": "select",
                "label": "Action",
                "options": [
                    {"value": "stand", "label": "Stand"},
                    {"value": "hit", "label": "Hit"},
                ],
                "default": "stand",
            }
        ],
        "category": "table",
        "provider": "NetEnt",
        "rtp": 99.4,
        "volatility": "Low",
    },
    "baccarat": {
        "id": "baccarat",
        "name": "Punto Banco Baccarat",
        "description": "Classic Player, Banker (2x) and Tie (8x) high roller table.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _baccarat_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Bet",
                "options": [
                    {"value": "player", "label": "Player (2x)"},
                    {"value": "banker", "label": "Banker (2x)"},
                    {"value": "tie", "label": "Tie (8x)"},
                ],
                "default": "player",
            }
        ],
        "category": "table",
        "provider": "Relax Gaming",
        "rtp": 98.9,
        "volatility": "Low",
    },
    "hilo": {
        "id": "hilo",
        "name": "Hi-Lo Orbit",
        "description": "Guess higher or lower card in streak sequence.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _hilo_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Prediction",
                "options": [
                    {"value": "higher", "label": "Higher (2x)"},
                    {"value": "lower", "label": "Lower (2x)"},
                ],
                "default": "higher",
            }
        ],
        "category": "instant",
        "provider": "Lunaland Original",
        "rtp": 97.0,
        "volatility": "Low",
    },
    "keno": {
        "id": "keno",
        "name": "Cosmic Keno 80",
        "description": "Pick 5 lucky numbers from 1 to 80 with 20 balls draw.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _keno_game,
        "fields": [
            {
                "name": "numbers",
                "type": "text",
                "label": "Numbers (comma-separated, 1-80)",
                "default": "7,14,21,42,77",
            }
        ],
        "category": "lottery",
        "provider": "RubyPlay",
        "rtp": 95.5,
        "volatility": "High",
    },
}


def list_games() -> list[dict[str, Any]]:
    return [
        {
            "id": game["id"],
            "name": game["name"],
            "description": game["description"],
            "min_bet": game["min_bet"],
            "max_bet": game["max_bet"],
            "fields": game["fields"],
            "category": game.get("category", "other"),
            "provider": game.get("provider", "Lunaland"),
            "rtp": game.get("rtp", 96.0),
            "volatility": game.get("volatility", "Medium"),
            "featured": game.get("featured", False),
        }
        for game in GAMES.values()
    ]


def get_game(game_id: str) -> dict[str, Any] | None:
    if game_id in GAMES:
        return GAMES[game_id]
    # Check LuckyConnect 6,000+ catalog
    from luckyconnect import luckyconnect
    with luckyconnect._lock:
        agg_game = luckyconnect._games.get(game_id)
        if agg_game:
            return {
                "id": agg_game.game_id,
                "name": agg_game.name,
                "description": f"{agg_game.provider} flagship {agg_game.type} title aggregated via LuckyConnect.",
                "min_bet": MIN_BET,
                "max_bet": MAX_BET,
                "fields": [],
                "category": agg_game.category,
                "provider": agg_game.provider,
                "rtp": agg_game.rtp,
                "volatility": agg_game.volatility,
                "featured": True,
            }
    return None


def play_game(game_id: str, ctx: GameContext) -> dict[str, Any]:
    game = GAMES.get(game_id)
    if game is not None:
        return game["play"](ctx)

    # Dynamic Universal Simulation for LuckyConnect Aggregated Titles
    from luckyconnect import luckyconnect
    with luckyconnect._lock:
        agg = luckyconnect._games.get(game_id)
        if not agg:
            raise ValueError(f"unknown game: {game_id}")

        # Live Dealer Blackjack / Baccarat / Roulette routing
        if agg.type == "live_dealer":
            if "blackjack" in game_id:
                return _blackjack_game(ctx)
            elif "roulette" in game_id:
                return _roulette_game(ctx)
            elif "baccarat" in game_id:
                return _baccarat_game(ctx)
            return _slots_game(ctx)

        # Slots / Crash / Arcade Routing
        if agg.type == "crash":
            return _crash_game(ctx)
        elif agg.type == "arcade":
            return _plinko_game(ctx)
        elif "olympus" in game_id or "princess" in game_id:
            return _gates_of_olympus_game(ctx)
        elif "sugar" in game_id or "bonanza" in game_id:
            return _sugar_rush_game(ctx)
        elif "hold" in game_id or "immortal" in game_id or "mayan" in game_id:
            return _hold_and_win_game(ctx)
        elif "tumble" in game_id or "megaways" in game_id or "ways" in game_id:
            return _ancient_tumble_game(ctx)
        return _slots_game(ctx)
