/* Controlled TenderCouncil Bradbury replacement deployment and E2E proof. */
import fs from "node:fs/promises";
import crypto from "node:crypto";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SDK_ROOT = "C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist";
const sdk = await import(pathToFileURL(`${SDK_ROOT}/index.js`));
const { testnetBradbury } = await import(pathToFileURL(`${SDK_ROOT}/chains/index.js`));
const keytar = createRequire(pathToFileURL("C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/dist/index.js"))("keytar");

const NETWORK = "testnet-bradbury";
const CHAIN_ID = 4221;
const VERSION = "tendercouncil.evaluator.v1";
const TENDER_ID = "analytics-dashboard-2026";
const RESPONSE_WINDOW = 7200;
const BUDGET = 80_000_000_000_000_000n;
const BIDDER_FUNDING = 20_000_000_000_000_000n;
const BRIEF_URL = "https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/brief.json";
const BRIEF_HASH = "sha256:44bb3d24956a4ea2d9a8828afc7f6cde822c7f0c06708aea3fa9f7d365a33f8e";
const FIXTURE_COMMIT = "a4dff59f3803198f6724a31392464cd5807dfa1d";
const BLOB_COMMIT = "fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7";
const CHALLENGE_COMMIT = "1c10be9fde812aba326d60db3fe9b6c0bb60e413";
const CHALLENGE_URL = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${CHALLENGE_COMMIT}/fixtures/live/challenge_a.json`;
const CHALLENGE_HASH = "sha256:699b727a8ce9a074f77a13d6b0d59a691463cd047d4562258e56be84c6145ca2";
const E2E_PATH = path.join(ROOT, "artifacts/tender_council_bradbury_e2e.json");
const REPLACEMENT_DEPLOYMENT_PATH = path.join(ROOT, "artifacts/tender_council_bradbury_replacement_deployment.json");
const LAST_FAILURE_PATH = path.join(ROOT, "artifacts/tender_council_bradbury_e2e_failure_2026-08-12T011155901Z.json");

// These are the five immutable bid envelopes already submitted before the
// transient RPC outage. They allow a recovery run to poll rather than resubmit.
const KNOWN_BID_TXS = {
  A: "0xce784b7ae81dd5fea3f1a0fe5440c9eef268e278031d207d2eb6281e0547d2b6",
  B: "0x436fdb7fdef1bad697c370f73c4fe33055ade0dc65d69e94c0beabb1d816c54e",
  C: "0xa8b8418648cc5af0b4f4cbc5fd2c8241a99d7e3372d9db17bbe60665da27eec9",
  D: "0xe50eb1f7ceec40d8239740c6ea892b3ca19a752a60f20c673ede7d74acfa0bd5",
  E: "0x45d2e566a7c1a4ac6a3966158aeb654a655dc956d11f0a2d4fd3faa2cb068223",
};

const BID_DEFS = [
  ["A", "bidder_a", 62_000_000_000_000_000n, 26, 90, "bid_a.json", "sha256:7400bb115fbdb4fa80b1c31910946cb90abe6b0d3d224f885ed99a672e7c6fbd", "a-capability|CAPABILITY|capability|1|https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/a_capability.json|sha256:999c266ed1dd81a07ea519d4fd997683c88f9be22e23b0c6995d963ddb51a153"],
  ["B", "bidder_b", 74_000_000_000_000_000n, 27, 120, "bid_b.json", "sha256:0b0d8be698b82ae285e6d0f3d5b2c83f71b618b3721ac6021bbea019428c8837", "b-capability|CAPABILITY|capability|1|https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/b_capability.json|sha256:b480be749f5462c9223adf51ccf1de9bf1eb2f039916e57727139f45e33cd0a0"],
  ["C", "bidder_c", 43_000_000_000_000_000n, 20, 90, "bid_c.json", "sha256:f17a5263e9c6edca7e361366bc64acc25ff4e43cc8cdb3eb9dd010e497cc0763", "c-capability|CAPABILITY|capability|1|https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/c_capability.json|sha256:42257f097c64c030b79a3203a8ebedea937c2c582898fe646c46576c9275908a"],
  ["D", "bidder_d", 87_000_000_000_000_000n, 22, 120, "bid_d.json", "sha256:d355065fc7fc8f0b963c3d475796f76d31841238aa60dcea0ba1502abe74babe", "d-capability|CAPABILITY|capability|1|https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/b_capability.json|sha256:b480be749f5462c9223adf51ccf1de9bf1eb2f039916e57727139f45e33cd0a0"],
  ["E", "bidder_e", 69_000_000_000_000_000n, 45, 120, "bid_e.json", "sha256:a8a72af7f1bab0dfcb1101581b87d78d49c590a8cacfad58570b55e6c1c7d859", "e-capability|CAPABILITY|capability|1|https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/fdb255d11f67f7ca449f3a2e7b6c204c03abfeb7/fixtures/live/blobs/a_capability.json|sha256:999c266ed1dd81a07ea519d4fd997683c88f9be22e23b0c6995d963ddb51a153"],
];

function jsonSafe(value) {
  return JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
}
function sha256(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function statusName(receipt) { return receipt?.statusName || receipt?.status || "UNKNOWN"; }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function parseJson(value) { return typeof value === "string" ? JSON.parse(value) : jsonSafe(value); }
function addressFrom(receipt) { return receipt?.data?.contract_address || receipt?.txDataDecoded?.contractAddress || receipt?.txDataDecoded?.contract_address || null; }

async function accountFor(name) {
  const privateKey = await keytar.getPassword("genlayer-cli", `account:${name}`);
  if (!privateKey) throw new Error(`keychain account missing: ${name}`);
  return sdk.createAccount(privateKey);
}
function clientFor(account) { return sdk.createClient({ chain: testnetBradbury, account }); }

async function waitStatus(client, hash, status) {
  console.log(`waiting ${status}: ${hash}`);
  const maxAttempts = status === "FINALIZED" ? 720 : 240;
  let lastError = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const receipt = await client.getTransaction({ hash });
      const current = statusName(receipt);
      if (current === status || (status === "ACCEPTED" && current === "FINALIZED")) return receipt;
      lastError = new Error(`transaction ${hash} is ${current}, waiting for ${status}`);
    } catch (error) {
      lastError = error;
      console.log(`genlayer_poll_error=${String(error?.shortMessage || error?.message || error)}`);
    }
    if (attempt % 2 === 0) console.log(`waiting ${status} attempt=${attempt}: ${hash}`);
    await sleep(5000);
  }
  throw new Error(`timed out waiting ${status}: ${hash}: ${String(lastError?.message || lastError)}`);
}
async function waitEvmFinal(client, hash) {
  for (let attempt = 1; attempt <= 720; attempt += 1) {
    try {
      const receipt = await client.request({ method: "eth_getTransactionReceipt", params: [hash] });
      if (receipt?.status === "0x1") return { hash, evm_receipt: jsonSafe(receipt), finality: "EVM_RECEIPT" };
      if (receipt?.status === "0x0") throw new Error(`native funding transfer reverted: ${hash}`);
    } catch (error) {
      if (String(error?.message || error).includes("reverted")) throw error;
      console.log(`evm_poll_error=${String(error?.shortMessage || error?.message || error)}`);
    }
    if (attempt % 2 === 0) console.log(`waiting EVM receipt: ${hash}`);
    await sleep(5000);
  }
  throw new Error(`native funding transfer did not receive a successful EVM receipt: ${hash}`);
}
async function waitAcceptedFinalized(client, hash) {
  const accepted = await waitStatus(client, hash, "ACCEPTED");
  const finalized = await waitStatus(client, hash, "FINALIZED");
  if (statusName(finalized) !== "FINALIZED") throw new Error(`not finalized: ${hash}`);
  return { hash, accepted: jsonSafe(accepted), finalized: jsonSafe(finalized) };
}
async function read(client, address, functionName, args = []) { return jsonSafe(await client.readContract({ address, functionName, args })); }
async function readMaybe(client, address, functionName, args = []) {
  for (let attempt = 1; attempt <= 12; attempt += 1) {
    try { return await read(client, address, functionName, args); }
    catch (error) {
      const message = String(error?.shortMessage || error?.message || error);
      const transient = /fetch failed|ENOTFOUND|ECONNRESET|ETIMEDOUT|timeout|network|503|502/i.test(message);
      if (!transient) return null;
      console.log(`read_poll_error=${message}`);
      await sleep(5000);
    }
  }
  throw new Error(`read did not recover: ${functionName}`);
}
async function writeHash(client, address, functionName, args = [], value = 0n) {
  return client.writeContract({ account: client.account, address, functionName, args, value, leaderOnly: false });
}
async function writeFinal(client, address, functionName, args = [], value = 0n) {
  const hash = await writeHash(client, address, functionName, args, value);
  return waitAcceptedFinalized(client, hash);
}
async function sendNativeHash(client, to, value) {
  return client.sendTransaction({ account: client.account, to, value, data: "0x" });
}
async function children(client, hash, label) {
  for (let attempt = 1; attempt <= 120; attempt += 1) {
    try {
      const ids = await client.getTriggeredTransactionIds({ hash });
      if (ids && ids.length) {
        console.log(`${label}_children=${JSON.stringify(ids)}`);
        return ids;
      }
    } catch (error) { console.log(`${label}_children_poll_error=${String(error)}`); }
    if (attempt % 2 === 0) console.log(`${label}_waiting_for_children_attempt=${attempt}`);
    await sleep(30_000);
  }
  throw new Error(`timed out waiting for child transaction of ${hash}`);
}
async function chainTime(client) {
  const block = await client.getBlock({ blockTag: "latest" });
  return Number(block.timestamp);
}
async function waitChainTime(client, target, label) {
  while (true) {
    const now = await chainTime(client);
    if (now >= target) return now;
    console.log(`${label}_chain_time=${now} target=${target} remaining=${target - now}`);
    await sleep(30_000);
  }
}
async function simulation(client, address, functionName, args) {
  try {
    await client.simulateContract({ account: client.account, address, functionName, args });
    return { supported: true, reverted: false };
  } catch (error) {
    return { supported: true, reverted: true, error: String(error?.shortMessage || error?.message || error) };
  }
}

async function sourceManifest() {
  const files = {
    coreSource: path.join(ROOT, "contracts/tender_council_core.py"),
    coreArtifact: path.join(ROOT, "artifacts/tender_council_core_deployable.py"),
    evaluatorSource: path.join(ROOT, "contracts/tender_council_evaluator.py"),
    evaluatorArtifact: path.join(ROOT, "artifacts/tender_council_evaluator_deployable.py"),
  };
  const out = {};
  for (const [key, file] of Object.entries(files)) {
    const bytes = await fs.readFile(file);
    out[key] = { path: path.relative(ROOT, file).replaceAll("\\", "/"), bytes: bytes.length, sha256: sha256(bytes) };
  }
  return out;
}

async function run() {
  if (process.env.TENDERCOUNCIL_E2E_CONFIRM !== "RUN_TENDERCOUNCIL_BRADBURY_E2E") throw new Error("explicit E2E confirmation missing");
  const bootstrap = await accountFor("player3");
  const deployClient = clientFor(bootstrap);
  if (deployClient.chain.id !== CHAIN_ID) throw new Error("wrong chain");
  const localAccounts = JSON.parse(await fs.readFile(path.join(ROOT, ".local/tendercouncil_bradbury_accounts.json"), "utf8")).accounts;
  if (localAccounts.length !== 5) throw new Error("five local bidder accounts required");
  const bidderAccounts = Object.fromEntries(localAccounts.map((item) => [item.label, sdk.createAccount(item.private_key)]));
  const bidders = Object.fromEntries(localAccounts.map((item) => [item.label, item.address]));
  const manifest = {
    release: { network: NETWORK, chain_id: CHAIN_ID, rpc: testnetBradbury.rpcUrls.default.http[0], deployment_wallet: bootstrap.address, bidder_addresses: bidders },
    fixtures: { blob_commit: BLOB_COMMIT, manifest_commit: FIXTURE_COMMIT, challenge_commit: CHALLENGE_COMMIT, brief_url: BRIEF_URL, brief_sha256: BRIEF_HASH, challenge_url: CHALLENGE_URL, challenge_sha256: CHALLENGE_HASH },
    failures: [],
    transactions: {},
  };
  try {
    if (process.env.TENDERCOUNCIL_USE_EXISTING_PAIR !== "USE_EXISTING_BOUND_PAIR") {
      throw new Error("E2E requires explicit reuse of the reviewed bound pair; deployment is a separate operation");
    }
    const replacement = JSON.parse(await fs.readFile(REPLACEMENT_DEPLOYMENT_PATH, "utf8"));
    if (replacement.core?.address?.toLowerCase() !== "0xaf12cf3b7225c94e6674255780b16adcfeb03e15" || replacement.evaluator?.address?.toLowerCase() !== "0xef30f069a8be376d40f18758b9bfda54d7c04ec7" || replacement.final_readback?.get_production_ready !== true) {
      throw new Error("reviewed bound replacement pair is missing or does not match the approved live pair");
    }
    manifest.release.git_commit = replacement.git_commit;
    manifest.release.canonical_core_source_sha256 = replacement.canonical_core_source_sha256;
    manifest.release.deployable_core_artifact_sha256 = replacement.deployable_core_artifact_sha256;
    manifest.release.canonical_evaluator_source_sha256 = replacement.canonical_evaluator_source_sha256;
    manifest.release.deployable_evaluator_artifact_sha256 = replacement.deployable_evaluator_artifact_sha256;
    manifest.core = replacement.core;
    manifest.evaluator = replacement.evaluator;
    manifest.binding = replacement.binding;
    try {
      const prior = JSON.parse(await fs.readFile(LAST_FAILURE_PATH, "utf8"));
      manifest.recovery = { prior_failure_artifact: path.relative(ROOT, LAST_FAILURE_PATH).replaceAll("\\", "/"), prior_failures: prior.failures || [], prior_transactions: prior.transactions || {} };
      manifest.transactions = jsonSafe(prior.transactions || {});
    } catch {
      manifest.transactions = {};
    }
    const core = replacement.core.address;
    const evaluator = replacement.evaluator.address;
    const readClient = sdk.createClient({ chain: testnetBradbury });
    const buyer = deployClient;
    manifest.live_binding = { production_ready: await read(readClient, core, "get_production_ready"), binding: parseJson(await read(readClient, core, "get_evaluator_binding")), evaluator_core: await read(readClient, evaluator, "get_core_address"), evaluator_version: await read(readClient, evaluator, "get_evaluator_version"), core_balance: String(await read(readClient, core, "get_contract_balance")) };
    if (!manifest.live_binding.production_ready || manifest.live_binding.binding?.bound !== true || manifest.live_binding.binding?.address?.toLowerCase() !== evaluator.toLowerCase() || manifest.live_binding.evaluator_core?.toLowerCase() !== core.toLowerCase() || manifest.live_binding.evaluator_version !== VERSION) throw new Error("replacement binding readback failed");

    manifest.funding = [];
    for (const item of localAccounts) {
      const currentBalance = await buyer.getBalance({ address: item.address, blockTag: "latest" });
      if (currentBalance >= BIDDER_FUNDING) {
        manifest.funding.push({ bidder: item.address, amount_wei: BIDDER_FUNDING.toString(), existing_balance_wei: String(currentBalance), skipped_existing_funding: true, note: "preserved from an earlier interrupted funding phase" });
        continue;
      }
      const hash = await sendNativeHash(buyer, item.address, BIDDER_FUNDING);
      const tx = await waitEvmFinal(buyer, hash);
      manifest.funding.push({ bidder: item.address, amount_wei: BIDDER_FUNDING.toString(), ...tx });
    }

    let currentTender = await readMaybe(readClient, core, "get_tender", [TENDER_ID]);
    if (!currentTender) {
      const deadline = (await chainTime(readClient)) + 21_600;
      const create = await writeFinal(buyer, core, "create_tender", [TENDER_ID, "Analytics Dashboard Development", BRIEF_URL, BRIEF_HASH, BUDGET, 30, 90, deadline, RESPONSE_WINDOW, "authentication;CSV export;responsive/mobile support;dashboard/chart functionality", 35, 20, 20, 15, 10, "capability:required;delivery:optional;support:optional;technical:optional"], BUDGET);
      manifest.transactions.create_tender = create;
      currentTender = await read(readClient, core, "get_tender", [TENDER_ID]);
    }
    manifest.tender = { tender_id: TENDER_ID, budget_gen: "0.08", budget_wei: BUDGET.toString(), max_delivery_days: 30, min_support_days: 90, bidding_deadline: Number(currentTender.bidding_deadline), response_window_seconds: Number(currentTender.response_window_seconds), rubric: { technical: 35, delivery: 20, price: 20, capability: 15, support: 10 }, existing_tender_resumed: Boolean(manifest.recovery) };
    if (currentTender.status === "DRAFT") {
      const open = await writeFinal(buyer, core, "open_tender", [TENDER_ID]);
      manifest.transactions.open_tender = open;
      currentTender = await read(readClient, core, "get_tender", [TENDER_ID]);
    }
    if (!["OPEN", "CLOSED", "EVALUATING", "PROVISIONAL_AWARD", "RESPONSE_WINDOW", "REVIEWING_CHALLENGES", "AWARDED", "SETTLED", "NO_VALID_BID"].includes(currentTender.status)) throw new Error(`unexpected existing tender status: ${currentTender.status}`);
    manifest.tender.open_readback = currentTender;

    manifest.bids = [];
    const bidHashes = [];
    for (const [id, label, price, delivery, support, file, proposalHash, commitment] of BID_DEFS) {
      const address = bidders[label];
      const client = clientFor(bidderAccounts[label]);
      const proposalUrl = `https://raw.githubusercontent.com/GIFTEDLOV/tendercouncil/${FIXTURE_COMMIT}/fixtures/live/manifests/${file}`;
      const bidId = `bid-${id.toLowerCase()}`;
      const existingBid = await readMaybe(readClient, core, "get_bid", [bidId]);
      if (existingBid) {
        bidHashes.push({ id, label, address, hash: KNOWN_BID_TXS[id], client, price, delivery, support, proposalUrl, proposalHash, commitment, existing: existingBid });
        console.log(`bid_existing=${id}`);
      } else {
        const hash = KNOWN_BID_TXS[id];
        if (!hash) throw new Error(`missing known immutable bid transaction for ${id}`);
        bidHashes.push({ id, label, address, hash, client, price, delivery, support, proposalUrl, proposalHash, commitment });
        console.log(`bid_recovery_poll=${id}:${hash}`);
      }
    }
    for (const item of bidHashes) {
      const tx = item.existing ? { hash: item.hash, existing_onchain: true } : await waitAcceptedFinalized(item.client, item.hash);
      const onchain = item.existing || await read(readClient, core, "get_bid", [`bid-${item.id.toLowerCase()}`]);
      if (!onchain || onchain.bidder?.toLowerCase() !== item.address.toLowerCase() || String(onchain.price_wei) !== item.price.toString()) throw new Error(`bid readback mismatch: ${item.id}`);
      manifest.bids.push({ bid_id: `bid-${item.id.toLowerCase()}`, bidder: item.address, price_wei: item.price.toString(), delivery_days: item.delivery, support_days: item.support, proposal_url: item.proposalUrl, proposal_sha256: item.proposalHash, evidence_commitment: item.commitment, ...tx });
    }
    manifest.tender.after_bids = await read(readClient, core, "get_tender", [TENDER_ID]);

    await waitChainTime(readClient, deadline + 1, "bidding_deadline");
    manifest.transactions.close_tender = await writeFinal(buyer, core, "close_tender", [TENDER_ID]);
    const closedSnapshot = await read(readClient, core, "get_closed_snapshot", [TENDER_ID]);
    const closedTender = await read(readClient, core, "get_tender", [TENDER_ID]);
    manifest.snapshot = { canonical_json: closedSnapshot, independent_sha256: `sha256:${sha256(Buffer.from(closedSnapshot, "utf8"))}`, onchain_digest: closedTender.closed_snapshot_digest };
    if (manifest.snapshot.independent_sha256 !== manifest.snapshot.onchain_digest) throw new Error("closed snapshot digest mismatch");

    manifest.transactions.start_evaluation = await writeFinal(buyer, core, "start_evaluation", [TENDER_ID]);
    const evalChildren = await children(readClient, manifest.transactions.start_evaluation.hash, "evaluation_parent");
    manifest.transactions.evaluator_job = await waitAcceptedFinalized(readClient, evalChildren[0]);
    const callbackChildren = await children(readClient, evalChildren[0], "evaluator_job");
    manifest.transactions.evaluation_callback = await waitAcceptedFinalized(readClient, callbackChildren[0]);
    const resultPayload = await read(readClient, evaluator, "get_evaluation_result", [TENDER_ID, closedTender.evaluation_nonce]);
    manifest.evaluation = { result_digest: `sha256:${sha256(Buffer.from(resultPayload, "utf8"))}`, onchain_result_digest: (await read(readClient, core, "get_tender", [TENDER_ID])).evaluation_result_digest, bounded_result: parseJson(resultPayload), parent: manifest.transactions.start_evaluation.hash, evaluator_job: evalChildren[0], callback: callbackChildren[0] };
    const result = manifest.evaluation.bounded_result;
    if (result.winner_bid_id !== "bid-b" || result.valid_bid_ids.sort().join(",") !== "bid-a,bid-b" || !result.semantic_disqualified_bid_ids.includes("bid-c") || !result.deterministic_disqualified_bid_ids.includes("bid-d") || !result.deterministic_disqualified_bid_ids.includes("bid-e")) throw new Error("canonical comparative result did not meet required classifications");

    manifest.transactions.start_response_window = await writeFinal(buyer, core, "start_response_window", [TENDER_ID]);
    let responseTender = await read(readClient, core, "get_tender", [TENDER_ID]);
    manifest.response = { start: responseTender.response_window_start, end: responseTender.response_window_end, duration: RESPONSE_WINDOW, early_advance_simulation: await simulation(buyer, core, "advance_after_response", [TENDER_ID]), early_settlement_simulation: await simulation(buyer, core, "settle_award", [TENDER_ID]) };
    if (!manifest.response.early_advance_simulation.reverted || !manifest.response.early_settlement_simulation.reverted) throw new Error("response-window early-action simulation did not revert");

    const challengeClient = clientFor(bidderAccounts.bidder_a);
    manifest.transactions.challenge = await writeFinal(challengeClient, core, "submit_challenge", ["challenge-a-rubric", TENDER_ID, "RUBRIC_MISAPPLIED", "bid-b", "", CHALLENGE_URL, CHALLENGE_HASH]);
    manifest.challenge = { challenger: bidders.bidder_a, reason_code: "RUBRIC_MISAPPLIED", target_bid_id: "bid-b", url: CHALLENGE_URL, sha256: CHALLENGE_HASH, state: (await read(readClient, core, "get_challenge", ["challenge-a-rubric"])).status };
    if (manifest.challenge.state !== "ADMITTED") throw new Error("challenge was not admitted");

    await waitChainTime(readClient, Number(responseTender.response_window_end) + 1, "response_window");
    manifest.transactions.advance_after_response = await writeFinal(buyer, core, "advance_after_response", [TENDER_ID]);
    const reviewChildren = await children(readClient, manifest.transactions.advance_after_response.hash, "review_parent");
    manifest.transactions.review_job = await waitAcceptedFinalized(readClient, reviewChildren[0]);
    const reviewCallbackChildren = await children(readClient, reviewChildren[0], "review_job");
    manifest.transactions.review_callback = await waitAcceptedFinalized(readClient, reviewCallbackChildren[0]);
    const reviewedTender = await read(readClient, core, "get_tender", [TENDER_ID]);
    const reviewPayload = await read(readClient, evaluator, "get_review_result", [TENDER_ID, reviewedTender.review_nonce]);
    manifest.review = { review_nonce: reviewedTender.review_nonce, challenge_set_digest: reviewedTender.challenge_set_digest, bounded_result: parseJson(reviewPayload), result_digest: `sha256:${sha256(Buffer.from(reviewPayload, "utf8"))}`, evaluator_job: reviewChildren[0], callback: reviewCallbackChildren[0] };
    if (manifest.review.bounded_result.decision !== "UPHOLD" || manifest.review.bounded_result.winner_bid_id !== "bid-b") throw new Error("canonical challenge review did not uphold B");

    const awarded = await read(readClient, core, "get_tender", [TENDER_ID]);
    if (awarded.status !== "AWARDED" || awarded.final_winner !== "bid-b") throw new Error("final award readback failed");
    manifest.settlement = { before: parseJson(await read(readClient, core, "get_settlement_accounting", [TENDER_ID])), winner: "bid-b", winner_payout_amount: "74000000000000000", buyer_refund_amount: "6000000000000000" };
    manifest.transactions.settle_award = await writeFinal(buyer, core, "settle_award", [TENDER_ID]);
    const payoutChildren = await children(readClient, manifest.transactions.settle_award.hash, "payout_parent");
    manifest.transactions.payout_transfer = await waitAcceptedFinalized(readClient, payoutChildren[0]);
    manifest.settlement.payout_pending = parseJson(await read(readClient, core, "get_settlement_accounting", [TENDER_ID]));
    manifest.transactions.confirm_settlement = await writeFinal(buyer, core, "confirm_settlement", [TENDER_ID]);
    const refundChildren = await children(readClient, manifest.transactions.confirm_settlement.hash, "refund_parent");
    manifest.transactions.refund_transfer = await waitAcceptedFinalized(readClient, refundChildren[0]);
    manifest.settlement.refund_pending = parseJson(await read(readClient, core, "get_settlement_accounting", [TENDER_ID]));
    manifest.transactions.confirm_refund = await writeFinal(buyer, core, "confirm_refund", [TENDER_ID]);
    manifest.settlement.after = parseJson(await read(readClient, core, "get_settlement_accounting", [TENDER_ID]));
    manifest.settlement.final_tender = await read(readClient, core, "get_tender", [TENDER_ID]);
    manifest.settlement.final_core_balance_wei = String(await read(readClient, core, "get_contract_balance"));
    manifest.source = await sourceManifest();
    manifest.completed_at_utc = new Date().toISOString();
    await fs.writeFile(E2E_PATH, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ status: "E2E_COMPLETE", e2e_manifest: E2E_PATH, core, evaluator, winner: "bid-b", final_core_balance_wei: manifest.settlement.final_core_balance_wei }, null, 2));
  } catch (error) {
    manifest.failures.push({ at_utc: new Date().toISOString(), error: String(error?.stack || error) });
    manifest.source = await sourceManifest();
    const failurePath = path.join(ROOT, `artifacts/tender_council_bradbury_e2e_failure_${new Date().toISOString().replaceAll(":", "").replaceAll(".", "")}.json`);
    await fs.writeFile(failurePath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    console.error(JSON.stringify({ status: "E2E_FAILED", e2e_failure_manifest: failurePath, failure: String(error?.stack || error) }, null, 2));
    throw error;
  }
}

await run();
