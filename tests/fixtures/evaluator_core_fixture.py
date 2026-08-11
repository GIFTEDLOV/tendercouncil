from genlayer import *
import json


class EvaluatorCoreFixture(gl.Contract):
    def __init__(self, snapshot_text: str, snapshot_digest: str):
        self.snapshot_text = snapshot_text
        self.snapshot_digest = snapshot_digest
        self.callback_status = ""

    @gl.public.view
    def get_evaluation_context(self, tender_id: str) -> str:
        return json.dumps({"evaluation_nonce": 1, "snapshot_digest": self.snapshot_digest, "status": "EVALUATING"}, separators=(",", ":"))

    @gl.public.view
    def get_closed_snapshot(self, tender_id: str) -> str:
        return self.snapshot_text

    @gl.public.view
    def get_review_context(self, tender_id: str, review_nonce: u64) -> str:
        return json.dumps({"evaluation_nonce": 1, "snapshot_digest": self.snapshot_digest, "original_result_digest": "", "challenge_set_digest": "", "challenges": []}, separators=(",", ":"))

    @gl.public.write
    def receive_evaluation_result(self, tender_id: str, nonce: u64, snapshot_digest: str, evaluator_schema_version: str, result_type: str, winner_bid_id: str, result_digest: str):
        self.callback_status = result_type

    @gl.public.write
    def receive_review_result(self, tender_id: str, evaluation_nonce: u64, review_nonce: u64, snapshot_digest: str, original_result_digest: str, challenge_set_digest: str, decision: str, winner_bid_id: str, result_digest: str):
        self.callback_status = decision
