# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""TenderCouncil's authoritative custody and procurement state machine.

This contract deliberately contains no web access, LLM calls, or semantic
judgment.  The evaluator is an immutable, separately deployed service.  Core
binds exactly one evaluator and accepts only correlated finalized callbacks.
"""

from dataclasses import dataclass
import datetime
import hashlib
import json

from genlayer import *


STATUS_DRAFT = "DRAFT"
STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"
STATUS_EVALUATING = "EVALUATING"
STATUS_PROVISIONAL_AWARD = "PROVISIONAL_AWARD"
STATUS_RESPONSE_WINDOW = "RESPONSE_WINDOW"
STATUS_REVIEWING_CHALLENGES = "REVIEWING_CHALLENGES"
STATUS_AWARDED = "AWARDED"
STATUS_SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
STATUS_SETTLED = "SETTLED"
STATUS_NO_VALID_BID = "NO_VALID_BID"
STATUS_CANCELLED = "CANCELLED"
STATUS_REFUND_PENDING = "REFUND_PENDING"

SETTLEMENT_ESCROWED = "ESCROWED"
SETTLEMENT_UNSETTLED = "UNSETTLED"
SETTLEMENT_TRANSFER_PENDING = "TRANSFER_PENDING"
SETTLEMENT_SETTLED = "SETTLED"
SETTLEMENT_REFUND_PENDING = "REFUND_PENDING"

CHALLENGE_PENDING = "PENDING"
CHALLENGE_VALID = "VALID"
CHALLENGE_INVALID = "INVALID"

CHALLENGE_MANDATORY_REQUIREMENT = "MANDATORY_REQUIREMENT_MISAPPLIED"
CHALLENGE_EVIDENCE_OVERLOOKED = "COMMITTED_EVIDENCE_OVERLOOKED"
CHALLENGE_RUBRIC = "RUBRIC_MISAPPLIED"
CHALLENGE_INTEGRITY = "EVIDENCE_INTEGRITY_ERROR"
ALLOWED_CHALLENGES = (
    CHALLENGE_MANDATORY_REQUIREMENT,
    CHALLENGE_EVIDENCE_OVERLOOKED,
    CHALLENGE_RUBRIC,
    CHALLENGE_INTEGRITY,
)

CORE_SCHEMA_VERSION = "tendercouncil.core.v1"
EVALUATOR_SCHEMA_VERSION = "tendercouncil.evaluator.v1"
SNAPSHOT_SCHEMA_VERSION = "tendercouncil.snapshot.v1"
MIN_RESPONSE_WINDOW_SECONDS = 600
MAX_ID = 96
MAX_TITLE = 200
MAX_URL = 512
MAX_TEXT = 4000
MAX_BIDS = 32
MAX_CHALLENGES = 16
MAX_EVIDENCE_COMMITMENTS = 12000
ZERO_ADDRESS = Address("0x" + "0" * 40)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_hash(value: str) -> bool:
    if len(value) != 71 or value[:7] != "sha256:":
        return False
    for char in value[7:]:
        if char not in "0123456789abcdef":
            return False
    return True


def _canonical(value) -> str:
    """Canonical JSON: sorted keys, compact separators, UTF-8 at hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _parse_rubric(value: str):
    expected = ("technical", "delivery", "price", "capability", "support")
    values = {}
    for item in value.split(";"):
        parts = item.split("=")
        if len(parts) != 2 or parts[0] in values:
            raise ValueError("malformed rubric")
        values[parts[0]] = int(parts[1])
    if tuple(sorted(values)) != tuple(sorted(expected)):
        raise ValueError("malformed rubric")
    weights = tuple(values[name] for name in expected)
    if sum(weights) != 100:
        raise ValueError("rubric must total 100")
    return weights


def _valid_commitments(value: str) -> bool:
    if len(value) > MAX_EVIDENCE_COMMITMENTS:
        return False
    if value == "":
        return True
    seen = []
    for item in value.split(";"):
        fields = item.split("|")
        if len(fields) != 6:
            return False
        evidence_id, kind, criterion, required, url, digest = fields
        if evidence_id == "" or evidence_id in seen or len(evidence_id) > MAX_ID:
            return False
        if kind not in ("CAPABILITY", "DELIVERY", "SUPPORT", "TECHNICAL"):
            return False
        if criterion not in ("capability", "delivery", "support", "technical"):
            return False
        if required not in ("0", "1") or not url.startswith("https://"):
            return False
        if not _is_hash(digest):
            return False
        seen.append(evidence_id)
    return True


@allow_storage
@dataclass
class CoreTender:
    tender_id: str
    buyer: Address
    title: str
    brief_url: str
    brief_sha256: str
    max_budget: u256
    award_amount: u256
    max_delivery_days: u64
    min_support_days: u64
    bidding_deadline: u64
    response_window_seconds: u64
    status: str
    requirements: str
    rubric: str
    evidence_policy: str
    escrow_amount: u256
    closed_snapshot_digest: str
    evaluation_nonce: u64
    evaluation_result_digest: str
    provisional_winner: str
    final_winner: str
    response_window_start: u64
    response_window_end: u64
    review_nonce: u64
    challenge_set_digest: str
    settlement_state: str
    balance_before: u256


@allow_storage
@dataclass
class CoreBid:
    bid_id: str
    tender_id: str
    bidder: Address
    price: u256
    delivery_days: u64
    support_days: u64
    proposal_url: str
    proposal_sha256: str
    evidence_commitments: str
    schema_version: str
    submitted_at: u64


@allow_storage
@dataclass
class CoreChallenge:
    challenge_id: str
    tender_id: str
    challenger: Address
    reason_code: str
    target_bid_id: str
    referenced_evidence_id: str
    challenge_url: str
    challenge_sha256: str
    submitted_at: u64
    status: str
    claims: str


@gl.contract_interface
class EvaluatorInterface:
    class View:
        def get_evaluation_result(self, tender_id: str, nonce: u64) -> str: ...
        def get_review_result(self, tender_id: str, nonce: u64) -> str: ...

    class Write:
        def start_evaluation_job(self, tender_id: str, nonce: u64, snapshot_digest: str): ...
        def start_review_job(
            self, tender_id: str, evaluation_nonce: u64, review_nonce: u64,
            snapshot_digest: str, result_digest: str, challenge_set_digest: str,
        ): ...


@gl.evm.contract_interface
class Recipient:
    class View:
        pass

    class Write:
        pass


class TenderCouncilCore(gl.Contract):
    """Only this contract owns GEN, procurement state, and final settlement."""

    tenders: TreeMap[str, CoreTender]
    bids: TreeMap[str, CoreBid]
    challenges: TreeMap[str, CoreChallenge]
    tender_ids: DynArray[str]
    bid_ids: DynArray[str]
    challenge_ids: DynArray[str]
    bootstrapper: Address
    evaluator_address: Address
    evaluator_version: str
    evaluator_source_hash: str
    evaluator_bound: bool
    total_locked_escrow: u256

    def __init__(self):
        self.bootstrapper = gl.message.sender_address
        self.evaluator_address = ZERO_ADDRESS
        self.evaluator_version = ""
        self.evaluator_source_hash = ""
        self.evaluator_bound = False
        self.total_locked_escrow = u256(0)

    def _now(self) -> u64:
        return u64(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    def _require_length(self, value: str, maximum: int, field: str):
        if value == "" or len(value) > maximum:
            raise gl.vm.UserError(field + " is empty or exceeds its bound")

    def _require_url(self, value: str, field: str):
        self._require_length(value, MAX_URL, field)
        if not value.startswith("https://"):
            raise gl.vm.UserError(field + " must use https")

    def _require_buyer(self, tender: CoreTender):
        if gl.message.sender_address != tender.buyer:
            raise gl.vm.UserError("only the tender buyer may perform this action")

    def _require_ready(self):
        if not self.evaluator_bound:
            raise gl.vm.UserError("evaluator binding is incomplete")

    def _tender(self, tender_id: str) -> CoreTender:
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("tender does not exist")
        return tender

    def _snapshot(self, tender_id: str) -> str:
        tender = self._tender(tender_id)
        bid_values = []
        for bid_id in sorted(self.bid_ids):
            bid = self.bids[bid_id]
            if bid.tender_id != tender_id:
                continue
            bid_values.append({
                "bid_id": str(bid.bid_id),
                "bidder": str(bid.bidder),
                "price": int(bid.price),
                "delivery_days": int(bid.delivery_days),
                "support_days": int(bid.support_days),
                "proposal_url": str(bid.proposal_url),
                "proposal_sha256": str(bid.proposal_sha256),
                "evidence_commitments": str(bid.evidence_commitments),
                "schema_version": str(bid.schema_version),
                "submitted_at": int(bid.submitted_at),
            })
        return _canonical({
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "tender_id": str(tender.tender_id),
            "buyer": str(tender.buyer),
            "title": str(tender.title),
            "brief_url": str(tender.brief_url),
            "brief_sha256": str(tender.brief_sha256),
            "award_amount": int(tender.award_amount),
            "max_budget": int(tender.max_budget),
            "max_delivery_days": int(tender.max_delivery_days),
            "min_support_days": int(tender.min_support_days),
            "bidding_deadline": int(tender.bidding_deadline),
            "response_window_seconds": int(tender.response_window_seconds),
            "requirements": str(tender.requirements),
            "rubric": str(tender.rubric),
            "evidence_policy": str(tender.evidence_policy),
            "bids": bid_values,
        })

    def _challenge_digest(self, tender_id: str) -> str:
        rows = []
        for challenge_id in sorted(self.challenge_ids):
            challenge = self.challenges[challenge_id]
            if challenge.tender_id != tender_id:
                continue
            rows.append({
                "challenge_id": str(challenge.challenge_id),
                "challenger": str(challenge.challenger),
                "reason_code": str(challenge.reason_code),
                "target_bid_id": str(challenge.target_bid_id),
                "referenced_evidence_id": str(challenge.referenced_evidence_id),
                "challenge_url": str(challenge.challenge_url),
                "challenge_sha256": str(challenge.challenge_sha256),
                "submitted_at": int(challenge.submitted_at),
                "status": str(challenge.status),
                "claims": str(challenge.claims),
            })
        return _sha256(_canonical({"schema_version": "tendercouncil.challenges.v1", "items": rows}))

    def _validate_result(self, tender: CoreTender, result: dict, result_type: str):
        required = (
            "confidence", "disqualified_bid_ids", "runner_up_bid_id",
            "runner_up_score", "scores", "valid_bid_ids", "winner_bid_id",
            "winner_total_score", "status",
        )
        if not isinstance(result, dict) or tuple(sorted(result)) != tuple(sorted(required)):
            raise gl.vm.UserError("malformed evaluator result")
        if result["status"] != result_type:
            raise gl.vm.UserError("result type mismatch")
        valid = result["valid_bid_ids"]
        disqualified = result["disqualified_bid_ids"]
        if not isinstance(valid, list) or not isinstance(disqualified, list):
            raise gl.vm.UserError("result bid sets are malformed")
        all_ids = set()
        for bid_id in self.bid_ids:
            if self.bids[bid_id].tender_id == tender.tender_id:
                all_ids.add(bid_id)
        if set(valid) | set(disqualified) != all_ids or set(valid) & set(disqualified):
            raise gl.vm.UserError("result bid partition is invalid")
        if result_type == "NO_VALID_BID":
            if result["winner_bid_id"] != "" or valid or result["scores"]:
                raise gl.vm.UserError("NO_VALID_BID result contains a winner")
            return
        if result["winner_bid_id"] not in valid or result["winner_bid_id"] in disqualified:
            raise gl.vm.UserError("result winner is not a valid bid")
        scores = result["scores"]
        if not isinstance(scores, list) or len(scores) != len(valid):
            raise gl.vm.UserError("result scores do not cover valid bids")
        score_map = {}
        weights = _parse_rubric(tender.rubric)
        for score in scores:
            keys = ("bid_id", "capability", "delivery", "price", "support", "technical", "total")
            if not isinstance(score, dict) or tuple(sorted(score)) != keys:
                raise gl.vm.UserError("malformed score")
            if score["bid_id"] not in valid or score["bid_id"] in score_map:
                raise gl.vm.UserError("score bid is invalid")
            for name, limit in zip(("technical", "delivery", "price", "capability", "support"), weights):
                value = score[name]
                if not isinstance(value, int) or value < 0 or value > limit:
                    raise gl.vm.UserError("score exceeds rubric bound")
            total = sum(score[name] for name in ("technical", "delivery", "price", "capability", "support"))
            if score["total"] != total:
                raise gl.vm.UserError("score arithmetic mismatch")
            score_map[score["bid_id"]] = score
        if set(score_map) != set(valid):
            raise gl.vm.UserError("score coverage mismatch")
        ordered = sorted(score_map.values(), key=lambda row: (-row["total"], row["bid_id"]))
        if ordered[0]["bid_id"] != result["winner_bid_id"] or ordered[0]["total"] != result["winner_total_score"]:
            raise gl.vm.UserError("winner score mismatch")
        if len(ordered) > 1:
            if ordered[0]["total"] <= ordered[1]["total"]:
                raise gl.vm.UserError("unresolved score tie")
            if result["runner_up_bid_id"] != ordered[1]["bid_id"] or result["runner_up_score"] != ordered[1]["total"]:
                raise gl.vm.UserError("runner-up mismatch")
        elif result["runner_up_bid_id"] != "" or result["runner_up_score"] != 0:
            raise gl.vm.UserError("single bid runner-up must be empty")

    @gl.public.view
    def get_production_ready(self) -> bool:
        return self.evaluator_bound

    @gl.public.view
    def get_evaluator_binding(self) -> str:
        return _canonical({
            "bound": self.evaluator_bound,
            "address": str(self.evaluator_address),
            "version": self.evaluator_version,
            "source_hash": self.evaluator_source_hash,
        })

    @gl.public.view
    def get_contract_balance(self) -> u256:
        return self.balance

    @gl.public.view
    def get_tender(self, tender_id: str) -> CoreTender:
        return self._tender(tender_id)

    @gl.public.view
    def get_bid(self, bid_id: str) -> CoreBid:
        bid = self.bids.get(bid_id)
        if bid is None:
            raise gl.vm.UserError("bid does not exist")
        return bid

    @gl.public.view
    def get_challenge(self, challenge_id: str) -> CoreChallenge:
        challenge = self.challenges.get(challenge_id)
        if challenge is None:
            raise gl.vm.UserError("challenge does not exist")
        return challenge

    @gl.public.view
    def list_tender_ids(self) -> DynArray[str]:
        return self.tender_ids

    @gl.public.view
    def get_evaluation_context(self, tender_id: str) -> str:
        tender = self._tender(tender_id)
        return _canonical({
            "core_schema_version": CORE_SCHEMA_VERSION,
            "tender_id": tender_id,
            "status": tender.status,
            "evaluation_nonce": int(tender.evaluation_nonce),
            "snapshot_digest": tender.closed_snapshot_digest,
        })

    @gl.public.view
    def get_closed_snapshot(self, tender_id: str) -> str:
        tender = self._tender(tender_id)
        if tender.status not in (STATUS_CLOSED, STATUS_EVALUATING, STATUS_PROVISIONAL_AWARD, STATUS_RESPONSE_WINDOW, STATUS_REVIEWING_CHALLENGES, STATUS_AWARDED, STATUS_SETTLEMENT_PENDING, STATUS_SETTLED, STATUS_NO_VALID_BID):
            raise gl.vm.UserError("closed snapshot is unavailable")
        return self._snapshot(tender_id)

    @gl.public.view
    def get_review_context(self, tender_id: str, review_nonce: u64) -> str:
        tender = self._tender(tender_id)
        if tender.review_nonce != review_nonce or tender.status != STATUS_REVIEWING_CHALLENGES:
            raise gl.vm.UserError("review context is stale")
        rows = []
        for challenge_id in sorted(self.challenge_ids):
            challenge = self.challenges[challenge_id]
            if challenge.tender_id == tender_id and challenge.status == CHALLENGE_VALID:
                rows.append({
                    "challenge_id": challenge.challenge_id,
                    "tender_id": challenge.tender_id,
                    "challenger": str(challenge.challenger),
                    "reason_code": challenge.reason_code,
                    "target_bid_id": challenge.target_bid_id,
                    "referenced_evidence_id": challenge.referenced_evidence_id,
                    "challenge_url": challenge.challenge_url,
                    "challenge_sha256": challenge.challenge_sha256,
                    "claims": challenge.claims,
                })
        return _canonical({
            "tender_id": tender_id,
            "evaluation_nonce": int(tender.evaluation_nonce),
            "review_nonce": int(review_nonce),
            "snapshot_digest": tender.closed_snapshot_digest,
            "original_result_digest": tender.evaluation_result_digest,
            "challenge_set_digest": tender.challenge_set_digest,
            "challenges": rows,
        })

    @gl.public.write
    def bind_evaluator(self, evaluator_address: Address, evaluator_version: str, evaluator_source_hash: str):
        if self.evaluator_bound:
            raise gl.vm.UserError("evaluator is already permanently bound")
        if gl.message.sender_address != self.bootstrapper:
            raise gl.vm.UserError("only the deployment bootstrapper may bind evaluator")
        if evaluator_address == ZERO_ADDRESS:
            raise gl.vm.UserError("evaluator address is zero")
        self._require_length(evaluator_version, 96, "evaluator_version")
        if not _is_hash(evaluator_source_hash):
            raise gl.vm.UserError("invalid evaluator source hash")
        self.evaluator_address = evaluator_address
        self.evaluator_version = evaluator_version
        self.evaluator_source_hash = evaluator_source_hash
        self.evaluator_bound = True

    @gl.public.write.payable
    def create_tender(
        self, tender_id: str, title: str, brief_url: str, brief_sha256: str,
        max_budget: u256, award_amount: u256, max_delivery_days: u64,
        min_support_days: u64, bidding_deadline: u64, response_window_seconds: u64,
        requirements: str, technical_weight: u8, delivery_weight: u8,
        price_weight: u8, capability_weight: u8, support_weight: u8,
        evidence_policy: str,
    ):
        self._require_length(tender_id, MAX_ID, "tender_id")
        self._require_length(title, MAX_TITLE, "title")
        self._require_url(brief_url, "brief_url")
        if not _is_hash(brief_sha256):
            raise gl.vm.UserError("invalid brief hash")
        self._require_length(requirements, MAX_TEXT, "requirements")
        self._require_length(evidence_policy, MAX_TEXT, "evidence policy")
        if tender_id in self.tenders:
            raise gl.vm.UserError("tender already exists")
        if max_budget == u256(0) or award_amount == u256(0) or award_amount > max_budget:
            raise gl.vm.UserError("invalid budget or award")
        if max_delivery_days == u64(0) or min_support_days == u64(0):
            raise gl.vm.UserError("invalid delivery or support constraint")
        if bidding_deadline <= self._now():
            raise gl.vm.UserError("bidding deadline must be in the future")
        if response_window_seconds < MIN_RESPONSE_WINDOW_SECONDS:
            raise gl.vm.UserError("response window below protocol minimum")
        rubric = (
            "technical=" + str(technical_weight) + ";delivery=" + str(delivery_weight)
            + ";price=" + str(price_weight) + ";capability=" + str(capability_weight)
            + ";support=" + str(support_weight)
        )
        try:
            _parse_rubric(rubric)
        except Exception:
            raise gl.vm.UserError("rubric must total exactly 100")
        if gl.message.value != award_amount:
            raise gl.vm.UserError("exact award funding is required")
        self.tenders[tender_id] = CoreTender(
            tender_id, gl.message.sender_address, title, brief_url, brief_sha256,
            max_budget, award_amount, max_delivery_days, min_support_days,
            bidding_deadline, response_window_seconds, STATUS_DRAFT, requirements,
            rubric, evidence_policy, gl.message.value, "", u64(0), "", "", "",
            u64(0), u64(0), u64(0), "", SETTLEMENT_ESCROWED, u256(0),
        )
        self.tender_ids.append(tender_id)
        self.total_locked_escrow = self.total_locked_escrow + gl.message.value

    @gl.public.write
    def open_tender(self, tender_id: str):
        self._require_ready()
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_DRAFT:
            raise gl.vm.UserError("only draft tenders may open")
        if self.balance < self.total_locked_escrow or self._now() >= tender.bidding_deadline:
            raise gl.vm.UserError("escrow or deadline is invalid")
        tender.status = STATUS_OPEN
        self.tenders[tender_id] = tender

    @gl.public.write
    def submit_bid(
        self, bid_id: str, tender_id: str, price: u256, delivery_days: u64,
        support_days: u64, proposal_url: str, proposal_sha256: str,
        evidence_commitments: str, schema_version: str = "tendercouncil.bid.v1",
    ):
        self._require_ready()
        self._require_length(bid_id, MAX_ID, "bid_id")
        self._require_url(proposal_url, "proposal_url")
        if not _is_hash(proposal_sha256) or not _valid_commitments(evidence_commitments):
            raise gl.vm.UserError("invalid proposal or evidence commitment")
        if schema_version != "tendercouncil.bid.v1":
            raise gl.vm.UserError("unsupported bid schema")
        if bid_id in self.bids:
            raise gl.vm.UserError("bid already exists")
        tender = self._tender(tender_id)
        if tender.status != STATUS_OPEN or self._now() > tender.bidding_deadline:
            raise gl.vm.UserError("bidding is closed")
        if price == u256(0):
            raise gl.vm.UserError("price must be positive")
        for known_id in self.bid_ids:
            known = self.bids[known_id]
            if known.tender_id == tender_id and known.bidder == gl.message.sender_address:
                raise gl.vm.UserError("one immutable bid per wallet is required")
        self.bids[bid_id] = CoreBid(
            bid_id, tender_id, gl.message.sender_address, price, delivery_days,
            support_days, proposal_url, proposal_sha256, evidence_commitments,
            schema_version, self._now(),
        )
        self.bid_ids.append(bid_id)

    @gl.public.write
    def close_tender(self, tender_id: str):
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_OPEN or self._now() < tender.bidding_deadline:
            raise gl.vm.UserError("tender cannot close yet")
        snapshot = self._snapshot(tender_id)
        tender.closed_snapshot_digest = _sha256(snapshot)
        tender.status = STATUS_CLOSED
        self.tenders[tender_id] = tender

    @gl.public.write
    def start_evaluation(self, tender_id: str):
        self._require_ready()
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_CLOSED:
            raise gl.vm.UserError("only closed tenders may be evaluated")
        tender.evaluation_nonce = tender.evaluation_nonce + u64(1)
        tender.status = STATUS_EVALUATING
        self.tenders[tender_id] = tender
        EvaluatorInterface(self.evaluator_address).emit(on="finalized").start_evaluation_job(
            tender_id, tender.evaluation_nonce, tender.closed_snapshot_digest,
        )

    @gl.public.write
    def receive_evaluation_result(
        self, tender_id: str, nonce: u64, snapshot_digest: str,
        evaluator_schema_version: str, result_type: str, winner_bid_id: str,
        result_digest: str,
    ):
        if gl.message.sender_address != self.evaluator_address:
            raise gl.vm.UserError("caller is not the bound evaluator")
        tender = self._tender(tender_id)
        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:
            raise gl.vm.UserError("evaluation callback is stale or out of state")
        if snapshot_digest != tender.closed_snapshot_digest:
            raise gl.vm.UserError("evaluation snapshot mismatch")
        if evaluator_schema_version != EVALUATOR_SCHEMA_VERSION:
            raise gl.vm.UserError("evaluator schema mismatch")
        if result_type not in ("COMPARATIVE", "NO_VALID_BID"):
            raise gl.vm.UserError("unknown result type")
        payload = EvaluatorInterface(self.evaluator_address).view().get_evaluation_result(tender_id, nonce)
        if _sha256(payload) != result_digest:
            raise gl.vm.UserError("evaluation result digest mismatch")
        result = json.loads(payload)
        if result.get("winner_bid_id", "") != winner_bid_id:
            raise gl.vm.UserError("callback winner mismatch")
        self._validate_result(tender, result, result_type)
        tender.evaluation_result_digest = result_digest
        if result_type == "NO_VALID_BID":
            tender.status = STATUS_NO_VALID_BID
            tender.settlement_state = SETTLEMENT_UNSETTLED
        else:
            tender.provisional_winner = winner_bid_id
            tender.response_window_start = u64(0)
            tender.response_window_end = u64(0)
            tender.status = STATUS_PROVISIONAL_AWARD
        self.tenders[tender_id] = tender

    @gl.public.write
    def start_response_window(self, tender_id: str):
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_PROVISIONAL_AWARD:
            raise gl.vm.UserError("no provisional award exists")
        tender.response_window_start = self._now()
        tender.response_window_end = tender.response_window_start + tender.response_window_seconds
        tender.status = STATUS_RESPONSE_WINDOW
        self.tenders[tender_id] = tender

    @gl.public.write
    def submit_challenge(
        self, challenge_id: str, tender_id: str, reason_code: str,
        target_bid_id: str, referenced_evidence_id: str,
        challenge_url: str, challenge_sha256: str,
    ):
        self._require_length(challenge_id, MAX_ID, "challenge_id")
        tender = self._tender(tender_id)
        if tender.status != STATUS_RESPONSE_WINDOW or self._now() > tender.response_window_end:
            raise gl.vm.UserError("response window is closed")
        if reason_code not in ALLOWED_CHALLENGES or challenge_id in self.challenges:
            raise gl.vm.UserError("invalid or duplicate challenge")
        target = self.bids.get(target_bid_id)
        if target is None or target.tender_id != tender_id:
            raise gl.vm.UserError("invalid challenge target")
        bidder = False
        for bid_id in self.bid_ids:
            bid = self.bids[bid_id]
            if bid.tender_id == tender_id and bid.bidder == gl.message.sender_address:
                bidder = True
        if not bidder:
            raise gl.vm.UserError("only a tender bidder may challenge")
        if reason_code in (CHALLENGE_EVIDENCE_OVERLOOKED, CHALLENGE_INTEGRITY):
            if referenced_evidence_id == "" or referenced_evidence_id + "|" not in target.evidence_commitments:
                raise gl.vm.UserError("challenge evidence was not committed before close")
        elif referenced_evidence_id != "":
            raise gl.vm.UserError("evidence reference is not allowed for this reason")
        if (challenge_url == "") != (challenge_sha256 == ""):
            raise gl.vm.UserError("challenge URL and hash must be paired")
        if challenge_url != "":
            self._require_url(challenge_url, "challenge_url")
            if not _is_hash(challenge_sha256):
                raise gl.vm.UserError("invalid challenge hash")
        for old_id in self.challenge_ids:
            old = self.challenges[old_id]
            if old.tender_id == tender_id and old.challenger == gl.message.sender_address:
                raise gl.vm.UserError("one challenge per bidder is required")
        count = sum(1 for old_id in self.challenge_ids if self.challenges[old_id].tender_id == tender_id)
        if count >= MAX_CHALLENGES:
            raise gl.vm.UserError("challenge limit exceeded")
        self.challenges[challenge_id] = CoreChallenge(
            challenge_id, tender_id, gl.message.sender_address, reason_code,
            target_bid_id, referenced_evidence_id, challenge_url, challenge_sha256,
            self._now(), CHALLENGE_PENDING if challenge_url else CHALLENGE_VALID, "",
        )
        self.challenge_ids.append(challenge_id)

    @gl.public.write
    def resolve_challenge(self, challenge_id: str, valid: bool, claims: str = ""):
        challenge = self.challenges.get(challenge_id)
        if challenge is None:
            raise gl.vm.UserError("challenge does not exist")
        tender = self._tender(challenge.tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_RESPONSE_WINDOW or challenge.status != CHALLENGE_PENDING:
            raise gl.vm.UserError("challenge cannot be resolved")
        if len(claims) > MAX_TEXT:
            raise gl.vm.UserError("challenge claims exceed bound")
        challenge.status = CHALLENGE_VALID if valid else CHALLENGE_INVALID
        challenge.claims = claims if valid else ""
        self.challenges[challenge_id] = challenge

    @gl.public.write
    def advance_after_response(self, tender_id: str):
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_RESPONSE_WINDOW or self._now() <= tender.response_window_end:
            raise gl.vm.UserError("response window is still open")
        valid = 0
        for challenge_id in self.challenge_ids:
            challenge = self.challenges[challenge_id]
            if challenge.tender_id != tender_id:
                continue
            if challenge.status == CHALLENGE_PENDING:
                raise gl.vm.UserError("pending challenge remains")
            if challenge.status == CHALLENGE_VALID:
                valid += 1
        if valid == 0:
            tender.final_winner = tender.provisional_winner
            tender.status = STATUS_AWARDED
            tender.settlement_state = SETTLEMENT_UNSETTLED
        else:
            tender.review_nonce = tender.review_nonce + u64(1)
            tender.challenge_set_digest = self._challenge_digest(tender_id)
            tender.status = STATUS_REVIEWING_CHALLENGES
            self.tenders[tender_id] = tender
            EvaluatorInterface(self.evaluator_address).emit(on="finalized").start_review_job(
                tender_id, tender.evaluation_nonce, tender.review_nonce,
                tender.closed_snapshot_digest, tender.evaluation_result_digest,
                tender.challenge_set_digest,
            )
            return
        self.tenders[tender_id] = tender

    @gl.public.write
    def receive_review_result(
        self, tender_id: str, evaluation_nonce: u64, review_nonce: u64,
        snapshot_digest: str, original_result_digest: str,
        challenge_set_digest: str, decision: str, winner_bid_id: str,
        result_digest: str,
    ):
        if gl.message.sender_address != self.evaluator_address:
            raise gl.vm.UserError("caller is not the bound evaluator")
        tender = self._tender(tender_id)
        if tender.status != STATUS_REVIEWING_CHALLENGES or tender.evaluation_nonce != evaluation_nonce or tender.review_nonce != review_nonce:
            raise gl.vm.UserError("review callback is stale")
        if (snapshot_digest != tender.closed_snapshot_digest
                or original_result_digest != tender.evaluation_result_digest
                or challenge_set_digest != tender.challenge_set_digest):
            raise gl.vm.UserError("review correlation digest mismatch")
        payload = EvaluatorInterface(self.evaluator_address).view().get_review_result(tender_id, review_nonce)
        if _sha256(payload) != result_digest:
            raise gl.vm.UserError("review result digest mismatch")
        result = json.loads(payload)
        if result.get("decision") != decision or result.get("winner_bid_id") != winner_bid_id:
            raise gl.vm.UserError("review callback payload mismatch")
        if decision == "NO_VALID_BID":
            tender.status = STATUS_NO_VALID_BID
            tender.final_winner = ""
        elif decision in ("UPHOLD", "REPLACE_WINNER"):
            if winner_bid_id == "" or winner_bid_id not in [bid_id for bid_id in self.bid_ids if self.bids[bid_id].tender_id == tender_id]:
                raise gl.vm.UserError("review winner is not a tender bid")
            tender.final_winner = winner_bid_id
            tender.status = STATUS_AWARDED
            tender.settlement_state = SETTLEMENT_UNSETTLED
        else:
            raise gl.vm.UserError("invalid review decision")
        self.tenders[tender_id] = tender

    @gl.public.write
    def settle_award(self, tender_id: str):
        tender = self._tender(tender_id)
        if tender.status != STATUS_AWARDED or tender.settlement_state != SETTLEMENT_UNSETTLED:
            raise gl.vm.UserError("only an unsettled awarded tender may settle")
        winner = self.bids.get(tender.final_winner)
        if winner is None or winner.tender_id != tender_id:
            raise gl.vm.UserError("final winner is invalid")
        if self.balance < tender.award_amount:
            raise gl.vm.UserError("escrow balance is insufficient")
        before = self.balance
        Recipient(winner.bidder).emit_transfer(value=tender.award_amount, on="finalized")
        tender.balance_before = before
        tender.settlement_state = SETTLEMENT_TRANSFER_PENDING
        tender.status = STATUS_SETTLEMENT_PENDING
        self.tenders[tender_id] = tender

    @gl.public.write
    def confirm_settlement(self, tender_id: str):
        tender = self._tender(tender_id)
        if tender.status != STATUS_SETTLEMENT_PENDING or tender.settlement_state != SETTLEMENT_TRANSFER_PENDING:
            raise gl.vm.UserError("settlement is not pending")
        if self.balance != tender.balance_before - tender.award_amount:
            raise gl.vm.UserError("finalized transfer was not verified")
        self.total_locked_escrow = self.total_locked_escrow - tender.award_amount
        tender.settlement_state = SETTLEMENT_SETTLED
        tender.status = STATUS_SETTLED
        self.tenders[tender_id] = tender

    @gl.public.write
    def cancel_tender(self, tender_id: str):
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_DRAFT:
            raise gl.vm.UserError("only an unopened tender may be cancelled")
        before = self.balance
        Recipient(tender.buyer).emit_transfer(value=tender.award_amount, on="finalized")
        tender.balance_before = before
        tender.status = STATUS_REFUND_PENDING
        tender.settlement_state = SETTLEMENT_REFUND_PENDING
        self.tenders[tender_id] = tender

    @gl.public.write
    def confirm_refund(self, tender_id: str):
        tender = self._tender(tender_id)
        if tender.status != STATUS_REFUND_PENDING or tender.settlement_state != SETTLEMENT_REFUND_PENDING:
            raise gl.vm.UserError("refund is not pending")
        if self.balance != tender.balance_before - tender.award_amount:
            raise gl.vm.UserError("refund transfer was not verified")
        self.total_locked_escrow = self.total_locked_escrow - tender.award_amount
        tender.status = STATUS_CANCELLED
        tender.settlement_state = SETTLEMENT_SETTLED
        self.tenders[tender_id] = tender

    @gl.public.write
    def refund_no_valid_bid(self, tender_id: str):
        tender = self._tender(tender_id)
        self._require_buyer(tender)
        if tender.status != STATUS_NO_VALID_BID or tender.settlement_state != SETTLEMENT_UNSETTLED:
            raise gl.vm.UserError("tender is not refundable")
        before = self.balance
        Recipient(tender.buyer).emit_transfer(value=tender.award_amount, on="finalized")
        tender.balance_before = before
        tender.status = STATUS_REFUND_PENDING
        tender.settlement_state = SETTLEMENT_REFUND_PENDING
        self.tenders[tender_id] = tender

    @gl.public.write
    def confirm_no_valid_refund(self, tender_id: str):
        self.confirm_refund(tender_id)
