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
