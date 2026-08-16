/*
 * TenderCouncil v2.1 bidder reference.
 *
 * The helpers return the exact Core method/argument shape. They do not call
 * client.writeContract and therefore never broadcast during tests or import.
 * The returned bodies must be served byte-for-byte at their committed URLs.
 */

import crypto from "node:crypto";

export const CORE = "0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd";
export const BID_SCHEMA = "tendercouncil.bid.v1";
export const EVIDENCE_SCHEMA = "tendercouncil.evidence.v1";

const sha256Text = (body) => `sha256:${crypto.createHash("sha256").update(body, "utf8").digest("hex")}`;
const call = (functionName, args) => ({
  address: CORE,
  functionName,
  args,
  value: 0n,
  leaderOnly: false,
});

export async function inspectTender(client, tenderId) {
  return client.readContract({
    address: CORE,
    functionName: "get_tender",
    args: [tenderId],
  });
}

export function makeEvidenceBody({ kind, claims }) {
  const body = JSON.stringify({ schema_version: EVIDENCE_SCHEMA, kind, claims });
  return { body, sha256: sha256Text(body) };
}

export function makeBidSubmission({
  bidId,
  tenderId,
  bidder,
  priceWei,
  deliveryDays,
  supportDays,
  proposalUrl,
  proposal,
  evidence,
}) {
  // `proposal` must have exactly the v2.1 manifest keys and the served bytes
  // must be exactly this JSON string. Each evidence row must match its served
  // evidence body and its on-chain commitment entry.
  const evidenceBody = JSON.stringify(evidence.map((item) => ({
      criterion: item.criterion,
      evidence_id: item.evidenceId,
      kind: item.kind,
      required: item.required,
      sha256: item.sha256,
      url: item.url,
    })));
  // JSON numbers must remain decimal integers. Do not coerce GEN wei through
  // JavaScript Number, which would lose precision for ordinary escrow values.
  const proposalBody = [
    `{"bidder":${JSON.stringify(bidder)}`,
    `,"delivery_days":${BigInt(deliveryDays).toString()}`,
    `,"evidence":${evidenceBody}`,
    `,"price_wei":${BigInt(priceWei).toString()}`,
    `,"proposal":${JSON.stringify(proposal)}`,
    `,"schema_version":${JSON.stringify(BID_SCHEMA)}`,
    `,"support_days":${BigInt(supportDays).toString()}`,
    `,"tender_id":${JSON.stringify(tenderId)}}`,
  ].join("");
  const commitments = evidence.map((item) => [
    item.evidenceId,
    item.kind,
    item.criterion,
    item.required ? "1" : "0",
    item.url,
    item.sha256,
  ].join("|")).join(";");

  return {
    bidId,
    proposalBody,
    proposalSha256: sha256Text(proposalBody),
    evidenceCommitments: commitments,
    write: call("submit_bid", [
      bidId,
      tenderId,
      BigInt(priceWei),
      BigInt(deliveryDays),
      BigInt(supportDays),
      proposalUrl,
      sha256Text(proposalBody),
      commitments,
      BID_SCHEMA,
    ]),
  };
}

export async function readBidState(client, { tenderId, bidId }) {
  const tender = await client.readContract({
    address: CORE,
    functionName: "get_tender",
    args: [tenderId],
  });
  const bid = await client.readContract({
    address: CORE,
    functionName: "get_bid",
    args: [bidId],
  });
  return { tender, bid };
}

// A real SDK write uses: await client.writeContract({ account, ...submission.write }).
// Reconcile the returned transaction hash and Core state before any retry.
