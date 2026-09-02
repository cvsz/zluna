"""Tests for new ZLUNA modules: WebRTC, Redis Cluster, Smart Contract, i18n."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webrtc_stream import WebRTCStreamEngine, StreamRoom, webrtc_engine
from redis_cluster import RedisClusterManager, InMemoryEventBus, redis_cluster
from smart_contract import SmartContractAnchor, MerkleTree, smart_contract
from i18n import I18nEngine, i18n_engine, TRANSLATIONS
from bot_integrations import BotIntegrationHub, TelegramMiniApp, DiscordBot, bot_hub


class TestMerkleTree(unittest.TestCase):
    def test_merkle_root_computation(self):
        leaves = ["a", "b", "c", "d"]
        tree = MerkleTree(leaves)
        self.assertTrue(len(tree.root) == 64)  # SHA-256 hex

    def test_merkle_proof_verification(self):
        leaves = ["result1", "result2", "result3"]
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)
        self.assertTrue(MerkleTree.verify_proof("result1", proof, tree.root))

    def test_merkle_proof_invalid(self):
        leaves = ["a", "b"]
        tree = MerkleTree(leaves)
        proof = tree.get_proof(0)
        self.assertFalse(MerkleTree.verify_proof("tampered", proof, tree.root))

    def test_empty_tree(self):
        tree = MerkleTree([])
        self.assertEqual(tree.root, "")


class TestSmartContract(unittest.TestCase):
    def setUp(self):
        self.contract = SmartContractAnchor()

    def test_submit_result(self):
        res = self.contract.submit_result("hash123", "client", "server_hash", 1, 1)
        self.assertTrue(res["ok"])
        self.assertEqual(res["submission"]["status"], "pending")

    def test_anchor_batch(self):
        for i in range(3):
            self.contract.submit_result(f"hash_{i}", "client", f"server_{i}", i, i)
        res = self.contract.anchor_batch(batch_size=3)
        self.assertTrue(res["ok"])
        self.assertIn("merkle_root", res["batch"])
        self.assertIn("tx_hash", res["batch"])

    def test_anchor_empty(self):
        res = self.contract.anchor_batch()
        self.assertFalse(res["ok"])

    def test_verify_on_chain(self):
        for i in range(5):
            self.contract.submit_result(f"hash_{i}", "client", f"server_{i}", i, i)
        batch = self.contract.anchor_batch(batch_size=5)
        first_result = batch["batch"]["results"][0]
        verify = self.contract.verify_on_chain(
            first_result["result_hash"],
            first_result["merkle_proof"],
            batch["batch"]["merkle_root"],
        )
        self.assertTrue(verify["valid"])

    def test_contract_info(self):
        info = self.contract.get_contract_info()
        self.assertTrue(info["ok"])
        self.assertIn("polygon", info["supported_chains"])

    def test_solidity_generation(self):
        source = self.contract.generate_solidity_contract()
        self.assertIn("contract ZlunaProvablyFair", source)
        self.assertIn("anchorBatch", source)
        self.assertIn("verifyResult", source)


class TestWebRTC(unittest.TestCase):
    def setUp(self):
        self.engine = WebRTCStreamEngine()

    def test_register_studio(self):
        res = self.engine.register_studio("studio_1", "Monte Carlo Live", "Monaco")
        self.assertTrue(res["ok"])
        self.assertEqual(res["studio"]["status"], "online")

    def test_create_room(self):
        self.engine.register_studio("studio_1", "Test Studio")
        res = self.engine.create_room("studio_1", "blackjack", 50)
        self.assertTrue(res["ok"])
        self.assertEqual(res["room"]["game_type"], "blackjack")

    def test_studio_join(self):
        self.engine.register_studio("studio_1", "Test")
        room = self.engine.create_room("studio_1")
        room_id = room["room"]["room_id"]
        res = self.engine.studio_join_room(room_id, "peer_studio")
        self.assertTrue(res["ok"])
        self.assertEqual(res["room"]["status"], "live")

    def test_viewer_join(self):
        self.engine.register_studio("studio_1", "Test")
        room = self.engine.create_room("studio_1")
        room_id = room["room"]["room_id"]
        self.engine.studio_join_room(room_id, "peer_studio")
        res = self.engine.viewer_join_room(room_id, "peer_viewer", "player1")
        self.assertTrue(res["ok"])

    def test_room_full(self):
        self.engine.register_studio("studio_1", "Test")
        room = self.engine.create_room("studio_1", max_viewers=2)
        room_id = room["room"]["room_id"]
        self.engine.studio_join_room(room_id, "peer_studio")
        self.engine.viewer_join_room_room = lambda: None
        self.engine.viewer_join_room(room_id, "v1", "p1")
        self.engine.viewer_join_room(room_id, "v2", "p2")
        res = self.engine.viewer_join_room(room_id, "v3", "p3")
        self.assertFalse(res["ok"])

    def test_close_room(self):
        self.engine.register_studio("studio_1", "Test")
        room = self.engine.create_room("studio_1")
        room_id = room["room"]["room_id"]
        res = self.engine.close_room(room_id)
        self.assertTrue(res["ok"])

    def test_generate_peer_id(self):
        pid = self.engine.generate_peer_id()
        self.assertTrue(pid.startswith("peer_"))

    def test_studio_config(self):
        config = self.engine.get_studio_config()
        self.assertIn("ice_servers", config)
        self.assertIn("VP9", config["codec_preferences"])


class TestRedisCluster(unittest.TestCase):
    def setUp(self):
        self.manager = RedisClusterManager()

    def test_standalone_mode(self):
        res = self.manager.configure([])
        self.assertTrue(res["ok"])
        self.assertFalse(self.manager.is_cluster_enabled)

    def test_node_registration(self):
        self.manager.configure([])
        res = self.manager.register_node("127.0.0.1", 9581)
        self.assertTrue(res["ok"])
        self.assertEqual(res["node"]["host"], "127.0.0.1")

    def test_list_nodes_standalone(self):
        self.manager.configure([])
        self.manager.register_node("127.0.0.1", 9581)
        nodes = self.manager.list_nodes()
        self.assertTrue(len(nodes) >= 1)

    def test_cluster_status(self):
        self.manager.configure([])
        status = self.manager.get_cluster_status()
        self.assertTrue(status["ok"])
        self.assertEqual(status["mode"], "standalone")

    def test_distributed_lock(self):
        self.manager.configure([])
        token = self.manager.acquire_lock("test_lock")
        self.assertIsNotNone(token)
        released = self.manager.release_lock("test_lock", token)
        self.assertTrue(released)


class TestInMemoryEventBus(unittest.TestCase):
    def test_publish_subscribe(self):
        bus = InMemoryEventBus()
        q = MagicMock()
        q.put_nowait = MagicMock()
        bus.subscribe("test_channel", q)
        bus.publish("test_channel", {"data": "hello"})
        q.put_nowait.assert_called_once()


class TestI18n(unittest.TestCase):
    def test_all_languages_present(self):
        for lang in ["EN", "TH", "JA", "ZH", "ES", "PT"]:
            self.assertIn(lang, TRANSLATIONS)

    def test_english_keys_complete(self):
        en = TRANSLATIONS["EN"]
        required_keys = ["app_title", "spin_to_win", "nav_lobby", "store_title", "redeem_title", "vip_title", "fair_title", "live_dealer_title", "bot_title"]
        for key in required_keys:
            self.assertIn(key, en)

    def test_translations_differ(self):
        en = TRANSLATIONS["EN"]["spin_to_win"]
        th = TRANSLATIONS["TH"]["spin_to_win"]
        self.assertNotEqual(en, th)

    def test_get_translations(self):
        engine = I18nEngine()
        res = engine.get_translations("EN")
        self.assertTrue(res["ok"])
        self.assertEqual(res["language"], "EN")
        self.assertIn("dictionary", res)

    def test_get_all_translations(self):
        engine = I18nEngine()
        res = engine.get_all_translations()
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["languages"]), 6)


class TestBotIntegrations(unittest.TestCase):
    def test_telegram_miniapp_url(self):
        res = bot_hub.generate_telegram_miniapp_url("player1")
        self.assertTrue(res["ok"])
        self.assertIn("miniapp", res["miniapp_url"])

    def test_telegram_session(self):
        res = bot_hub.telegram.create_miniapp_session("player1", 12345)
        self.assertTrue(res["ok"])
        self.assertIn("session_token", res)

    def test_telegram_validation(self):
        res = bot_hub.telegram.validate_init_data("hash=abc&user=123", "test_token")
        self.assertTrue(res["ok"])

    def test_discord_connect(self):
        res = bot_hub.discord.connect("valid_token_xyz123456789")
        self.assertTrue(res["ok"])

    def test_discord_disconnect(self):
        bot_hub.discord.connect("valid_token")
        res = bot_hub.discord.disconnect()
        self.assertTrue(res["ok"])
        self.assertFalse(bot_hub.discord.is_connected)

    def test_discord_big_win(self):
        res = bot_hub.discord.format_big_win_alert("Player1", "Slots", 50.0, 5000.0, "LC")
        self.assertIn("embeds", res)
        self.assertIn("BIG WIN", res["embeds"][0]["title"])

    def test_discord_embed(self):
        res = bot_hub.discord.format_embed("Title", "Desc", [{"name": "F", "value": "V"}])
        self.assertIn("embeds", res)

    def test_bot_status(self):
        res = bot_hub.get_bot_status()
        self.assertTrue(res["ok"])
        self.assertIn("telegram", res)
        self.assertIn("discord", res)

    def test_slash_commands(self):
        res = bot_hub.discord.format_slash_command_menu()
        self.assertTrue(res["ok"])
        self.assertTrue(len(res["commands"]) > 0)


if __name__ == "__main__":
    unittest.main()
