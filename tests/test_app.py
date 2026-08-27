import http.client
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


class SimulatorTests(unittest.TestCase):
    def test_spin_records_fake_credit_win_and_bonus_spins(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(
                data_path=Path(tmp) / "events.jsonl",
                starting_balance=100,
                rng=SequenceRng([0.01]),
            )

            result = sim.spin(2)

            self.assertEqual(result["event"]["outcome"], "JACKPOT")
            self.assertEqual(result["event"]["payout"], 24)
            self.assertEqual(result["state"]["balance"], 122)
            self.assertEqual(result["state"]["bonus_spins"], 5)
            self.assertEqual(len(sim.recent_events()), 1)
            self.assertTrue((Path(tmp) / "events.jsonl").read_text())

    def test_bet_validation_and_insufficient_credits_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = Simulator(data_path=Path(tmp) / "events.jsonl", starting_balance=1)

            with self.assertRaises(InvalidBet):
                sim.spin(0)
            with self.assertRaises(InvalidBet):
                sim.spin(101)
            with self.assertRaises(InsufficientCredits):
                sim.spin(2)

    def test_state_reloads_from_append_only_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            first = Simulator(
                data_path=path,
                starting_balance=50,
                rng=SequenceRng([0.99]),
            )
            first.spin(2)

            second = Simulator(data_path=path, starting_balance=50)

            self.assertEqual(second.state()["rounds"], 1)
            self.assertEqual(second.state()["balance"], first.state()["balance"])


class HttpTests(unittest.TestCase):
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

    def get_json(self, path):
        with urlopen(self.base_url + path, timeout=2) as response:
            return response.status, json.load(response)

    def post_json(self, path, payload):
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            return response.status, json.load(response)

    def test_health_state_and_spin_endpoints(self):
        status, health = self.get_json("/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["service"], "zslog")
        self.assertEqual(health["mode"], "demo")

        status, result = self.post_json("/api/spin", {"bet": 2})
        self.assertEqual(status, 200)
        self.assertEqual(result["event"]["source"], "manual")
        self.assertEqual(result["state"]["rounds"], 1)

        status, state = self.get_json("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["rounds"], 1)

    def test_sse_stream_starts_with_snapshot(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        connection.request("GET", "/events")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertTrue(response.getheader("Content-Type").startswith("text/event-stream"))
        self.assertEqual(response.readline().decode().strip(), "event: snapshot")
        connection.close()

    def test_auto_run_is_bounded(self):
        status, result = self.post_json(
            "/api/auto/start", {"rounds": 3, "bet": 2, "interval_ms": 0}
        )
        self.assertEqual(status, 202)
        self.assertTrue(result["running"])

        deadline = time.time() + 2
        while time.time() < deadline and self.server.app.runner.is_running():
            time.sleep(0.01)

        self.assertFalse(self.server.app.runner.is_running())
        state = self.get_json("/api/state")[1]
        self.assertEqual(state["rounds"], 3)

    def test_static_dashboard_is_demo_labelled(self):
        with urlopen(self.base_url + "/", timeout=2) as response:
            html = response.read().decode()
        self.assertIn("DEMO ONLY", html)
        self.assertIn("/app.js", html)


if __name__ == "__main__":
    unittest.main()
