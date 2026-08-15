from genlayer import *
import hashlib
import json


@gl.contract_interface
class CoreInterface:
    class View:
        pass

    class Write:
        def receive_evaluation_result(self, tender_id, nonce, snapshot_digest,
                                      evaluator_schema_version, result_type,
                                      winner_bid_id, result_digest): ...
        def receive_review_result(self, tender_id, evaluation_nonce, review_nonce,
                                  snapshot_digest, original_result_digest,
                                  challenge_set_digest, decision, winner_bid_id,
                                  result_digest): ...
        def receive_evaluation_failure(self, tender_id, nonce, snapshot_digest,
                                       failure_code, failure_digest): ...
        def receive_review_failure(self, tender_id, evaluation_nonce, review_nonce,
                                   snapshot_digest, original_result_digest,
                                   challenge_set_digest, failure_code,
                                   failure_digest): ...


class SplitFakeEvaluator(gl.Contract):
    def __init__(self, core_address):
        self.core_address = Address(core_address) if isinstance(core_address, str) else core_address
        self.evaluation_result = ""
        self.review_result = ""

    def _digest(self, payload):
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @gl.public.view
    def get_evaluation_result(self, tender_id, nonce):
        return self.evaluation_result

    @gl.public.view
    def get_review_result(self, tender_id, nonce):
        return self.review_result

    @gl.public.write
    def start_evaluation_job(self, tender_id, nonce, snapshot_digest):
        self.evaluation_result = json.dumps({
            "status": "NO_VALID_BID",
            "winner_bid_id": "",
            "valid_bid_ids": [],
            "disqualified_bid_ids": [],
            "deterministic_disqualified_bid_ids": [],
            "integrity_disqualified_bid_ids": [],
            "semantic_candidate_ids": [],
            "semantic_disqualified_bid_ids": [],
            "semantic_classifications": [],
            "scores": [],
            "winner_total_score": 0,
            "runner_up_bid_id": "",
            "runner_up_score": 0,
            "confidence": "LOW",
            "rationale": "test result",
        }, sort_keys=True, separators=(",", ":"))

    @gl.public.write
    def emit_evaluation(self, tender_id, nonce, snapshot_digest, result_digest):
        result = json.loads(self.evaluation_result)
        CoreInterface(self.core_address).emit(on="finalized").receive_evaluation_result(
            tender_id, nonce, snapshot_digest, "tendercouncil.evaluator.v2.1",
            result["status"], result.get("winner_bid_id", ""), result_digest,
        )

    @gl.public.write
    def emit_evaluation_failure(self, tender_id, nonce, snapshot_digest, failure_code):
        self.evaluation_result = json.dumps(
            {"state": failure_code, "result": {}},
            sort_keys=True, separators=(",", ":"),
        )
        CoreInterface(self.core_address).emit(on="finalized").receive_evaluation_failure(
            tender_id, nonce, snapshot_digest, failure_code,
            self._digest(self.evaluation_result),
        )

    @gl.public.write
    def start_review_job(self, tender_id, evaluation_nonce, review_nonce,
                         snapshot_digest, original_result_digest, challenge_set_digest):
        self.review_result = json.dumps({
            "decision": "UPHOLD",
            "winner_bid_id": "bid",
            "rationale": "test review",
        }, sort_keys=True, separators=(",", ":"))

    @gl.public.write
    def emit_review(self, tender_id, evaluation_nonce, review_nonce,
                    snapshot_digest, original_result_digest, challenge_set_digest,
                    result_digest):
        CoreInterface(self.core_address).emit(on="finalized").receive_review_result(
            tender_id, evaluation_nonce, review_nonce, snapshot_digest,
            original_result_digest, challenge_set_digest, "UPHOLD", "bid",
            result_digest,
        )

    @gl.public.write
    def emit_review_failure(self, tender_id, evaluation_nonce, review_nonce,
                            snapshot_digest, original_result_digest,
                            challenge_set_digest, failure_code):
        self.review_result = json.dumps(
            {"state": failure_code, "result": {}},
            sort_keys=True, separators=(",", ":"),
        )
        CoreInterface(self.core_address).emit(on="finalized").receive_review_failure(
            tender_id, evaluation_nonce, review_nonce, snapshot_digest,
            original_result_digest, challenge_set_digest, failure_code,
            self._digest(self.review_result),
        )
