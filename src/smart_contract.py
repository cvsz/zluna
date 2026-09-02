"""On-Chain Smart Contract Integration for Decentralized Provably Fair Verification.

Provides blockchain anchoring of game results, merkle root commitments,
and on-chain verification for transparent, decentralized auditing.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any


class MerkleTree:
    """Simple merkle tree for batch commitment of game results."""

    def __init__(self, leaves: list[str]) -> None:
        self.leaves = leaves
        self.layers: list[list[str]] = []
        self._build()

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _build(self) -> None:
        if not self.leaves:
            self.layers = [[""]]
            return
        current_layer = [self._hash(leaf) for leaf in self.leaves]
        self.layers.append(current_layer)
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else left
                next_layer.append(self._hash(left + right))
            current_layer = next_layer
            self.layers.append(current_layer)

    @property
    def root(self) -> str:
        if self.layers and self.layers[-1]:
            return self.layers[-1][0]
        return ""

    def get_proof(self, index: int) -> list[dict[str, str]]:
        """Get merkle proof for a leaf at given index."""
        proof = []
        idx = index
        for layer in self.layers[:-1]:
            if len(layer) <= 1:
                break
            is_right = idx % 2 == 1
            if is_right:
                sibling_idx = idx - 1
            else:
                sibling_idx = idx + 1 if idx + 1 < len(layer) else idx
            proof.append({
                "position": "left" if is_right else "right",
                "hash": layer[sibling_idx],
            })
            idx //= 2
        return proof

    @staticmethod
    def verify_proof(leaf: str, proof: list[dict[str, str]], root: str) -> bool:
        """Verify a merkle proof."""
        current = hashlib.sha256(leaf.encode("utf-8")).hexdigest()
        for step in proof:
            sibling = step["hash"]
            if step["position"] == "left":
                current = hashlib.sha256((sibling + current).encode("utf-8")).hexdigest()
            else:
                current = hashlib.sha256((current + sibling).encode("utf-8")).hexdigest()
        return current == root


class SmartContractAnchor:
    """Manages on-chain anchoring of provably fair game results."""

    SUPPORTED_CHAINS = {
        "ethereum": {"chain_id": 1, "confirmations": 12, "block_time_s": 12},
        "polygon": {"chain_id": 137, "confirmations": 20, "block_time_s": 2},
        "arbitrum": {"chain_id": 42161, "confirmations": 10, "block_time_s": 0.25},
        "base": {"chain_id": 8453, "confirmations": 5, "block_time_s": 2},
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pending_results: list[dict[str, Any]] = []
        self._anchored_batches: list[dict[str, Any]] = []
        self._merkle_trees: dict[str, MerkleTree] = {}
        self._total_anchored = 0
        self._contract_address = "0x" + secrets.token_hex(20)
        self._active_chain = "polygon"

    def get_contract_info(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "contract_address": self._contract_address,
                "active_chain": self._active_chain,
                "supported_chains": self.SUPPORTED_CHAINS,
                "total_anchored": self._total_anchored,
                "pending_count": len(self._pending_results),
                "anchored_batches": len(self._anchored_batches),
            }

    def submit_result(self, result_hash: str, client_seed: str, server_seed_hash: str, nonce: int, round_id: int) -> dict[str, Any]:
        """Submit a game result for on-chain anchoring."""
        with self._lock:
            submission = {
                "id": f"anchor_{secrets.token_hex(8)}",
                "result_hash": result_hash,
                "client_seed": client_seed,
                "server_seed_hash": server_seed_hash,
                "nonce": nonce,
                "round_id": round_id,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
                "confirmations": 0,
            }
            self._pending_results.append(submission)
            return {"ok": True, "submission": submission}

    def anchor_batch(self, batch_size: int = 10) -> dict[str, Any]:
        """Anchor a pending batch of results on-chain (simulated)."""
        with self._lock:
            if not self._pending_results:
                return {"ok": False, "error": "no pending results to anchor"}
            batch = self._pending_results[:batch_size]
            leaves = [r["result_hash"] for r in batch]
            merkle_tree = MerkleTree(leaves)
            batch_id = f"batch_{secrets.token_hex(8)}"
            tx_hash = "0x" + secrets.token_hex(32)
            block_number = 18_000_000 + len(self._anchored_batches) * 17
            anchored = {
                "batch_id": batch_id,
                "merkle_root": merkle_tree.root,
                "tx_hash": tx_hash,
                "block_number": block_number,
                "chain": self._active_chain,
                "chain_id": self.SUPPORTED_CHAINS[self._active_chain]["chain_id"],
                "result_count": len(batch),
                "results": [
                    {
                        "round_id": r["round_id"],
                        "result_hash": r["result_hash"],
                        "merkle_proof": merkle_tree.get_proof(i),
                    }
                    for i, r in enumerate(batch)
                ],
                "anchored_at": datetime.now(timezone.utc).isoformat(),
                "confirmations": self.SUPPORTED_CHAINS[self._active_chain]["confirmations"],
                "status": "confirmed",
                "gas_used": 85_000 + len(batch) * 12_000,
            }
            self._pending_results = self._pending_results[len(batch):]
            self._anchored_batches.append(anchored)
            self._merkle_trees[batch_id] = merkle_tree
            self._total_anchored += len(batch)
            for r in batch:
                r["status"] = "anchored"
                r["batch_id"] = batch_id
            return {"ok": True, "batch": anchored}

    def verify_on_chain(self, result_hash: str, merkle_proof: list[dict[str, str]], merkle_root: str) -> dict[str, Any]:
        """Verify a result against an on-chain merkle root."""
        valid = MerkleTree.verify_proof(result_hash, merkle_proof, merkle_root)
        return {
            "ok": True,
            "valid": valid,
            "result_hash": result_hash,
            "merkle_root": merkle_root,
            "verification_method": "merkle_proof",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        with self._lock:
            for batch in self._anchored_batches:
                if batch["batch_id"] == batch_id:
                    return batch
            return None

    def list_batches(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return self._anchored_batches[-limit:]

    def get_pending(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._pending_results)

    def generate_solidity_contract(self) -> str:
        """Return a Solidity smart contract template for on-chain verification."""
        return '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ZlunaProvablyFair {
    struct Batch {
        bytes32 merkleRoot;
        uint256 blockNumber;
        uint256 timestamp;
        uint256 resultCount;
        bool confirmed;
    }

    address public immutable operator;
    mapping(bytes32 => Batch) public batches;
    bytes32[] public batchIds;

    event BatchAnchored(bytes32 indexed batchId, bytes32 merkleRoot, uint256 resultCount);
    event ResultVerified(bytes32 indexed batchId, bytes32 indexed resultHash, bool valid);

    constructor() {
        operator = msg.sender;
    }

    modifier onlyOperator() {
        require(msg.sender == operator, "Not authorized");
        _;
    }

    function anchorBatch(bytes32 merkleRoot, uint256 resultCount) external onlyOperator returns (bytes32) {
        bytes32 batchId = keccak256(abi.encodePacked(merkleRoot, block.number, block.timestamp));
        batches[batchId] = Batch({
            merkleRoot: merkleRoot,
            blockNumber: block.number,
            timestamp: block.timestamp,
            resultCount: resultCount,
            confirmed: true
        });
        batchIds.push(batchId);
        emit BatchAnchored(batchId, merkleRoot, resultCount);
        return batchId;
    }

    function verifyResult(
        bytes32 batchId,
        bytes32 resultHash,
        bytes32[] calldata proof
    ) external view returns (bool) {
        Batch memory batch = batches[batchId];
        require(batch.confirmed, "Batch not confirmed");
        bytes32 computedHash = resultHash;
        for (uint256 i = 0; i < proof.length; i++) {
            if (computedHash < proof[i]) {
                computedHash = keccak256(abi.encodePacked(computedHash, proof[i]));
            } else {
                computedHash = keccak256(abi.encodePacked(proof[i], computedHash));
            }
        }
        return computedHash == batch.merkleRoot;
    }

    function getBatchCount() external view returns (uint256) {
        return batchIds.length;
    }
}'''


smart_contract = SmartContractAnchor()
