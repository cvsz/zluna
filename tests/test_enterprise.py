import json
import tempfile
import threading
import time
import unittest
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
        # 1. Register new member
        status, reg = self.post_json("/api/members/register", {
            "username": "TestGamer99",
            "password": "SecurePassword123!",
            "email": "gamer@test.com"
        })
        self.assertEqual(status, 201)
        self.assertTrue(reg["ok"])
        self.assertIn("token", reg)
        token = reg["token"]
        self.assertEqual(reg["member"]["username"], "TestGamer99")
        self.assertEqual(reg["member"]["balance_lc"], 50_000)

        # 2. Login with valid credentials
        status, login = self.post_json("/api/members/login", {
            "username": "TestGamer99",
            "password": "SecurePassword123!"
        })
        self.assertEqual(status, 200)
        self.assertTrue(login["ok"])
        self.assertEqual(login["member"]["username"], "TestGamer99")

        # 3. Login with wrong password should be rejected
        req = Request(
            self.base_url + "/api/members/login",
            data=json.dumps({"username": "TestGamer99", "password": "WrongPassword"}).encode(),
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
            self.assertEqual(me_data["member"]["username"], "TestGamer99")


if __name__ == "__main__":
    unittest.main()
