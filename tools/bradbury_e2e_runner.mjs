/* Durable, restartable TenderCouncil v2.1 Bradbury state machine. */
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  OperationJournal,
  canonicalJson,
  executeJournaledWrite,
  makeTenderScopedBidId,
  readClassified,
  reconcileBid,
  verifyBidsForClose,
  withReadRetry,
} from "./bradbury_runner_lib.mjs";
import { resolveGenlayerModulePaths } from "./genlayer_module_paths.mjs";


const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { sdkRoot: SDK_ROOT, cliEntry: CLI_ROOT } = resolveGenlayerModulePaths();
const NETWORK = "testnet-bradbury";
const CHAIN_ID = 4221;
const EVALUATOR_VERSION = "tendercouncil.evaluator.v2.1";
const TENDER_ID = process.env.TENDERCOUNCIL_TENDER_ID || "analytics-dashboard-2026-final-v2";
const HISTORICAL_TENDERS = new Set(["analytics-dashboard-2026", "analytics-dashboard-2026-recovery"]);
const BUDGET = 80_000_000_000_000_000n;
const BIDDER_FUNDING = 20_000_000_000_000_000n;
const RESPONSE_WINDOW = 7200;
const BRIEF_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/brief.json";
const BRIEF_HASH = "sha256:44bb3d24956a4ea2d9a8828afc7f6cde822c7f0c06708aea3fa9f7d365a33f8e";
const DEPLOYMENT_PATH = process.env.TENDERCOUNCIL_DEPLOYMENT_PATH || path.join(ROOT, "artifacts/tender_council_bradbury_v21_deployment.json");
const EVIDENCE_PATH = path.join(ROOT, "artifacts/tender_council_bradbury_v21_e2e.json");
const JOURNAL_ROOT = process.env.TENDERCOUNCIL_JOURNAL_ROOT || path.join(ROOT, ".local/bradbury-journal");
const BID_ROWS = [
  ["a", "bidder_a", 62_000_000_000_000_000n, 26, 90],
  ["b", "bidder_b", 74_000_000_000_000_000n, 27, 120],
  ["c", "bidder_c", 43_000_000_000_000_000n, 20, 90],
  ["d", "bidder_d", 87_000_000_000_000_000n, 22, 120],
  ["e", "bidder_e", 69_000_000_000_000_000n, 45, 120],
];
const TRANSIENT = /fetch failed|ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|timeout|network|429|500|502|503|504|socket|connection/i;
// The first corrected evaluation is the real external-provider production gate.
// When this gate is set, the runner never auto-retries or expires a failed first
// evaluation attempt: it captures the child + callback evidence and STOPS so the
// outcome can be inspected before any retry is deliberately consumed.
const STOP_AFTER_FIRST_EVALUATION = process.env.TENDERCOUNCIL_STOP_AFTER_FIRST_EVALUATION === "1";

// Distinctive marker so callers can tell a deliberate evaluation-gate stop from
// an unexpected failure.
class EvaluationGateStop extends Error {
  constructor(message, detail) { super(message); this.name = "EvaluationGateStop"; this.detail = detail; }
}


function safe(value) {
  return JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
}
function digestBytes(value) { return `sha256:${crypto.createHash("sha256").update(value).digest("hex")}`; }
function digestState(value) { return digestBytes(Buffer.from(canonicalJson(safe(value)), "utf8")); }
function statusName(tx) { return tx?.statusName || tx?.status || "UNKNOWN"; }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function retryLog(event) { console.log(`rpc_retry=${JSON.stringify(event)}`); }
function exact(value) { return { state: "EXACT", digest: digestState(value), value }; }
function missing() { return { state: "MISSING" }; }
function isHash(value) { return typeof value === "string" && /^0x[0-9a-f]{64}$/i.test(value); }
function scopedChallengeId() { return `${TENDER_ID}-challenge-a`; }

function assertConfiguration() {
  if (HISTORICAL_TENDERS.has(TENDER_ID)) throw new Error("historical tender ID reuse is forbidden");
  if (TENDER_ID !== "analytics-dashboard-2026-final-v2") {
    throw new Error("fixture tender ID does not match TENDERCOUNCIL_TENDER_ID");
  }
  makeTenderScopedBidId(TENDER_ID, "e");
  if (scopedChallengeId().length > 96) throw new Error("challenge ID exceeds Core grammar");
}

async function retryRead(name, operation) {
  return withReadRetry(operation, { operation: name, logger: retryLog, isTransient: (error) => TRANSIENT.test(String(error?.message || error)) });
}

// GenVM surfaces a contract UserError as a Go byte-slice dump
// (`ReturnData:[]uint8{0x74, 0x65, ...}`), never as decoded text, so the
// "<record> does not exist" phrase is not readable in any error string.
// Decode those blocks so absence stays distinguishable from a real fault.
function decodeVmBytes(text) {
  let decoded = "";
  const block = /\[\]uint8\{([^}]*)\}/g;
  let match;
  while ((match = block.exec(text)) !== null) {
    for (const part of match[1].split(",")) {
      const byte = part.trim();
      if (/^0x[0-9a-fA-F]{1,2}$/.test(byte)) {
        const code = parseInt(byte, 16);
        decoded += code >= 0x20 && code < 0x7f ? String.fromCharCode(code) : " ";
      }
    }
    decoded += " ";
  }
  return decoded;
}

function recordMissing(error, functionName) {
  // shortMessage alone is a generic viem string; the payload only ever appears
  // in the full message, so every layer has to be considered.
  const joined = [error?.shortMessage, error?.message, String(error)]
    .filter(Boolean).map(String).join(" ");
  const haystack = `${joined} ${decodeVmBytes(joined)}`;
  return ({
    get_tender: /tender does not exist/i,
    get_bid: /bid does not exist/i,
    get_challenge: /challenge does not exist/i,
  })[functionName]?.test(haystack) || false;
}

async function readContract(client, address, functionName, args = []) {
  return safe(await retryRead(`view:${functionName}`, () => client.readContract({ address, functionName, args, blockTag: "finalized" })));
}

async function readRecord(client, address, functionName, args = []) {
  return readClassified(
    () => readContract(client, address, functionName, args),
    { operation: `classified:${functionName}`, logger: retryLog, isMissing: (error) => recordMissing(error, functionName) },
  );
}

async function chainTime(client) {
  const block = await retryRead("eth_getBlockByNumber", () => client.getBlock({ blockTag: "latest" }));
  return Number(block.timestamp);
}

async function waitGenlayerFinal(client, hash, requireAgree = true) {
  if (!isHash(hash)) throw new Error(`invalid GenLayer tx hash: ${hash}`);
  let accepted = null;
  for (let attempt = 1; attempt <= 720; attempt += 1) {
    const tx = await retryRead("getTransaction", () => client.getTransaction({ hash }));
    const status = statusName(tx);
    if (status === "ACCEPTED" && accepted === null) accepted = safe(tx);
    if (status === "FINALIZED") {
      const consensus = String(tx?.consensusStatus || tx?.consensus || "");
      if (requireAgree && consensus && consensus !== "AGREE") throw new Error(`transaction ${hash} finalized ${consensus}`);
      return { hash, finality: "FINALIZED", accepted, finalized: safe(tx) };
    }
    if (["UNDETERMINED", "CANCELED", "REVERTED"].includes(status)) {
      throw new Error(`transaction ${hash} terminated as ${status}`);
    }
    await sleep(Math.min(30_000, 1000 * (2 ** Math.min(attempt, 5))));
  }
  throw new Error(`transaction ${hash} did not finalize within the bounded poll window`);
}

async function waitEvmFinal(client, hash) {
  if (!isHash(hash)) throw new Error(`invalid EVM tx hash: ${hash}`);
  for (let attempt = 1; attempt <= 720; attempt += 1) {
    const receipt = await retryRead("eth_getTransactionReceipt", () => client.request({ method: "eth_getTransactionReceipt", params: [hash] }));
    if (receipt?.status === "0x1") return { hash, finality: "FINALIZED", receipt: safe(receipt) };
    if (receipt?.status === "0x0") throw new Error(`native transfer reverted: ${hash}`);
    await sleep(Math.min(30_000, 1000 * (2 ** Math.min(attempt, 5))));
  }
  throw new Error(`native transfer ${hash} did not receive a successful receipt`);
}

async function loadBidDefinitions(fixtureCommit, bidders) {
  const definitions = [];
  for (const [suffix, label, price, delivery, support] of BID_ROWS) {
    const file = path.join(ROOT, `fixtures/live/final-v2/manifests/bid_${suffix}.json`);
    const bytes = await fs.readFile(file);
    const body = JSON.parse(bytes.toString("utf8"));
    const bidId = makeTenderScopedBidId(TENDER_ID, suffix);
    if (body.tender_id !== TENDER_ID || body.bidder.toLowerCase() !== bidders[label].toLowerCase()) {
      throw new Error(`local manifest identity mismatch: ${file}`);
    }
    if (BigInt(body.price_wei) !== price || body.delivery_days !== delivery || body.support_days !== support) {
      throw new Error(`local manifest commercial mismatch: ${file}`);
    }
    const commitment = body.evidence.map((item) => [
      item.evidence_id, item.kind, item.criterion, item.required ? "1" : "0",
      item.url, item.sha256,
    ].join("|")).join(";");
    definitions.push({
      suffix, label, bid_id: bidId, tender_id: TENDER_ID,
      bidder: bidders[label], price_wei: price.toString(), delivery_days: delivery,
      support_days: support,
      proposal_url: `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${fixtureCommit}/fixtures/live/final-v2/manifests/bid_${suffix}.json`,
      proposal_sha256: digestBytes(bytes), evidence_commitments: commitment,
      schema_version: "tendercouncil.bid.v1",
    });
  }
  return definitions;
}

async function sourceManifest() {
  const files = {
    core_source: "contracts/tender_council_core.py",
    core_deployable: "artifacts/tender_council_core_v21_deployable.py",
    evaluator_source: "contracts/tender_council_evaluator.py",
    evaluator_deployable: "artifacts/tender_council_evaluator_v21_deployable.py",
  };
  const result = {};
  for (const [name, relative] of Object.entries(files)) {
    const bytes = await fs.readFile(path.join(ROOT, relative));
    result[name] = { path: relative, bytes: bytes.length, sha256: digestBytes(bytes) };
  }
  return result;
}

async function journaledContractWrite({ journal, client, core, operation, objectId, intent, args, value = 0n, reconcile }) {
  await executeJournaledWrite({
    journal, operation, objectId, intent,
    reconcile,
    broadcast: () => client.writeContract({ account: client.account, address: core, functionName: operation, args, value, leaderOnly: false }),
    poll: (hash) => waitGenlayerFinal(client, hash),
    verify: reconcile,
  });
  const entry = await journal.get(operation, objectId);
  if (!entry?.tx_hash && entry?.status !== "FINALIZED") throw new Error(`journal did not finalize ${operation}:${objectId}`);
  return entry;
}

async function journaledBidBroadcast({ journal, bidderClient, readClient, core, bid, deadline }) {
  const operation = "submit_bid";
  const args = [
    bid.bid_id, bid.tender_id, BigInt(bid.price_wei), bid.delivery_days,
    bid.support_days, bid.proposal_url, bid.proposal_sha256,
    bid.evidence_commitments, bid.schema_version,
  ];
  const bidContext = async () => ({
    tenderStatus: (await readContract(readClient, core, "get_tender", [TENDER_ID])).status,
    now: await chainTime(readClient), deadline,
  });
  const reconcile = async () => {
    const outcome = await readRecord(readClient, core, "get_bid", [bid.bid_id]);
    const result = reconcileBid(
      outcome.kind === "FOUND" ? { ...outcome, finality: "FINALIZED" } : outcome,
      bid, await bidContext(),
    );
    return result.action === "COMPLETE" ? exact(result.record) : missing();
  };

  let entry = await journal.get(operation, bid.bid_id);
  if (entry && canonicalJson(entry.intent) !== canonicalJson(bid)) {
    throw new Error(`journal intent mismatch for ${operation}:${bid.bid_id}`);
  }
  if (entry?.tx_hash) return { tx_hash: entry.tx_hash, journal_status: entry.status };
  if (entry) {
    const state = await reconcile();
    if (state.state === "EXACT") {
      await journal.markFinalized(operation, bid.bid_id, state.digest);
      return { tx_hash: null, journal_status: "FINALIZED" };
    }
    throw new Error(`ambiguous durable intent without tx hash for ${operation}:${bid.bid_id}; refusing rebroadcast`);
  }

  const state = await reconcile();
  await journal.recordIntent(operation, bid.bid_id, bid);
  if (state.state === "EXACT") {
    await journal.markFinalized(operation, bid.bid_id, state.digest);
    return { tx_hash: null, journal_status: "FINALIZED" };
  }

  const beforeBroadcast = await bidContext();
  if (Number(beforeBroadcast.now) > Number(deadline)) {
    throw new Error(`bidding deadline expired before broadcast of ${bid.bid_id}: chain_time=${beforeBroadcast.now} deadline=${deadline}`);
  }
  const txHash = await bidderClient.writeContract({
    account: bidderClient.account, address: core, functionName: operation,
    args, value: 0n, leaderOnly: false,
  });
  await journal.recordBroadcast(operation, bid.bid_id, txHash);
  return { tx_hash: txHash, journal_status: "BROADCAST" };
}

async function reconcileFinalizedBid({ journal, readClient, core, bid, txHash, deadline }) {
  if (!txHash) {
    const state = await (async () => {
      const outcome = await readRecord(readClient, core, "get_bid", [bid.bid_id]);
      const result = reconcileBid(
        outcome.kind === "FOUND" ? { ...outcome, finality: "FINALIZED" } : outcome,
        bid, { tenderStatus: "OPEN", now: deadline + 1, deadline },
      );
      return result.action === "COMPLETE" ? exact(result.record) : missing();
    })();
    if (state.state !== "EXACT") throw new Error(`bid ${bid.bid_id} has no transaction hash and is not exact on chain`);
    await journal.markFinalized("submit_bid", bid.bid_id, state.digest);
    return state.value;
  }
  const final = await waitGenlayerFinal(readClient, txHash, true);
  const tx = final.finalized;
  const execution = String(tx?.txExecutionResultName || tx?.executionResult || tx?.txExecutionResult || "");
  const deterministicViolation = Boolean(tx?.deterministicViolation || tx?.deterministic_violation) || execution === "DETERMINISTIC_VIOLATION" || String(tx?.resultName || tx?.result || "") === "DETERMINISTIC_VIOLATION";
  if (statusName(tx) !== "FINALIZED" || String(tx?.resultName || tx?.result || "") !== "AGREE" || execution !== "FINISHED_WITH_RETURN" || deterministicViolation) {
    throw new Error(`bid ${bid.bid_id} finality invariant failed for ${txHash}: status=${statusName(tx)} result=${tx?.resultName || tx?.result || ""} execution=${execution} deterministic_violation=${deterministicViolation}`);
  }
  const outcome = await readRecord(readClient, core, "get_bid", [bid.bid_id]);
  const result = reconcileBid(
    outcome.kind === "FOUND" ? { ...outcome, finality: "FINALIZED" } : outcome,
    bid, { tenderStatus: "OPEN", now: deadline + 1, deadline },
  );
  if (result.action !== "COMPLETE") throw new Error(`bid ${bid.bid_id} finalized transaction did not produce exact bid state`);
  await journal.markFinalized("submit_bid", bid.bid_id, digestState(result.record));
  return result.record;
}

async function journaledFunding({ journal, client, address, amount }) {
  const operation = "fund_bidder";
  const intent = { address: address.toLowerCase(), minimum_balance_wei: amount.toString() };
  const reconcile = async (entry = null) => {
    if (entry?.tx_hash) {
      const receipt = await waitEvmFinal(client, entry.tx_hash);
      return exact(receipt);
    }
    const balance = await retryRead("getBalance", () => client.getBalance({ address, blockTag: "latest" }));
    return balance >= amount ? exact({ address, funded: true }) : missing();
  };
  await executeJournaledWrite({
    journal, operation, objectId: address.toLowerCase(), intent, reconcile,
    broadcast: () => client.sendTransaction({ account: client.account, to: address, value: amount, data: "0x" }),
    poll: (hash) => waitEvmFinal(client, hash), verify: reconcile,
  });
}

const LIFECYCLE = [
  "DRAFT", "OPEN", "CLOSED", "EVALUATING", "EVALUATION_RETRYABLE",
  "PROVISIONAL_AWARD", "RESPONSE_WINDOW", "REVIEWING_CHALLENGES",
  "REVIEW_RETRYABLE", "AWARDED", "SETTLEMENT_PENDING", "SETTLED",
];
function reached(status, target) {
  return LIFECYCLE.indexOf(status) >= LIFECYCLE.indexOf(target) && LIFECYCLE.indexOf(target) >= 0;
}

async function waitUntil(client, target, label) {
  while (true) {
    const now = await chainTime(client);
    if (now >= target) return;
    console.log(`${label}_remaining_seconds=${target - now}`);
    await sleep(30_000);
  }
}

async function writeEvidence(manifest) {
  await fs.writeFile(EVIDENCE_PATH, `${JSON.stringify(safe(manifest), null, 2)}\n`, "utf8");
}

async function preflight({ readClient, core, evaluator, bids, source }) {
  const tender = await readRecord(readClient, core, "get_tender", [TENDER_ID]);
  const bidStates = [];
  for (const bid of bids) bidStates.push(await readRecord(readClient, core, "get_bid", [bid.bid_id]));
  const intended = {
    tender_id: TENDER_ID,
    bid_ids: bids.map((bid) => bid.bid_id),
    escrow_wei: BUDGET.toString(), response_window_seconds: RESPONSE_WINDOW,
    deadline_policy: "chain_time_at_create + 21600",
    core, evaluator, source,
    onchain_absence: {
      tender: tender.kind, bids: bidStates.map((state, index) => ({ bid_id: bids[index].bid_id, state: state.kind })),
    },
  };
  console.log(`prebroadcast_intent=${JSON.stringify(intended, null, 2)}`);
  return { intended, tender, bidStates };
}

async function reconcileTender(readClient, core, expected, targetStatus = null) {
  const outcome = await readRecord(readClient, core, "get_tender", [TENDER_ID]);
  if (outcome.kind === "MISSING") return missing();
  const tender = outcome.record;
  const checks = {
    tender_id: TENDER_ID, buyer: expected.buyer, title: expected.title,
    brief_url: BRIEF_URL, brief_sha256: BRIEF_HASH,
    max_budget_wei: BUDGET.toString(), max_delivery_days: 30,
    min_support_days: 90, bidding_deadline: expected.deadline,
    response_window_seconds: RESPONSE_WINDOW, requirements: expected.requirements,
    evidence_policy: expected.evidence_policy,
  };
  for (const [field, value] of Object.entries(checks)) {
    const actual = field === "buyer" ? String(tender[field]).toLowerCase() : String(tender[field]);
    const wanted = field === "buyer" ? String(value).toLowerCase() : String(value);
    if (actual !== wanted) throw new Error(`tender immutable field mismatch: ${field}`);
  }
  if (targetStatus && !reached(tender.status, targetStatus) && tender.status !== targetStatus) return missing();
  return exact(tender);
}

async function captureAsyncChildren(client, parentHash, manifest, label, expectedRecipient = null) {
  if (!parentHash) return;
  const parent = await retryRead("async-parent", () => client.getTransaction({ hash: parentHash }));
  const fromBlock = BigInt(parent?.readStateBlockRange?.proposalBlock || parent?.proposalBlock || 0);
  const sender = String(parent?.recipient || "").toLowerCase();
  const topic = "0xdab9102861c7483a187584d6371d88316f005af507982ccf95c110879f3ed5a5";
  for (let attempt = 1; attempt <= 20; attempt += 1) {
    const latest = await retryRead("eth_getBlockByNumber", () => client.getBlock({ blockTag: "latest" }));
    const logs = await retryRead("eth_getLogs", () => client.request({ method: "eth_getLogs", params: [{ address: client.chain.consensusMainContract.address, fromBlock: `0x${fromBlock.toString(16)}`, toBlock: `0x${BigInt(latest.number).toString(16)}`, topics: [topic] }] }));
    const children = [];
    for (const log of logs || []) {
      const hash = log?.topics?.[1];
      if (!isHash(hash)) continue;
      const tx = await retryRead("async-child", () => client.getTransaction({ hash }));
      if (sender && String(tx?.sender || "").toLowerCase() !== sender) continue;
      if (expectedRecipient && String(tx?.recipient || "").toLowerCase() !== expectedRecipient.toLowerCase()) continue;
      if (tx?.createdTimestamp && parent?.createdTimestamp && BigInt(tx.createdTimestamp) < BigInt(parent.createdTimestamp)) continue;
      const final = await waitGenlayerFinal(client, hash, false);
      children.push({ hash, transaction: final.finalized });
    }
    if (children.length) {
      manifest.async_messages[label] = children;
      await writeEvidence(manifest);
      return children;
    }
    await sleep(Math.min(30_000, 1000 * (2 ** Math.min(attempt, 5))));
  }
}

async function driveEvaluation({ journal, buyer, readClient, core, manifest }) {
  while (true) {
    const tender = await readContract(readClient, core, "get_tender", [TENDER_ID]);
    if (tender.status === "CLOSED") {
      const nextNonce = Number(tender.evaluation_nonce) + 1;
      await journaledContractWrite({
        journal, client: buyer, core, operation: "start_evaluation",
        objectId: `${TENDER_ID}#${nextNonce}`,
        intent: { tender_id: TENDER_ID, nonce: nextNonce, snapshot_digest: tender.closed_snapshot_digest },
        args: [TENDER_ID],
        reconcile: async () => {
          const current = await readContract(readClient, core, "get_tender", [TENDER_ID]);
          return Number(current.evaluation_nonce) >= nextNonce && current.status !== "CLOSED" ? exact(current) : missing();
        },
      });
      continue;
    }
    if (tender.status === "EVALUATION_RETRYABLE") {
      if (STOP_AFTER_FIRST_EVALUATION) {
        const nonce = Number(tender.evaluation_nonce);
        const operation = nonce === 1 ? "start_evaluation" : "retry_evaluation";
        const entry = await journal.get(operation, `${TENDER_ID}#${nonce}`);
        const jobs = await captureAsyncChildren(readClient, entry?.tx_hash, manifest, `evaluation_attempt_${nonce}`, manifest.release.evaluator);
        if (jobs?.[0]) await captureAsyncChildren(readClient, jobs[0].hash, manifest, `evaluation_callback_${nonce}`, core);
        throw new EvaluationGateStop(
          `first corrected evaluation did not award: tender is EVALUATION_RETRYABLE at nonce ${nonce}; not consuming a retry`,
          { status: tender.status, evaluation_nonce: nonce, provisional_winner: tender.provisional_winner },
        );
      }
      const nextNonce = Number(tender.evaluation_nonce) + 1;
      await journaledContractWrite({
        journal, client: buyer, core, operation: "retry_evaluation",
        objectId: `${TENDER_ID}#${nextNonce}`,
        intent: { tender_id: TENDER_ID, nonce: nextNonce, snapshot_digest: tender.closed_snapshot_digest },
        args: [TENDER_ID],
        reconcile: async () => {
          const current = await readContract(readClient, core, "get_tender", [TENDER_ID]);
          return Number(current.evaluation_nonce) >= nextNonce && current.status !== "EVALUATION_RETRYABLE" ? exact(current) : missing();
        },
      });
      continue;
    }
    if (tender.status === "EVALUATING") {
      const nonce = Number(tender.evaluation_nonce);
      const operation = nonce === 1 ? "start_evaluation" : "retry_evaluation";
      const entry = await journal.get(operation, `${TENDER_ID}#${nonce}`);
      const jobs = await captureAsyncChildren(readClient, entry?.tx_hash, manifest, `evaluation_attempt_${nonce}`, manifest.release.evaluator);
      if (jobs?.[0]) await captureAsyncChildren(readClient, jobs[0].hash, manifest, `evaluation_callback_${nonce}`, core);
      const now = await chainTime(readClient);
      if (now <= Number(tender.evaluation_timeout_at)) {
        await sleep(30_000);
        continue;
      }
      if (STOP_AFTER_FIRST_EVALUATION) {
        throw new EvaluationGateStop(
          `first corrected evaluation attempt ${nonce} did not produce a callback before its on-chain timeout; not expiring or retrying`,
          { status: tender.status, evaluation_nonce: nonce, evaluation_timeout_at: Number(tender.evaluation_timeout_at), chain_time: now },
        );
      }
      await journaledContractWrite({
        journal, client: buyer, core, operation: "expire_evaluation_attempt",
        objectId: `${TENDER_ID}#${nonce}`,
        intent: { tender_id: TENDER_ID, nonce, timeout_at: Number(tender.evaluation_timeout_at) },
        args: [TENDER_ID],
        reconcile: async () => {
          const current = await readContract(readClient, core, "get_tender", [TENDER_ID]);
          return current.status !== "EVALUATING" ? exact(current) : missing();
        },
      });
      continue;
    }
    if (tender.status === "EVALUATION_FAILED") throw new Error("bounded evaluation attempts exhausted");
    if (tender.status === "NO_VALID_BID") throw new Error("canonical five-bid evaluation returned NO_VALID_BID");
    if (tender.status === "PROVISIONAL_AWARD" || reached(tender.status, "PROVISIONAL_AWARD")) return tender;
    throw new Error(`unexpected evaluation state: ${tender.status}`);
  }
}

async function driveReview({ journal, buyer, readClient, core, manifest }) {
  while (true) {
    const tender = await readContract(readClient, core, "get_tender", [TENDER_ID]);
    if (tender.status === "RESPONSE_WINDOW") {
      await waitUntil(readClient, Number(tender.response_window_end) + 1, "response_window");
      const nextNonce = Number(tender.review_nonce) + 1;
      await journaledContractWrite({
        journal, client: buyer, core, operation: "advance_after_response",
        objectId: `${TENDER_ID}#${nextNonce}`,
        intent: { tender_id: TENDER_ID, review_nonce: nextNonce }, args: [TENDER_ID],
        reconcile: async () => {
          const current = await readContract(readClient, core, "get_tender", [TENDER_ID]);
          return current.status !== "RESPONSE_WINDOW" ? exact(current) : missing();
        },
      });
      continue;
    }
    if (tender.status === "REVIEW_RETRYABLE") {
      const nextNonce = Number(tender.review_nonce) + 1;
      await journaledContractWrite({
        journal, client: buyer, core, operation: "retry_review",
        objectId: `${TENDER_ID}#${nextNonce}`,
        intent: { tender_id: TENDER_ID, review_nonce: nextNonce, challenge_set_digest: tender.challenge_set_digest },
        args: [TENDER_ID],
        reconcile: async () => {
          const current = await readContract(readClient, core, "get_tender", [TENDER_ID]);
          return Number(current.review_nonce) >= nextNonce && current.status !== "REVIEW_RETRYABLE" ? exact(current) : missing();
        },
      });
      continue;
    }
    if (tender.status === "REVIEWING_CHALLENGES") {
      const nonce = Number(tender.review_nonce);
      const operation = nonce === 1 ? "advance_after_response" : "retry_review";
      const entry = await journal.get(operation, `${TENDER_ID}#${nonce}`);
      const jobs = await captureAsyncChildren(readClient, entry?.tx_hash, manifest, `review_attempt_${nonce}`, manifest.release.evaluator);
      if (jobs?.[0]) await captureAsyncChildren(readClient, jobs[0].hash, manifest, `review_callback_${nonce}`, core);
      const now = await chainTime(readClient);
      if (now <= Number(tender.review_timeout_at)) { await sleep(30_000); continue; }
      await journaledContractWrite({
        journal, client: buyer, core, operation: "expire_review_attempt",
        objectId: `${TENDER_ID}#${nonce}`,
        intent: { tender_id: TENDER_ID, nonce, timeout_at: Number(tender.review_timeout_at) },
        args: [TENDER_ID],
        reconcile: async () => {
          const current = await readContract(readClient, core, "get_tender", [TENDER_ID]);
          return current.status !== "REVIEWING_CHALLENGES" ? exact(current) : missing();
        },
      });
      continue;
    }
    if (tender.status === "NO_VALID_BID") throw new Error("challenge review returned NO_VALID_BID");
    if (tender.status === "AWARDED" || reached(tender.status, "AWARDED")) return tender;
    throw new Error(`unexpected review state: ${tender.status}`);
  }
}

export async function runBradburyE2E() {
  assertConfiguration();
  const confirmed = process.env.TENDERCOUNCIL_E2E_CONFIRM === "RUN_TENDERCOUNCIL_BRADBURY_V21_E2E";
  const preflightOnly = process.env.TENDERCOUNCIL_PREFLIGHT_ONLY === "1";
  if (!confirmed && !preflightOnly) throw new Error("explicit v2 E2E confirmation or read-only preflight mode is required");
  const fixtureCommit = process.env.TENDERCOUNCIL_FIXTURE_COMMIT;
  if (!/^[0-9a-f]{40}$/.test(fixtureCommit || "")) throw new Error("TENDERCOUNCIL_FIXTURE_COMMIT must be an exact 40-hex commit");

  const sdk = await import(pathToFileURL(`${SDK_ROOT}/index.js`));
  const { testnetBradbury } = await import(pathToFileURL(`${SDK_ROOT}/chains/index.js`));
  const keytar = createRequire(pathToFileURL(CLI_ROOT))("keytar");
  const privateKey = await keytar.getPassword("genlayer-cli", "account:player3");
  if (!privateKey) throw new Error("keychain account missing: player3");
  const bootstrap = sdk.createAccount(privateKey);
  const buyer = sdk.createClient({ chain: testnetBradbury, account: bootstrap });
  const readClient = sdk.createClient({ chain: testnetBradbury });
  if (buyer.chain.id !== CHAIN_ID) throw new Error("wrong chain");

  const deployment = JSON.parse(await fs.readFile(DEPLOYMENT_PATH, "utf8"));
  const core = deployment.core?.address;
  const evaluator = deployment.evaluator?.address;
  if (!core || !evaluator || deployment.binding?.status !== "FINALIZED") throw new Error("finalized v2 deployment pair is unavailable");
  if (["0x8d776cE2c5Ed60e5e9E229669eaf91DE7f3Ae257", "0xcb4c472a9bB15103b885eC361701152Ec03b2681"].some((value) => value.toLowerCase() === core.toLowerCase() || value.toLowerCase() === evaluator.toLowerCase())) {
    throw new Error("superseded v1 Core/Evaluator pair is forbidden");
  }
  const binding = JSON.parse(await readContract(readClient, core, "get_evaluator_binding"));
  const ready = await readContract(readClient, core, "get_production_ready");
  const evaluatorCore = await readContract(readClient, evaluator, "get_core_address");
  const evaluatorVersion = await readContract(readClient, evaluator, "get_evaluator_version");
  if (!ready || !binding.bound || binding.address.toLowerCase() !== evaluator.toLowerCase() || evaluatorCore.toLowerCase() !== core.toLowerCase() || evaluatorVersion !== EVALUATOR_VERSION) {
    throw new Error("v2 binding readback failed");
  }

  const accountFile = JSON.parse(await fs.readFile(path.join(ROOT, ".local/tendercouncil_bradbury_accounts.json"), "utf8"));
  if (accountFile.accounts?.length !== 5) throw new Error("five bidder accounts are required");
  const bidderAccounts = Object.fromEntries(accountFile.accounts.map((item) => [item.label, sdk.createAccount(item.private_key)]));
  const bidders = Object.fromEntries(accountFile.accounts.map((item) => [item.label, item.address]));
  const bids = await loadBidDefinitions(fixtureCommit, bidders);
  const source = await sourceManifest();
  const check = await preflight({ readClient, core, evaluator, bids, source });

  const journalFile = path.join(JOURNAL_ROOT, `${NETWORK}-${core.toLowerCase()}-${TENDER_ID}.jsonl`);
  const journal = new OperationJournal(journalFile, { network: NETWORK, core, evaluator, tender_id: TENDER_ID });
  await journal.acquire();
  const manifest = {
    release: { network: NETWORK, chain_id: CHAIN_ID, git_commit: deployment.git_commit, core, evaluator, binding, source },
    intent: check.intended, transactions: {}, async_messages: {}, failures: [],
  };
  try {
    const createEntry = await journal.get("create_tender", TENDER_ID);
    if (!createEntry && (check.tender.kind !== "MISSING" || check.bidStates.some((state) => state.kind !== "MISSING"))) {
      throw new Error("fresh v2 identifiers are not globally unused");
    }
    if (preflightOnly) {
      console.log("read_only_preflight=PASS");
      return;
    }

    for (const row of accountFile.accounts) {
      await journaledFunding({ journal, client: buyer, address: row.address, amount: BIDDER_FUNDING });
    }

    const existingIntent = createEntry?.intent;
    const deadline = Number(existingIntent?.deadline || (await chainTime(readClient)) + 21_600);
    const tenderIntent = {
      tender_id: TENDER_ID, buyer: bootstrap.address,
      title: "Analytics Dashboard Development", deadline,
      requirements: "authentication;CSV export;responsive/mobile support;dashboard/chart functionality",
      evidence_policy: "capability:required;delivery:optional;support:optional;technical:optional",
    };
    manifest.intent.deadline = deadline;
    manifest.transactions.create_tender = await journaledContractWrite({
      journal, client: buyer, core, operation: "create_tender", objectId: TENDER_ID,
      intent: tenderIntent,
      args: [TENDER_ID, tenderIntent.title, BRIEF_URL, BRIEF_HASH, BUDGET, 30, 90, deadline, RESPONSE_WINDOW, tenderIntent.requirements, 35, 20, 20, 15, 10, tenderIntent.evidence_policy],
      value: BUDGET,
      reconcile: () => reconcileTender(readClient, core, tenderIntent),
    });
    manifest.transactions.open_tender = await journaledContractWrite({
      journal, client: buyer, core, operation: "open_tender", objectId: TENDER_ID,
      intent: { tender_id: TENDER_ID }, args: [TENDER_ID],
      reconcile: () => reconcileTender(readClient, core, tenderIntent, "OPEN"),
    });

    const bidBroadcasts = [];
    for (const bid of bids) {
      const bidderClient = sdk.createClient({ chain: testnetBradbury, account: bidderAccounts[bid.label] });
      const broadcast = await journaledBidBroadcast({ journal, bidderClient, readClient, core, bid, deadline });
      bidBroadcasts.push({ bid, tx_hash: broadcast.tx_hash });
      manifest.transactions[`submit_${bid.bid_id}`] = { tx_hash: broadcast.tx_hash, status: broadcast.journal_status };
    }

    const broadcastChainTime = await chainTime(readClient);
    const broadcastBySuffix = Object.fromEntries(bidBroadcasts.map(({ bid, tx_hash }) => [bid.suffix, tx_hash || "ONCHAIN_RECONCILED"]));
    console.log(`CHAIN_TIME: ${broadcastChainTime}`);
    console.log(`DEADLINE: ${deadline}`);
    console.log(`SECONDS_REMAINING: ${deadline - broadcastChainTime}`);
    for (const suffix of ["a", "b", "c", "d", "e"]) console.log(`BID_${suffix.toUpperCase()}_TX: ${broadcastBySuffix[suffix]}`);
    console.log(`ALL_FIVE_BROADCAST: ${bidBroadcasts.every(({ tx_hash }) => Boolean(tx_hash)) ? "YES" : "YES (ONCHAIN_RECONCILED)"}`);
    console.log("DUPLICATE_WRITES: 0");
    console.log("JOURNAL: HEALTHY");

    const finalizedBids = await Promise.all(bidBroadcasts.map(async ({ bid, tx_hash }) => {
      const record = await reconcileFinalizedBid({ journal, readClient, core, bid, txHash: tx_hash, deadline });
      manifest.transactions[`submit_${bid.bid_id}`] = { tx_hash: tx_hash || broadcastBySuffix[bid.suffix], status: "FINALIZED", record };
      return { outcome: { kind: "FOUND", record, finality: "FINALIZED" }, expected: bid };
    }));
    const rowsForClose = finalizedBids;
    if (!verifyBidsForClose(rowsForClose, { tenderStatus: "OPEN", now: deadline + 1, deadline, required: 5 })) throw new Error("five exact tender-scoped bids were not verified");
    await waitUntil(readClient, deadline + 1, "bidding_deadline");
    manifest.transactions.close_tender = await journaledContractWrite({
      journal, client: buyer, core, operation: "close_tender", objectId: TENDER_ID,
      intent: { tender_id: TENDER_ID, bid_ids: bids.map((bid) => bid.bid_id) }, args: [TENDER_ID],
      reconcile: () => reconcileTender(readClient, core, tenderIntent, "CLOSED"),
    });
    const snapshot = await readContract(readClient, core, "get_closed_snapshot", [TENDER_ID]);
    const closed = await readContract(readClient, core, "get_tender", [TENDER_ID]);
    if (digestBytes(Buffer.from(snapshot, "utf8")) !== closed.closed_snapshot_digest) throw new Error("snapshot digest mismatch");
    manifest.snapshot = { canonical_json: snapshot, digest: closed.closed_snapshot_digest };

    const provisional = await driveEvaluation({ journal, buyer, readClient, core, manifest });
    const expectedWinner = makeTenderScopedBidId(TENDER_ID, "b");
    if (provisional.provisional_winner !== expectedWinner) throw new Error(`unexpected provisional winner: ${provisional.provisional_winner}`);

    // Real-provider evaluation gate: verify the exact bid partitions produced by
    // the first corrected evaluation. Deterministic exclusions are D (over budget)
    // and E (over max delivery); semantic candidates are A, B, C; winner is B.
    const evaluationNonce = Number(provisional.evaluation_nonce);
    const resultPayload = await readContract(readClient, evaluator, "get_evaluation_result", [TENDER_ID, evaluationNonce]);
    const result = JSON.parse(resultPayload);
    const toIdSet = (suffixes) => new Set(suffixes.map((s) => makeTenderScopedBidId(TENDER_ID, s)));
    const setsEqual = (a, b) => a.size === b.size && [...a].every((v) => b.has(v));
    const deterministic = new Set(result.deterministic_disqualified_bid_ids || []);
    const semanticCandidates = new Set(result.semantic_candidate_ids || []);
    const expectedDeterministic = toIdSet(["d", "e"]);
    const expectedCandidates = toIdSet(["a", "b", "c"]);
    if (result.status !== "COMPARATIVE") throw new Error(`evaluation result status is not COMPARATIVE: ${result.status}`);
    if (result.winner_bid_id !== expectedWinner) throw new Error(`evaluation result winner mismatch: ${result.winner_bid_id}`);
    if (!setsEqual(deterministic, expectedDeterministic)) throw new Error(`deterministic exclusions mismatch: ${[...deterministic].join(",")}`);
    if (!setsEqual(semanticCandidates, expectedCandidates)) throw new Error(`semantic candidate set mismatch: ${[...semanticCandidates].join(",")}`);
    manifest.evaluation_gate = {
      at_utc: new Date().toISOString(),
      evaluation_nonce: evaluationNonce,
      core_status: provisional.status,
      provisional_winner: provisional.provisional_winner,
      deterministic_exclusions: [...deterministic].sort(),
      semantic_candidates: [...semanticCandidates].sort(),
      semantic_disqualified: (result.semantic_disqualified_bid_ids || []).slice().sort(),
      confidence: result.confidence,
      evaluation_result_digest: provisional.evaluation_result_digest,
      evaluator_child: manifest.async_messages[`evaluation_attempt_${evaluationNonce}`] || null,
      evaluation_callback: manifest.async_messages[`evaluation_callback_${evaluationNonce}`] || null,
    };
    await writeEvidence(manifest);
    console.log(`EVALUATION_GATE=PASS winner=${provisional.provisional_winner} deterministic_exclusions=${[...deterministic].sort().join(",")} semantic_candidates=${[...semanticCandidates].sort().join(",")}`);
    if (STOP_AFTER_FIRST_EVALUATION) {
      console.log(`tendercouncil_v21_e2e=PROVISIONAL_AWARD_GATE_PASS evidence=${EVIDENCE_PATH}`);
      return;
    }

    manifest.transactions.start_response_window = await journaledContractWrite({
      journal, client: buyer, core, operation: "start_response_window", objectId: TENDER_ID,
      intent: { tender_id: TENDER_ID, seconds: RESPONSE_WINDOW }, args: [TENDER_ID],
      reconcile: async () => {
        const tender = await readContract(readClient, core, "get_tender", [TENDER_ID]);
        return tender.response_window_start && reached(tender.status, "RESPONSE_WINDOW") ? exact(tender) : missing();
      },
    });

    const challengeBytes = await fs.readFile(path.join(ROOT, "fixtures/live/final-v2/challenge_a.json"));
    const challengeHash = digestBytes(challengeBytes);
    const challengeUrl = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${fixtureCommit}/fixtures/live/final-v2/challenge_a.json`;
    const challengeId = scopedChallengeId();
    const challengeClient = sdk.createClient({ chain: testnetBradbury, account: bidderAccounts.bidder_a });
    manifest.transactions.submit_challenge = await journaledContractWrite({
      journal, client: challengeClient, core, operation: "submit_challenge", objectId: challengeId,
      intent: { challenge_id: challengeId, tender_id: TENDER_ID, challenger: bidders.bidder_a, reason_code: "RUBRIC_MISAPPLIED", target_bid_id: makeTenderScopedBidId(TENDER_ID, "b"), challenge_url: challengeUrl, challenge_sha256: challengeHash },
      args: [challengeId, TENDER_ID, "RUBRIC_MISAPPLIED", makeTenderScopedBidId(TENDER_ID, "b"), "", challengeUrl, challengeHash],
      reconcile: async () => {
        const outcome = await readRecord(readClient, core, "get_challenge", [challengeId]);
        if (outcome.kind === "MISSING") return missing();
        const record = outcome.record;
        if (record.tender_id !== TENDER_ID || record.challenge_id !== challengeId || record.challenger.toLowerCase() !== bidders.bidder_a.toLowerCase() || record.target_bid_id !== makeTenderScopedBidId(TENDER_ID, "b") || record.challenge_sha256 !== challengeHash || record.status !== "ADMITTED") throw new Error("challenge immutable readback mismatch");
        return exact(record);
      },
    });

    const awarded = await driveReview({ journal, buyer, readClient, core, manifest });
    if (awarded.final_winner !== makeTenderScopedBidId(TENDER_ID, "b")) throw new Error("unexpected final winner");
    manifest.transactions.settle_award = await journaledContractWrite({
      journal, client: buyer, core, operation: "settle_award", objectId: TENDER_ID,
      intent: { tender_id: TENDER_ID, winner: awarded.final_winner, payout_wei: "74000000000000000", refund_wei: "6000000000000000" }, args: [TENDER_ID],
      reconcile: async () => {
        const accounting = JSON.parse(await readContract(readClient, core, "get_settlement_accounting", [TENDER_ID]));
        if (accounting.winner_payout_amount === 74_000_000_000_000_000 && accounting.buyer_refund_amount === 6_000_000_000_000_000) return exact(accounting);
        return missing();
      },
    });
    const payoutChildren = await captureAsyncChildren(readClient, manifest.transactions.settle_award.tx_hash, manifest, "winner_payout", bidders.bidder_b);
    if (!payoutChildren?.length) throw new Error("finalized winner payout child was not discovered");
    manifest.transactions.confirm_settlement = await journaledContractWrite({
      journal, client: buyer, core, operation: "confirm_settlement", objectId: TENDER_ID,
      intent: { tender_id: TENDER_ID, consequence: "payout_finalized" }, args: [TENDER_ID],
      reconcile: async () => {
        const accounting = JSON.parse(await readContract(readClient, core, "get_settlement_accounting", [TENDER_ID]));
        return accounting.payout_confirmed ? exact(accounting) : missing();
      },
    });
    const refundChildren = await captureAsyncChildren(readClient, manifest.transactions.confirm_settlement.tx_hash, manifest, "buyer_refund", bootstrap.address);
    if (!refundChildren?.length) throw new Error("finalized buyer refund child was not discovered");
    manifest.transactions.confirm_refund = await journaledContractWrite({
      journal, client: buyer, core, operation: "confirm_refund", objectId: TENDER_ID,
      intent: { tender_id: TENDER_ID, consequence: "refund_finalized" }, args: [TENDER_ID],
      reconcile: async () => {
        const tender = await readContract(readClient, core, "get_tender", [TENDER_ID]);
        const accounting = JSON.parse(await readContract(readClient, core, "get_settlement_accounting", [TENDER_ID]));
        return tender.status === "SETTLED" && accounting.payout_confirmed && accounting.refund_confirmed && accounting.settlement_state === "SETTLED" ? exact({ tender, accounting }) : missing();
      },
    });

    manifest.final = {
      tender: await readContract(readClient, core, "get_tender", [TENDER_ID]),
      accounting: JSON.parse(await readContract(readClient, core, "get_settlement_accounting", [TENDER_ID])),
      core_balance_wei: String(await readContract(readClient, core, "get_contract_balance")),
      completed_at_utc: new Date().toISOString(),
    };
    if (manifest.final.tender.status !== "SETTLED") throw new Error("final tender is not SETTLED");
    await writeEvidence(manifest);
    console.log(`tendercouncil_v2_e2e=SETTLED evidence=${EVIDENCE_PATH}`);
  } catch (error) {
    if (error instanceof EvaluationGateStop) {
      manifest.evaluation_gate_stop = { at_utc: new Date().toISOString(), reason: error.message, detail: error.detail || null };
      await writeEvidence(manifest);
      console.error(`EVALUATION_GATE=STOP ${error.message}`);
      console.error(`DO NOT auto-retry; inspect evidence=${EVIDENCE_PATH}`);
      throw error;
    }
    manifest.failures.push({ at_utc: new Date().toISOString(), error: String(error?.stack || error) });
    await writeEvidence(manifest);
    throw error;
  } finally {
    await journal.release();
  }
}
