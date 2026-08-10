# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""TenderCouncil production foundation: public buyers and funded tenders.

This module intentionally stops before semantic evaluation and settlement. It
establishes the immutable commercial record and escrow invariants that later
phases consume.
"""

from dataclasses import dataclass
import datetime
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
STATUS_SETTLED = "SETTLED"
STATUS_NO_VALID_BID = "NO_VALID_BID"
STATUS_CANCELLED = "CANCELLED"

SETTLEMENT_ESCROWED = "ESCROWED"
SETTLEMENT_UNSETTLED = "UNSETTLED"
SETTLEMENT_SETTLED = "SETTLED"

MANIFEST_PENDING = "MANIFEST_PENDING"
MANIFEST_VALID = "MANIFEST_VALID"
MANIFEST_INVALID = "MANIFEST_INVALID"
MANIFEST_HASH_MISMATCH = "HASH_MISMATCH"
MANIFEST_UNAVAILABLE = "UNAVAILABLE"
MANIFEST_SCHEMA_INVALID = "SCHEMA_INVALID"

MIN_RESPONSE_WINDOW_SECONDS = 600
MAX_ID_LENGTH = 96
MAX_TITLE_LENGTH = 200
MAX_URL_LENGTH = 512
MAX_REQUIREMENTS_LENGTH = 4000
MAX_POLICY_LENGTH = 4000
MAX_MANIFEST_BYTES = 32768
MAX_PROPOSAL_FIELD_LENGTH = 6000
MAX_REQUIREMENT_ITEMS = 16
MAX_REQUIREMENT_ITEM_LENGTH = 240
MAX_EVIDENCE_ITEMS = 8
MAX_EVIDENCE_ID_LENGTH = 96
MAX_EVIDENCE_KIND_LENGTH = 32
MAX_CRITERION_LENGTH = 32
SHA256_HEX = "0123456789abcdef"
MANIFEST_TOP_LEVEL_KEYS = (
    "bidder", "delivery_days", "evidence", "price", "proposal",
    "schema_version", "support_days", "tender_id",
)
MANIFEST_PROPOSAL_KEYS = (
    "delivery_plan", "requirements", "support_plan", "technical_approach",
)
MANIFEST_EVIDENCE_KEYS = (
    "criterion", "evidence_id", "kind", "required", "sha256", "url",
)
ALLOWED_EVIDENCE_KINDS = ("CAPABILITY", "DELIVERY", "SUPPORT", "TECHNICAL")
ALLOWED_CRITERIA = ("capability", "delivery", "support", "technical")


def _rotate_right(value: int, amount: int) -> int:
    return ((value >> amount) | (value << (32 - amount))) & 0xFFFFFFFF


def _sha256_hex(data: bytes) -> str:
    """Pure-Python SHA-256 used for exact fetched-byte commitments."""
    constants = (
        0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
        0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
        0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
        0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
        0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
        0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
        0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
        0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
        0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
        0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
        0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
        0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
        0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
        0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
        0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
        0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
    )
    state = [
        0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
        0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
    ]
    padded = data + b"\x80"
    while len(padded) % 64 != 56:
        padded += b"\x00"
    padded += (len(data) * 8).to_bytes(8, "big")
    for offset in range(0, len(padded), 64):
        words = [0] * 64
        for index in range(16):
            start = offset + index * 4
            words[index] = int.from_bytes(padded[start:start + 4], "big")
        for index in range(16, 64):
            s0 = (_rotate_right(words[index - 15], 7)
                  ^ _rotate_right(words[index - 15], 18)
                  ^ (words[index - 15] >> 3))
            s1 = (_rotate_right(words[index - 2], 17)
                  ^ _rotate_right(words[index - 2], 19)
                  ^ (words[index - 2] >> 10))
            words[index] = (words[index - 16] + s0 + words[index - 7] + s1) & 0xFFFFFFFF
        a, b, c, d, e, f, g, h = state
        for index in range(64):
            s1 = _rotate_right(e, 6) ^ _rotate_right(e, 11) ^ _rotate_right(e, 25)
            choice = (e & f) ^ ((~e) & g)
            temp1 = (h + s1 + choice + constants[index] + words[index]) & 0xFFFFFFFF
            s0 = _rotate_right(a, 2) ^ _rotate_right(a, 13) ^ _rotate_right(a, 22)
            majority = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (s0 + majority) & 0xFFFFFFFF
            h, g, f, e, d, c, b, a = (
                g, f, e, (d + temp1) & 0xFFFFFFFF,
                c, b, a, (temp1 + temp2) & 0xFFFFFFFF,
            )
        state = [
            (state[0] + a) & 0xFFFFFFFF, (state[1] + b) & 0xFFFFFFFF,
            (state[2] + c) & 0xFFFFFFFF, (state[3] + d) & 0xFFFFFFFF,
            (state[4] + e) & 0xFFFFFFFF, (state[5] + f) & 0xFFFFFFFF,
            (state[6] + g) & 0xFFFFFFFF, (state[7] + h) & 0xFFFFFFFF,
        ]
    return "".join(format(value, "08x") for value in state)


def _manifest_failure(status: str):
    return {"status": status, "evidence_count": 0}


def _validate_manifest_bytes(
    raw_body: bytes,
    committed_hash: str,
    expected_tender_id: str,
    expected_bidder: str,
    expected_price: int,
    expected_delivery_days: int,
    expected_support_days: int,
):
    """Validate only the bounded manifest schema, after exact-byte hashing."""
    if not isinstance(raw_body, bytes):
        raw_body = str(raw_body).encode("utf-8")
    if len(raw_body) > MAX_MANIFEST_BYTES:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if "sha256:" + _sha256_hex(raw_body) != committed_hash:
        return _manifest_failure(MANIFEST_HASH_MISMATCH)
    try:
        body = raw_body.decode("utf-8")
        manifest = json.loads(body)
    except Exception:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if not isinstance(manifest, dict):
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if tuple(sorted(manifest.keys())) != MANIFEST_TOP_LEVEL_KEYS:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if manifest["schema_version"] != "tendercouncil.bid.v1":
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if manifest["tender_id"] != expected_tender_id:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if (not isinstance(manifest["bidder"], str)
            or manifest["bidder"].lower() != expected_bidder.lower()):
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if not isinstance(manifest["price"], int) or isinstance(manifest["price"], bool):
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if not isinstance(manifest["delivery_days"], int) or isinstance(manifest["delivery_days"], bool):
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if not isinstance(manifest["support_days"], int) or isinstance(manifest["support_days"], bool):
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if manifest["price"] != expected_price:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if manifest["delivery_days"] != expected_delivery_days:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if manifest["support_days"] != expected_support_days:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)

    proposal = manifest["proposal"]
    if not isinstance(proposal, dict):
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    if tuple(sorted(proposal.keys())) != MANIFEST_PROPOSAL_KEYS:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    for field in ("technical_approach", "delivery_plan", "support_plan"):
        value = proposal[field]
        if not isinstance(value, str) or value == "" or len(value) > MAX_PROPOSAL_FIELD_LENGTH:
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    requirements = proposal["requirements"]
    if not isinstance(requirements, list) or len(requirements) > MAX_REQUIREMENT_ITEMS:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    for requirement in requirements:
        if (not isinstance(requirement, str) or requirement == ""
                or len(requirement) > MAX_REQUIREMENT_ITEM_LENGTH):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)

    evidence = manifest["evidence"]
    if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE_ITEMS:
        return _manifest_failure(MANIFEST_SCHEMA_INVALID)
    evidence_ids = []
    evidence_commitments = []
    for item in evidence:
        if not isinstance(item, dict):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if tuple(sorted(item.keys())) != MANIFEST_EVIDENCE_KEYS:
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        evidence_id = item["evidence_id"]
        kind = item["kind"]
        criterion = item["criterion"]
        required = item["required"]
        url = item["url"]
        item_hash = item["sha256"]
        if (not isinstance(evidence_id, str) or evidence_id == ""
                or len(evidence_id) > MAX_EVIDENCE_ID_LENGTH):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if (not isinstance(kind, str) or len(kind) > MAX_EVIDENCE_KIND_LENGTH
                or kind not in ALLOWED_EVIDENCE_KINDS):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if (not isinstance(criterion, str) or len(criterion) > MAX_CRITERION_LENGTH
                or criterion not in ALLOWED_CRITERIA):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if not isinstance(required, bool):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if not isinstance(url, str) or len(url) > MAX_URL_LENGTH or url[:8] != "https://":
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if (not isinstance(item_hash, str) or len(item_hash) != 71
                or item_hash[:7] != "sha256:"):
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        for char in item_hash[7:]:
            if char not in SHA256_HEX:
                return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        if evidence_id in evidence_ids:
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        commitment = url + "|" + item_hash
        if commitment in evidence_commitments:
            return _manifest_failure(MANIFEST_SCHEMA_INVALID)
        evidence_ids.append(evidence_id)
        evidence_commitments.append(commitment)
    return {"status": MANIFEST_VALID, "evidence_count": len(evidence)}


@allow_storage
@dataclass
class ProductionTenderRecord:
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
    mandatory_requirements: str
    rubric: str
    evidence_policy: str
    escrow_amount: u256
    provisional_winner: str
    final_winner: str
    response_deadline: u64
    settlement_state: str


@allow_storage
@dataclass
class ProductionBidRecord:
    bid_id: str
    tender_id: str
    bidder: Address
    price: u256
    delivery_days: u64
    support_days: u64
    proposal_url: str
    proposal_sha256: str
    submitted_at: u64
    state: str
    manifest_status: str
    manifest_evidence_count: u8


class TenderCouncilProduction(gl.Contract):
    """Public multi-tender procurement record with real award custody."""

    tenders: TreeMap[str, ProductionTenderRecord]
    bids: TreeMap[str, ProductionBidRecord]
    tender_ids: DynArray[str]
    bid_ids: DynArray[str]
    total_locked_escrow: u256

    def __init__(self):
        self.total_locked_escrow = u256(0)

    def _require_length(self, value: str, field: str, maximum: int):
        if value == "":
            raise gl.vm.UserError(field + " must not be empty")
        if len(value) > maximum:
            raise gl.vm.UserError(field + " exceeds its bounded length")

    def _require_sha256(self, value: str, field: str):
        if not self._is_sha256_commitment(value):
            raise gl.vm.UserError(field + " must be sha256:<64 lowercase hex chars>")

    def _require_https_url(self, value: str, field: str):
        self._require_length(value, field, MAX_URL_LENGTH)
        if value[:8] != "https://":
            raise gl.vm.UserError(field + " must use https")

    def _is_sha256_commitment(self, value: str) -> bool:
        if len(value) != 71 or value[:7] != "sha256:":
            return False
        for char in value[7:]:
            if char not in SHA256_HEX:
                return False
        return True

    def _now_seconds(self) -> u64:
        return u64(int(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    def _require_buyer(self, tender: ProductionTenderRecord):
        if gl.message.sender_address != tender.buyer:
            raise gl.vm.UserError("Only the tender buyer may perform this action")

    def _empty_tender(self) -> ProductionTenderRecord:
        return ProductionTenderRecord(
            "",
            Address("0x" + "0" * 40),
            "",
            "",
            "",
            u256(0),
            u256(0),
            u64(0),
            u64(0),
            u64(0),
            u64(0),
            "",
            "",
            "",
            "",
            u256(0),
            "",
            "",
            u64(0),
            "",
        )

    def _empty_bid(self) -> ProductionBidRecord:
        return ProductionBidRecord(
            "",
            "",
            Address("0x" + "0" * 40),
            u256(0),
            u64(0),
            u64(0),
            "",
            "",
            u64(0),
            "",
            "",
            u8(0),
        )

    @gl.public.view
    def get_tender(self, tender_id: str) -> ProductionTenderRecord:
        return self.tenders.get(tender_id, self._empty_tender())

    @gl.public.view
    def get_bid(self, bid_id: str) -> ProductionBidRecord:
        return self.bids.get(bid_id, self._empty_bid())

    @gl.public.view
    def list_tender_ids(self) -> DynArray[str]:
        return self.tender_ids

    @gl.public.view
    def list_bid_ids(self) -> DynArray[str]:
        return self.bid_ids

    @gl.public.view
    def get_contract_balance(self) -> u256:
        return self.balance

    @gl.public.write.payable
    def create_tender(
        self,
        tender_id: str,
        title: str,
        brief_url: str,
        brief_sha256: str,
        max_budget: u256,
        award_amount: u256,
        max_delivery_days: u64,
        min_support_days: u64,
        bidding_deadline: u64,
        response_window_seconds: u64,
        mandatory_requirements: str,
        technical_weight: u8,
        delivery_weight: u8,
        price_weight: u8,
        capability_weight: u8,
        support_weight: u8,
        evidence_policy: str,
    ):
        self._require_length(tender_id, "tender_id", MAX_ID_LENGTH)
        self._require_length(title, "title", MAX_TITLE_LENGTH)
        self._require_https_url(brief_url, "brief_url")
        self._require_sha256(brief_sha256, "brief_sha256")
        self._require_length(mandatory_requirements, "mandatory_requirements", MAX_REQUIREMENTS_LENGTH)
        self._require_length(evidence_policy, "evidence_policy", MAX_POLICY_LENGTH)
        if tender_id in self.tenders:
            raise gl.vm.UserError("Tender already exists")
        if max_budget == u256(0) or award_amount == u256(0):
            raise gl.vm.UserError("budget and award must be greater than zero")
        if award_amount > max_budget:
            raise gl.vm.UserError("award_amount cannot exceed max_budget")
        if max_delivery_days == u64(0) or min_support_days == u64(0):
            raise gl.vm.UserError("delivery and support constraints must be positive")
        if bidding_deadline == u64(0):
            raise gl.vm.UserError("bidding_deadline must be greater than zero")
        if response_window_seconds < MIN_RESPONSE_WINDOW_SECONDS:
            raise gl.vm.UserError("response window is below the protocol minimum")
        weights_total = (
            technical_weight + delivery_weight + price_weight
            + capability_weight + support_weight
        )
        if weights_total != 100:
            raise gl.vm.UserError("rubric weights must total exactly 100")
        if gl.message.value != award_amount:
            raise gl.vm.UserError("exact award funding is required")

        rubric = (
            "technical=" + str(technical_weight)
            + ";delivery=" + str(delivery_weight)
            + ";price=" + str(price_weight)
            + ";capability=" + str(capability_weight)
            + ";support=" + str(support_weight)
        )
        self.tenders[tender_id] = ProductionTenderRecord(
            tender_id,
            gl.message.sender_address,
            title,
            brief_url,
            brief_sha256,
            max_budget,
            award_amount,
            max_delivery_days,
            min_support_days,
            bidding_deadline,
            response_window_seconds,
            STATUS_DRAFT,
            mandatory_requirements,
            rubric,
            evidence_policy,
            gl.message.value,
            "",
            "",
            u64(0),
            SETTLEMENT_ESCROWED,
        )
        self.tender_ids.append(tender_id)
        self.total_locked_escrow = self.total_locked_escrow + gl.message.value

    @gl.public.write
    def open_tender(self, tender_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_buyer(tender)
        if tender.status != STATUS_DRAFT:
            raise gl.vm.UserError("Only draft tenders may be opened")
        if self.balance < self.total_locked_escrow:
            raise gl.vm.UserError("contract balance does not cover locked escrow")
        if self._now_seconds() >= tender.bidding_deadline:
            raise gl.vm.UserError("bidding deadline has passed")
        tender.status = STATUS_OPEN
        self.tenders[tender_id] = tender

    @gl.public.write
    def submit_bid(
        self,
        bid_id: str,
        tender_id: str,
        price: u256,
        delivery_days: u64,
        support_days: u64,
        proposal_url: str,
        proposal_sha256: str,
    ):
        self._require_length(bid_id, "bid_id", MAX_ID_LENGTH)
        self._require_https_url(proposal_url, "proposal_url")
        self._require_sha256(proposal_sha256, "proposal_sha256")
        if bid_id in self.bids:
            raise gl.vm.UserError("Bid already exists")
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        if tender.status != STATUS_OPEN:
            raise gl.vm.UserError("Bids are accepted only while the tender is open")
        if self._now_seconds() > tender.bidding_deadline:
            raise gl.vm.UserError("bid is late")
        if price == u256(0):
            raise gl.vm.UserError("price must be greater than zero")
        for known_bid_id in self.bid_ids:
            known_bid = self.bids[known_bid_id]
            if known_bid.tender_id == tender_id and known_bid.bidder == gl.message.sender_address:
                raise gl.vm.UserError("one bid per wallet per tender is required")

        self.bids[bid_id] = ProductionBidRecord(
            bid_id,
            tender_id,
            gl.message.sender_address,
            price,
            delivery_days,
            support_days,
            proposal_url,
            proposal_sha256,
            self._now_seconds(),
            "SUBMITTED",
            MANIFEST_PENDING,
            u8(0),
        )
        self.bid_ids.append(bid_id)

    @gl.public.write
    def validate_bid_manifest(self, bid_id: str):
        """Fetch and validate one immutable bid.v1 manifest.

        The callback captures only primitive immutable values. It hashes the
        exact fetched bytes before decoding or interpreting JSON. A malformed,
        unavailable, or hash-mismatched manifest is recorded as invalid and
        cannot become semantic input later.
        """
        bid = self.bids.get(bid_id)
        if bid is None:
            raise gl.vm.UserError("Bid does not exist")
        tender = self.tenders.get(bid.tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_buyer(tender)
        if tender.status not in (STATUS_OPEN, STATUS_CLOSED):
            raise gl.vm.UserError("Manifest validation is unavailable in this state")
        if bid.manifest_status != MANIFEST_PENDING:
            raise gl.vm.UserError("Bid manifest has already been validated")

        proposal_url = str(bid.proposal_url)
        committed_hash = str(bid.proposal_sha256)
        expected_tender_id = str(bid.tender_id)
        expected_bidder = str(bid.bidder)
        expected_price = int(bid.price)
        expected_delivery_days = int(bid.delivery_days)
        expected_support_days = int(bid.support_days)

        def leader_fn():
            try:
                response = gl.nondet.web.get(proposal_url)
                raw_body = response.body
            except Exception:
                return _manifest_failure(MANIFEST_UNAVAILABLE)
            return _validate_manifest_bytes(
                raw_body,
                committed_hash,
                expected_tender_id,
                expected_bidder,
                expected_price,
                expected_delivery_days,
                expected_support_days,
            )

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_data = leader_fn()
                leader_data = leader_result.calldata
                return (
                    leader_data["status"] == validator_data["status"]
                    and leader_data["evidence_count"] == validator_data["evidence_count"]
                )
            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        bid.manifest_status = result["status"]
        bid.manifest_evidence_count = u8(result["evidence_count"])
        self.bids[bid_id] = bid

    @gl.public.write
    def close_tender(self, tender_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_buyer(tender)
        if tender.status != STATUS_OPEN:
            raise gl.vm.UserError("Only open tenders may be closed")
        if self._now_seconds() < tender.bidding_deadline:
            raise gl.vm.UserError("bidding deadline has not passed")
        tender.status = STATUS_CLOSED
        self.tenders[tender_id] = tender

    @gl.public.write
    def cancel_tender(self, tender_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_buyer(tender)
        raise gl.vm.UserError("funded cancellation is disabled until finalized refund is implemented")
