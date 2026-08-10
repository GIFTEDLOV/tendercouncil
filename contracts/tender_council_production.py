# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""TenderCouncil production foundation: public buyers and funded tenders.

This module intentionally stops before semantic evaluation and settlement. It
establishes the immutable commercial record and escrow invariants that later
phases consume.
"""

from dataclasses import dataclass
import datetime

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

MIN_RESPONSE_WINDOW_SECONDS = 600
MAX_ID_LENGTH = 96
MAX_TITLE_LENGTH = 200
MAX_URL_LENGTH = 512
MAX_REQUIREMENTS_LENGTH = 4000
MAX_POLICY_LENGTH = 4000
SHA256_HEX = "0123456789abcdef"


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

    def _is_sha256_commitment(self, value: str) -> bool:
        if len(value) != 71 or value[:7] != "sha256:":
            return False
        for char in value[7:]:
            if char not in SHA256_HEX:
                return False
        return True

    def _require_sha256(self, value: str, field: str):
        if not self._is_sha256_commitment(value):
            raise gl.vm.UserError(field + " must be sha256:<64 lowercase hex chars>")

    def _require_https_url(self, value: str, field: str):
        self._require_length(value, field, MAX_URL_LENGTH)
        if value[:8] != "https://":
            raise gl.vm.UserError(field + " must use https")

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
        )
        self.bid_ids.append(bid_id)

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
