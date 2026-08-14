import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  OperationJournal,
  executeJournaledWrite,
  makeTenderScopedBidId,
  readClassified,
  reconcileBid,
  verifyBidsForClose,
  withReadRetry,
} from "../../tools/bradbury_runner_lib.mjs";


const ROOT = path.resolve(".local/runner-tests");
const CORE = "0x" + "11".repeat(20);
const EVALUATOR = "0x" + "22".repeat(20);
const TENDER = "analytics-dashboard-2026-final";

function expected(suffix = "a") {
  return {
    bid_id: makeTenderScopedBidId(TENDER, suffix),
    tender_id: TENDER,
    bidder: "0x" + "33".repeat(20),
    price_wei: "62000000000000000",
    delivery_days: 26,
    support_days: 90,
    proposal_url: "https://fixture.example/bid-a.json",
    proposal_sha256: "sha256:" + "a".repeat(64),
    evidence_commitments: "evidence|CAPABILITY|capability|1|https://fixture.example/evidence|sha256:" + "b".repeat(64),
    schema_version: "tendercouncil.bid.v1",
  };
}

function found(record, finality = "FINALIZED") {
  return { kind: "FOUND", record, finality };
}

function exactRecord(value = expected()) {
  return { ...value, submitted_at: 1_800_000_000 };
}

async function journal(name) {
  await fs.mkdir(ROOT, { recursive: true });
  const file = path.join(ROOT, `${name}-${crypto.randomUUID()}.jsonl`);
  const instance = new OperationJournal(file, {
    network: "testnet-bradbury", core: CORE, evaluator: EVALUATOR,
    tender_id: TENDER,
  });
  await instance.acquire();
  return instance;
}


test("1 old global bid-a is never counted for a new tender", () => {
  const scoped = expected("a");
  assert.notEqual(scoped.bid_id, "bid-a");
  assert.throws(
    () => reconcileBid(found({ ...exactRecord(scoped), bid_id: "bid-a", tender_id: "analytics-dashboard-2026" }), scoped, { tenderStatus: "OPEN", now: 10, deadline: 20 }),
    /object ID mismatch|collision/i,
  );
});

test("2 missing tender-scoped bid is eligible before deadline", () => {
  assert.deepEqual(
    reconcileBid({ kind: "MISSING" }, expected(), { tenderStatus: "OPEN", now: 10, deadline: 20 }),
    { action: "SUBMIT" },
  );
});

test("3 exact same-tender finalized bid resumes", () => {
  assert.deepEqual(
    reconcileBid(found(exactRecord()), expected(), { tenderStatus: "OPEN", now: 10, deadline: 20 }),
    { action: "COMPLETE", record: exactRecord() },
  );
});

test("4 same-tender immutable mismatch stops", () => {
  assert.throws(
    () => reconcileBid(found({ ...exactRecord(), support_days: 89 }), expected(), { tenderStatus: "OPEN", now: 10, deadline: 20 }),
    /immutable field mismatch.*support_days/i,
  );
});

test("5 globally colliding ID under another tender fails closed", () => {
  assert.throws(
    () => reconcileBid(found({ ...exactRecord(), tender_id: "old-tender" }), expected(), { tenderStatus: "OPEN", now: 10, deadline: 20 }),
    /global id collision/i,
  );
});

test("6 restart after broadcast-before-receipt polls the exact hash once", async (t) => {
  const j = await journal("after-broadcast");
  t.after(() => j.release());
  let broadcasts = 0;
  let polls = 0;
  const options = {
    journal: j, operation: "submit_bid", objectId: expected().bid_id,
    intent: expected(),
    reconcile: async () => ({ state: "MISSING" }),
    broadcast: async () => { broadcasts += 1; return "0x" + "a".repeat(64); },
    poll: async (hash) => {
      polls += 1;
      assert.equal(hash, "0x" + "a".repeat(64));
      if (polls === 1) throw new Error("RPC_TIMEOUT");
      return { finality: "FINALIZED" };
    },
    verify: async () => ({ state: "EXACT", digest: "sha256:" + "c".repeat(64) }),
  };
  await assert.rejects(() => executeJournaledWrite(options), /RPC_TIMEOUT/);
  await executeJournaledWrite(options);
  assert.equal(broadcasts, 1);
  assert.equal(polls, 2);
});

test("7 restart after finalized bid recognizes chain state", async (t) => {
  const j = await journal("after-finalized");
  t.after(() => j.release());
  await j.recordIntent("submit_bid", expected().bid_id, expected());
  await j.recordBroadcast("submit_bid", expected().bid_id, "0x" + "b".repeat(64));
  let broadcasts = 0;
  await executeJournaledWrite({
    journal: j, operation: "submit_bid", objectId: expected().bid_id,
    intent: expected(), reconcile: async () => ({ state: "EXACT", digest: "d" }),
    broadcast: async () => { broadcasts += 1; return "0xnever"; },
    poll: async () => ({ finality: "FINALIZED" }),
    verify: async () => ({ state: "EXACT", digest: "d" }),
  });
  assert.equal(broadcasts, 0);
  assert.equal((await j.get("submit_bid", expected().bid_id)).status, "FINALIZED");
});

test("8 five exact finalized bids permit close only after deadline", () => {
  const rows = ["a", "b", "c", "d", "e"].map((suffix) => {
    const value = expected(suffix);
    return { outcome: found(exactRecord(value)), expected: value };
  });
  assert.equal(verifyBidsForClose(rows, { tenderStatus: "OPEN", now: 21, deadline: 20, required: 5 }), true);
});

test("9 only four finalized bids never permit close", () => {
  const rows = ["a", "b", "c", "d"].map((suffix) => {
    const value = expected(suffix);
    return { outcome: found(exactRecord(value)), expected: value };
  });
  assert.equal(verifyBidsForClose(rows, { tenderStatus: "OPEN", now: 21, deadline: 20, required: 5 }), false);
});

test("10 expired tender with a missing bid cannot submit or pretend to continue", () => {
  assert.throws(
    () => reconcileBid({ kind: "MISSING" }, expected(), { tenderStatus: "OPEN", now: 21, deadline: 20 }),
    /deadline expired/i,
  );
});

test("11 RPC timeout before broadcast never becomes MISSING", async () => {
  let broadcasts = 0;
  await assert.rejects(
    () => readClassified(async () => { throw new Error("ETIMEDOUT"); }, {
      operation: "get_bid", maxAttempts: 3, sleep: async () => {},
      isMissing: () => false,
    }),
    /read retries exhausted/i,
  );
  assert.equal(broadcasts, 0);
});

test("12 RPC timeout after broadcast leaves exact tx pending, never rebroadcasts", async (t) => {
  const j = await journal("poll-timeout");
  t.after(() => j.release());
  let broadcasts = 0;
  const run = () => executeJournaledWrite({
    journal: j, operation: "close_tender", objectId: TENDER,
    intent: { tender_id: TENDER }, reconcile: async () => ({ state: "MISSING" }),
    broadcast: async () => { broadcasts += 1; return "0x" + "c".repeat(64); },
    poll: async () => { throw new Error("receipt timeout"); },
    verify: async () => ({ state: "MISSING" }),
  });
  await assert.rejects(run, /receipt timeout/);
  await assert.rejects(run, /receipt timeout/);
  assert.equal(broadcasts, 1);
  assert.equal((await j.get("close_tender", TENDER)).tx_hash, "0x" + "c".repeat(64));
});

test("13 duplicate runner process cannot acquire the same journal", async (t) => {
  const first = await journal("duplicate-process");
  t.after(() => first.release());
  const second = new OperationJournal(first.file, first.context);
  await assert.rejects(() => second.acquire(), /already locked/i);
});

test("14 stale journal intent with different immutable fields fails closed", async (t) => {
  const j = await journal("stale-intent");
  t.after(() => j.release());
  await j.recordIntent("submit_bid", expected().bid_id, expected());
  const changed = { ...expected(), price_wei: "1" };
  await assert.rejects(
    () => executeJournaledWrite({
      journal: j, operation: "submit_bid", objectId: expected().bid_id,
      intent: changed, reconcile: async () => ({ state: "MISSING" }),
      broadcast: async () => "0xnever", poll: async () => ({}),
      verify: async () => ({ state: "MISSING" }),
    }),
    /journal intent mismatch/i,
  );
});

test("15 finalized tx with pending journal is reconciled and finalized locally", async (t) => {
  const j = await journal("finalized-pending");
  t.after(() => j.release());
  await j.recordIntent("submit_bid", expected().bid_id, expected());
  await j.recordBroadcast("submit_bid", expected().bid_id, "0x" + "d".repeat(64));
  let broadcasts = 0;
  await executeJournaledWrite({
    journal: j, operation: "submit_bid", objectId: expected().bid_id,
    intent: expected(), reconcile: async () => ({ state: "MISSING" }),
    broadcast: async () => { broadcasts += 1; return "0xnever"; },
    poll: async () => ({ finality: "FINALIZED" }),
    verify: async () => ({ state: "EXACT", digest: "chain-digest" }),
  });
  assert.equal(broadcasts, 0);
  const entry = await j.get("submit_bid", expected().bid_id);
  assert.equal(entry.status, "FINALIZED");
  assert.equal(entry.result_digest, "chain-digest");
});

test("read retry uses bounded exponential backoff and succeeds without mutation", async () => {
  const delays = [];
  let calls = 0;
  const value = await withReadRetry(async () => {
    calls += 1;
    if (calls < 3) throw new Error("ECONNRESET");
    return "ok";
  }, {
    operation: "eth_getBlockByNumber", maxAttempts: 4, baseDelayMs: 10,
    maxDelayMs: 100, jitterRatio: 0, sleep: async (ms) => delays.push(ms),
  });
  assert.equal(value, "ok");
  assert.deepEqual(delays, [10, 20]);
});

test("dead same-host journal owner is recovered after process loss", async (t) => {
  await fs.mkdir(ROOT, { recursive: true });
  const file = path.join(ROOT, `dead-owner-${crypto.randomUUID()}.jsonl`);
  await fs.writeFile(`${file}.lock`, JSON.stringify({
    pid: 2_147_483_647, hostname: os.hostname(),
    created_at_ms: Date.now(), context: {},
  }));
  const instance = new OperationJournal(file, {
    network: "testnet-bradbury", core: CORE, evaluator: EVALUATOR,
    tender_id: TENDER,
  });
  await instance.acquire();
  t.after(() => instance.release());
});

test("live journal owner is never displaced merely because lock is old", async () => {
  await fs.mkdir(ROOT, { recursive: true });
  const file = path.join(ROOT, `live-old-owner-${crypto.randomUUID()}.jsonl`);
  await fs.writeFile(`${file}.lock`, JSON.stringify({
    pid: process.pid, hostname: os.hostname(),
    created_at_ms: 1, context: {},
  }));
  const instance = new OperationJournal(file, {
    network: "testnet-bradbury", core: CORE, evaluator: EVALUATOR,
    tender_id: TENDER,
  }, { staleLockMs: 1 });
  await assert.rejects(() => instance.acquire(), /already locked/i);
  await fs.unlink(`${file}.lock`);
});
