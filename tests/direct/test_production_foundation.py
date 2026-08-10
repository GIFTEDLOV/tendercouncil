import hashlib
import json

import pytest


PRODUCTION = "contracts/tender_council_production.py"
BRIEF_HASH = "sha256:" + "b" * 64
PROPOSAL_HASH = "sha256:" + "c" * 64
START = "2026-01-01T00:00:00Z"
DEADLINE = 1767225600 + 3600


def _create(contract, direct_vm, buyer, tender_id, award=8000):
    direct_vm.sender = buyer
    direct_vm.value = award
    contract.create_tender(
        tender_id,
        "Analytics dashboard procurement",
        "https://buyer.example/brief.json",
        BRIEF_HASH,
        8000,
        award,
        30,
        90,
        DEADLINE,
        600,
        "authentication;CSV export;responsive/mobile;dashboard/chart",
        35,
        20,
        20,
        15,
        10,
        "capability:required;secondary:optional",
    )
    direct_vm.value = 0


def _manifest_payload(bidder, tender_id="manifest-policy", **overrides):
    payload = {
        "schema_version": "tendercouncil.bid.v1",
        "tender_id": tender_id,
        "bidder": "0x" + bidder.hex(),
        "price": 7400,
        "delivery_days": 27,
        "support_days": 120,
        "proposal": {
            "technical_approach": "Bounded dashboard architecture",
            "delivery_plan": "Iterative delivery with acceptance checks",
            "support_plan": "Ninety day support with incident response",
            "requirements": ["authentication", "CSV export", "responsive/mobile"],
        },
        "evidence": [
            {
                "evidence_id": "cap-1",
                "kind": "CAPABILITY",
                "criterion": "capability",
                "required": True,
                "url": "https://bidder.example/capability.json",
                "sha256": "sha256:" + "d" * 64,
            }
        ],
    }
    payload.update(overrides)
    body = json.dumps(payload, separators=(",", ":"))
    return body, "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _canonical_manifest(
    bidder, tender_id, price, delivery_days, support_days, technical,
    requirements, claims,
):
    evidence_body = json.dumps(
        {
            "schema_version": "tendercouncil.evidence.v1",
            "kind": "CAPABILITY",
            "claims": claims,
        },
        separators=(",", ":"),
    )
    evidence_hash = "sha256:" + hashlib.sha256(evidence_body.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "tendercouncil.bid.v1",
        "tender_id": tender_id,
        "bidder": "0x" + bidder.hex(),
        "price": price,
        "delivery_days": delivery_days,
        "support_days": support_days,
        "proposal": {
            "technical_approach": technical,
            "delivery_plan": "Acceptance-driven delivery plan",
            "support_plan": "Support and warranty plan",
            "requirements": requirements,
        },
        "evidence": [{
            "evidence_id": "cap-" + bidder.hex()[:8],
            "kind": "CAPABILITY",
            "criterion": "capability",
            "required": True,
            "url": "https://fixture.example/cap-" + bidder.hex()[:8] + ".json",
            "sha256": evidence_hash,
        }],
    }
    body = json.dumps(manifest, separators=(",", ":"))
    return body, "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest(), evidence_body


def _prepare_single_evaluation(
    direct_vm, contract, buyer, bidder, tender_id="response-policy"
):
    _create(contract, direct_vm, buyer, tender_id)
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender(tender_id)
    body, body_hash, evidence_body = _canonical_manifest(
        bidder,
        tender_id,
        7400,
        27,
        120,
        "Authenticated dashboard architecture",
        ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"],
        "Authenticated capability evidence for dashboard delivery.",
    )
    direct_vm.sender = bidder
    bid_id = "response-bid"
    manifest_url = "https://fixture.example/response-bid.json"
    contract.submit_bid(
        bid_id, tender_id, 7400, 27, 120, manifest_url, body_hash
    )
    evidence_url = "https://fixture.example/cap-" + bidder.hex()[:8] + ".json"
    direct_vm.mock_web(
        manifest_url.replace(".", "\\."), {"status": 200, "body": body}
    )
    direct_vm.mock_web(
        evidence_url.replace(".", "\\."), {"status": 200, "body": evidence_body}
    )
    direct_vm.sender = buyer
    contract.validate_bid_manifest(bid_id)
    direct_vm.warp("2026-01-01T02:00:00Z")
    contract.close_tender(tender_id)
    direct_vm.mock_web(
        manifest_url.replace(".", "\\."), {"status": 200, "body": body}
    )
    direct_vm.mock_web(
        evidence_url.replace(".", "\\."), {"status": 200, "body": evidence_body}
    )
    direct_vm.mock_llm(
        r"^You are the TenderCouncil comparative procurement evaluator",
        json.dumps({
            "winner_bid_id": bid_id,
            "valid_bid_ids": [bid_id],
            "disqualified_bid_ids": [],
            "scores": [{
                "bid_id": bid_id,
                "technical": 34,
                "delivery": 19,
                "price": 16,
                "capability": 15,
                "support": 10,
                "total": 94,
            }],
            "winner_total_score": 94,
            "runner_up_bid_id": "",
            "runner_up_score": 0,
            "confidence": "HIGH",
            "rationale": "Authenticated bid satisfies the locked policy.",
        }, separators=(",", ":")),
    )
    direct_vm.sender = buyer
    contract.evaluate_tender(tender_id)
    return bid_id, evidence_body


def test_any_wallet_can_create_and_open_a_funded_tender(
    direct_vm, direct_deploy, direct_bob
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "buyer-owned-1")
    direct_vm.deal(direct_vm._contract_address, 8000)

    contract.open_tender("buyer-owned-1")

    tender = contract.get_tender("buyer-owned-1")
    assert tender.buyer.as_bytes == direct_bob
    assert tender.status == "OPEN"
    assert tender.escrow_amount == 8000
    assert contract.get_contract_balance() == 8000


@pytest.mark.parametrize("funding", [0, 7999, 8001])
def test_creation_requires_exact_award_funding(
    direct_vm, direct_deploy, direct_bob, funding
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    direct_vm.sender = direct_bob
    direct_vm.value = funding
    with direct_vm.expect_revert("exact award funding"):
        contract.create_tender(
            "funding-" + str(funding),
            "Funded tender",
            "https://buyer.example/brief.json",
            BRIEF_HASH,
            8000,
            8000,
            30,
            90,
            DEADLINE,
            600,
            "authentication",
            35,
            20,
            20,
            15,
            10,
            "required",
        )


def test_rubric_total_and_constraints_are_locked(
    direct_vm, direct_deploy, direct_bob
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    direct_vm.sender = direct_bob
    direct_vm.value = 8000
    with direct_vm.expect_revert("total exactly 100"):
        contract.create_tender(
            "bad-rubric",
            "Bad rubric",
            "https://buyer.example/brief.json",
            BRIEF_HASH,
            8000,
            8000,
            30,
            90,
            DEADLINE,
            600,
            "authentication",
            35,
            20,
            20,
            15,
            11,
            "required",
        )


def test_bid_terms_are_sender_bound_unique_and_deadline_checked(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "bid-policy")
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender("bid-policy")

    direct_vm.sender = direct_charlie
    contract.submit_bid(
        "bid-c",
        "bid-policy",
        7400,
        27,
        120,
        "https://bidder.example/proposal.json",
        PROPOSAL_HASH,
    )
    with direct_vm.expect_revert("one bid per wallet"):
        contract.submit_bid(
            "bid-c-2",
            "bid-policy",
            7300,
            27,
            120,
            "https://bidder.example/proposal-2.json",
            PROPOSAL_HASH,
        )

    direct_vm.warp("2026-01-01T02:00:00Z")
    with direct_vm.expect_revert("bid is late"):
        contract.submit_bid(
            "late",
            "bid-policy",
            7000,
            20,
            90,
            "https://bidder.example/late.json",
            PROPOSAL_HASH,
        )


def test_close_requires_deadline_and_buyer_authorization(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "close-policy")
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender("close-policy")

    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only the tender buyer"):
        contract.close_tender("close-policy")

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("deadline has not passed"):
        contract.close_tender("close-policy")
    direct_vm.warp("2026-01-01T02:00:00Z")
    contract.close_tender("close-policy")
    assert contract.get_tender("close-policy").status == "CLOSED"


def test_multiple_buyers_and_tenders_share_only_observed_locked_escrow(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "funded-a")
    _create(contract, direct_vm, direct_charlie, "funded-b")

    direct_vm.deal(direct_vm._contract_address, 8000)
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("does not cover locked escrow"):
        contract.open_tender("funded-a")

    direct_vm.deal(direct_vm._contract_address, 16000)
    contract.open_tender("funded-a")
    direct_vm.sender = direct_charlie
    contract.open_tender("funded-b")
    assert contract.get_tender("funded-a").escrow_amount == 8000
    assert contract.get_tender("funded-b").escrow_amount == 8000
    assert contract.get_contract_balance() == 16000


def test_funded_cancellation_is_disabled_until_refund_is_finalized(
    direct_vm, direct_deploy, direct_bob
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "refund-policy")
    with direct_vm.expect_revert("finalized refund"):
        contract.cancel_tender("refund-policy")


def test_bid_v1_manifest_is_hash_bound_sender_bound_and_schema_checked(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "manifest-policy")
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender("manifest-policy")

    direct_vm.sender = direct_bob
    body, manifest_hash = _manifest_payload(direct_bob)
    contract.submit_bid(
        "manifest-bid",
        "manifest-policy",
        7400,
        27,
        120,
        "https://bidder.example/manifest.json",
        manifest_hash,
    )
    direct_vm.mock_web(
        r"https://bidder\.example/manifest\.json",
        {"status": 200, "body": body},
    )

    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only the tender buyer"):
        contract.validate_bid_manifest("manifest-bid")

    direct_vm.sender = direct_bob
    contract.validate_bid_manifest("manifest-bid")
    bid = contract.get_bid("manifest-bid")
    assert bid.manifest_status == "MANIFEST_VALID"
    assert bid.manifest_evidence_count == 1


def test_manifest_hash_mismatch_and_schema_mutations_fail_closed(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "manifest-attacks")
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender("manifest-attacks")
    direct_vm.sender = direct_bob

    body, manifest_hash = _manifest_payload(direct_bob, "manifest-attacks")
    contract.submit_bid(
        "manifest-hash-mismatch",
        "manifest-attacks",
        7400,
        27,
        120,
        "https://bidder.example/manifest.json",
        manifest_hash,
    )
    direct_vm.mock_web(
        r"https://bidder\.example/manifest\.json",
        {"status": 200, "body": body + " changed"},
    )
    contract.validate_bid_manifest("manifest-hash-mismatch")
    assert contract.get_bid("manifest-hash-mismatch").manifest_status == "HASH_MISMATCH"

    invalid_body, invalid_hash = _manifest_payload(
        direct_charlie,
        "manifest-attacks",
        evidence=[{
            "evidence_id": "cap-1",
            "kind": "UNSUPPORTED",
            "criterion": "capability",
            "required": True,
            "url": "https://bidder.example/capability.json",
            "sha256": "sha256:" + "d" * 64,
        }],
    )
    direct_vm.sender = direct_charlie
    contract.submit_bid(
        "manifest-schema-invalid",
        "manifest-attacks",
        7400,
        27,
        120,
        "https://bidder.example/invalid-manifest.json",
        invalid_hash,
    )
    direct_vm.mock_web(
        r"https://bidder\.example/invalid-manifest\.json",
        {"status": 200, "body": invalid_body},
    )
    direct_vm.sender = direct_bob
    contract.validate_bid_manifest("manifest-schema-invalid")
    assert contract.get_bid("manifest-schema-invalid").manifest_status == "SCHEMA_INVALID"


def test_canonical_five_bid_comparative_evaluator_selects_authenticated_best_bid(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "canonical-five")
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender("canonical-five")

    bidder_a = bytes.fromhex("11" * 20)
    bidder_d = bytes.fromhex("33" * 20)
    bidder_e = bytes.fromhex("44" * 20)
    bid_inputs = [
        ("bid-a", bidder_a, 6200, 26, 90, "Strong but conventional dashboard architecture", ["authentication", "CSV export", "responsive/mobile"], "Authenticated delivery history and dashboard implementation."),
        ("bid-b", direct_charlie, 7400, 27, 120, "Layered architecture with robust authentication and analytics", ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"], "Authenticated capability evidence for multiple analytics dashboards and exports."),
        ("bid-c", direct_bob, 4300, 20, 90, "Low-cost dashboard with exports but no authentication design", ["CSV export", "responsive/mobile", "dashboard/chart"], "Authenticated evidence is not supplied for the missing authentication capability."),
        ("bid-d", bidder_d, 8700, 24, 120, "Excellent architecture", ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"], "Excellent authenticated capability."),
        ("bid-e", bidder_e, 6900, 45, 120, "Excellent architecture", ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"], "Excellent authenticated capability."),
    ]
    prepared = []
    for bid_id, bidder, price, delivery_days, support_days, technical, requirements, claims in bid_inputs:
        direct_vm.sender = bidder
        if bid_id in ("bid-a", "bid-b", "bid-c"):
            manifest_body, manifest_hash, evidence_body = _canonical_manifest(
                bidder,
                "canonical-five",
                price,
                delivery_days,
                support_days,
                technical,
                requirements,
                claims,
            )
            manifest_url = "https://fixture.example/" + bid_id + ".json"
            contract.submit_bid(
                bid_id,
                "canonical-five",
                price,
                delivery_days,
                support_days,
                manifest_url,
                manifest_hash,
            )
            prepared.append((bid_id, manifest_url, manifest_body, evidence_body, bidder))
        else:
            contract.submit_bid(
                bid_id,
                "canonical-five",
                price,
                delivery_days,
                support_days,
                "https://fixture.example/" + bid_id + ".json",
                PROPOSAL_HASH,
            )

    direct_vm.sender = direct_bob
    for bid_id, manifest_url, manifest_body, evidence_body, bidder in prepared:
        evidence_url = "https://fixture.example/cap-" + bidder.hex()[:8] + ".json"
        direct_vm.mock_web(
            manifest_url.replace(".", "\\."),
            {"status": 200, "body": manifest_body},
        )
        direct_vm.mock_web(
            evidence_url.replace(".", "\\."),
            {"status": 200, "body": evidence_body},
        )
        contract.validate_bid_manifest(bid_id)

    direct_vm.sender = direct_bob
    direct_vm.warp("2026-01-01T02:00:00Z")
    contract.close_tender("canonical-five")

    result = {
        "winner_bid_id": "bid-b",
        "valid_bid_ids": ["bid-a", "bid-b"],
        "disqualified_bid_ids": ["bid-c", "bid-d", "bid-e"],
        "scores": [
            {"bid_id": "bid-a", "technical": 30, "delivery": 17, "price": 14, "capability": 8, "support": 8, "total": 77},
            {"bid_id": "bid-b", "technical": 34, "delivery": 19, "price": 16, "capability": 15, "support": 10, "total": 94},
        ],
        "winner_total_score": 94,
        "runner_up_bid_id": "bid-a",
        "runner_up_score": 77,
        "confidence": "HIGH",
        "rationale": "Bid B best satisfies the locked policy with authenticated capability evidence.",
    }
    for bid_id, manifest_url, manifest_body, evidence_body, bidder in prepared:
        evidence_url = "https://fixture.example/cap-" + bidder.hex()[:8] + ".json"
        direct_vm.mock_web(
            manifest_url.replace(".", "\\."),
            {"status": 200, "body": manifest_body},
        )
        direct_vm.mock_web(
            evidence_url.replace(".", "\\."),
            {"status": 200, "body": evidence_body},
        )
    direct_vm.mock_llm(
        r"Return JSON only with exactly these fields",
        json.dumps(result, separators=(",", ":")),
    )

    contract.evaluate_tender("canonical-five")
    evaluation = contract.get_evaluation("canonical-five")
    assert evaluation.winner_bid_id == "bid-b"
    assert evaluation.valid_bid_ids == "bid-a,bid-b"
    assert evaluation.disqualified_bid_ids == "bid-c,bid-d,bid-e"
    assert evaluation.winner_total_score == 94
    assert evaluation.runner_up_bid_id == "bid-a"
    assert contract.get_tender("canonical-five").status == "EVALUATING"


def test_comparative_evaluator_fails_closed_on_impossible_model_score(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    _create(contract, direct_vm, direct_bob, "malformed-evaluator")
    direct_vm.deal(direct_vm._contract_address, 8000)
    contract.open_tender("malformed-evaluator")

    direct_vm.sender = direct_charlie
    body, body_hash, evidence_body = _canonical_manifest(
        direct_charlie,
        "malformed-evaluator",
        7400,
        27,
        120,
        "A compliant technical approach",
        ["authentication"],
        "Authenticated capability claim",
    )
    contract.submit_bid(
        "malformed-bid",
        "malformed-evaluator",
        7400,
        27,
        120,
        "https://fixture.example/malformed-bid.json",
        body_hash,
    )
    evidence_url = "https://fixture.example/cap-" + direct_charlie.hex()[:8] + ".json"
    direct_vm.mock_web(
        r"https://fixture\.example/malformed-bid\.json",
        {"status": 200, "body": body},
    )
    direct_vm.mock_web(
        evidence_url.replace(".", "\\."),
        {"status": 200, "body": evidence_body},
    )
    direct_vm.sender = direct_bob
    contract.validate_bid_manifest("malformed-bid")
    direct_vm.warp("2026-01-01T02:00:00Z")
    contract.close_tender("malformed-evaluator")

    direct_vm.mock_web(
        r"https://fixture\.example/malformed-bid\.json",
        {"status": 200, "body": body},
    )
    direct_vm.mock_web(
        evidence_url.replace(".", "\\."),
        {"status": 200, "body": evidence_body},
    )
    direct_vm.mock_llm(
        r"Return JSON only with exactly these fields",
        json.dumps({
            "winner_bid_id": "malformed-bid",
            "valid_bid_ids": ["malformed-bid"],
            "disqualified_bid_ids": [],
            "scores": [{
                "bid_id": "malformed-bid",
                "technical": 35,
                "delivery": 20,
                "price": 20,
                "capability": 15,
                "support": 10,
                "total": 1,
            }],
            "winner_total_score": 1,
            "runner_up_bid_id": "",
            "runner_up_score": 0,
            "confidence": "HIGH",
            "rationale": "Impossible arithmetic",
        }, separators=(",", ":")),
    )
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert():
        contract.evaluate_tender("malformed-evaluator")
    assert contract.get_tender("malformed-evaluator").status == "CLOSED"


def test_provisional_award_requires_response_window_before_advancement(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    bid_id, _ = _prepare_single_evaluation(
        direct_vm, contract, direct_bob, direct_charlie
    )
    direct_vm.sender = direct_bob
    contract.begin_provisional_award("response-policy")
    assert contract.get_tender("response-policy").status == "PROVISIONAL_AWARD"
    contract.start_response_window("response-policy")
    tender = contract.get_tender("response-policy")
    assert tender.status == "RESPONSE_WINDOW"
    assert tender.provisional_winner == bid_id
    assert tender.response_deadline > 0
    with direct_vm.expect_revert("response window is still open"):
        contract.advance_award("response-policy")
    direct_vm.warp("2026-01-01T02:10:01Z")
    contract.advance_award("response-policy")
    assert contract.get_tender("response-policy").status == "AWARDED"
    assert contract.get_tender("response-policy").final_winner == bid_id


def test_only_authenticated_bidder_can_submit_one_committed_evidence_challenge(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    bid_id, _ = _prepare_single_evaluation(
        direct_vm, contract, direct_bob, direct_charlie, "challenge-policy"
    )
    direct_vm.sender = direct_bob
    contract.begin_provisional_award("challenge-policy")
    contract.start_response_window("challenge-policy")
    with direct_vm.expect_revert("only a tender bidder"):
        contract.submit_challenge(
            "unauthorized-challenge",
            "challenge-policy",
            "RUBRIC_MISAPPLIED",
            bid_id,
            "",
            "",
            "",
        )
    direct_vm.sender = direct_charlie
    contract.submit_challenge(
        "committed-challenge",
        "challenge-policy",
        "COMMITTED_EVIDENCE_OVERLOOKED",
        bid_id,
        "cap-" + direct_charlie.hex()[:8],
        "",
        "",
    )
    direct_vm.sender = direct_bob
    contract.validate_challenge("committed-challenge")
    assert contract.get_challenge("committed-challenge").status == "VALID"
    with direct_vm.expect_revert("one challenge per bidder"):
        direct_vm.sender = direct_charlie
        contract.submit_challenge(
            "second-challenge",
            "challenge-policy",
            "RUBRIC_MISAPPLIED",
            bid_id,
            "",
            "",
            "",
        )


def test_mutated_external_challenge_content_is_not_reviewable(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    bid_id, _ = _prepare_single_evaluation(
        direct_vm, contract, direct_bob, direct_charlie, "challenge-mutation"
    )
    direct_vm.sender = direct_bob
    contract.begin_provisional_award("challenge-mutation")
    contract.start_response_window("challenge-mutation")
    challenge_body = json.dumps({
        "schema_version": "tendercouncil.challenge.v1",
        "challenge_id": "mutated-challenge",
        "tender_id": "challenge-mutation",
        "challenger": "0x" + direct_charlie.hex(),
        "reason_code": "RUBRIC_MISAPPLIED",
        "target_bid_id": bid_id,
        "referenced_evidence_id": "",
        "claim": "The locked rubric was misapplied.",
    }, separators=(",", ":"))
    challenge_hash = "sha256:" + hashlib.sha256(challenge_body.encode("utf-8")).hexdigest()
    direct_vm.sender = direct_charlie
    contract.submit_challenge(
        "mutated-challenge",
        "challenge-mutation",
        "RUBRIC_MISAPPLIED",
        bid_id,
        "",
        "https://fixture.example/challenge.json",
        challenge_hash,
    )
    direct_vm.mock_web(
        r"https://fixture\.example/challenge\.json",
        {"status": 200, "body": challenge_body + " changed"},
    )
    direct_vm.sender = direct_bob
    contract.validate_challenge("mutated-challenge")
    assert contract.get_challenge("mutated-challenge").status == "INVALID"
    tender = contract.get_tender("challenge-mutation")
    direct_vm.warp("2026-01-01T02:10:01Z")
    contract.advance_award("challenge-mutation")
    assert contract.get_tender("challenge-mutation").status == "AWARDED"


def test_valid_challenge_enters_one_bounded_review_and_can_uphold_result(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    bid_id, _ = _prepare_single_evaluation(
        direct_vm, contract, direct_bob, direct_charlie, "review-policy"
    )
    direct_vm.sender = direct_bob
    contract.begin_provisional_award("review-policy")
    contract.start_response_window("review-policy")
    direct_vm.sender = direct_charlie
    contract.submit_challenge(
        "review-challenge",
        "review-policy",
        "RUBRIC_MISAPPLIED",
        bid_id,
        "",
        "",
        "",
    )
    direct_vm.sender = direct_bob
    contract.validate_challenge("review-challenge")
    tender = contract.get_tender("review-policy")
    direct_vm.warp("2026-01-01T02:10:01Z")
    contract.advance_award("review-policy")
    assert contract.get_tender("review-policy").status == "REVIEWING_CHALLENGES"
    direct_vm.mock_llm(
        r"You are conducting one bounded TenderCouncil challenge review",
        json.dumps({
            "decision": "UPHOLD",
            "winner_bid_id": bid_id,
            "rationale": "The challenge does not overcome the original comparative result.",
        }, separators=(",", ":")),
    )
    contract.review_challenges("review-policy")
    reviewed = contract.get_tender("review-policy")
    assert reviewed.status == "AWARDED"
    assert reviewed.final_winner == bid_id


def test_settlement_is_separate_from_award_and_replay_protected(
    direct_vm, direct_deploy, direct_bob, direct_charlie
):
    direct_vm.warp(START)
    contract = direct_deploy(PRODUCTION)
    bid_id, _ = _prepare_single_evaluation(
        direct_vm, contract, direct_bob, direct_charlie, "settlement-policy"
    )
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Only awarded tenders"):
        contract.settle_award("settlement-policy")
    contract.begin_provisional_award("settlement-policy")
    contract.start_response_window("settlement-policy")
    with direct_vm.expect_revert("Only awarded tenders"):
        contract.settle_award("settlement-policy")
    direct_vm.warp("2026-01-01T02:10:01Z")
    contract.advance_award("settlement-policy")
    assert contract.get_tender("settlement-policy").final_winner == bid_id
    contract.settle_award("settlement-policy")
    pending = contract.get_tender("settlement-policy")
    assert pending.status == "SETTLEMENT_PENDING"
    assert pending.settlement_state == "TRANSFER_PENDING"
    with direct_vm.expect_revert("already been requested"):
        contract.settle_award("settlement-policy")
    with direct_vm.expect_revert("finalized transfer balance delta"):
        contract.confirm_settlement("settlement-policy")
