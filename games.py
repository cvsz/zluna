"""Game registry for the zslog synthetic simulator."""

from __future__ import annotations

import random
from typing import Any

MIN_BET = 1
MAX_BET = 100


class GameContext:
    def __init__(self, rng: random.Random, bet: int, payload: dict[str, Any]) -> None:
        self.rng = rng
        self.bet = bet
        self.payload = payload


def _slots_game(ctx: GameContext) -> dict[str, Any]:
    roll = float(ctx.rng.random())
    if roll < 0.05:
        return {"outcome": "JACKPOT", "multiplier": 12, "bonus_awarded": 5}
    if roll < 0.15:
        return {"outcome": "SURGE", "multiplier": 5, "bonus_awarded": 0}
    if roll < 0.40:
        return {"outcome": "WIN", "multiplier": 2, "bonus_awarded": 0}
    if roll < 0.55:
        return {"outcome": "RETURN", "multiplier": 1, "bonus_awarded": 0}
    return {"outcome": "MISS", "multiplier": 0, "bonus_awarded": 0}


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
        picked = ctx.payload.get("number", 0)
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
    if action == "hit":
        player_card3 = ctx.rng.randint(1, 11)
        player_total += player_card3
        player_bust = player_total > 21
    if player_bust:
        return {"outcome": "BUST", "multiplier": 0, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": f"{player_card1},{player_card2},{player_card3 if action == 'hit' else '-'}"}
    if dealer_bust or player_total > dealer_total:
        return {"outcome": "WIN", "multiplier": 2, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": f"{player_card1},{player_card2},{player_card3 if action == 'hit' else '-'}"}
    if player_total == dealer_total:
        return {"outcome": "PUSH", "multiplier": 1, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": f"{player_card1},{player_card2},{player_card3 if action == 'hit' else '-'}"}
    return {"outcome": "LOSE", "multiplier": 0, "bonus_awarded": 0, "player_total": player_total, "dealer_total": dealer_total, "cards": f"{player_card1},{player_card2},{player_card3 if action == 'hit' else '-'}"}


def _crash_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "cashout")
    crash_point = max(1.0, round(ctx.rng.expovariate(1 / 3) + 1, 2))
    if prediction == "cashout":
        cashout = ctx.payload.get("cashout", 2.0)
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


def _baccarat_game(ctx: GameContext) -> dict[str, Any]:
    prediction = ctx.payload.get("prediction", "player")
    player = sum(ctx.rng.randint(1, 10) for _ in range(2)) % 10
    banker = sum(ctx.rng.randint(1, 10) for _ in range(2)) % 10
    if player > banker:
        result = "player"
    elif banker > player:
        result = "banker"
    else:
        result = "tie"
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


GAMES: dict[str, dict[str, Any]] = {
    "slots": {
        "id": "slots",
        "name": "Slots",
        "description": "Classic reel spin with jackpot, surge, win, return, and miss outcomes.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _slots_game,
        "fields": [],
        "category": "table",
    },
    "dice": {
        "id": "dice",
        "name": "Dice",
        "description": "Roll two dice. Bet on over, under, or exactly seven.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _dice_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Prediction",
                "options": [
                    {"value": "over", "label": "Over 7"},
                    {"value": "under", "label": "Under 7"},
                    {"value": "seven", "label": "Exactly 7"},
                ],
                "default": "over",
            }
        ],
        "category": "table",
    },
    "coin": {
        "id": "coin",
        "name": "Coin Flip",
        "description": "Simple heads or tails. Double or nothing.",
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
    },
    "roulette": {
        "id": "roulette",
        "name": "Roulette",
        "description": "European wheel. Bet on red, black, green, or a specific number.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _roulette_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Bet",
                "options": [
                    {"value": "red", "label": "Red (2x)"},
                    {"value": "black", "label": "Black (2x)"},
                    {"value": "green", "label": "Green / 0 (3x)"},
                    {"value": "number", "label": "Number (35x)"},
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
    },
    "blackjack": {
        "id": "blackjack",
        "name": "Blackjack",
        "description": "Beat the dealer. Hit or stand. Closest to 21 without busting wins.",
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
    },
    "crash": {
        "id": "crash",
        "name": "Crash",
        "description": "Cash out before the multiplier crashes. Higher risk, higher reward.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _crash_game,
        "fields": [
            {
                "name": "cashout",
                "type": "number",
                "label": "Auto cashout",
                "min": 1.1,
                "max": 100,
                "step": 0.1,
                "default": 2.0,
            }
        ],
        "category": "instant",
    },
    "plinko": {
        "id": "plinko",
        "name": "Plinko",
        "description": "Drop a ball through 8 rows of pegs. Predict left, center, or right.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _plinko_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Prediction",
                "options": [
                    {"value": "left", "label": "Left"},
                    {"value": "center", "label": "Center"},
                    {"value": "right", "label": "Right"},
                ],
                "default": "center",
            }
        ],
        "category": "instant",
    },
    "keno": {
        "id": "keno",
        "name": "Keno",
        "description": "Pick 5 numbers from 1-80. 20 numbers drawn. Up to 50x payout.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _keno_game,
        "fields": [
            {
                "name": "numbers",
                "type": "text",
                "label": "Numbers (comma-separated, 1-80)",
                "default": "1,5,12,34,78",
            }
        ],
        "category": "lottery",
    },
    "baccarat": {
        "id": "baccarat",
        "name": "Baccarat",
        "description": "Player or banker? Tie pays 8x. Closest to 9 wins.",
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
    },
    "hilo": {
        "id": "hilo",
        "name": "Hi-Lo",
        "description": "Guess if the next card is higher or lower. 2x on correct guess.",
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "play": _hilo_game,
        "fields": [
            {
                "name": "prediction",
                "type": "select",
                "label": "Prediction",
                "options": [
                    {"value": "higher", "label": "Higher"},
                    {"value": "lower", "label": "Lower"},
                ],
                "default": "higher",
            }
        ],
        "category": "instant",
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
        }
        for game in GAMES.values()
    ]


def get_game(game_id: str) -> dict[str, Any] | None:
    return GAMES.get(game_id)


def play_game(game_id: str, ctx: GameContext) -> dict[str, Any]:
    game = GAMES.get(game_id)
    if game is None:
        raise ValueError(f"unknown game: {game_id}")
    return game["play"](ctx)
