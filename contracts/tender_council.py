# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Deterministic procurement records for TenderCouncil Stage 1.

This contract deliberately stores only authenticated submissions and their
provenance anchors. The evaluator that interprets external evidence belongs
to a later stage and must use an explicit Equivalence Principle validator.
"""

from dataclasses import dataclass

from genlayer import *


STATUS_DRAFT = "DRAFT"
STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"
STATUS_AWARDED = "AWARDED"
STATUS_CANCELLED = "CANCELLED"

BID_SUBMITTED = "SUBMITTED"
BID_AWARDED = "AWARDED"
BID_REJECTED = "REJECTED"


@allow_storage
@dataclass
class TenderRecord:
    tender_id: str
    title: str
    specification: str
    issuer: Address
    deadline_at: u64
    status: str
    awarded_bid_id: str


@allow_storage
@dataclass
class BidRecord:
    bid_id: str
    tender_id: str
    supplier: Address
    amount: u256
    proposal: str
    evidence_root: str
    status: str


@allow_storage
@dataclass
class EvidenceRecord:
    evidence_id: str
    bid_id: str
    submitted_by: Address
    uri: str
    content_hash: str
    kind: str


class TenderCouncil(gl.Contract):
    """Stage 1 state machine for authenticated procurement submissions."""

    owner: Address
    tenders: TreeMap[str, TenderRecord]
    bids: TreeMap[str, BidRecord]
    evidence: TreeMap[str, EvidenceRecord]
    tender_ids: DynArray[str]
    bid_ids: DynArray[str]
    evidence_ids: DynArray[str]

    def __init__(self):
        self.owner = gl.message.sender_address

    def _require_owner(self):
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError("Only the contract owner may perform this action")

    def _require_tender_issuer(self, tender: TenderRecord):
        if gl.message.sender_address != tender.issuer:
            raise gl.vm.UserError("Only the tender issuer may perform this action")

    def _require_nonempty(self, value: str, field: str):
        if value == "":
            raise gl.vm.UserError(field + " must not be empty")

    @gl.public.view
    def get_owner(self) -> Address:
        return self.owner

    @gl.public.view
    def get_tender(self, tender_id: str) -> TenderRecord:
        return self.tenders.get(
            tender_id,
            TenderRecord("", "", "", Address("0x" + "0" * 40), u64(0), "", ""),
        )

    @gl.public.view
    def get_bid(self, bid_id: str) -> BidRecord:
        return self.bids.get(
            bid_id,
            BidRecord("", "", Address("0x" + "0" * 40), u256(0), "", "", ""),
        )

    @gl.public.view
    def get_evidence(self, evidence_id: str) -> EvidenceRecord:
        return self.evidence.get(
            evidence_id,
            EvidenceRecord("", "", Address("0x" + "0" * 40), "", "", ""),
        )

    @gl.public.view
    def list_tender_ids(self) -> DynArray[str]:
        return self.tender_ids

    @gl.public.view
    def list_bid_ids(self) -> DynArray[str]:
        return self.bid_ids

    @gl.public.view
    def list_evidence_ids(self) -> DynArray[str]:
        return self.evidence_ids

    @gl.public.write
    def create_tender(
        self,
        tender_id: str,
        title: str,
        specification: str,
        deadline_at: u64,
    ):
        self._require_owner()
        self._require_nonempty(tender_id, "tender_id")
        self._require_nonempty(title, "title")
        self._require_nonempty(specification, "specification")
        if deadline_at == 0:
            raise gl.vm.UserError("deadline_at must be greater than zero")
        if tender_id in self.tenders:
            raise gl.vm.UserError("Tender already exists")

        self.tenders[tender_id] = TenderRecord(
            tender_id=tender_id,
            title=title,
            specification=specification,
            issuer=gl.message.sender_address,
            deadline_at=deadline_at,
            status=STATUS_DRAFT,
            awarded_bid_id="",
        )
        self.tender_ids.append(tender_id)

    @gl.public.write
    def open_tender(self, tender_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_tender_issuer(tender)
        if tender.status != STATUS_DRAFT:
            raise gl.vm.UserError("Only draft tenders may be opened")
        tender.status = STATUS_OPEN
        self.tenders[tender_id] = tender

    @gl.public.write
    def submit_bid(
        self,
        bid_id: str,
        tender_id: str,
        amount: u256,
        proposal: str,
        evidence_root: str,
    ):
        self._require_nonempty(bid_id, "bid_id")
        self._require_nonempty(proposal, "proposal")
        self._require_nonempty(evidence_root, "evidence_root")
        if bid_id in self.bids:
            raise gl.vm.UserError("Bid already exists")
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        if tender.status != STATUS_OPEN:
            raise gl.vm.UserError("Bids are accepted only while the tender is open")
        if amount == 0:
            raise gl.vm.UserError("amount must be greater than zero")

        self.bids[bid_id] = BidRecord(
            bid_id=bid_id,
            tender_id=tender_id,
            supplier=gl.message.sender_address,
            amount=amount,
            proposal=proposal,
            evidence_root=evidence_root,
            status=BID_SUBMITTED,
        )
        self.bid_ids.append(bid_id)

    @gl.public.write
    def add_evidence(
        self,
        evidence_id: str,
        bid_id: str,
        uri: str,
        content_hash: str,
        kind: str,
    ):
        self._require_nonempty(evidence_id, "evidence_id")
        self._require_nonempty(uri, "uri")
        self._require_nonempty(content_hash, "content_hash")
        self._require_nonempty(kind, "kind")
        if evidence_id in self.evidence:
            raise gl.vm.UserError("Evidence already exists")
        bid = self.bids.get(bid_id)
        if bid is None:
            raise gl.vm.UserError("Bid does not exist")
        if gl.message.sender_address != bid.supplier:
            raise gl.vm.UserError("Only the bid supplier may add evidence")
        if uri[:8] != "https://":
            raise gl.vm.UserError("Evidence URI must use https")

        self.evidence[evidence_id] = EvidenceRecord(
            evidence_id=evidence_id,
            bid_id=bid_id,
            submitted_by=gl.message.sender_address,
            uri=uri,
            content_hash=content_hash,
            kind=kind,
        )
        self.evidence_ids.append(evidence_id)

    @gl.public.write
    def close_tender(self, tender_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_tender_issuer(tender)
        if tender.status != STATUS_OPEN:
            raise gl.vm.UserError("Only open tenders may be closed")
        tender.status = STATUS_CLOSED
        self.tenders[tender_id] = tender

    @gl.public.write
    def award_bid(self, tender_id: str, bid_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_tender_issuer(tender)
        if tender.status != STATUS_CLOSED:
            raise gl.vm.UserError("Only closed tenders may be awarded")
        bid = self.bids.get(bid_id)
        if bid is None or bid.tender_id != tender_id:
            raise gl.vm.UserError("Bid does not belong to this tender")
        if bid.status != BID_SUBMITTED:
            raise gl.vm.UserError("Only submitted bids may be awarded")

        for known_bid_id in self.bid_ids:
            known_bid = self.bids[known_bid_id]
            if known_bid.tender_id == tender_id:
                known_bid.status = (
                    BID_AWARDED if known_bid_id == bid_id else BID_REJECTED
                )
                self.bids[known_bid_id] = known_bid

        tender.status = STATUS_AWARDED
        tender.awarded_bid_id = bid_id
        self.tenders[tender_id] = tender

    @gl.public.write
    def cancel_tender(self, tender_id: str):
        tender = self.tenders.get(tender_id)
        if tender is None:
            raise gl.vm.UserError("Tender does not exist")
        self._require_tender_issuer(tender)
        if tender.status not in (STATUS_DRAFT, STATUS_OPEN, STATUS_CLOSED):
            raise gl.vm.UserError("This tender cannot be cancelled")
        tender.status = STATUS_CANCELLED
        self.tenders[tender_id] = tender
