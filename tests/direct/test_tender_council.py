STATUS_OPEN = "OPEN"
STATUS_AWARDED = "AWARDED"
STATUS_CANCELLED = "CANCELLED"
BID_SUBMITTED = "SUBMITTED"
BID_AWARDED = "AWARDED"
BID_REJECTED = "REJECTED"


def same_address(actual, expected_bytes):
    return actual.as_bytes == expected_bytes


def test_owner_can_create_and_open_tender(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_owner

    contract.create_tender("roads-2026", "Road maintenance", "Resurface route A", 1_800_000_000)
    contract.open_tender("roads-2026")

    tender = contract.get_tender("roads-2026")
    assert tender.status == STATUS_OPEN
    assert same_address(tender.issuer, direct_owner)
    assert list(contract.list_tender_ids()) == ["roads-2026"]


def test_non_owner_cannot_create_tender(direct_vm, direct_deploy, direct_bob):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_bob

    with direct_vm.expect_revert("Only the contract owner"):
        contract.create_tender("unauthorized", "Nope", "Nope", 1)


def test_supplier_can_submit_bid_and_evidence(direct_vm, direct_deploy, direct_owner, direct_bob):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_owner
    contract.create_tender("solar-2026", "Solar panels", "Install 100 panels", 1_800_000_000)
    contract.open_tender("solar-2026")

    direct_vm.sender = direct_bob
    contract.submit_bid("bid-bob", "solar-2026", 42_000, "Full installation", "sha256:root")
    contract.add_evidence(
        "ev-bob-1",
        "bid-bob",
        "https://supplier.example/evidence.pdf",
        "sha256:document",
        "capacity-certificate",
    )

    assert contract.get_bid("bid-bob").status == BID_SUBMITTED
    assert same_address(contract.get_evidence("ev-bob-1").submitted_by, direct_bob)


def test_only_supplier_can_add_evidence(direct_vm, direct_deploy, direct_owner, direct_bob, direct_charlie):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_owner
    contract.create_tender("water-2026", "Water works", "Repair borehole", 1_800_000_000)
    contract.open_tender("water-2026")
    direct_vm.sender = direct_bob
    contract.submit_bid("bid-bob", "water-2026", 5_000, "Repair it", "sha256:root")

    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only the bid supplier"):
        contract.add_evidence("ev-1", "bid-bob", "https://example.test/a", "sha256:a", "license")


def test_award_closes_bid_set_and_records_winner(direct_vm, direct_deploy, direct_owner, direct_bob, direct_charlie):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_owner
    contract.create_tender("it-2026", "IT services", "Managed support", 1_800_000_000)
    contract.open_tender("it-2026")
    direct_vm.sender = direct_bob
    contract.submit_bid("bid-bob", "it-2026", 11_000, "Support", "sha256:bob")
    direct_vm.sender = direct_charlie
    contract.submit_bid("bid-charlie", "it-2026", 12_000, "Support", "sha256:charlie")

    direct_vm.sender = direct_owner
    contract.close_tender("it-2026")
    contract.award_bid("it-2026", "bid-bob")

    assert contract.get_tender("it-2026").status == STATUS_AWARDED
    assert contract.get_tender("it-2026").awarded_bid_id == "bid-bob"
    assert contract.get_bid("bid-bob").status == BID_AWARDED
    assert contract.get_bid("bid-charlie").status == BID_REJECTED


def test_invalid_lifecycle_transitions_revert(direct_vm, direct_deploy, direct_owner):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_owner
    contract.create_tender("cancel-me", "Cancellation", "Test", 1)
    contract.cancel_tender("cancel-me")

    assert contract.get_tender("cancel-me").status == STATUS_CANCELLED
    with direct_vm.expect_revert("cannot be cancelled"):
        contract.cancel_tender("cancel-me")


def test_bid_rejected_after_tender_closes(direct_vm, direct_deploy, direct_owner, direct_bob):
    contract = direct_deploy("contracts/tender_council.py")
    direct_vm.sender = direct_owner
    contract.create_tender("closed", "Closed tender", "Test", 1)
    contract.open_tender("closed")
    contract.close_tender("closed")

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("only while the tender is open"):
        contract.submit_bid("late", "closed", 1, "Late", "sha256:late")
