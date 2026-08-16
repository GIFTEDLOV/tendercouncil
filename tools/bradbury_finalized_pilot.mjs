/* One canonical, crash-safe, no-challenge TenderCouncil v2.1 Bradbury pilot. */
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  OperationJournal,
  canonicalJson,
  executeJournaledWrite,
  withReadRetry,
} from "./bradbury_runner_lib.mjs";
import { resolveGenlayerModulePaths } from "./genlayer_module_paths.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { sdkRoot: SDK_ROOT, cliEntry: CLI_ROOT } = resolveGenlayerModulePaths();
const NETWORK = "testnet-bradbury";
const CHAIN_ID = 4221;
const CORE = "0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd";
const EVALUATOR = "0x023AB3434761715a531884Ca0852aC14beE03acE";
const VERSION = "tendercouncil.evaluator.v2.1";
const CODE_HASH = "sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b";
const PILOT_FIXTURE_COMMIT = "81b5656a311cf0eb83b651422c848d11b5bde47e";
const EXPECTATION_COMMIT = "d18f1e9";
const TENDER_ID = "TENDER_PILOT_V21_20260816T164802Z";
const BID_A_ID = `${TENDER_ID}-bid-a`;
const BID_B_ID = `${TENDER_ID}-bid-b`;
const BUDGET = 50_000_000_000_000_000n;
const A_PRICE = 32_000_000_000_000_000n;
const B_PRICE = 39_000_000_000_000_000n;
const RESPONSE_WINDOW = 600;
const BRIEF_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/bfddc6c4c2fcd16431af6da797213c0f42ade4fb/fixtures/live/blobs/brief.json";
const BRIEF_HASH = "sha256:44bb3d24956a4ea2d9a8828afc7f6cde822c7f0c06708aea3fa9f7d365a33f8e";
const A_PROPOSAL_URL = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${PILOT_FIXTURE_COMMIT}/fixtures/live-pilot-v21/bidder-a-proposal.json`;
const B_PROPOSAL_URL = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${PILOT_FIXTURE_COMMIT}/fixtures/live-pilot-v21/bidder-b-proposal.json`;
const A_PROPOSAL_HASH = "sha256:234468225a374da5c9cb2486338f2c9e4826dc7613a87a46ba0136d3827336c3";
const B_PROPOSAL_HASH = "sha256:9278303248bd3b410236f35554863fa42c154b40a282743fe3e06c718384bfdd";
const A_EVIDENCE_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/bfddc6c4c2fcd16431af6da797213c0f42ade4fb/fixtures/live/blobs/a_capability.json";
const B_EVIDENCE_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/bfddc6c4c2fcd16431af6da797213c0f42ade4fb/fixtures/live/blobs/b_capability.json";
const A_EVIDENCE_HASH = "sha256:83366c33c2cf2257f0a920f6cc6a51c61dfdf7cae7256cda922f759aa36cd8de";
const B_EVIDENCE_HASH = "sha256:50ccede1e2904873ce72abcfb8c6b7c277ae5b782dd45d38ed48e86a25a56ce5";
const JOURNAL_FILE = path.join(ROOT, "artifacts/tender_council_bradbury_v21_finalized_pilot_journal.json");
const OP_JOURNAL_FILE = path.join(ROOT, `.local/bradbury-journal/${NETWORK}-${CORE.toLowerCase()}-${TENDER_ID}.jsonl`);
const TRANSIENT = /fetch failed|ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|timeout|network|429|500|502|503|504|socket|connection/i;

function safe(value) {
  return JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
}
function sha256Bytes(bytes) { return `sha256:${crypto.createHash("sha256").update(bytes).digest("hex")}`; }
function sha256Text(value) { return sha256Bytes(Buffer.from(value, "utf8")); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function statusName(tx) { return tx?.statusName || tx?.status || "UNKNOWN"; }
function resultName(tx) { return tx?.resultName || tx?.result_name || tx?.result || "UNKNOWN"; }
function executionName(tx) {
  return tx?.txExecutionResultName || tx?.tx_execution_result_name
    || tx?.txExecutionResult || tx?.tx_execution_result || "UNKNOWN";
}
function isHash(value) { return typeof value === "string" && /^0x[0-9a-f]{64}$/i.test(value); }
function exact(value) { return { state: "EXACT", digest: sha256Text(canonicalJson(safe(value))), value }; }
function missing() { return { state: "MISSING" }; }
function logReadRetry(event) { console.log(`read_retry=${JSON.stringify(event)}`); }
async function retryRead(name, operation) {
  return withReadRetry(operation, { operation: name, logger: logReadRetry, isTransient: (error) => TRANSIENT.test(String(error?.message || error)) });
}

class PilotJournal {
  constructor(file, metadata) {
    this.file = file;
    this.metadata = metadata;
    this.state = { version: 1, ...metadata, events: [], async_observations: [], errors: [] };
  }
  async load() {
    try {
      this.state = JSON.parse(await fs.readFile(this.file, "utf8"));
      if (this.state.tender_id !== TENDER_ID || this.state.core?.toLowerCase() !== CORE.toLowerCase()) throw new Error("pilot journal context mismatch");
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
  }
  async persist() {
    await fs.mkdir(path.dirname(this.file), { recursive: true });
    const temp = `${this.file}.tmp-${process.pid}`;
    await fs.writeFile(temp, `${JSON.stringify(this.state, null, 2)}\n`, "utf8");
    await fs.rename(temp, this.file);
  }
  async event(event) {
    this.state.events.push({ sequence: this.state.events.length + 1, observed_at_utc: new Date().toISOString(), ...safe(event) });
    await this.persist();
  }
  async asyncObservation(observation) {
    this.state.async_observations.push({ observed_at_utc: new Date().toISOString(), ...safe(observation) });
    await this.persist();
  }
  async error(error, context = {}) {
    this.state.errors.push({ observed_at_utc: new Date().toISOString(), error: String(error?.stack || error), ...safe(context) });
    await this.persist();
  }
  async final(value) { this.state.final = safe(value); await this.persist(); }
}

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
function isMissing(error, functionName) {
  const joined = [error?.shortMessage, error?.message, String(error)].filter(Boolean).map(String).join(" ");
  const haystack = `${joined} ${decodeVmBytes(joined)}`;
  return ({ get_tender: /tender does not exist/i, get_bid: /bid does not exist/i }[functionName] || /record does not exist/i).test(haystack);
}
async function readContract(client, address, functionName, args = []) {
  return safe(await retryRead(`view:${functionName}`, () => client.readContract({ address, functionName, args, blockTag: "finalized" })));
}
async function readRecord(client, address, functionName, args = []) {
  return retryRead(`classified:${functionName}`, async () => {
    try { return { kind: "FOUND", record: await readContract(client, address, functionName, args) }; }
    catch (error) { if (isMissing(error, functionName)) return { kind: "MISSING" }; throw error; }
  });
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
      const consensus = String(tx?.consensusStatus || tx?.consensus || resultName(tx));
      if (requireAgree && consensus && !["AGREE", "UNKNOWN"].includes(consensus)) throw new Error(`transaction ${hash} finalized ${consensus}`);
      return { hash, finality: "FINALIZED", accepted, finalized: safe(tx) };
    }
    if (["UNDETERMINED", "CANCELED", "REVERTED"].includes(status)) throw new Error(`transaction ${hash} terminated as ${status}`);
    await sleep(10_000);
  }
  throw new Error(`transaction ${hash} did not finalize within the bounded poll window`);
}

async function coreState(readClient) {
  const tender = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]);
  const state = { tender: tender.kind === "FOUND" ? tender.record : null };
  if (state.tender) {
    state.accounting = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID]));
    state.core_balance_wei = String(await readContract(readClient, CORE, "get_contract_balance"));
  }
  return state;
}
async function txObservation(client, hash) {
  if (!hash) return null;
  const tx = await retryRead("getTransaction:final", () => client.getTransaction({ hash }));
  return {
    tx_hash: hash,
    status: statusName(tx), resultName: resultName(tx), execution: executionName(tx),
    consensus: tx?.consensusStatus || tx?.consensus || null,
    validator_split: tx?.lastRound ? { votes: tx.lastRound.validatorVotesName || null, result_hashes: tx.lastRound.validatorResultHash || null, validators: tx.lastRound.roundValidators || null } : null,
    transaction: safe(tx),
  };
}

async function runWrite({ opJournal, pilot, client, readClient, operation, objectId, actor, args, value = 0n, reconcile }) {
  const before = await coreState(readClient);
  const intent = { operation, object_id: objectId, actor, args: safe(args), value_wei: String(value) };
  await pilot.event({ kind: "WRITE_INTENT", ...intent, core_state_before: before });
  try {
    await executeJournaledWrite({
      journal: opJournal, operation, objectId, intent,
      reconcile,
      broadcast: () => client.writeContract({ account: client.account, address: CORE, functionName: operation, args, value, leaderOnly: false }),
      poll: (hash) => waitGenlayerFinal(client, hash, true),
      verify: reconcile,
    });
    const entry = await opJournal.get(operation, objectId);
    if (!entry || entry.status !== "FINALIZED") throw new Error(`${operation} did not reach FINALIZED in the durable operation journal`);
    const after = await coreState(readClient);
    const tx = await txObservation(readClient, entry.tx_hash);
    await pilot.event({ kind: "WRITE_FINALIZED", ...intent, tx_hash: entry.tx_hash, broadcast_timestamp: entry.recorded_at, final_status: entry.status, transaction: tx, core_state_after: after });
    return { entry, after, tx };
  } catch (error) {
    await pilot.error(error, { kind: "WRITE_UNKNOWN_OR_FAILED", ...intent, core_state_observation: await coreState(readClient).catch((readError) => ({ read_error: String(readError) })) });
    throw error;
  }
}

function tenderExpected({ buyer, deadline }) {
  return {
    tender_id: TENDER_ID, buyer, title: "Analytics Dashboard Development",
    brief_url: BRIEF_URL, brief_sha256: BRIEF_HASH, max_budget_wei: BUDGET.toString(),
    max_delivery_days: 30, min_support_days: 90, bidding_deadline: deadline,
    response_window_seconds: RESPONSE_WINDOW,
    requirements: "authentication;CSV export;responsive/mobile support;dashboard/chart functionality",
    evidence_policy: "capability:required;delivery:optional;support:optional;technical:optional",
  };
}
function tenderMatches(tender, expected, target = null) {
  for (const [field, wanted] of Object.entries(expected)) {
    const actual = field === "buyer" ? String(tender[field]).toLowerCase() : String(tender[field]);
    const value = field === "buyer" ? String(wanted).toLowerCase() : String(wanted);
    if (actual !== value) throw new Error(`tender immutable field mismatch: ${field}: ${actual} != ${value}`);
  }
  return !target || tender.status === target;
}
function bidIntent({ id, bidder, price, delivery, support, proposalUrl, proposalHash, evidenceId, evidenceUrl, evidenceHash }) {
  return {
    bid_id: id, tender_id: TENDER_ID, bidder, price_wei: price.toString(), delivery_days: delivery,
    support_days: support, proposal_url: proposalUrl, proposal_sha256: proposalHash,
    evidence_commitments: `${evidenceId}|CAPABILITY|capability|1|${evidenceUrl}|${evidenceHash}`,
    schema_version: "tendercouncil.bid.v1",
  };
}
function bidMatches(record, expected) {
  for (const field of ["bid_id", "tender_id", "proposal_url", "proposal_sha256", "evidence_commitments", "schema_version"]) {
    if (String(record[field]) !== String(expected[field])) throw new Error(`bid immutable field mismatch ${expected.bid_id}: ${field}`);
  }
  if (String(record.bidder).toLowerCase() !== expected.bidder.toLowerCase()) throw new Error(`bidder mismatch ${expected.bid_id}`);
  if (String(record.price_wei) !== expected.price_wei || Number(record.delivery_days) !== expected.delivery_days || Number(record.support_days) !== expected.support_days) throw new Error(`commercial field mismatch ${expected.bid_id}`);
  return exact(record);
}
async function waitUntil(readClient, timestamp, label) {
  while (true) {
    const now = await chainTime(readClient);
    if (now > timestamp) return now;
    console.log(`${label}_remaining_seconds=${timestamp - now}`);
    await sleep(15_000);
  }
}
async function waitBalance(readClient, expected, label) {
  for (let attempt = 1; attempt <= 240; attempt += 1) {
    const actual = String(await readContract(readClient, CORE, "get_contract_balance"));
    if (actual === String(expected)) return actual;
    if (attempt % 4 === 0) console.log(`${label}_balance=${actual}_expected=${expected}`);
    await sleep(15_000);
  }
  throw new Error(`${label} balance delta was not observable: expected ${expected}`);
}
async function findAsyncChildren(client, parentHash, expectedRecipient) {
  if (!parentHash) return [];
  const parent = await retryRead("async-parent", () => client.getTransaction({ hash: parentHash }));
  const fromBlock = BigInt(parent?.readStateBlockRange?.proposalBlock || parent?.proposalBlock || 0);
  const latest = await retryRead("eth_getBlockByNumber", () => client.getBlock({ blockTag: "latest" }));
  const topic = "0xdab9102861c7483a187584d6371d88316f005af507982ccf95c110879f3ed5a5";
  const logs = await retryRead("eth_getLogs", () => client.request({ method: "eth_getLogs", params: [{ address: client.chain.consensusMainContract.address, fromBlock: `0x${fromBlock.toString(16)}`, toBlock: `0x${BigInt(latest.number).toString(16)}`, topics: [topic] }] }));
  const result = [];
  for (const log of logs || []) {
    const hash = log?.topics?.[1];
    if (!isHash(hash)) continue;
    const tx = await retryRead("async-child", () => client.getTransaction({ hash }));
    if (String(tx?.sender || "").toLowerCase() !== String(parent?.recipient || "").toLowerCase()) continue;
    if (expectedRecipient && String(tx?.recipient || "").toLowerCase() !== expectedRecipient.toLowerCase()) continue;
    if (tx?.createdTimestamp && parent?.createdTimestamp && BigInt(tx.createdTimestamp) < BigInt(parent.createdTimestamp)) continue;
    result.push({ hash, transaction: safe(tx) });
  }
  return result;
}
async function observeAsync(pilot, client, parentHash, label, expectedRecipient) {
  const children = await findAsyncChildren(client, parentHash, expectedRecipient);
  if (children.length) await pilot.asyncObservation({ label, parent_hash: parentHash, children });
  return children;
}

async function main() {
  const sdk = await import(pathToFileURL(`${SDK_ROOT}/index.js`));
  const { testnetBradbury } = await import(pathToFileURL(`${SDK_ROOT}/chains/index.js`));
  const keytar = createRequire(pathToFileURL(CLI_ROOT))("keytar");
  const buyerKey = await keytar.getPassword("genlayer-cli", "account:player3");
  if (!buyerKey) throw new Error("keychain account player3 missing");
  const buyerAccount = sdk.createAccount(buyerKey);
  const readClient = sdk.createClient({ chain: testnetBradbury });
  const buyer = sdk.createClient({ chain: testnetBradbury, account: buyerAccount });
  if (readClient.chain.id !== CHAIN_ID) throw new Error("wrong chain: expected Bradbury 4221");
  const accountRows = JSON.parse(await fs.readFile(path.join(ROOT, ".local/tendercouncil_bradbury_accounts.json"), "utf8")).accounts || [];
  const rowA = accountRows.find((row) => row.label === "bidder_a");
  const rowB = accountRows.find((row) => row.label === "bidder_b");
  if (!rowA || !rowB) throw new Error("fewer than three configured actors: bidder_a/bidder_b unavailable");
  const bidderAAccount = sdk.createAccount(rowA.private_key);
  const bidderBAccount = sdk.createAccount(rowB.private_key);
  const bidderA = sdk.createClient({ chain: testnetBradbury, account: bidderAAccount });
  const bidderB = sdk.createClient({ chain: testnetBradbury, account: bidderBAccount });
  if (bidderAAccount.address.toLowerCase() !== rowA.address.toLowerCase() || bidderBAccount.address.toLowerCase() !== rowB.address.toLowerCase()) throw new Error("configured actor address mismatch");
  const pilot = new PilotJournal(JOURNAL_FILE, { network: NETWORK, chain_id: CHAIN_ID, core: CORE, evaluator: EVALUATOR, evaluator_version: VERSION, tender_id: TENDER_ID, pilot_id: TENDER_ID, pilot_fixture_commit: PILOT_FIXTURE_COMMIT, expectation_commit: EXPECTATION_COMMIT, actors: { buyer: buyerAccount.address, bidder_a: rowA.address, bidder_b: rowB.address } });
  await pilot.load();
  const opJournal = new OperationJournal(OP_JOURNAL_FILE, { network: NETWORK, core: CORE, evaluator: EVALUATOR, tender_id: TENDER_ID });
  await opJournal.acquire();
  try {
    const binding = JSON.parse(await readContract(readClient, CORE, "get_evaluator_binding"));
    const ready = await readContract(readClient, CORE, "get_production_ready");
    const evaluatorCore = await readContract(readClient, EVALUATOR, "get_core_address");
    const evaluatorVersion = await readContract(readClient, EVALUATOR, "get_evaluator_version");
    const preflight = { chain_id: readClient.chain.id, production_ready: ready, binding, evaluator_core: evaluatorCore, evaluator_version: evaluatorVersion, core_balance_before: String(await readContract(readClient, CORE, "get_contract_balance")), observed_at_utc: new Date().toISOString() };
    if (!ready || !binding.bound || binding.address.toLowerCase() !== EVALUATOR.toLowerCase() || binding.version !== VERSION || binding.evaluator_code_hash !== CODE_HASH || evaluatorCore.toLowerCase() !== CORE.toLowerCase() || evaluatorVersion !== VERSION) throw new Error(`production binding readback mismatch: ${JSON.stringify(preflight)}`);
    await pilot.event({ kind: "READ_ONLY_PREFLIGHT", ...preflight });
    const existingTender = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]);
    if (!await opJournal.get("create_tender", TENDER_ID) && existingTender.kind !== "MISSING") throw new Error("fresh pilot tender ID is already used");
    for (const id of [BID_A_ID, BID_B_ID]) {
      const existingBid = await readRecord(readClient, CORE, "get_bid", [id]);
      if (!await opJournal.get("submit_bid", id) && existingBid.kind !== "MISSING") throw new Error(`fresh pilot bid ID is already used: ${id}`);
    }
    const balances = { buyer: String(await readClient.getBalance({ address: buyerAccount.address, blockTag: "latest" })), bidder_a: String(await readClient.getBalance({ address: rowA.address, blockTag: "latest" })), bidder_b: String(await readClient.getBalance({ address: rowB.address, blockTag: "latest" })) };
    if (BigInt(balances.buyer) <= BUDGET || BigInt(balances.bidder_a) === 0n || BigInt(balances.bidder_b) === 0n) throw new Error(`required funded actors unavailable: ${JSON.stringify({ addresses: { buyer: buyerAccount.address, bidder_a: rowA.address, bidder_b: rowB.address }, balances })}`);
    await pilot.event({ kind: "ACTOR_FUNDING_READBACK", balances });

    const existingIntent = (await opJournal.get("create_tender", TENDER_ID))?.intent;
    const deadline = Number(existingIntent?.deadline || existingIntent?.args?.[7] || (await chainTime(readClient)) + 3600);
    const tenderExpectedValues = tenderExpected({ buyer: buyerAccount.address, deadline });
    const createArgs = [TENDER_ID, "Analytics Dashboard Development", BRIEF_URL, BRIEF_HASH, BUDGET, 30, 90, deadline, RESPONSE_WINDOW, tenderExpectedValues.requirements, 35, 20, 20, 15, 10, tenderExpectedValues.evidence_policy];
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "create_tender", objectId: TENDER_ID, actor: buyerAccount.address, args: createArgs, value: BUDGET, reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]); if (outcome.kind === "MISSING") return missing(); if (!tenderMatches(outcome.record, tenderExpectedValues)) return missing(); return exact(outcome.record); } });
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "open_tender", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]); return outcome.kind === "FOUND" && tenderMatches(outcome.record, tenderExpectedValues, "OPEN") ? exact(outcome.record) : missing(); } });

    const bidA = bidIntent({ id: BID_A_ID, bidder: rowA.address, price: A_PRICE, delivery: 20, support: 180, proposalUrl: A_PROPOSAL_URL, proposalHash: A_PROPOSAL_HASH, evidenceId: "pilot-a-capability", evidenceUrl: A_EVIDENCE_URL, evidenceHash: A_EVIDENCE_HASH });
    const bidB = bidIntent({ id: BID_B_ID, bidder: rowB.address, price: B_PRICE, delivery: 25, support: 120, proposalUrl: B_PROPOSAL_URL, proposalHash: B_PROPOSAL_HASH, evidenceId: "pilot-b-capability", evidenceUrl: B_EVIDENCE_URL, evidenceHash: B_EVIDENCE_HASH });
    for (const [bid, client] of [[bidA, bidderA], [bidB, bidderB]]) {
      const args = [bid.bid_id, bid.tender_id, BigInt(bid.price_wei), bid.delivery_days, bid.support_days, bid.proposal_url, bid.proposal_sha256, bid.evidence_commitments, bid.schema_version];
      await runWrite({ opJournal, pilot, client, readClient, operation: "submit_bid", objectId: bid.bid_id, actor: bid.bidder, args, reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_bid", [bid.bid_id]); if (outcome.kind === "MISSING") return missing(); return bidMatches(outcome.record, bid); } });
    }
    await waitUntil(readClient, deadline, "bidding_deadline");
    const snapshotBefore = await coreState(readClient);
    const bidRows = { a: await readContract(readClient, CORE, "get_bid", [BID_A_ID]), b: await readContract(readClient, CORE, "get_bid", [BID_B_ID]) };
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "close_tender", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]); return outcome.kind === "FOUND" && tenderMatches(outcome.record, tenderExpectedValues, "CLOSED") ? exact(outcome.record) : missing(); } });
    const closedTender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    const snapshot = await readContract(readClient, CORE, "get_closed_snapshot", [TENDER_ID]);
    const snapshotDigest = sha256Text(snapshot);
    if (snapshotDigest !== closedTender.closed_snapshot_digest) throw new Error(`closed snapshot digest mismatch: computed=${snapshotDigest} stored=${closedTender.closed_snapshot_digest}`);
    const snapshotParsed = JSON.parse(snapshot);
    if (snapshotParsed.bids.length !== 2 || snapshotParsed.bids.filter((bid) => [BID_A_ID, BID_B_ID].includes(bid.bid_id)).length !== 2) throw new Error("closed snapshot does not contain both intended bids exactly once");
    await pilot.event({ kind: "CLOSED_SNAPSHOT", snapshot, snapshot_digest: snapshotDigest, bid_ordering: snapshotParsed.bids.map((bid) => bid.bid_id), core_state_after: await coreState(readClient), pre_close_state: snapshotBefore, bid_readbacks: bidRows });
    const expectedText = await fs.readFile(path.join(ROOT, "fixtures/live-pilot-v21/EXPECTED.md"), "utf8");
    if (!expectedText.includes(PILOT_FIXTURE_COMMIT) || !expectedText.includes(BID_A_ID) || !expectedText.includes(BID_B_ID) || !expectedText.includes("Expected winner: **Bid A**")) throw new Error("precommitted EXPECTED.md readback failed");
    await pilot.event({ kind: "PRECOMMITTED_EXPECTATION", fixture_commit: PILOT_FIXTURE_COMMIT, expectation_commit: EXPECTATION_COMMIT, expected_winner: BID_A_ID, expected_escrow_wei: BUDGET.toString(), expected_winning_quote_wei: A_PRICE.toString(), expected_remainder_wei: (BUDGET - A_PRICE).toString() });

    let tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    while (tender.status !== "PROVISIONAL_AWARD") {
      if (tender.status === "CLOSED") {
        const nonce = Number(tender.evaluation_nonce) + 1;
        await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "start_evaluation", objectId: `${TENDER_ID}#${nonce}`, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const current = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); return Number(current.evaluation_nonce) >= nonce && current.status !== "CLOSED" ? exact(current) : missing(); } });
        tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
        continue;
      }
      if (tender.status === "EVALUATION_RETRYABLE") {
        const nonce = Number(tender.evaluation_nonce) + 1;
        await pilot.event({ kind: "EVALUATION_RETRYABLE_OBSERVED", evaluation_nonce: nonce - 1, snapshot_digest: tender.closed_snapshot_digest, status: tender.status });
        await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "retry_evaluation", objectId: `${TENDER_ID}#${nonce}`, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const current = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); return Number(current.evaluation_nonce) >= nonce && current.status !== "EVALUATION_RETRYABLE" ? exact(current) : missing(); } });
        tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
        continue;
      }
      if (tender.status === "EVALUATING") {
        const nonce = Number(tender.evaluation_nonce);
        const op = await opJournal.get(nonce === 1 ? "start_evaluation" : "retry_evaluation", `${TENDER_ID}#${nonce}`);
        const jobs = await observeAsync(pilot, readClient, op?.tx_hash, `evaluation_attempt_${nonce}`, EVALUATOR);
        if (jobs[0]) await observeAsync(pilot, readClient, jobs[0].hash, `evaluation_callback_${nonce}`, CORE);
        let evaluatorResult = null;
        try { evaluatorResult = JSON.parse(await readContract(readClient, EVALUATOR, "get_evaluation_result", [TENDER_ID, nonce])); } catch (error) { if (!/does not exist|missing|not found/i.test(String(error))) throw error; }
        await pilot.event({ kind: "EVALUATION_RECONCILIATION", evaluation_nonce: nonce, core_status: tender.status, evaluation_context: JSON.parse(await readContract(readClient, CORE, "get_evaluation_context", [TENDER_ID])), evaluator_result: evaluatorResult, async_job_observed: jobs.length > 0 });
        const now = await chainTime(readClient);
        if (now <= Number(tender.evaluation_timeout_at)) { await sleep(30_000); tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); continue; }
        throw new Error(`evaluation remained EVALUATING past timeout without an explicit retryable callback: nonce=${nonce}`);
      }
      throw new Error(`unexpected evaluation state: ${tender.status}`);
    }
    tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    const evaluationNonce = Number(tender.evaluation_nonce);
    const evaluationPayload = await readContract(readClient, EVALUATOR, "get_evaluation_result", [TENDER_ID, evaluationNonce]);
    const evaluationResult = JSON.parse(evaluationPayload);
    const resultDigest = sha256Text(evaluationPayload);
    if (resultDigest !== tender.evaluation_result_digest || evaluationResult.status !== "COMPARATIVE" || ![BID_A_ID, BID_B_ID].includes(evaluationResult.winner_bid_id)) throw new Error("successful evaluation result correlation or winner validation failed");
    await pilot.event({ kind: "EVALUATION_RESULT", evaluation_nonce: evaluationNonce, snapshot_digest: tender.closed_snapshot_digest, evaluation_result_digest: resultDigest, expected_winner: BID_A_ID, actual_winner: evaluationResult.winner_bid_id, expected_winner_match: evaluationResult.winner_bid_id === BID_A_ID, result: evaluationResult });
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "start_response_window", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const current = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); return current.status === "RESPONSE_WINDOW" ? exact(current) : missing(); } });
    tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    await pilot.event({ kind: "RESPONSE_WINDOW_STARTED", start: Number(tender.response_window_start), end: Number(tender.response_window_end), duration_seconds: Number(tender.response_window_end) - Number(tender.response_window_start), challenge_count: 0 });
    await waitUntil(readClient, Number(tender.response_window_end), "response_window");
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "advance_after_response", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const current = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); return current.status === "AWARDED" ? exact(current) : missing(); } });
    tender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    if (tender.final_winner !== tender.provisional_winner || tender.final_winner !== evaluationResult.winner_bid_id) throw new Error("no-challenge final winner mismatch");
    const winnerBid = await readContract(readClient, CORE, "get_bid", [tender.final_winner]);
    await pilot.event({ kind: "FINAL_AWARD", final_winner: tender.final_winner, winner_bidder: winnerBid.bidder, winning_quote_wei: String(winnerBid.price_wei), result_digest: tender.evaluation_result_digest, challenge_branch_run: false });

    const accountingBefore = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID]));
    const balanceBefore = String(await readContract(readClient, CORE, "get_contract_balance"));
    const payout = BigInt(winnerBid.price_wei);
    const remainder = BigInt(accountingBefore.escrow_deposited) - payout;
    if (BigInt(accountingBefore.escrow_deposited) !== payout + remainder || remainder < 0n) throw new Error("independent settlement accounting precheck failed");
    await pilot.event({ kind: "SETTLEMENT_PRECHECK", initial_escrow_wei: String(accountingBefore.escrow_deposited), winning_quote_wei: payout.toString(), expected_buyer_remainder_wei: remainder.toString(), core_balance_before_wei: balanceBefore, accounting: accountingBefore });
    const settle = await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "settle_award", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const current = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); const accounting = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID])); return current.status === "SETTLEMENT_PENDING" && String(accounting.winner_payout_amount) === payout.toString() && String(accounting.buyer_refund_amount) === remainder.toString() ? exact({ current, accounting }) : missing(); } });
    await observeAsync(pilot, readClient, settle.entry.tx_hash, "winner_payout", String(winnerBid.bidder));
    await waitBalance(readClient, BigInt(balanceBefore) - payout, "winner_payout");
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "confirm_settlement", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const accounting = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID])); return accounting.payout_confirmed ? exact(accounting) : missing(); } });
    const balanceAfterPayout = String(await readContract(readClient, CORE, "get_contract_balance"));
    const refundExpectedBalance = BigInt(balanceAfterPayout) - remainder;
    await observeAsync(pilot, readClient, (await opJournal.get("confirm_settlement", TENDER_ID))?.tx_hash, "buyer_remainder_refund", buyerAccount.address);
    await waitBalance(readClient, refundExpectedBalance, "buyer_remainder_refund");
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "confirm_refund", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], reconcile: async () => { const current = await readContract(readClient, CORE, "get_tender", [TENDER_ID]); const accounting = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID])); return current.status === "SETTLED" && accounting.refund_confirmed && accounting.settlement_state === "SETTLED" ? exact({ current, accounting }) : missing(); } });
    const finalTender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    const finalAccounting = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID]));
    const finalBalance = String(await readContract(readClient, CORE, "get_contract_balance"));
    const accountingReconciles = BigInt(finalAccounting.escrow_deposited) === BigInt(finalAccounting.winner_payout_amount) + BigInt(finalAccounting.buyer_refund_amount) && finalTender.status === "SETTLED" && finalAccounting.payout_confirmed && finalAccounting.refund_confirmed && !finalAccounting.financial_outflow_pending;
    if (!accountingReconciles) throw new Error(`final accounting does not reconcile: ${JSON.stringify({ finalTender, finalAccounting, finalBalance })}`);
    await pilot.final({ tender: finalTender, accounting: finalAccounting, final_core_balance_wei: finalBalance, initial_escrow_wei: String(finalAccounting.escrow_deposited), winner_payout_wei: String(finalAccounting.winner_payout_amount), buyer_refund_wei: String(finalAccounting.buyer_refund_amount), accounting_reconciles: accountingReconciles, expected_winner: BID_A_ID, actual_winner: evaluationResult.winner_bid_id, all_relevant_writes_finalized: true, completed_at_utc: new Date().toISOString() });
    console.log(JSON.stringify({ status: "SETTLED", tender_id: TENDER_ID, expected_winner: BID_A_ID, actual_winner: evaluationResult.winner_bid_id, journal: JOURNAL_FILE }, null, 2));
  } catch (error) {
    await pilot.error(error, { tender_id: TENDER_ID });
    throw error;
  } finally {
    await opJournal.release();
  }
}

await main();
