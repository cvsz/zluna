import json
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from app import InsufficientCredits, InvalidBet, Simulator, create_server


class SequenceRng:
    def __init__(self, values):
        self.values = iter(values)

    def random(self):
        return next(self.values)


class LunalandEnterpriseTests(unittest.TestCase):
    def test_store_package_purchase(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(data_path=Path(tmp) / "events.jsonl", starting_balance=1000)
            res = sim.purchase_coin_package("popular")
            self.assertTrue(res["ok"])
            self.assertEqual(res["package"]["name"], "Nebula Explorer Pack")
            self.assertEqual(res["state"]["balance_lc"], 1000 + 120_000)
            self.assertEqual(res["state"]["balance_sc"], 10.00 + 21.00)

    def test_sweeps_prize_redemption_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(data_path=Path(tmp) / "events.jsonl", starting_balance=1000, starting_balance_sc=60.00)
            
            # Less than 50 SC minimum should raise ValueError
            with self.assertRaises(ValueError):
                sim.request_redemption(30.00)

            # Valid redemption
            res = sim.request_redemption(50.00, "crypto")
            self.assertTrue(res["ok"])
            self.assertTrue(res["ref_id"].startswith("LUNA-RED-"))
            self.assertEqual(res["state"]["balance_sc"], 10.00)

            # Overdraw SC balance should fail
            with self.assertRaises(InsufficientCredits):
                sim.request_redemption(50.00)

    def test_progressive_daily_streak_bonus(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(data_path=Path(tmp) / "events.jsonl", starting_balance=1000, starting_balance_sc=0.0)
            day1 = sim.claim_daily_bonus()
            self.assertEqual(day1["streak_day"], 1)
            self.assertEqual(day1["reward_lc"], 10_000)
            self.assertEqual(day1["reward_sc"], 1.00)

            day2 = sim.claim_daily_bonus()
            self.assertEqual(day2["streak_day"], 2)
            self.assertEqual(day2["reward_lc"], 20_000)
            self.assertEqual(day2["reward_sc"], 1.25)

    def test_provably_fair_cryptographic_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(data_path=Path(tmp) / "events.jsonl", starting_balance=1000)
            res = sim.spin(2, game_id="ancient_tumble")
            event = res["event"]
            self.assertIn("provably_fair", event)
            pf = event["provably_fair"]
            self.assertEqual(len(pf["server_seed_hash"]), 64)
            self.assertEqual(len(pf["result_hash"]), 64)
            self.assertEqual(pf["nonce"], 1)

    def test_referral_reward(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(data_path=Path(tmp) / "events.jsonl", starting_balance=1000, starting_balance_sc=0.0)
            res = sim.claim_referral("LUNA-FRIEND-999")
            self.assertTrue(res["ok"])
            self.assertEqual(res["reward_lc"], 50_000)
            self.assertEqual(res["reward_sc"], 5.00)


class LunalandEnterpriseHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = create_server(
            "127.0.0.1", 0, data_path=Path(self.tmp.name) / "events.jsonl"
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.app.runner.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def post_json(self, path, payload):
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            return response.status, json.load(response)

    def test_store_api_endpoint(self):
        status, data = self.post_json("/api/store/buy", {"package_id": "starter"})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["package"]["lc"], 25_000)

    def test_members_registration_login_and_profile(self):
        # 1. Register new member with unique username per test
        test_user = f"Gamer_{uuid.uuid4().hex[:6]}"
        status, reg = self.post_json("/api/members/register", {
            "username": test_user,
            "password": "SecurePassword123!",
            "email": f"{test_user.lower()}@test.com"
        })
        self.assertEqual(status, 201)
        self.assertTrue(reg["ok"])
        self.assertIn("token", reg)
        token = reg["token"]
        self.assertEqual(reg["member"]["username"], test_user)
        self.assertEqual(reg["member"]["balance_lc"], 50_000)

        # 2. Login with valid credentials
        status, login = self.post_json("/api/members/login", {
            "username": test_user,
            "password": "SecurePassword123!"
        })
        self.assertEqual(status, 200)
        self.assertTrue(login["ok"])
        self.assertEqual(login["member"]["username"], test_user)

        # 3. Login with wrong password should be rejected
        req = Request(
            self.base_url + "/api/members/login",
            data=json.dumps({"username": test_user, "password": "WrongPassword"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            urlopen(req, timeout=2)
            self.fail("Expected 401 Unauthorized for wrong password")
        except Exception as e:
            self.assertTrue(hasattr(e, "code"))
            self.assertEqual(e.code, 401)

        # 4. Query /api/members/me with token
        req_me = Request(
            self.base_url + "/api/members/me",
            headers={"Authorization": f"Bearer {token}"},
            method="GET"
        )
        with urlopen(req_me, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            me_data = json.load(resp)
            self.assertTrue(me_data["ok"])
            self.assertEqual(me_data["member"]["username"], test_user)

    def test_zwallet_crypto_deposit_and_staking(self):
        # 1. Check zwallet info endpoint
        req_info = Request(self.base_url + "/api/zwallet/info", method="GET")
        with urlopen(req_info, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            data = json.load(resp)
            self.assertTrue(data["ok"])
            self.assertIn("ERC20", data["wallet"]["addresses"])

        # 2. Simulate crypto deposit (20 USDT)
        status, dep = self.post_json("/api/zwallet/deposit", {
            "asset": "USDT",
            "amount": 20.0,
            "network": "ERC20"
        })
        self.assertEqual(status, 200)
        self.assertTrue(dep["ok"])
        self.assertEqual(dep["lc_credited"], 120_000)
        self.assertEqual(dep["sc_credited"], 21.00)

        # 3. Stake 10 SC into vault
        status, stk = self.post_json("/api/zwallet/stake", {"amount_sc": 10.0})
        self.assertEqual(status, 200)
        self.assertTrue(stk["ok"])
        self.assertEqual(stk["transaction"]["amount_sc"], 10.0)

        # 4. Check zwallet ledger
        req_tx = Request(self.base_url + "/api/zwallet/ledger", method="GET")
        with urlopen(req_tx, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            txs = json.load(resp)
            self.assertTrue(txs["ok"])
            self.assertTrue(len(txs["transactions"]) >= 2)

    def test_tournaments_and_community_challenge_api(self):
        # 1. List tournaments
        req = Request(self.base_url + "/api/tournaments", method="GET")
        with urlopen(req, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            data = json.load(resp)
            self.assertTrue(data["ok"])
            self.assertTrue(len(data["tournaments"]) >= 1)

        # 2. Community Challenge
        req_c = Request(self.base_url + "/api/tournaments/community", method="GET")
        with urlopen(req_c, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            c = json.load(resp)
            self.assertTrue(c["ok"])
            self.assertIn("target_spins", c["challenge"])

        # 3. Cash drop trigger
        status, drop = self.post_json("/api/tournaments/drop", {})
        self.assertEqual(status, 200)
        self.assertTrue(drop["ok"])
        self.assertEqual(drop["drop"]["reward_lc"], 25_000)

    def test_luckyconnect_aggregator_api(self):
        # 1. Test LuckyConnect games list
        req = Request(self.base_url + "/api/luckyconnect/games", method="GET")
        with urlopen(req, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            data = json.load(resp)
            self.assertTrue(data["ok"])
            self.assertTrue(len(data["games"]) >= 5)

        # 2. Test LuckyConnect providers summary
        req_p = Request(self.base_url + "/api/luckyconnect/providers", method="GET")
        with urlopen(req_p, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            summary = json.load(resp)
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["summary"]["total_available_games"], 6000)

        # 3. Test LuckyConnect authenticated launch session creation with Hawk Security
        status, launch = self.post_json("/api/luckyconnect/launch", {
            "game_id": "ls_live_blackjack_vip",
            "currency": "LC",
            "demo": True
        })
        self.assertEqual(status, 200)
        self.assertTrue(launch["ok"])
        self.assertIn("luckyconnect.luckystreaklive.com", launch["launch_url"])
        self.assertTrue(launch["live_stream"])
        self.assertIn("hawk_auth", launch)
        self.assertIn("Hawk id=", launch["hawk_auth"]["Authorization"])

        # 4. Test LuckyConnect Seamless Webhook Callback
        status, hook = self.post_json("/api/luckyconnect/webhook", {
            "action": "debit",
            "amount": 50.0,
            "session_token": launch["session_token"],
            "transaction_id": "TX-TEST-001",
            "round_id": "RND-TEST-001"
        })
        self.assertEqual(status, 200)
        self.assertTrue(hook["ok"])
        self.assertEqual(hook["status"], "SUCCESS")

    def test_keyless_gaming_hub_and_marketing_api(self):
        # 1. Test Keyless Gaming Hub Feed
        req = Request(self.base_url + "/api/keyless/hub", method="GET")
        with urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.load(resp)
            self.assertTrue(data["ok"])
            self.assertTrue(len(data["providers"]) >= 4)
            self.assertTrue(len(data["deals"]) >= 1)

        # 2. Test Marketing Promo Voucher Redemption
        status, v_res = self.post_json("/api/marketing/redeem", {"code": "LUNA2026"})
        self.assertEqual(status, 200)
        self.assertTrue(v_res["ok"])
        self.assertEqual(v_res["reward_lc"], 100_000)

        # 3. Test Lucky Fortune Wheel Spin
        status_w, w_res = self.post_json("/api/marketing/wheel", {})
        self.assertEqual(status_w, 200)
        self.assertTrue(w_res["ok"])
        self.assertIn("slice", w_res)

        # 4. Test Studio P&L & Fraud Risk Dashboard
        req_r = Request(self.base_url + "/api/risk/dashboard", method="GET")
        with urlopen(req_r, timeout=2) as resp_r:
            self.assertEqual(resp_r.status, 200)
            r_data = json.load(resp_r)
            self.assertTrue(r_data["ok"])
            self.assertIn("LuckyStreak Live", r_data["studios_pnl"])

    def test_ai_dealer_voice_host_api(self):
        # 1. Test AI Dealer Status GET
        req = Request(self.base_url + "/api/ai-dealer/status", method="GET")
        with urlopen(req, timeout=2) as resp:
            self.assertEqual(resp.status, 200)
            data = json.load(resp)
            self.assertTrue(data["ok"])
            self.assertEqual(data["status"], "STREAMING_ONLINE")
            self.assertIn("Gemini 2.5", data["model_engine"])

        # 2. Test Dynamic Voice Commentary POST
        status, comm = self.post_json("/api/ai-dealer/commentary", {
            "event_kind": "spin",
            "game_name": "Gates of Olympus 1000",
            "multiplier": 15.0,
            "payout": 30000,
            "currency": "LC",
            "player_name": "LunaWinner"
        })
        self.assertEqual(status, 200)
        self.assertTrue(comm["ok"])
        self.assertIn("commentary", comm)
        self.assertEqual(comm["commentary"]["emotion"], "excited")
        self.assertEqual(comm["commentary"]["audio_cue"], "fanfare")


if __name__ == "__main__":
    unittest.main()
