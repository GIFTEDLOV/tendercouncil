/* Crash-safe, tender-scoped reconciliation primitives for Bradbury workflows. */
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";


export const MAX_CONTRACT_ID_LENGTH = 96;
const TRANSIENT_READ = /fetch failed|ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|timeout|network|429|500|502|503|504|socket|connection/i;
const BID_FIELDS = [
  "bid_id", "tender_id", "bidder", "price_wei", "delivery_days",
  "support_days", "proposal_url", "proposal_sha256",
  "evidence_commitments", "schema_version",
];

function jsonValue(value) {
  if (typeof value === "bigint") return value.toString();
  if (Array.isArray(value)) return value.map(jsonValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, jsonValue(value[key])]),
    );
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(jsonValue(value));
}

export function requireContractId(value, field = "object_id") {
  if (typeof value !== "string" || value.length === 0 || value.length > MAX_CONTRACT_ID_LENGTH) {
    throw new Error(`${field} violates Core grammar (non-empty, <= ${MAX_CONTRACT_ID_LENGTH})`);
  }
  return value;
}

export function makeTenderScopedBidId(tenderId, suffix) {
  requireContractId(tenderId, "tender_id");
  if (typeof suffix !== "string" || !/^[a-z0-9][a-z0-9-]*$/i.test(suffix)) {
    throw new Error("bid suffix is malformed");
  }
  return requireContractId(`${tenderId}-bid-${suffix.toLowerCase()}`, "bid_id");
}

function comparable(field, value) {
  if (field === "bidder") return String(value ?? "").toLowerCase();
  if (field === "price_wei") return String(value);
  if (field === "delivery_days" || field === "support_days") return Number(value);
  return String(value ?? "");
}

export function reconcileBid(outcome, expected, context) {
  requireContractId(expected.bid_id, "bid_id");
  requireContractId(expected.tender_id, "tender_id");
  if (!outcome || outcome.kind === "READ_ERROR") {
    throw new Error("bid read state is unknown; refusing mutation");
  }
  if (outcome.kind === "MISSING") {
    if (context.tenderStatus !== "OPEN") {
      throw new Error(`missing bid cannot be submitted while tender is ${context.tenderStatus}`);
    }
    if (Number(context.now) > Number(context.deadline)) {
      throw new Error("tender deadline expired with a missing bid");
    }
    return { action: "SUBMIT" };
  }
  if (outcome.kind !== "FOUND" || !outcome.record) {
    throw new Error(`unknown bid read classification: ${String(outcome.kind)}`);
  }
  const record = outcome.record;
  if (String(record.bid_id) !== expected.bid_id) {
    throw new Error(`object ID mismatch for ${expected.bid_id}`);
  }
  if (String(record.tender_id) !== expected.tender_id) {
    throw new Error(
      `GLOBAL ID COLLISION: ${expected.bid_id} belongs to ${String(record.tender_id)}`,
    );
  }
  if (outcome.finality !== "FINALIZED") {
    throw new Error(`bid ${expected.bid_id} is not FINALIZED`);
  }
  if (!Number.isInteger(Number(record.submitted_at)) || Number(record.submitted_at) <= 0) {
    throw new Error(`bid ${expected.bid_id} has no valid finalized submission state`);
  }
  for (const field of BID_FIELDS) {
    if (comparable(field, record[field]) !== comparable(field, expected[field])) {
      throw new Error(`immutable field mismatch for ${expected.bid_id}: ${field}`);
    }
  }
  return { action: "COMPLETE", record };
}

export function verifyBidsForClose(rows, context) {
  if (rows.length !== context.required) return false;
  for (const row of rows) {
    const result = reconcileBid(row.outcome, row.expected, context);
    if (result.action !== "COMPLETE") return false;
  }
  return context.tenderStatus === "OPEN" && Number(context.now) > Number(context.deadline);
}

export async function withReadRetry(operation, options = {}) {
  const {
    operation: name = "read", maxAttempts = 7, baseDelayMs = 250,
    maxDelayMs = 5000, jitterRatio = 0.2,
    sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    logger = () => {}, isTransient = (error) => TRANSIENT_READ.test(String(error?.message || error)),
  } = options;
  let lastError;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (!isTransient(error)) {
        throw new Error(`${name} read failed (non-transient): ${String(error?.message || error)}`, { cause: error });
      }
      if (attempt === maxAttempts) break;
      const bounded = Math.min(maxDelayMs, baseDelayMs * (2 ** (attempt - 1)));
      const jitter = jitterRatio === 0 ? 0 : bounded * jitterRatio * ((Math.random() * 2) - 1);
      const delay = Math.max(0, Math.round(bounded + jitter));
      logger({ kind: "READ_RETRY", operation: name, attempt, maxAttempts, delay_ms: delay, error: String(error?.message || error) });
      await sleep(delay);
    }
  }
  throw new Error(`${name} read retries exhausted after ${maxAttempts} attempts`, { cause: lastError });
}

export async function readClassified(readOperation, options = {}) {
  const { isMissing = () => false } = options;
  return withReadRetry(async () => {
    try {
      return { kind: "FOUND", record: await readOperation() };
    } catch (error) {
      if (isMissing(error)) return { kind: "MISSING" };
      throw error;
    }
  }, options);
}

function operationKey(context, operation, objectId) {
  return [
    context.network, context.core.toLowerCase(), context.evaluator.toLowerCase(),
    context.tender_id, operation, objectId,
  ].join("|");
}

export class OperationJournal {
  constructor(file, context, { staleLockMs = 21_600_000 } = {}) {
    this.file = path.resolve(file);
    this.context = jsonValue(context);
    this.lockFile = `${this.file}.lock`;
    this.staleLockMs = staleLockMs;
    this.lockHandle = null;
  }

  async acquire() {
    await fs.mkdir(path.dirname(this.file), { recursive: true });
    try {
      this.lockHandle = await fs.open(this.lockFile, "wx");
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      let lock;
      try { lock = JSON.parse(await fs.readFile(this.lockFile, "utf8")); } catch { lock = null; }
      const age = Date.now() - Number(lock?.created_at_ms || Date.now());
      const sameHost = lock?.hostname === os.hostname();
      let ownerAlive = false;
      if (sameHost && Number.isInteger(lock?.pid) && lock.pid > 0) {
        try {
          process.kill(lock.pid, 0);
          ownerAlive = true;
        } catch (error) {
          ownerAlive = error?.code === "EPERM";
        }
      }
      if (ownerAlive || (!sameHost && age <= this.staleLockMs) || (!lock && age <= this.staleLockMs)) {
        throw new Error(`operation journal is already locked: ${this.lockFile}`);
      }
      await fs.unlink(this.lockFile);
      this.lockHandle = await fs.open(this.lockFile, "wx");
    }
    await this.lockHandle.writeFile(`${canonicalJson({ pid: process.pid, hostname: os.hostname(), created_at_ms: Date.now(), context: this.context })}\n`, "utf8");
    await this.lockHandle.sync();
  }

  async release() {
    if (!this.lockHandle) return;
    await this.lockHandle.close();
    this.lockHandle = null;
    try { await fs.unlink(this.lockFile); } catch (error) { if (error?.code !== "ENOENT") throw error; }
  }

  async _entries() {
    let raw;
    try { raw = await fs.readFile(this.file, "utf8"); }
    catch (error) { if (error?.code === "ENOENT") return new Map(); throw error; }
    const entries = new Map();
    for (const line of raw.split(/\r?\n/)) {
      if (!line) continue;
      const event = JSON.parse(line);
      if (canonicalJson(event.context) !== canonicalJson(this.context)) {
        throw new Error("journal context mismatch");
      }
      entries.set(event.key, event);
    }
    return entries;
  }

  async _append(event) {
    if (!this.lockHandle) throw new Error("operation journal lock is not held");
    const handle = await fs.open(this.file, "a");
    try {
      await handle.writeFile(`${canonicalJson(event)}\n`, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
  }

  async get(operation, objectId) {
    return (await this._entries()).get(operationKey(this.context, operation, objectId)) || null;
  }

  async recordIntent(operation, objectId, intent) {
    const existing = await this.get(operation, objectId);
    if (existing) {
      if (canonicalJson(existing.intent) !== canonicalJson(intent)) {
        throw new Error(`journal intent mismatch for ${operation}:${objectId}`);
      }
      return existing;
    }
    const event = {
      version: 1, context: this.context,
      key: operationKey(this.context, operation, objectId), operation, object_id: objectId,
      status: "INTENT", intent: jsonValue(intent), tx_hash: null,
      result_digest: null, recorded_at: new Date().toISOString(),
    };
    await this._append(event);
    return event;
  }

  async recordBroadcast(operation, objectId, txHash) {
    const existing = await this.get(operation, objectId);
    if (!existing) throw new Error(`broadcast has no durable intent: ${operation}:${objectId}`);
    if (existing.tx_hash && existing.tx_hash !== txHash) {
      throw new Error(`journal tx hash mismatch for ${operation}:${objectId}`);
    }
    if (existing.tx_hash === txHash) return existing;
    const event = { ...existing, status: "BROADCAST", tx_hash: txHash, recorded_at: new Date().toISOString() };
    await this._append(event);
    return event;
  }

  async markFinalized(operation, objectId, resultDigest) {
    const existing = await this.get(operation, objectId);
    if (!existing) throw new Error(`finality has no durable intent: ${operation}:${objectId}`);
    const event = { ...existing, status: "FINALIZED", result_digest: resultDigest || null, recorded_at: new Date().toISOString() };
    await this._append(event);
    return event;
  }
}

function requireExact(state, label) {
  if (!state || state.state !== "EXACT") {
    throw new Error(`${label} did not produce exact intended chain state`);
  }
  return state;
}

export async function executeJournaledWrite({
  journal, operation, objectId, intent, reconcile, broadcast, poll, verify,
}) {
  let entry = await journal.get(operation, objectId);
  const fresh = entry === null;
  if (entry && canonicalJson(entry.intent) !== canonicalJson(intent)) {
    throw new Error(`journal intent mismatch for ${operation}:${objectId}`);
  }
  if (!entry) {
    const existingState = await reconcile();
    entry = await journal.recordIntent(operation, objectId, intent);
    if (existingState?.state === "EXACT") {
      await journal.markFinalized(operation, objectId, existingState.digest);
      return existingState;
    }
    if (existingState?.state !== "MISSING") {
      throw new Error(`${operation}:${objectId} pre-broadcast chain state is not safely reconcilable`);
    }
  }

  if (entry.status === "FINALIZED") {
    return requireExact(await verify(entry), `${operation}:${objectId} finalized reconciliation`);
  }
  if (entry.tx_hash) {
    const receipt = await poll(entry.tx_hash);
    if (receipt?.finality !== "FINALIZED") {
      throw new Error(`${operation}:${objectId} exact transaction is not FINALIZED`);
    }
    const state = requireExact(await verify(entry, receipt), `${operation}:${objectId} post-transaction verification`);
    await journal.markFinalized(operation, objectId, state.digest);
    return state;
  }
  if (!fresh) {
    const state = await reconcile(entry);
    if (state?.state === "EXACT") {
      await journal.markFinalized(operation, objectId, state.digest);
      return state;
    }
    throw new Error(`ambiguous durable intent without tx hash for ${operation}:${objectId}; refusing rebroadcast`);
  }

  const txHash = await broadcast();
  if (typeof txHash !== "string" || !/^0x[0-9a-f]{64}$/i.test(txHash)) {
    throw new Error(`${operation}:${objectId} broadcast returned an invalid tx hash`);
  }
  entry = await journal.recordBroadcast(operation, objectId, txHash);
  const receipt = await poll(txHash);
  if (receipt?.finality !== "FINALIZED") {
    throw new Error(`${operation}:${objectId} exact transaction is not FINALIZED`);
  }
  const state = requireExact(await verify(entry, receipt), `${operation}:${objectId} post-transaction verification`);
  await journal.markFinalized(operation, objectId, state.digest);
  return state;
}
