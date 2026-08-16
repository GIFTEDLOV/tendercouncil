/* Crash-safe Pilot 2 Phase A: create, open, and store two finalized bids. */
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

import { OperationJournal, canonicalJson, executeJournaledWrite, withReadRetry } from "./bradbury_runner_lib.mjs";
import { resolveGenlayerModulePaths } from "./genlayer_module_paths.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { sdkRoot: SDK_ROOT, cliEntry: CLI_ROOT } = resolveGenlayerModulePaths();
const NETWORK = "testnet-bradbury";
const CHAIN_ID = 4221;
const CORE = "0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd";
const EVALUATOR = "0x023AB3434761715a531884Ca0852aC14beE03acE";
const VERSION = "tendercouncil.evaluator.v2.1";
const CODE_HASH = "sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b";
const CORE_SHA256 = "54acb8815411c3bbc0623a6587cdb4a29bc77a0a8b91b3c7022c4d77c6dbfbd2";
const EVALUATOR_SHA256 = "1956b3c984ec6310c4a4d6532e8bd8f456532b9c4e171dae82aa9ae8d7194e5d";
const PILOT2_ID = "PILOT2_20260816T184818Z";
const TENDER_ID = "TENDER_PILOT_V21_P2_20260816T184818Z";
const BID_A_ID = `${TENDER_ID}-bid-a`;
const BID_B_ID = `${TENDER_ID}-bid-b`;
const PILOT2_FIXTURE_COMMIT = "837565d9f0b4633f3ae111197d839f3790f164ca";
const EXPECTATION_COMMIT = "dbe77d6fff8215973a90dc0ac0df2414dc13cbac";
const BUDGET = 50_000_000_000_000_000n;
const A_PRICE = 32_000_000_000_000_000n;
const B_PRICE = 39_000_000_000_000_000n;
const RESPONSE_WINDOW = 600;
const DEADLINE_WINDOW = 24 * 60 * 60;
const BID_A_MIN_MARGIN = 12 * 60 * 60;
const BID_B_MIN_MARGIN = 10 * 60 * 60;
const BRIEF_HASH = "sha256:44bb3d24956a4ea2d9a8828afc7f6cde822c7f0c06708aea3fa9f7d365a33f8e";
const A_PROPOSAL_HASH = "sha256:81fc47eb482fcbb58f4d5b8f0df7ee8b5827ca67b6394ce88a9a2083cb46b980";
const B_PROPOSAL_HASH = "sha256:e3d371df8354e57d0a87c15fdb9c186f8bca7f7a4a1f50ff1025242269b9cbf6";
const A_EVIDENCE_HASH = "sha256:83366c33c2cf2257f0a920f6cc6a51c61dfdf7cae7256cda922f759aa36cd8de";
const B_EVIDENCE_HASH = "sha256:50ccede1e2904873ce72abcfb8c6b7c277ae5b782dd45d38ed48e86a25a56ce5";
const BRIEF_URL = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${PILOT2_FIXTURE_COMMIT}/fixtures/live-pilot-v21-attempt-2/tender-brief.json`;
const A_PROPOSAL_URL = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${PILOT2_FIXTURE_COMMIT}/fixtures/live-pilot-v21-attempt-2/bidder-a-proposal.json`;
const B_PROPOSAL_URL = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${PILOT2_FIXTURE_COMMIT}/fixtures/live-pilot-v21-attempt-2/bidder-b-proposal.json`;
const A_EVIDENCE_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/bfddc6c4c2fcd16431af6da797213c0f42ade4fb/fixtures/live/blobs/a_capability.json";
const B_EVIDENCE_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/bfddc6c4c2fcd16431af6da797213c0f42ade4fb/fixtures/live/blobs/b_capability.json";
const JOURNAL_FILE = path.join(ROOT, "artifacts/tender_council_bradbury_v21_pilot2_journal.json");
const OP_JOURNAL_FILE = path.join(ROOT, `.local/bradbury-journal/${NETWORK}-${CORE.toLowerCase()}-${TENDER_ID}.jsonl`);
const TRANSIENT = /fetch failed|ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|timeout|network|429|500|502|503|504|socket|connection/i;

function safe(value) {
  return JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
}
function digest(value) { return `sha256:${crypto.createHash("sha256").update(canonicalJson(safe(value))).digest("hex")}`; }
function sha256Bytes(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function statusName(tx) { return tx?.statusName || tx?.status || "UNKNOWN"; }
function resultName(tx) { return tx?.resultName || tx?.result_name || tx?.result || "UNKNOWN"; }
function executionName(tx) { return tx?.txExecutionResultName || tx?.tx_execution_result_name || tx?.txExecutionResult || tx?.tx_execution_result || "UNKNOWN"; }
function isHash(value) { return typeof value === "string" && /^0x[0-9a-f]{64}$/i.test(value); }
function logReadRetry(event) { console.log(`read_retry=${JSON.stringify(event)}`); }
async function retryRead(name, operation) { return withReadRetry(operation, { operation: name, logger: logReadRetry, isTransient: (error) => TRANSIENT.test(String(error?.message || error)) }); }

class PilotJournal {
  constructor(file, metadata) { this.file = file; this.metadata = metadata; this.state = { version: 1, ...metadata, events: [], errors: [] }; }
  async load() {
    try {
      this.state = JSON.parse(await fs.readFile(this.file, "utf8"));
      if (this.state.pilot_id !== PILOT2_ID || this.state.tender_id !== TENDER_ID || this.state.core?.toLowerCase() !== CORE.toLowerCase()) throw new Error("Pilot 2 journal context mismatch");
    } catch (error) { if (error?.code !== "ENOENT") throw error; }
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
  const joined = [error?.shortMessage, error?.message, String(error)].filter(Boolean).join(" ");
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
async function txObservation(client, hash) {
  const tx = await retryRead("getTransaction:observation", () => client.getTransaction({ hash }));
  return { tx_hash: hash, status: statusName(tx), result_name: resultName(tx), execution_status: executionName(tx), consensus: tx?.consensusStatus || tx?.consensus || null, validator_split: tx?.lastRound ? { votes: tx.lastRound.validatorVotesName || null, result_hashes: tx.lastRound.validatorResultHash || null, validators: tx.lastRound.roundValidators || null } : null, transaction: safe(tx) };
}
async function waitGenlayerFinal(client, hash, pilot, operation, objectId) {
  if (!isHash(hash)) throw new Error(`invalid transaction hash: ${hash}`);
  let lastStatus = null;
  for (let attempt = 1; attempt <= 1080; attempt += 1) {
    const tx = await retryRead("getTransaction", () => client.getTransaction({ hash }));
    const status = statusName(tx);
    if (status !== lastStatus) {
      lastStatus = status;
      await pilot.event({ kind: "POLL_OBSERVATION", operation, object_id: objectId, tx_hash: hash, poll_attempt: attempt, status, result_name: resultName(tx), execution_status: executionName(tx), consensus: tx?.consensusStatus || tx?.consensus || null, transaction: safe(tx) });
    }
    if (status === "FINALIZED") {
      const consensus = tx?.consensusStatus || tx?.consensus || resultName(tx);
      if (String(consensus) !== "AGREE") throw new Error(`transaction ${hash} finalized with consensus ${String(consensus)}`);
      return { finality: "FINALIZED", transaction: safe(tx) };
    }
    if (["UNDETERMINED", "CANCELED", "REVERTED"].includes(status)) throw new Error(`transaction ${hash} terminated as ${status}`);
    await sleep(10_000);
  }
  throw new Error(`transaction ${hash} did not finalize within bounded polling`);
}
async function coreState(readClient) {
  const tender = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]);
  if (tender.kind === "MISSING") return { tender: null };
  return { tender: tender.record, accounting: JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID])), core_balance_wei: String(await readContract(readClient, CORE, "get_contract_balance")) };
}
function tenderExpected(buyer, deadline) {
  return { tender_id: TENDER_ID, buyer, title: "Analytics Dashboard Development", brief_url: BRIEF_URL, brief_sha256: BRIEF_HASH, max_budget_wei: BUDGET.toString(), max_delivery_days: 30, min_support_days: 90, bidding_deadline: deadline, response_window_seconds: RESPONSE_WINDOW, requirements: "authentication;CSV export;responsive/mobile support;dashboard/chart functionality", evidence_policy: "capability:required;delivery:optional;support:optional;technical:optional" };
}
function tenderMatches(tender, expected, status = null) {
  for (const field of Object.keys(expected)) {
    const actual = field === "buyer" ? String(tender[field]).toLowerCase() : String(tender[field]);
    const wanted = field === "buyer" ? String(expected[field]).toLowerCase() : String(expected[field]);
    if (actual !== wanted) throw new Error(`tender mismatch ${field}: ${actual} != ${wanted}`);
  }
  if (status && tender.status !== status) throw new Error(`tender status ${tender.status} != ${status}`);
  return tender;
}
function reconcileTender(tender, expected, status) {
  try { return { state: "EXACT", digest: digest(tender), value: tenderMatches(tender, expected, status) }; }
  catch { return { state: "MISSING" }; }
}
function bidExpected(id, bidder, price, delivery, support, proposalUrl, proposalHash, evidenceId, evidenceUrl, evidenceHash) {
  return { bid_id: id, tender_id: TENDER_ID, bidder, price_wei: price.toString(), delivery_days: delivery, support_days: support, proposal_url: proposalUrl, proposal_sha256: proposalHash, evidence_commitments: `${evidenceId}|CAPABILITY|capability|1|${evidenceUrl}|${evidenceHash}`, schema_version: "tendercouncil.bid.v1" };
}
function bidMatches(record, expected) {
  for (const field of ["bid_id", "tender_id", "proposal_url", "proposal_sha256", "evidence_commitments", "schema_version"]) if (String(record[field]) !== String(expected[field])) throw new Error(`bid immutable field mismatch ${expected.bid_id}: ${field}`);
  if (String(record.bidder).toLowerCase() !== expected.bidder.toLowerCase()) throw new Error(`bidder mismatch ${expected.bid_id}`);
  if (String(record.price_wei) !== expected.price_wei || Number(record.delivery_days) !== expected.delivery_days || Number(record.support_days) !== expected.support_days) throw new Error(`bid commercial field mismatch ${expected.bid_id}`);
  return record;
}
async function deadlineMargin(readClient, deadline) {
  const now = await chainTime(readClient);
  return { chain_time: now, remaining_seconds: Number(deadline) - now };
}
async function verifyImmutableFixtures() {
  const rows = [[BRIEF_URL, BRIEF_HASH], [A_PROPOSAL_URL, A_PROPOSAL_HASH], [B_PROPOSAL_URL, B_PROPOSAL_HASH], [A_EVIDENCE_URL, A_EVIDENCE_HASH], [B_EVIDENCE_URL, B_EVIDENCE_HASH]];
  const verified = [];
  for (const [url, expected] of rows) {
    if (!/^https:\/\/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/[0-9a-f]{40}\//i.test(url)) throw new Error(`fixture URL is not immutable: ${url}`);
    const response = await fetch(url);
    if (!response.ok) throw new Error(`immutable fixture fetch failed ${response.status}: ${url}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    const actual = `sha256:${sha256Bytes(bytes)}`;
    if (actual !== expected) throw new Error(`fixture hash mismatch ${url}: ${actual} != ${expected}`);
    verified.push({ url, sha256: actual, bytes: bytes.length });
  }
  return verified;
}
async function sourceHash(relative) { return sha256Bytes(await fs.readFile(path.join(ROOT, relative))); }

async function runWrite({ opJournal, pilot, client, readClient, operation, objectId, actor, args, value = 0n, reconcile, deadline }) {
  const before = await coreState(readClient);
  const margin = deadline === undefined ? null : await deadlineMargin(readClient, deadline);
  const persistedEntry = await opJournal.get(operation, objectId);
  const intent = persistedEntry?.intent || { operation, object_id: objectId, actor, args: safe(args), arguments_digest: digest(args), value_wei: String(value) };
  await pilot.event({ kind: "WRITE_INTENT", ...intent, core_state_before: before });
  try {
    await executeJournaledWrite({
      journal: opJournal, operation, objectId, intent,
      reconcile,
      broadcast: () => client.writeContract({ account: client.account, address: CORE, functionName: operation, args, value, leaderOnly: false }),
      poll: (hash) => waitGenlayerFinal(client, hash, pilot, operation, objectId),
      verify: reconcile,
    });
    const entry = await opJournal.get(operation, objectId);
    if (!entry || entry.status !== "FINALIZED") throw new Error(`${operation} did not reach FINALIZED in durable journal`);
    const tx = await txObservation(readClient, entry.tx_hash);
    if (tx.execution_status !== "FINISHED_WITH_RETURN") throw new Error(`${operation} finalized with execution ${tx.execution_status}`);
    const after = await coreState(readClient);
    const afterMargin = deadline === undefined ? null : await deadlineMargin(readClient, deadline);
    await pilot.event({ kind: "WRITE_FINALIZED", ...intent, tx_hash: entry.tx_hash, broadcast_timestamp: entry.recorded_at, final_status: entry.status, result_name: tx.result_name, execution_status: tx.execution_status, consensus: tx.consensus, validator_split: tx.validator_split, transaction: tx, core_state_after: after, deadline_margin_after_seconds: afterMargin?.remaining_seconds ?? null });
    return { entry, tx, after, margin: afterMargin };
  } catch (error) {
    await pilot.error(error, { kind: "WRITE_UNKNOWN_OR_FAILED", ...intent, core_state_observation: await coreState(readClient).catch((readError) => ({ read_error: String(readError) })) });
    throw error;
  }
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
  if (readClient.chain.id !== CHAIN_ID) throw new Error(`wrong chain ${readClient.chain.id}`);
  const accounts = JSON.parse(await fs.readFile(path.join(ROOT, ".local/tendercouncil_bradbury_accounts.json"), "utf8")).accounts || [];
  const rowA = accounts.find((row) => row.label === "bidder_a");
  const rowB = accounts.find((row) => row.label === "bidder_b");
  if (!rowA || !rowB) throw new Error("configured bidder_a/bidder_b accounts unavailable");
  const bidderAAccount = sdk.createAccount(rowA.private_key);
  const bidderBAccount = sdk.createAccount(rowB.private_key);
  const bidderA = sdk.createClient({ chain: testnetBradbury, account: bidderAAccount });
  const bidderB = sdk.createClient({ chain: testnetBradbury, account: bidderBAccount });
  if (buyerAccount.address.toLowerCase() !== "0xe0f17bef0587c3b66d2eb4bbE705dff821abdde7".toLowerCase() || bidderAAccount.address.toLowerCase() !== rowA.address.toLowerCase() || bidderBAccount.address.toLowerCase() !== rowB.address.toLowerCase()) throw new Error("configured actor address mismatch");
  const pilot = new PilotJournal(JOURNAL_FILE, { pilot_id: PILOT2_ID, tender_id: TENDER_ID, network: NETWORK, chain_id: CHAIN_ID, core: CORE, evaluator: EVALUATOR, evaluator_version: VERSION, pilot_fixture_commit: PILOT2_FIXTURE_COMMIT, expectation_commit: EXPECTATION_COMMIT, actors: { buyer: buyerAccount.address, bidder_a: rowA.address, bidder_b: rowB.address }, deadline_policy: { window_seconds: DEADLINE_WINDOW, bid_a_minimum_remaining_seconds: BID_A_MIN_MARGIN, bid_b_minimum_remaining_seconds: BID_B_MIN_MARGIN } });
  await pilot.load();
  if (pilot.state.final?.pilot2_predeadline_complete) { console.log(JSON.stringify(pilot.state.final, null, 2)); return; }
  const opJournal = new OperationJournal(OP_JOURNAL_FILE, { network: NETWORK, core: CORE, evaluator: EVALUATOR, tender_id: TENDER_ID });
  await opJournal.acquire();
  try {
    const coreSha = await sourceHash("contracts/tender_council_core.py");
    const evaluatorSha = await sourceHash("contracts/tender_council_evaluator.py");
    if (coreSha !== CORE_SHA256 || evaluatorSha !== EVALUATOR_SHA256) throw new Error(`production source hash mismatch: core=${coreSha} evaluator=${evaluatorSha}`);
    const binding = JSON.parse(await readContract(readClient, CORE, "get_evaluator_binding"));
    const ready = await readContract(readClient, CORE, "get_production_ready");
    const evaluatorCore = await readContract(readClient, EVALUATOR, "get_core_address");
    const evaluatorVersion = await readContract(readClient, EVALUATOR, "get_evaluator_version");
    const attempt1Accounting = JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", ["TENDER_PILOT_V21_20260816T164802Z"]));
    const balances = { buyer: String(await readClient.getBalance({ address: buyerAccount.address, blockTag: "latest" })), bidder_a: String(await readClient.getBalance({ address: rowA.address, blockTag: "latest" })), bidder_b: String(await readClient.getBalance({ address: rowB.address, blockTag: "latest" })) };
    const preflight = { chain_id: readClient.chain.id, production_ready: ready, binding, evaluator_core: evaluatorCore, evaluator_version: evaluatorVersion, source_hashes: { core_sha256: coreSha, evaluator_sha256: evaluatorSha }, attempt1_financial_outflow_pending: attempt1Accounting.financial_outflow_pending, balances, core_balance_before: String(await readContract(readClient, CORE, "get_contract_balance")) };
    if (!ready || !binding.bound || binding.address.toLowerCase() !== EVALUATOR.toLowerCase() || binding.version !== VERSION || binding.evaluator_code_hash !== CODE_HASH || evaluatorCore.toLowerCase() !== CORE.toLowerCase() || evaluatorVersion !== VERSION) throw new Error(`production binding readback mismatch: ${JSON.stringify(preflight)}`);
    if (attempt1Accounting.financial_outflow_pending) throw new Error("global financial outflow is pending");
    if (BigInt(balances.buyer) <= BUDGET || BigInt(balances.bidder_a) <= 1_000_000_000_000_000n || BigInt(balances.bidder_b) <= 1_000_000_000_000_000n) throw new Error(`actor funding insufficient: ${JSON.stringify({ balances })}`);
    const immutableFixtures = await verifyImmutableFixtures();
    await pilot.event({ kind: "READ_ONLY_PREFLIGHT", ...preflight, immutable_fixtures: immutableFixtures });
    const existingTender = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]);
    if (existingTender.kind !== "MISSING" && !(await opJournal.get("create_tender", TENDER_ID))) throw new Error("Pilot 2 tender ID is already used");
    for (const id of [BID_A_ID, BID_B_ID]) if ((await readRecord(readClient, CORE, "get_bid", [id])).kind !== "MISSING" && !(await opJournal.get("submit_bid", id))) throw new Error(`Pilot 2 bid ID is already used: ${id}`);

    const existingCreate = await opJournal.get("create_tender", TENDER_ID);
    const selectedDeadline = Number(existingCreate?.intent?.args?.[7] || (await chainTime(readClient)) + DEADLINE_WINDOW);
    if (!existingCreate) await pilot.event({ kind: "DEADLINE_SELECTED", pilot_id: PILOT2_ID, chain_time_at_selection: selectedDeadline - DEADLINE_WINDOW, bidding_deadline: selectedDeadline, bidding_deadline_utc: new Date(selectedDeadline * 1000).toISOString(), window_seconds: DEADLINE_WINDOW, safety_thresholds_seconds: { bid_a: BID_A_MIN_MARGIN, bid_b: BID_B_MIN_MARGIN } });
    const expectedTender = tenderExpected(buyerAccount.address, selectedDeadline);
    const createArgs = [TENDER_ID, expectedTender.title, expectedTender.brief_url, expectedTender.brief_sha256, BUDGET, expectedTender.max_delivery_days, expectedTender.min_support_days, selectedDeadline, RESPONSE_WINDOW, expectedTender.requirements, 35, 20, 20, 15, 10, expectedTender.evidence_policy];
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "create_tender", objectId: TENDER_ID, actor: buyerAccount.address, args: createArgs, value: BUDGET, deadline: selectedDeadline, reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]); return outcome.kind === "MISSING" ? { state: "MISSING" } : reconcileTender(outcome.record, expectedTender); } });
    const created = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    tenderMatches(created, expectedTender);
    if (!["DRAFT", "OPEN"].includes(created.status)) throw new Error(`unexpected tender state after create reconciliation: ${created.status}`);
    const createMargin = await deadlineMargin(readClient, selectedDeadline);
    await pilot.event({ kind: "CREATE_READBACK", tender: created, accounting: JSON.parse(await readContract(readClient, CORE, "get_settlement_accounting", [TENDER_ID])), core_balance_wei: String(await readContract(readClient, CORE, "get_contract_balance")), deadline: selectedDeadline, deadline_utc: new Date(selectedDeadline * 1000).toISOString(), remaining_seconds: createMargin.remaining_seconds });
    if (createMargin.remaining_seconds < BID_A_MIN_MARGIN) throw new Error(`DEADLINE_SAFETY_MARGIN_FAILED after create: ${createMargin.remaining_seconds}`);
    await runWrite({ opJournal, pilot, client: buyer, readClient, operation: "open_tender", objectId: TENDER_ID, actor: buyerAccount.address, args: [TENDER_ID], deadline: selectedDeadline, reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_tender", [TENDER_ID]); return outcome.kind === "MISSING" ? { state: "MISSING" } : reconcileTender(outcome.record, expectedTender, "OPEN"); } });
    const opened = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    tenderMatches(opened, expectedTender, "OPEN");
    const openMargin = await deadlineMargin(readClient, selectedDeadline);
    await pilot.event({ kind: "OPEN_READBACK", tender: opened, remaining_seconds: openMargin.remaining_seconds });
    if (openMargin.remaining_seconds < BID_A_MIN_MARGIN) throw new Error(`DEADLINE_SAFETY_MARGIN_FAILED before Bid A: ${openMargin.remaining_seconds}`);

    const bidA = bidExpected(BID_A_ID, rowA.address, A_PRICE, 20, 180, A_PROPOSAL_URL, A_PROPOSAL_HASH, "pilot2-a-capability", A_EVIDENCE_URL, A_EVIDENCE_HASH);
    const bidB = bidExpected(BID_B_ID, rowB.address, B_PRICE, 25, 120, B_PROPOSAL_URL, B_PROPOSAL_HASH, "pilot2-b-capability", B_EVIDENCE_URL, B_EVIDENCE_HASH);
    const bidAInitialMargin = await deadlineMargin(readClient, selectedDeadline);
    if (bidAInitialMargin.remaining_seconds < BID_A_MIN_MARGIN) throw new Error(`DEADLINE_SAFETY_MARGIN_FAILED before Bid A: ${bidAInitialMargin.remaining_seconds}`);
    const bidAArgs = [BID_A_ID, TENDER_ID, A_PRICE, 20, 180, A_PROPOSAL_URL, A_PROPOSAL_HASH, bidA.evidence_commitments, "tendercouncil.bid.v1"];
    await runWrite({ opJournal, pilot, client: bidderA, readClient, operation: "submit_bid", objectId: BID_A_ID, actor: rowA.address, args: bidAArgs, deadline: selectedDeadline, reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_bid", [BID_A_ID]); if (outcome.kind === "MISSING") return { state: "MISSING" }; return { state: "EXACT", digest: digest(outcome.record), value: bidMatches(outcome.record, bidA) }; } });
    const storedA = await readContract(readClient, CORE, "get_bid", [BID_A_ID]);
    bidMatches(storedA, bidA);
    const afterAMargin = await deadlineMargin(readClient, selectedDeadline);
    const afterATender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    if (afterATender.status !== "OPEN") throw new Error(`Bid A changed tender state to ${afterATender.status}`);
    await pilot.event({ kind: "BID_A_STORED", bid: storedA, bid_a_stored: true, tender_status: afterATender.status, remaining_seconds: afterAMargin.remaining_seconds });
    if (afterAMargin.remaining_seconds < BID_B_MIN_MARGIN) throw new Error(`DEADLINE_SAFETY_MARGIN_FAILED before Bid B: ${afterAMargin.remaining_seconds}`);
    const bidBArgs = [BID_B_ID, TENDER_ID, B_PRICE, 25, 120, B_PROPOSAL_URL, B_PROPOSAL_HASH, bidB.evidence_commitments, "tendercouncil.bid.v1"];
    await runWrite({ opJournal, pilot, client: bidderB, readClient, operation: "submit_bid", objectId: BID_B_ID, actor: rowB.address, args: bidBArgs, deadline: selectedDeadline, reconcile: async () => { const outcome = await readRecord(readClient, CORE, "get_bid", [BID_B_ID]); if (outcome.kind === "MISSING") return { state: "MISSING" }; return { state: "EXACT", digest: digest(outcome.record), value: bidMatches(outcome.record, bidB) }; } });
    const storedB = await readContract(readClient, CORE, "get_bid", [BID_B_ID]);
    bidMatches(storedB, bidB);
    const storedAAgain = await readContract(readClient, CORE, "get_bid", [BID_A_ID]);
    bidMatches(storedAAgain, bidA);
    const finalTender = await readContract(readClient, CORE, "get_tender", [TENDER_ID]);
    if (finalTender.status !== "OPEN") throw new Error(`Pilot 2 tender is not OPEN after Bid B: ${finalTender.status}`);
    const finalMargin = await deadlineMargin(readClient, selectedDeadline);
    await pilot.event({ kind: "BID_B_STORED", bid: storedB, bid_a_stored: true, bid_b_stored: true, tender_status: finalTender.status, remaining_seconds: finalMargin.remaining_seconds, no_close_or_evaluation_attempted: true });
    await pilot.final({ pilot2_predeadline_complete: true, pilot_id: PILOT2_ID, tender_id: TENDER_ID, tender_status: finalTender.status, bidding_deadline: selectedDeadline, bidding_deadline_utc: new Date(selectedDeadline * 1000).toISOString(), resume_not_before_utc: new Date((selectedDeadline + 5 * 60) * 1000).toISOString(), create_tx: (await opJournal.get("create_tender", TENDER_ID))?.tx_hash, open_tx: (await opJournal.get("open_tender", TENDER_ID))?.tx_hash, bid_a_tx: (await opJournal.get("submit_bid", BID_A_ID))?.tx_hash, bid_b_tx: (await opJournal.get("submit_bid", BID_B_ID))?.tx_hash, bid_a_stored: true, bid_b_stored: true, final_deadline_margin_seconds: finalMargin.remaining_seconds, close_tx: "NOT_RUN", start_evaluation_tx: "NOT_RUN", settlement_tx: "NOT_RUN", completed_at_utc: new Date().toISOString() });
    console.log(JSON.stringify(pilot.state.final, null, 2));
  } catch (error) {
    await pilot.error(error, { pilot_id: PILOT2_ID, tender_id: TENDER_ID });
    throw error;
  } finally { await opJournal.release(); }
}

await main();
