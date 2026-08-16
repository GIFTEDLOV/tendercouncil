# TenderCouncil overlap research

**Research date:** 2026-08-16  
**Release evaluated:** TenderCouncil v2.1  
**Purpose:** document where TenderCouncil overlaps with existing GenLayer and adjacent on-chain evaluation/escrow patterns, and state the narrower architectural contribution without claiming that generic AI evaluation, procurement, escrow, or dispute resolution is novel.

## Scope and research standard

This document compares TenderCouncil with the closest public patterns found in:

- official GenLayer documentation and official GenLayer repositories;
- public on-chain job/escrow standards with an evaluator role;
- adjacent Intelligent Contracts already built in the same project family where the trust boundary is materially similar.

The review is intentionally conservative. A public-repository and documentation search cannot prove that no private, unpublished, or differently named implementation exists. TenderCouncil therefore **does not claim to be the first procurement contract, the first AI evaluator, the first escrow with adjudication, or the first GenLayer contract that evaluates natural-language criteria**.

The relevant question is narrower:

> Does TenderCouncil combine authenticated competitive procurement, deterministic custody/lifecycle rules, validator-based comparative semantic ranking, bounded challenge review, and finalized-only settlement in the same on-chain system?

That combination is the project-specific contribution documented below.

## 1. Official GenLayer use cases

GenLayer explicitly identifies judgment-dependent workflows as appropriate Intelligent Contract use cases. Its current builder guidance names **performance/milestone adjudication**, **dispute workflows**, and **rule/policy verification** as good fits when an on-chain consequence depends on evidence or natural-language judgment and validators can independently inspect the relevant material.

Primary sources:

- [When to Use GenLayer](https://docs.genlayer.com/developers/intelligent-contracts/when-to-use-genlayer)
- [GenLayer Use Cases](https://docs.genlayer.com/understand-genlayer-protocol/typical-use-cases)
- [The Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)

### Overlap

TenderCouncil directly inhabits those categories. A normal deterministic contract can enforce budget, deadlines, custody, bidder identity, and settlement arithmetic, but it cannot reliably decide which admissible proposal best satisfies a qualitative procurement rubric.

### Difference

The official use-case documentation describes a category, not a complete competitive tender state machine. TenderCouncil turns the category into a specific procurement architecture with:

1. buyer-funded escrow;
2. multiple wallet-authenticated competing bids;
3. immutable proposal/evidence commitments;
4. deterministic admissibility before semantic evaluation;
5. comparative ranking across the admissible set;
6. a provisional award rather than immediate payout;
7. a bounded response/challenge phase;
8. correlated review of admitted challenges; and
9. finalized-only winner payout plus exact buyer refund accounting.

The project should therefore be presented as an implementation of a recognized GenLayer use case with a procurement-specific trust boundary, not as invention of the underlying category.

## 2. GenLayer ACP Evaluator

The official [`genlayerlabs/genlayer-acp-evaluator`](https://github.com/genlayerlabs/genlayer-acp-evaluator) is the closest public GenLayer evaluator found in this review. It evaluates Virtuals ACP job deliverables with multi-validator AI consensus and stores an immutable verdict/score. Its README describes one fresh evaluation contract per job, with a leader evaluation and validator re-evaluation within configurable score/confidence tolerances.

### Overlap

Both systems:

- use GenLayer for non-deterministic semantic evaluation;
- reduce model output to structured decision fields;
- rely on validator agreement instead of one backend/model;
- expose an immutable on-chain result that downstream logic can consume.

### Difference

ACP Evaluator is primarily an **evaluation service** for a submitted job. TenderCouncil is a **competitive procurement and settlement system**. Its Core contract is the financial/lifecycle authority and its bound Evaluator is only one component of a larger state machine.

TenderCouncil additionally owns bid intake, deterministic qualification, a closed multi-bid snapshot, comparative winner selection, response/challenge handling, award finalization, payout/refund accounting, and exact custody transitions. The semantic evaluator cannot independently choose recipients or arbitrary payment amounts.

The closest conceptual relationship is therefore:

`ACP Evaluator: job -> semantic evaluation result`

versus

`TenderCouncil: funded tender -> competing authenticated bids -> deterministic admissibility -> semantic comparison -> provisional award -> challenge/review -> deterministic settlement`.

## 3. ERC-8183 agentic-commerce job escrow

Ethereum ERC-8183 defines a job lifecycle with a **client**, **provider**, **evaluator**, budget funding, submission, evaluation, completion/rejection, and escrow consequences. The evaluator is an address designated for the job and may itself be a smart contract.

Primary source:

- [ERC-8183](https://github.com/ethereum/ERCs/blob/master/ERCS/erc-8183.md)

### Overlap

ERC-8183 and TenderCouncil both recognize that commercial settlement can require a distinct evaluation role between funding and payout. Both separate custody/lifecycle logic from the act of judging work.

### Difference

ERC-8183 is a general job-commerce interface and does not itself require decentralized semantic consensus. Its evaluator is a single designated address. It also models a client/provider job rather than a competitive tender with multiple bids and comparative ranking.

TenderCouncil's evaluator is permanently bound to Core by address/version/code hash, while the judgment itself is formed by GenLayer validators over committed evidence. Core then revalidates the correlated result before using it. TenderCouncil also includes a procurement-specific bid set, weighted comparative rubric, response window, bounded challenge review, and buyer remainder/refund settlement.

This is meaningful overlap, but not duplication: ERC-8183 is a generic job/evaluator settlement primitive; TenderCouncil is a GenLayer-native competitive procurement implementation.

## 4. SemanticConstraint

[`GIFTEDLOV/semantic-constraint`](https://github.com/GIFTEDLOV/semantic-constraint) asks whether one public artifact satisfies an explicit set of natural-language requirements. It partitions criteria into satisfied/failed/undetermined states and derives a bounded verdict.

### Overlap

Both projects use natural-language criteria, deterministic pre/post-processing, authenticated or pinned evidence, and validator consensus over decision-critical semantic fields.

### Difference

SemanticConstraint deliberately has no parties, escrow, competitive bids, award lifecycle, or settlement. Its output is a reusable compliance primitive. TenderCouncil evaluates a **set of competing proposals** and must preserve financial and lifecycle invariants around the semantic result.

SemanticConstraint answers:

> Does this artifact satisfy these requirements?

TenderCouncil answers:

> Among the deterministically admissible bids for this funded tender, which bid best satisfies the published weighted procurement rubric, and can that provisional award survive the bounded challenge process before funds move?

## 5. SourceConsensus

[`GIFTEDLOV/source-consensus`](https://github.com/GIFTEDLOV/source-consensus) resolves one typed factual question from a fixed set of public sources and deterministically derives confirmation/conflict/evidence states.

### Overlap

Both systems separate evidence authentication from semantic interpretation and intentionally constrain what validator output can affect contract state.

### Difference

SourceConsensus resolves a factual value and has no parties, escrow, bids, ranking, challenge process, or payout. TenderCouncil performs comparative procurement judgment rather than multi-source fact extraction.

The shared security lesson is architectural rather than functional: consensus does not authenticate evidence, so evidence integrity and deterministic admissibility must precede semantic judgment.

## 6. UptimeBond

[`GIFTEDLOV/uptimebond`](https://github.com/GIFTEDLOV/uptimebond) is an escrowed SLA-dispute system. Validators interpret pinned SLA/evidence material and select a bounded outcome; deterministic contract logic maps that outcome to a predefined payout split.

### Overlap

This is the strongest overlap inside the project family because both systems combine:

- on-chain custody;
- evidence-backed semantic adjudication;
- bounded validator influence over financial consequences; and
- deterministic settlement logic after the semantic decision.

### Difference

UptimeBond is fundamentally a **two-party dispute over an existing SLA**. TenderCouncil is a **multi-party competitive procurement process before service delivery**. TenderCouncil must admit and compare multiple bids, freeze a canonical bid set, choose a provisional winner, permit bounded bid-related challenges, possibly review the award, and settle the winner's quote while returning unused escrow to the buyer.

The financial state machines therefore solve different problems even though both use the same high-level principle: semantic consensus selects a bounded business outcome; deterministic contract code owns the money.

## Comparison matrix

| Capability | TenderCouncil | ACP Evaluator | ERC-8183 | SemanticConstraint | SourceConsensus | UptimeBond |
| --- | --- | --- | --- | --- | --- | --- |
| Natural-language / semantic evaluation | Yes | Yes | Evaluator-defined | Yes | Extraction/interpretation | Yes |
| GenLayer validator consensus | Yes | Yes | Not required by standard | Yes | Yes | Yes |
| On-chain custody/escrow | Yes | No procurement escrow in evaluator contract | Yes | No | No | Yes |
| Multiple competing bids | **Yes** | No | No | No | No | No |
| Comparative winner ranking | **Yes** | Job score/verdict | No | No | No | No |
| Deterministic admissibility before semantic ranking | **Yes** | Different job-specific checks | Evaluator-defined | Criteria/schema gates | Typed normalization | SLA/lifecycle gates |
| Exact evidence commitments / integrity checks | **Yes** | Job input oriented | Standard does not prescribe GenLayer evidence model | Yes | Source policy/pinning | Yes |
| Provisional award before payout | **Yes** | No | No comparable procurement award | No | No | No |
| Bounded challenge/review of award | **Yes** | Protocol appeal mechanism differs | Evaluator/job lifecycle differs | No | No | Native transaction appeal only | Native appeal / settlement exits |
| Winner payout + unused buyer refund | **Yes** | No | Generic job payment/refund | No | No | SLA payout split |

The matrix is architectural, not a claim that every adjacent project exposes identical terminology or implementation details.

## What TenderCouncil should claim

A defensible description is:

> TenderCouncil is a GenLayer-native competitive procurement system that keeps escrow, lifecycle, admissibility, challenge admission, and settlement deterministic while delegating only the bounded comparative proposal judgment to a permanently bound validator-driven Evaluator.

The differentiating combination is:

`authenticated immutable bids/evidence`
` -> deterministic admissibility`
` -> closed canonical bid snapshot`
` -> bounded comparative validator judgment`
` -> provisional award`
` -> response/challenge review`
` -> finalized-only deterministic payout/refund`.

## What TenderCouncil should not claim

Do **not** claim:

- that AI-based evaluation is new;
- that GenLayer rule verification or milestone adjudication is new;
- that escrow with an evaluator is new;
- that TenderCouncil is the first decentralized procurement protocol;
- that validator consensus proves source authenticity;
- that public search proves no similar unpublished project exists.

Those claims are unnecessary and stronger than the evidence supports.

## Conclusion

The closest public overlaps cover pieces of TenderCouncil rather than the full trust boundary. Official GenLayer materials already describe judgment-dependent settlement and rule verification; ACP Evaluator provides GenLayer job evaluation; ERC-8183 provides evaluator-mediated job escrow; SemanticConstraint provides criteria compliance; SourceConsensus provides evidence-backed fact resolution; and UptimeBond combines semantic adjudication with escrow for a two-party SLA dispute.

TenderCouncil's narrower contribution is the **composition of these ideas into a competitive multi-bid procurement lifecycle in which Core remains the deterministic financial authority and a permanently bound Evaluator supplies only the authenticated, bounded comparative judgment required to choose and review an award**.

That is the positioning used by the v2.1 release. No contract or deployment change is implied by this research document.
