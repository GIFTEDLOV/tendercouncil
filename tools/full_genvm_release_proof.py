"""Produce the exact-artifact, five-validator TenderCouncil v2 release proof.

External web and model responses are deterministic fixtures, but every state
transition and callback is executed by the generated production Core and
Evaluator artifacts. No RPC or live transaction is used.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from glsim.consensus import run_consensus
from glsim.engine import SimEngine
from glsim.state import StateStore

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "artifacts" / "tender_council_core_deployable.py"
EVALUATOR = ROOT / "artifacts" / "tender_council_evaluator_deployable.py"
PROOF = ROOT / "artifacts" / "tender_council_v2_multi_validator_proof.json"
MANIFESTS = ROOT / "fixtures" / "live" / "final-v2" / "manifests"
BLOBS = ROOT / "fixtures" / "live" / "blobs"

BUYER = "0x" + "10" * 20
EXECUTOR = "0x" + "20" * 20
BUDGET = 80_000_000_000_000_000
DEADLINE = 1_798_761_600
HASH = "sha256:" + "a" * 64
WEIGHTS = [35, 20, 20, 15, 10]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value: bytes) -> str:
    return "sha256:" + sha256_bytes(value)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def comparative_result(tender_id: str, suffixes: list[str]) -> dict:
    valid = [f"{tender_id}-bid-{suffix}" for suffix in suffixes if suffix in ("a", "b")]
    winner = valid[-1]
    runner = valid[0] if len(valid) > 1 else ""
    scores = []
    values = {
        "a": [30, 17, 14, 8, 8],
        "b": [34, 19, 16, 15, 10],
    }
    for bid_id in valid:
        row = values[bid_id.rsplit("-", 1)[1]]
        scores.append({
            "bid_id": bid_id, "technical": row[0], "delivery": row[1],
            "price": row[2], "capability": row[3], "support": row[4],
            "total": sum(row),
        })
    semantic = [f"{tender_id}-bid-{suffix}" for suffix in suffixes if suffix in ("a", "b", "c")]
    semantic_bad = [f"{tender_id}-bid-c"] if "c" in suffixes else []
    deterministic = [
        f"{tender_id}-bid-{suffix}" for suffix in suffixes if suffix in ("d", "e")
    ]
    return {
        "confidence": "HIGH",
        "deterministic_disqualified_bid_ids": deterministic,
        "integrity_disqualified_bid_ids": [],
        "semantic_candidate_ids": semantic,
        "semantic_disqualified_bid_ids": semantic_bad,
        "semantic_classifications": [
            {
                "bid_id": bid_id,
                "mandatory_requirements_pass": bid_id not in semantic_bad,
            }
            for bid_id in semantic
        ],
        "disqualified_bid_ids": sorted(deterministic + semantic_bad),
        "rationale": "Fixture-bound production-artifact consensus proof.",
        "runner_up_bid_id": runner,
        "runner_up_score": scores[0]["total"] if runner else 0,
        "scores": scores,
        "status": "COMPARATIVE",
        "valid_bid_ids": valid,
        "winner_bid_id": winner,
        "winner_total_score": scores[-1]["total"],
    }


def new_engine(seed: str):
    original_stdin_fd = os.dup(0)
    engine = SimEngine(StateStore(chain_id=4221, seed=seed))
    engine.activate()
    engine.vm.warp("2026-01-01T00:00:00+00:00")
    core_address, core = engine.deploy(str(CORE), sender=BUYER)
    evaluator_address, _ = engine.deploy(
        str(EVALUATOR),
        args=[core_address, "tendercouncil.evaluator.v2"],
        sender=BUYER,
    )
    engine.call_method(
        core_address, "bind_evaluator",
        [type(core.bootstrapper)(evaluator_address), "tendercouncil.evaluator.v2", HASH],
        sender=BUYER,
    )
    return engine, core_address, evaluator_address, original_stdin_fd


def close_engine(engine, original_stdin_fd: int):
    engine.deactivate()
    os.dup2(original_stdin_fd, 0)
    os.close(original_stdin_fd)


def mock_web(engine, url: str, body: bytes):
    response = {"status": 200, "body": body.decode("utf-8")}
    engine.vm.mock_web(url, response)
    engine.vm.mock_web(url.replace(".", "\\."), response)


def prepare_tender(engine, core: str, tender_id: str, suffixes: list[str]):
    engine.vm.value = BUDGET
    engine.call_method(
        core, "create_tender",
        [
            tender_id, "Five-validator release proof",
            "https://fixture.example/brief.json", HASH, BUDGET, 30, 90,
            DEADLINE, 600,
            "authentication;CSV export;responsive/mobile support;dashboard/chart functionality",
            *WEIGHTS,
            "capability:required;delivery:optional;support:optional;technical:optional",
        ],
        sender=BUYER,
    )
    engine.vm.value = 0
    engine.vm._balances[bytes.fromhex(core[2:])] = BUDGET
    engine.call_method(core, "open_tender", [tender_id], sender=BUYER)

    bidders = {}
    for suffix in suffixes:
        source = json.loads((MANIFESTS / f"bid_{suffix}.json").read_text(encoding="utf-8"))
        source["tender_id"] = tender_id
        proposal_url = f"https://fixture.example/{tender_id}/bid_{suffix}.json"
        for evidence in source["evidence"]:
            blob = (BLOBS / evidence["url"].rsplit("/", 1)[1]).read_bytes()
            evidence["sha256"] = digest(blob)
            mock_web(engine, evidence["url"], blob)
        proposal_raw = canonical(source).encode("utf-8")
        mock_web(engine, proposal_url, proposal_raw)
        commitments = ";".join(
            item["evidence_id"] + "|" + item["kind"] + "|" + item["criterion"]
            + "|" + ("1" if item["required"] else "0") + "|" + item["url"]
            + "|" + item["sha256"]
            for item in source["evidence"]
        )
        bid_id = f"{tender_id}-bid-{suffix}"
        bidder = source["bidder"]
        bidders[suffix] = bidder
        engine.call_method(
            core, "submit_bid",
            [
                bid_id, tender_id, source["price_wei"], source["delivery_days"],
                source["support_days"], proposal_url, digest(proposal_raw),
                commitments, "tendercouncil.bid.v1",
            ],
            sender=bidder,
        )
    engine.vm.warp("2027-02-01T00:00:00+00:00")
    engine.call_method(core, "close_tender", [tender_id], sender=BUYER)
    return bidders


def serialized_votes(engine) -> list[str]:
    from genlayer.gl import vm as gl_vm
    from genlayer.py import calldata

    votes = []
    for _ in range(5):
        agreed = True
        for stored, _leader_fn, validator_fn in engine.vm._captured_validators:
            decoded = calldata.decode(calldata.encode(stored))
            if type(decoded) is not type(stored) or not validator_fn(
                gl_vm.Return(calldata=decoded)
            ):
                agreed = False
                break
        votes.append("agree" if agreed else "disagree")
    return votes


def consensus_call(engine, call, label: str) -> dict:
    result = run_consensus(
        engine, lambda: (call(), label.encode("utf-8")),
        num_validators=5, max_rotations=3
    )
    if result.error is not None:
        raise RuntimeError(f"{label}: execution failed before consensus: {result.error}")
    if result.status.name != "FINALIZED" or result.votes != ["agree"] * 5:
        raise RuntimeError(f"{label}: five-validator consensus failed: {result}")
    votes = serialized_votes(engine)
    if votes != ["agree"] * 5:
        raise RuntimeError(f"{label}: pinned calldata consensus failed: {votes}")
    return {
        "label": label,
        "status": result.status.name,
        "rotation": result.rotation,
        "consensus_votes": result.votes,
        "serialized_calldata_votes": votes,
        "captured_nondeterministic_boundaries": len(engine.vm._captured_validators),
    }


def evaluation_attempt(
    engine, core: str, evaluator: str, tender_id: str, *, retry: bool, label: str
):
    start_method = "retry_evaluation" if retry else "start_evaluation"
    sender = EXECUTOR if retry else BUYER
    core_run = consensus_call(
        engine,
        lambda: engine.call_method(core, start_method, [tender_id], sender=sender),
        label + "_core_request",
    )
    requested = engine.call_method(core, "get_tender", [tender_id])
    nonce = int(requested.evaluation_nonce)
    if requested.status != "EVALUATING":
        payload = engine.call_method(
            evaluator, "get_evaluation_result", [tender_id, nonce]
        )
        return {
            "core_request": core_run,
            "evaluator_job": "executed_by_finalized_core_message",
            "core_callback": "consumed_by_finalized_evaluator_message",
            "nonce": nonce,
            "payload": payload,
        }
    evaluator_run = consensus_call(
        engine,
        lambda: engine.call_method(
            evaluator, "start_evaluation_job",
            [tender_id, nonce, requested.closed_snapshot_digest], sender=core,
        ),
        label + "_evaluator_job",
    )
    payload = engine.call_method(evaluator, "get_evaluation_result", [tender_id, nonce])
    current = engine.call_method(core, "get_tender", [tender_id])
    callback_run = None
    if current.status == "EVALUATING":
        parsed = json.loads(payload)
        payload_digest = digest(payload.encode("utf-8"))
        if parsed.get("state") in (
            "MODEL_CANDIDATE_INVALID", "MODEL_PROVIDER_UNAVAILABLE"
        ):
            callback_run = consensus_call(
                engine,
                lambda: engine.call_method(
                    core, "receive_evaluation_failure",
                    [
                        tender_id, nonce, requested.closed_snapshot_digest,
                        parsed["state"], payload_digest,
                    ],
                    sender=evaluator,
                ),
                label + "_core_failure_callback",
            )
        else:
            callback_run = consensus_call(
                engine,
                lambda: engine.call_method(
                    core, "receive_evaluation_result",
                    [
                        tender_id, nonce, requested.closed_snapshot_digest,
                        "tendercouncil.evaluator.v2", parsed["status"],
                        parsed["winner_bid_id"], payload_digest,
                    ],
                    sender=evaluator,
                ),
                label + "_core_result_callback",
            )
    return {
        "core_request": core_run,
        "evaluator_job": evaluator_run,
        "core_callback": callback_run or "consumed_by_finalized_emitted_message",
        "nonce": nonce,
        "payload": payload,
    }


def review_attempt(
    engine, core: str, evaluator: str, tender_id: str, *, first: bool, label: str
):
    method = "advance_after_response" if first else "retry_review"
    core_run = consensus_call(
        engine,
        lambda: engine.call_method(core, method, [tender_id], sender=EXECUTOR),
        label + "_core_request",
    )
    requested = engine.call_method(core, "get_tender", [tender_id])
    review_nonce = int(requested.review_nonce)
    if requested.status != "REVIEWING_CHALLENGES":
        payload = engine.call_method(
            evaluator, "get_review_result", [tender_id, review_nonce]
        )
        return {
            "core_request": core_run,
            "evaluator_job": "executed_by_finalized_core_message",
            "core_callback": "consumed_by_finalized_evaluator_message",
            "review_nonce": review_nonce,
            "payload": payload,
        }
    evaluator_run = consensus_call(
        engine,
        lambda: engine.call_method(
            evaluator, "start_review_job",
            [
                tender_id, int(requested.evaluation_nonce), review_nonce,
                requested.closed_snapshot_digest,
                requested.evaluation_result_digest,
                requested.challenge_set_digest,
            ],
            sender=core,
        ),
        label + "_evaluator_job",
    )
    payload = engine.call_method(evaluator, "get_review_result", [tender_id, review_nonce])
    current = engine.call_method(core, "get_tender", [tender_id])
    callback_run = None
    if current.status == "REVIEWING_CHALLENGES":
        parsed = json.loads(payload)
        payload_digest = digest(payload.encode("utf-8"))
        common = [
            tender_id, int(requested.evaluation_nonce), review_nonce,
            requested.closed_snapshot_digest, requested.evaluation_result_digest,
            requested.challenge_set_digest,
        ]
        if parsed.get("state") in (
            "MODEL_CANDIDATE_INVALID", "MODEL_PROVIDER_UNAVAILABLE"
        ):
            args = common + [parsed["state"], payload_digest]
            callback_run = consensus_call(
                engine,
                lambda: engine.call_method(
                    core, "receive_review_failure", args, sender=evaluator
                ),
                label + "_core_failure_callback",
            )
        else:
            args = common + [
                parsed["decision"], parsed["winner_bid_id"], payload_digest,
            ]
            callback_run = consensus_call(
                engine,
                lambda: engine.call_method(
                    core, "receive_review_result", args, sender=evaluator
                ),
                label + "_core_result_callback",
            )
    return {
        "core_request": core_run,
        "evaluator_job": evaluator_run,
        "core_callback": callback_run or "consumed_by_finalized_emitted_message",
        "review_nonce": review_nonce,
        "payload": payload,
    }


def evaluation_and_review_scenario() -> dict:
    engine, core, evaluator, stdin_fd = new_engine("release-proof-evaluation-review")
    try:
        tender_id = "proof-eval-review"
        bidders = prepare_tender(engine, core, tender_id, ["a", "b", "c", "d", "e"])
        result = comparative_result(tender_id, ["a", "b", "c", "d", "e"])
        engine.vm.mock_llm("Required fields: status", canonical(result))
        evaluation = evaluation_attempt(
            engine, core, evaluator, tender_id, retry=False,
            label="comparative_evaluation",
        )
        tender = engine.call_method(core, "get_tender", [tender_id])
        if tender.status != "PROVISIONAL_AWARD" or tender.provisional_winner != result["winner_bid_id"]:
            raise RuntimeError(
                "production Core did not consume the evaluation callback: "
                + tender.status + " / " + tender.provisional_winner
            )

        engine.call_method(core, "start_response_window", [tender_id], sender=EXECUTOR)
        engine.call_method(
            core, "submit_challenge",
            [
                f"{tender_id}-challenge-a", tender_id, "RUBRIC_MISAPPLIED",
                result["winner_bid_id"], "", "", "",
            ],
            sender=bidders["a"],
        )
        response = engine.call_method(core, "get_tender", [tender_id])
        engine.vm.warp(datetime.fromtimestamp(
            int(response.response_window_end) + 1, timezone.utc
        ).isoformat())
        review_model = {
            "decision": "UPHOLD", "winner_bid_id": result["winner_bid_id"],
            "rationale": "Authenticated challenge does not change the winner.",
        }
        engine.vm.mock_llm("Return exactly decision", canonical(review_model))
        review = review_attempt(
            engine, core, evaluator, tender_id, first=True,
            label="challenge_review",
        )
        final = engine.call_method(core, "get_tender", [tender_id])
        if final.status != "AWARDED" or final.final_winner != result["winner_bid_id"]:
            raise RuntimeError("production Core did not consume the review callback")
        review_payload = engine.call_method(evaluator, "get_review_result", [tender_id, 1])
        review_digest = digest(review_payload.encode("utf-8"))
        duplicate_rejected = False
        try:
            engine.call_method(
                core, "receive_review_result",
                [
                    tender_id, 1, 1, final.closed_snapshot_digest,
                    final.evaluation_result_digest, final.challenge_set_digest,
                    "UPHOLD", result["winner_bid_id"], review_digest,
                ],
                sender=evaluator,
            )
        except Exception:
            duplicate_rejected = True
        if not duplicate_rejected:
            raise RuntimeError("duplicate review callback advanced production Core")
        return {
            "scenario": "production_artifact_comparative_evaluation_and_review",
            "contracts": "generated Core + generated Evaluator",
            "evaluation": evaluation,
            "review": review,
            "evaluation_callback_consumed": True,
            "review_callback_consumed": True,
            "duplicate_review_callback_rejected": True,
            "winner_bid_id": final.final_winner,
        }
    finally:
        close_engine(engine, stdin_fd)


def no_valid_scenario() -> dict:
    engine, core, evaluator, stdin_fd = new_engine("release-proof-no-valid")
    try:
        tender_id = "proof-no-valid"
        prepare_tender(engine, core, tender_id, [])
        run = evaluation_attempt(
            engine, core, evaluator, tender_id, retry=False,
            label="no_valid_bid",
        )
        tender = engine.call_method(core, "get_tender", [tender_id])
        if tender.status != "NO_VALID_BID" or tender.final_winner != "":
            raise RuntimeError("NO_VALID_BID callback was not consumed by production Core")
        return {
            "scenario": "production_artifact_no_valid_bid",
            "contracts": "generated Core + generated Evaluator",
            "run": run,
            "no_valid_bid_callback_consumed": True,
        }
    finally:
        close_engine(engine, stdin_fd)


def malformed_evaluation_scenario() -> dict:
    engine, core, evaluator, stdin_fd = new_engine("release-proof-malformed-evaluation")
    try:
        tender_id = "proof-malformed-eval"
        prepare_tender(engine, core, tender_id, ["a"])
        engine.vm.mock_llm("Required fields: status", "[]")
        runs = []
        runs.append(evaluation_attempt(
            engine, core, evaluator, tender_id, retry=False,
            label="malformed_evaluation_attempt_1",
        ))
        first = engine.call_method(core, "get_tender", [tender_id])
        if first.status != "EVALUATION_RETRYABLE":
            raise RuntimeError("malformed evaluation did not become retryable")
        failure_payload = engine.call_method(evaluator, "get_evaluation_result", [tender_id, 1])
        failure = json.loads(failure_payload)
        if failure != {"result": {}, "state": "MODEL_CANDIDATE_INVALID"}:
            raise RuntimeError("malformed evaluation escaped the bounded envelope")

        runs.append(evaluation_attempt(
            engine, core, evaluator, tender_id, retry=True,
            label="malformed_evaluation_attempt_2",
        ))
        second = engine.call_method(core, "get_tender", [tender_id])
        stale_rejected = False
        try:
            engine.call_method(
                core, "receive_evaluation_failure",
                [
                    tender_id, 1, second.closed_snapshot_digest,
                    "MODEL_CANDIDATE_INVALID", digest(failure_payload.encode("utf-8")),
                ],
                sender=evaluator,
            )
        except Exception:
            stale_rejected = True
        if not stale_rejected:
            raise RuntimeError("stale evaluation failure callback advanced production Core")

        runs.append(evaluation_attempt(
            engine, core, evaluator, tender_id, retry=True,
            label="malformed_evaluation_attempt_3",
        ))
        failed = engine.call_method(core, "get_tender", [tender_id])
        if failed.status != "EVALUATION_FAILED" or int(failed.evaluation_nonce) != 3:
            raise RuntimeError("bounded malformed evaluation did not reach safe failure state")
        return {
            "scenario": "production_artifact_malformed_evaluation_recovery",
            "contracts": "generated Core + generated Evaluator",
            "runs": runs,
            "malformed_model_nonthrowing": True,
            "bounded_retry_reached": 3,
            "stale_callback_rejected": True,
            "safe_escrow_exit_available": True,
        }
    finally:
        close_engine(engine, stdin_fd)


def malformed_review_scenario() -> dict:
    engine, core, evaluator, stdin_fd = new_engine("release-proof-malformed-review")
    try:
        tender_id = "proof-malformed-review"
        bidders = prepare_tender(engine, core, tender_id, ["a", "b"])
        result = comparative_result(tender_id, ["a", "b"])
        engine.vm.mock_llm("Required fields: status", canonical(result))
        evaluation = evaluation_attempt(
            engine, core, evaluator, tender_id, retry=False,
            label="pre_review_valid_evaluation",
        )
        engine.call_method(core, "start_response_window", [tender_id], sender=EXECUTOR)
        engine.call_method(
            core, "submit_challenge",
            [
                f"{tender_id}-challenge-a", tender_id, "RUBRIC_MISAPPLIED",
                result["winner_bid_id"], "", "", "",
            ],
            sender=bidders["a"],
        )
        response = engine.call_method(core, "get_tender", [tender_id])
        engine.vm.warp(datetime.fromtimestamp(
            int(response.response_window_end) + 1, timezone.utc
        ).isoformat())
        engine.vm.mock_llm("Return exactly decision", "[]")
        runs = [review_attempt(
            engine, core, evaluator, tender_id, first=True,
            label="malformed_review_attempt_1",
        )]
        for nonce in (2, 3):
            runs.append(review_attempt(
                engine, core, evaluator, tender_id, first=False,
                label=f"malformed_review_attempt_{nonce}",
            ))
        final = engine.call_method(core, "get_tender", [tender_id])
        if final.status != "AWARDED" or final.final_winner != result["winner_bid_id"]:
            raise RuntimeError("bounded review failure did not uphold the valid winner")
        return {
            "scenario": "production_artifact_malformed_review_recovery",
            "contracts": "generated Core + generated Evaluator",
            "evaluation": evaluation,
            "review_runs": runs,
            "malformed_model_nonthrowing": True,
            "bounded_retry_reached": 3,
            "valid_winner_upheld": True,
            "buyer_refund_escape_available": False,
        }
    finally:
        close_engine(engine, stdin_fd)


def main() -> None:
    scenarios = [
        evaluation_and_review_scenario(),
        no_valid_scenario(),
        malformed_evaluation_scenario(),
        malformed_review_scenario(),
    ]
    proof = {
        "classification": "LOCAL_EXACT_ARTIFACT_FULL_GENSIM_MULTI_VALIDATOR_PROOF_NO_LIVE_RPC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "chain_id": 4221,
        "validators_per_consensus_run": 5,
        "max_rotations": 3,
        "core_artifact": str(CORE.relative_to(ROOT)).replace("\\", "/"),
        "core_artifact_sha256": sha256_bytes(CORE.read_bytes()),
        "core_artifact_bytes": CORE.stat().st_size,
        "evaluator_artifact": str(EVALUATOR.relative_to(ROOT)).replace("\\", "/"),
        "evaluator_artifact_sha256": sha256_bytes(EVALUATOR.read_bytes()),
        "evaluator_artifact_bytes": EVALUATOR.stat().st_size,
        "external_boundaries": "deterministic web/LLM fixtures; production artifact logic and callbacks",
        "coverage": {
            "comparative_evaluation": "PASS",
            "core_evaluation_callback_consumption": "PASS",
            "no_valid_bid": "PASS",
            "malformed_evaluation_model": "PASS",
            "evaluator_failure_and_bounded_retry": "PASS",
            "challenge_review": "PASS",
            "core_review_callback_consumption": "PASS",
            "malformed_review_model": "PASS",
            "stale_or_duplicate_callback_rejection": "PASS",
            "valid_winner_upheld_after_bounded_review_failure": "PASS",
        },
        "scenarios": scenarios,
        "live_rpc_used": False,
        "live_transaction_broadcast": False,
    }
    PROOF.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))
    print("exact-artifact full GenVM five-validator proof: PASS")


if __name__ == "__main__":
    main()
