import hashlib


CORE = "contracts/tender_council_core.py"
EVALUATOR = "contracts/tender_council_evaluator.py"
ZERO_HASH = "sha256:" + "a" * 64
DEADLINE = 1798761600


def _addr(raw, prototype):
    return type(prototype.bootstrapper)(raw)


def _create(core, direct_vm, buyer, tender_id="split-tender"):
    direct_vm.sender = buyer
    direct_vm.value = 8000
    core.create_tender(
        tender_id,
        "Analytics dashboard procurement",
        "https://buyer.example/brief.json",
        ZERO_HASH,
        8000,
        8000,
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


def test_core_is_unconfigured_until_one_time_binding(direct_vm, direct_deploy, direct_bob):
    core = direct_deploy(CORE)
    direct_vm.warp("2026-01-01T00:00:00Z")
    _create_unbound = lambda: core.open_tender("never")
    with direct_vm.expect_revert("evaluator binding"):
        _create_unbound()
    assert core.get_production_ready() is False

    evaluator_address = _addr(bytes.fromhex("12" * 20), core)
    source_hash = "sha256:" + "b" * 64
    direct_vm.sender = direct_vm.origin
    core.bind_evaluator(evaluator_address, "tendercouncil.evaluator.v1", source_hash)
    with direct_vm.expect_revert("already permanently bound"):
        core.bind_evaluator(evaluator_address, "tendercouncil.evaluator.v1", source_hash)
    assert core.get_production_ready() is True
    assert "12" * 20 in core.get_evaluator_binding()


def test_core_snapshot_is_canonical_and_evaluation_is_locked_until_callback(
    direct_vm, direct_deploy, direct_bob
):
    direct_vm.warp("2026-01-01T00:00:00Z")
    core = direct_deploy(CORE)
    evaluator_address = _addr(bytes.fromhex("34" * 20), core)
    direct_vm.sender = direct_vm.origin
    core.bind_evaluator(evaluator_address, "tendercouncil.evaluator.v1", "sha256:" + "c" * 64)
    _create(core, direct_vm, direct_bob)
    direct_vm.deal(direct_vm._contract_address, 8000)
    direct_vm.sender = direct_bob
    core.open_tender("split-tender")
    direct_vm.warp("2027-01-01T00:00:00Z")
    core.close_tender("split-tender")
    tender = core.get_tender("split-tender")
    snapshot = core.get_closed_snapshot("split-tender")
    assert tender.closed_snapshot_digest == "sha256:" + hashlib.sha256(snapshot.encode()).hexdigest()

    direct_vm.sender = direct_bob
    core.start_evaluation("split-tender")
    assert core.get_tender("split-tender").status == "EVALUATING"
    with direct_vm.expect_revert("caller is not the bound evaluator"):
        core.receive_evaluation_result(
            "split-tender", 1, tender.closed_snapshot_digest,
            "tendercouncil.evaluator.v1", "NO_VALID_BID", "", ZERO_HASH,
        )


def test_core_binds_immutable_commercial_terms_and_rejects_manual_award(
    direct_vm, direct_deploy, direct_bob
):
    direct_vm.warp("2026-01-01T00:00:00Z")
    core = direct_deploy(CORE)
    direct_vm.sender = direct_vm.origin
    core.bind_evaluator(_addr(bytes.fromhex("56" * 20), core), "tendercouncil.evaluator.v1", "sha256:" + "d" * 64)
    _create(core, direct_vm, direct_bob, "manual-award")
    direct_vm.deal(direct_vm._contract_address, 8000)
    direct_vm.sender = direct_bob
    core.open_tender("manual-award")
    assert not hasattr(core, "award_bid")


def test_evaluator_rejects_non_core_job_sender(direct_vm, direct_deploy):
    evaluator = direct_deploy(EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v1")
    with direct_vm.expect_revert("only the bound Core may call evaluator"):
        evaluator.start_evaluation_job("forged", 1, ZERO_HASH)
    assert not hasattr(evaluator, "settle_award")
