import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from app import create_server
from catalog import catalog, GameCatalog
from games import list_games


class CatalogTests(unittest.TestCase):
    def test_local_seed_populates_all_games(self):
        assert len(catalog._entries) == len(list_games())

    def test_list_games_supports_search_and_pagination(self):
        items, total = catalog.list_games(query="roul", page=1, page_size=5)
        assert total >= 1
        assert all("roulette" in item["name"].lower() or "roulette" in item["description"].lower() for item in items)

    def test_categories_providers_and_tags_are_populated(self):
        assert catalog.categories()
        assert catalog.providers()
        assert catalog.tags()

    def test_record_play_updates_count_and_last_played(self):
        before = catalog.get("slots")
        catalog.record_play("slots")
        after = catalog.get("slots")
        assert after["play_count"] == before["play_count"] + 1
        assert after["last_played_at"] is not None

    def test_set_favorite_toggle(self):
        catalog.set_favorite("dice", True)
        assert catalog.get("dice")["favorite"] is True
        catalog.set_favorite("dice", False)
        assert catalog.get("dice")["favorite"] is False


class CatalogHttpTests(unittest.TestCase):
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

    def test_catalog_list_endpoint(self):
        status, data = self.get_json("/api/catalog")
        self.assertEqual(status, 200)
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 1)

    def test_catalog_search_filter(self):
        status, data = self.get_json("/api/catalog?q=roul")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["total"], 1)

    def test_catalog_favorite_toggle(self):
        status, data = self.post_json("/api/catalog/favorite", {"game_id": "coin", "favorite": True})
        self.assertEqual(status, 200)
        self.assertTrue(data["favorite"])

    def test_catalog_sync_endpoint(self):
        status, data = self.post_json("/api/catalog/sync", {})
        self.assertEqual(status, 200)
        self.assertEqual(data["source"], "local-seed")


if __name__ == "__main__":
    unittest.main()
