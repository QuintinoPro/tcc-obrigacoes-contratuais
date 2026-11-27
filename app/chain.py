"""Adaptador blockchain.

Por padrão sobe uma chain EVM em memória (eth-tester/py-evm), que executa o
smart contract Solidity de verdade, sem depender de rede externa. Para usar um
nó persistente (Anvil, Hardhat ou uma testnet com conta desbloqueada), defina
CHAIN_RPC_URL.
"""
from __future__ import annotations

import os
from pathlib import Path

import solcx
from web3 import EthereumTesterProvider, Web3

SOLC_VERSION = "0.8.24"
CONTRACT_PATH = Path(__file__).resolve().parent.parent / "contracts" / "ObligationRegistry.sol"

STATUSES = ["PENDENTE", "EM_EXECUCAO", "ENTREGUE", "EM_ANALISE", "APROVADO", "REJEITADO", "CONCLUIDO"]


def _b32(hex_digest: str | None) -> bytes:
    if not hex_digest:
        return b"\x00" * 32
    return bytes.fromhex(hex_digest)


class Chain:
    def __init__(self) -> None:
        rpc = os.getenv("CHAIN_RPC_URL")
        self.mode = f"rpc:{rpc}" if rpc else "eth-tester (EVM local em memória)"
        self.w3 = Web3(Web3.HTTPProvider(rpc)) if rpc else Web3(EthereumTesterProvider())
        self.account = self.w3.eth.accounts[0]

        if SOLC_VERSION not in [str(v) for v in solcx.get_installed_solc_versions()]:
            solcx.install_solc(SOLC_VERSION)
        compiled = solcx.compile_files(
            [str(CONTRACT_PATH)], output_values=["abi", "bin"], solc_version=SOLC_VERSION
        )
        iface = next(v for k, v in compiled.items() if k.endswith(":ObligationRegistry"))
        self.abi = iface["abi"]
        factory = self.w3.eth.contract(abi=self.abi, bytecode=iface["bin"])
        rcpt = self._wait(factory.constructor().transact({"from": self.account}))
        self.address = rcpt.contractAddress
        self.contract = self.w3.eth.contract(address=self.address, abi=self.abi)

    def _wait(self, tx_hash):
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def _send(self, fn) -> dict:
        rcpt = self._wait(fn.transact({"from": self.account}))
        return {"tx": rcpt.transactionHash.hex(), "block": rcpt.blockNumber}

    # --- escrita -----------------------------------------------------------
    def register_contract(self, sha256_hex: str) -> dict | None:
        if self.contract.functions.contractRegisteredAt(_b32(sha256_hex)).call() != 0:
            return None
        return self._send(self.contract.functions.registerContract(_b32(sha256_hex)))

    def create_obligation(self, obligation_id: int, contract_sha: str, data_sha: str) -> dict:
        return self._send(
            self.contract.functions.createObligation(obligation_id, _b32(contract_sha), _b32(data_sha))
        )

    def transition(self, obligation_id: int, to: str, evidence_sha: str | None, actor_sha: str) -> dict:
        return self._send(
            self.contract.functions.transition(
                obligation_id, STATUSES.index(to), _b32(evidence_sha), _b32(actor_sha)
            )
        )

    # --- leitura -----------------------------------------------------------
    def contract_registered_at(self, sha256_hex: str) -> int:
        return self.contract.functions.contractRegisteredAt(_b32(sha256_hex)).call()

    def obligation(self, obligation_id: int) -> dict | None:
        contract_hash, data_hash, status, exists = self.contract.functions.obligations(obligation_id).call()
        if not exists:
            return None
        return {"status": STATUSES[status], "contract_sha256": contract_hash.hex(), "data_sha256": data_hash.hex()}

    def obligation_status(self, obligation_id: int) -> str | None:
        ob = self.obligation(obligation_id)
        return ob and ob["status"]

    def find_evidence(self, sha256_hex: str) -> dict | None:
        """Procura o hash de uma evidência nos eventos StatusChanged (a fonte é a chain, não o banco)."""
        target = _b32(sha256_hex)
        for e in self.contract.events.StatusChanged.get_logs(from_block=0):
            if e.args["evidenceHash"] == target:
                block = self.w3.eth.get_block(e.blockNumber)
                return {"obligation_id": e.args["obligationId"], "tx": e.transactionHash.hex(),
                        "block": e.blockNumber, "timestamp": block["timestamp"]}
        return None

    def is_valid_transition(self, frm: str, to: str) -> bool:
        return self.contract.functions.isValidTransition(STATUSES.index(frm), STATUSES.index(to)).call()

    def status_events(self, obligation_id: int) -> list[dict]:
        logs = self.contract.events.StatusChanged.get_logs(
            from_block=0, argument_filters={"obligationId": obligation_id}
        )
        return [
            {
                "from": STATUSES[e.args["from"]],
                "to": STATUSES[e.args["to"]],
                "evidence_sha256": e.args["evidenceHash"].hex(),
                "block": e.blockNumber,
                "tx": e.transactionHash.hex(),
            }
            for e in logs
        ]

    def info(self) -> dict:
        return {"mode": self.mode, "contract_address": self.address, "block": self.w3.eth.block_number}
