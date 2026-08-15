/* Read-only exact closed-snapshot exporter for local evaluator replay. */
import crypto from "node:crypto";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { resolveGenlayerModulePaths } from "./genlayer_module_paths.mjs";

const CORE = "0xCeBA3b0e28b5B538054755F91AA501213d9b23B9";
const TENDER = "analytics-dashboard-2026-final-v2";
const EXPECTED = "sha256:85880585a3b1617aa8185b133ef79c9fb36082f68853126500d00fde1a9dfc19";

function digest(bytes) { return `sha256:${crypto.createHash("sha256").update(bytes).digest("hex")}`; }
function utf8(value) { return Buffer.from(value, "utf8"); }
async function getBytes(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${url}`);
  return Buffer.from(await response.arrayBuffer());
}

const { sdkRoot } = resolveGenlayerModulePaths();
const sdk = await import(pathToFileURL(`${sdkRoot}/index.js`));
const { testnetBradbury } = await import(pathToFileURL(`${sdkRoot}/chains/index.js`));
const client = sdk.createClient({ chain: testnetBradbury });
const snapshotText = await client.readContract({
  address: CORE, functionName: "get_closed_snapshot", args: [TENDER], blockTag: "finalized",
});
const snapshotBytes = utf8(snapshotText);
const tender = await client.readContract({
  address: CORE, functionName: "get_tender", args: [TENDER], blockTag: "finalized",
});
if (digest(snapshotBytes) !== EXPECTED || digest(snapshotBytes) !== tender.closed_snapshot_digest) {
  throw new Error("exact live snapshot digest verification failed");
}
const snapshot = JSON.parse(snapshotText);
const bids = [];
for (const bid of snapshot.bids) {
  const proposalBytes = await getBytes(bid.proposal_url);
  if (digest(proposalBytes) !== bid.proposal_sha256) throw new Error(`proposal hash mismatch: ${bid.bid_id}`);
  const manifest = JSON.parse(proposalBytes.toString("utf8"));
  const evidence = [];
  for (const item of manifest.evidence) {
    const body = await getBytes(item.url);
    if (digest(body) !== item.sha256) throw new Error(`evidence hash mismatch: ${bid.bid_id}/${item.evidence_id}`);
    evidence.push({ url: item.url, body: body.toString("utf8"), sha256: digest(body) });
  }
  bids.push({
    bid_id: bid.bid_id,
    proposal_url: bid.proposal_url,
    proposal_body: proposalBytes.toString("utf8"),
    proposal_sha256: digest(proposalBytes),
    evidence,
  });
}
const brief = await getBytes(snapshot.brief_url);
if (digest(brief) !== snapshot.brief_sha256) throw new Error("brief hash mismatch");
process.stdout.write(JSON.stringify({
  tender_id: TENDER,
  snapshot_text: snapshotText,
  snapshot_sha256: digest(snapshotBytes),
  brief: { url: snapshot.brief_url, body: brief.toString("utf8"), sha256: digest(brief) },
  bids,
}));
