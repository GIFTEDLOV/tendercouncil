/*
 * TenderCouncil v2.1 EXISTING-PAIR binding recovery.
 *
 * The first v2.1 binding attempt (deploy/deploy_split_bradbury.mjs) reverted at
 * the OUTER EVM layer because bind_evaluator's first argument was passed as a
 * plain JavaScript address string. Core storage expects a GenLayer Address, so
 * GenVM saw a Python `str` and could not call `.as_bytes` on it. No GenLayer
 * consensus transaction was ever created; the Core/Evaluator pair is intact and
 * unbound.
 *
 * This script does NOT redeploy. It reuses the already-finalized v2.1 Core and
 * Evaluator, encodes the Evaluator address with the pinned SDK's
 * CalldataAddress(hexToBytes(...)) wrapper, proves the write with a
 * non-state-changing gen_call simulation, and only then broadcasts exactly one
 * binding write. It preserves the failed attempt #1 as forensic evidence.
 *
 * Phases:
 *   1. Reconcile the existing v2.1 manifest (identity fields must match).
 *   2. Re-verify Core + Evaluator deployment finality on chain.
 *   3. Verify Core is clean/unbound and Evaluator constructor references Core.
 *   4. Verify the frozen Evaluator artifact / code hash.
 *   5. Simulate bind_evaluator (gen_call). Failure => STOP, never broadcast.
 *   6. If TENDERCOUNCIL_BIND_CONFIRM is set: broadcast exactly one write,
 *      persisting the outer EVM hash and the GenLayer consensus hash before
 *      polling, then require finalization + a clean readback.
 *   Without the confirm token the script stops after a passing simulation
 *   (preflight-only mode).
 */
import fs from "node:fs/promises";
import crypto from "node:crypto";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SDK_ROOT = "C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist";
const sdk = await import(pathToFileURL(`${SDK_ROOT}/index.js`));
const { CalldataAddress } = await import(pathToFileURL(`${SDK_ROOT}/chunk-EY35NPSE.js`));
const { hexToBytes } = await import(pathToFileURL("C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/viem/_esm/index.js"));
const { testnetBradbury } = await import(pathToFileURL(`${SDK_ROOT}/chains/index.js`));
const keytar = createRequire(pathToFileURL("C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/dist/index.js"))("keytar");

// Frozen, reviewed v2.1 deployment identity. These are the already-finalized
// contracts; the recovery never derives or replaces them.
const CORE = "0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd";
const CORE_TX = "0x2cee5c4cb68b3ee97092c127e4688f24b54ffef1db9e7fe9b432922a0f1ce6ff";
const EVALUATOR = "0x023AB3434761715a531884Ca0852aC14beE03acE";
const EVALUATOR_TX = "0xdb7d159f7804f9626e61bf93ded39e8c1abdd3bf5c1f5ff1f6deb73a9862e261";
const FAILED_BINDING_EVM_TX = "0xf9526dcc579f2e4d143f69ba069f4182a2652f107d7aa4e8e4e29fa5cb2faa44";
const VERSION = "tendercouncil.evaluator.v2.1";
const EXPECTED_EVALUATOR_ARTIFACT_SHA256 = "e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b";
const CHAIN_ID = 4221;
const DEPLOYER = "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7";
const CONFIRM = "BIND_TENDERCOUNCIL_V21_PAIR";
const MANIFEST = path.join(ROOT, "artifacts/tender_council_bradbury_v21_deployment.json");
const EVALUATOR_ARTIFACT = path.join(ROOT, "artifacts/tender_council_evaluator_v21_deployable.py");
const ZERO = `0x${"0".repeat(40)}`;

const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex");
const safe = (value) => JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
const statusName = (value) => value?.statusName || value?.status_name || value?.status || "UNKNOWN";
const resultName = (value) => value?.resultName || value?.result_name || value?.result || "UNKNOWN";
const executionName = (value) => value?.txExecutionResultName || value?.tx_execution_result_name || value?.txExecutionResult || value?.tx_execution_result || "UNKNOWN";
const hasDV = (value) => Boolean(value?.deterministicViolation || value?.deterministic_violation) || resultName(value) === "DETERMINISTIC_VIOLATION" || executionName(value) === "DETERMINISTIC_VIOLATION";

async function writeManifest(value) {
  await fs.writeFile(MANIFEST, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function read(client, address, functionName, args = []) {
  return safe(await client.readContract({ address, functionName, args }));
}

/**
 * Find the outer EVM submission hash for a broadcast by locating the deployer's
 * transaction to the consensus contract at the exact nonce it consumed. Scans a
 * bounded window of recent blocks; returns null if not yet mined.
 */
async function reconcileOuterEvmTx(client, deployer, nonce) {
  const consensus = (client.chain.consensusMainContract?.address || "").toLowerCase();
  const from = deployer.toLowerCase();
  const latest = await client.getBlockNumber();
  const WINDOW = 400n;
  for (let b = latest; b > latest - WINDOW && b >= 0n; b--) {
    const block = await client.getBlock({ blockNumber: b, includeTransactions: true });
    for (const tx of block.transactions) {
      if (tx.from?.toLowerCase() === from && Number(tx.nonce) === Number(nonce)) {
        if ((tx.to || "").toLowerCase() !== consensus) throw new Error(`nonce ${nonce} tx target is not the consensus contract`);
        return tx.hash;
      }
    }
  }
  return null;
}

async function waitFinal(client, hash) {
  const accepted = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", fullTransaction: true, retries: 240, interval: 5000 });
  const finalized = await client.waitForTransactionReceipt({ hash, status: "FINALIZED", fullTransaction: true, retries: 720, interval: 5000 });
  if (statusName(finalized) !== "FINALIZED") throw new Error(`binding transaction did not finalize: ${hash}`);
  if (resultName(finalized) !== "AGREE" || executionName(finalized) !== "FINISHED_WITH_RETURN" || hasDV(finalized)) {
    throw new Error(`binding transaction outcome gate failed: status=${statusName(finalized)} result=${resultName(finalized)} execution=${executionName(finalized)} dv=${hasDV(finalized)}`);
  }
  return { accepted: safe(accepted), finalized: safe(finalized) };
}

async function main() {
  const HEAD = process.env.TENDERCOUNCIL_EXPECTED_HEAD || "";
  if (!HEAD || process.env.TENDERCOUNCIL_RELEASE_PREFLIGHT_OK !== HEAD) throw new Error("reviewed HEAD preflight token missing or mismatched");
  const broadcastRequested = process.env.TENDERCOUNCIL_BIND_CONFIRM === CONFIRM;

  // Account: existing locally configured GenLayer credential (never printed).
  const privateKey = await keytar.getPassword("genlayer-cli", "account:player3");
  if (!privateKey) throw new Error("deployment account player3 not present in local keystore");
  const account = sdk.createAccount(privateKey);
  if (account.address.toLowerCase() !== DEPLOYER) throw new Error("configured account is not the reviewed deployer/bootstrapper");
  const client = sdk.createClient({ chain: testnetBradbury, account });
  if (client.chain.id !== CHAIN_ID) throw new Error("client chain is not Bradbury 4221");

  // Phase 1: reconcile the existing manifest identity.
  const manifest = JSON.parse(await fs.readFile(MANIFEST, "utf8"));
  const identity = {
    sender: DEPLOYER,
    evaluator_schema_version: VERSION,
    deployable_evaluator_artifact_sha256: EXPECTED_EVALUATOR_ARTIFACT_SHA256,
  };
  if (manifest.sender?.toLowerCase() !== identity.sender) throw new Error("manifest sender mismatch");
  if (manifest.evaluator_schema_version !== identity.evaluator_schema_version) throw new Error("manifest evaluator schema version mismatch");
  if (manifest.deployable_evaluator_artifact_sha256 !== identity.deployable_evaluator_artifact_sha256) throw new Error("manifest frozen evaluator artifact hash mismatch");
  if (manifest.core?.address?.toLowerCase() !== CORE.toLowerCase()) throw new Error("manifest Core address mismatch");
  if (manifest.core?.deployment_tx !== CORE_TX) throw new Error("manifest Core deployment tx mismatch");
  if (manifest.evaluator?.address?.toLowerCase() !== EVALUATOR.toLowerCase()) throw new Error("manifest Evaluator address mismatch");
  if (manifest.evaluator?.deployment_tx !== EVALUATOR_TX) throw new Error("manifest Evaluator deployment tx mismatch");
  if (manifest.evaluator?.constructor_core?.toLowerCase() !== CORE.toLowerCase()) throw new Error("manifest Evaluator constructor_core mismatch");

  // If an earlier successful run already finished, do not touch anything.
  if (manifest.completed_at_utc && manifest.binding?.tx) {
    console.log("binding already completed; recovery is a no-op");
    console.log(JSON.stringify({ core: CORE, evaluator: EVALUATOR, binding: manifest.binding.tx, completed_at_utc: manifest.completed_at_utc }, null, 2));
    return;
  }

  // Phase 2: re-verify Core + Evaluator deployment finality on chain.
  const coreTx = await client.getTransaction({ hash: CORE_TX });
  if (coreTx.statusName !== "FINALIZED" || coreTx.resultName !== "AGREE" || coreTx.txExecutionResultName !== "FINISHED_WITH_RETURN" || coreTx.txDataDecoded?.contractAddress?.toLowerCase() !== CORE.toLowerCase()) {
    throw new Error(`Core deployment finality gate failed: status=${coreTx.statusName} result=${coreTx.resultName} execution=${coreTx.txExecutionResultName}`);
  }
  const evaluatorTx = await client.getTransaction({ hash: EVALUATOR_TX });
  if (evaluatorTx.statusName !== "FINALIZED" || evaluatorTx.resultName !== "AGREE" || evaluatorTx.txExecutionResultName !== "FINISHED_WITH_RETURN" || evaluatorTx.txDataDecoded?.contractAddress?.toLowerCase() !== EVALUATOR.toLowerCase()) {
    throw new Error(`Evaluator deployment finality gate failed: status=${evaluatorTx.statusName} result=${evaluatorTx.resultName} execution=${evaluatorTx.txExecutionResultName}`);
  }

  // Phase 3: verify Core is clean/unbound and Evaluator wiring.
  const bindingBefore = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  const readyBefore = await read(client, CORE, "get_production_ready");
  const balanceBefore = String(await read(client, CORE, "get_contract_balance"));
  if (readyBefore !== false || bindingBefore.bound !== false || bindingBefore.address.toLowerCase() !== ZERO || bindingBefore.version !== "" || bindingBefore.evaluator_code_hash !== "" || balanceBefore !== "0") {
    throw new Error(`Core is not clean/unbound: ready=${readyBefore} bound=${bindingBefore.bound} address=${bindingBefore.address} balance=${balanceBefore}`);
  }
  const evaluatorCore = await read(client, EVALUATOR, "get_core_address");
  const evaluatorVersion = await read(client, EVALUATOR, "get_evaluator_version");
  if (evaluatorCore.toLowerCase() !== CORE.toLowerCase() || evaluatorVersion !== VERSION) {
    throw new Error(`Evaluator constructor mismatch: core=${evaluatorCore} version=${evaluatorVersion}`);
  }

  // Phase 4: verify the frozen Evaluator artifact / code hash.
  const artifactBytes = await fs.readFile(EVALUATOR_ARTIFACT);
  const artifactHash = sha256(artifactBytes);
  if (artifactHash !== EXPECTED_EVALUATOR_ARTIFACT_SHA256) throw new Error(`frozen Evaluator artifact hash mismatch: ${artifactHash}`);
  const codeHash = `sha256:${artifactHash}`;

  // Correct pinned-SDK Address calldata encoding (the historically proven fix).
  const evaluatorArgument = new CalldataAddress(hexToBytes(EVALUATOR));

  // Preserve the failed attempt #1 as structured forensic evidence.
  if (!Array.isArray(manifest.binding_attempts)) {
    manifest.binding_attempts = [{
      attempt: 1,
      tool: "deploy/deploy_split_bradbury.mjs",
      outer_evm_tx: FAILED_BINDING_EVM_TX,
      genlayer_tx: null,
      status: "REVERTED",
      cause: "ADDRESS_CALLDATA_ENCODING",
      detail: "bind_evaluator first argument passed as raw JS address string; GenVM received Python str where Core storage expected GenLayer Address ('str' object has no attribute 'as_bytes').",
      failed_at_utc: manifest.failed_at_utc || null,
      evm_revert_error: manifest.failure || null,
    }];
    await writeManifest(manifest);
  }

  // Phase 5: non-state-changing simulation (gen_call). This exercises the exact
  // encode(makeCalldataObject(...)) path the real write uses, so it proves the
  // Address calldata encoding and every bind_evaluator guard before broadcast.
  let simulationResult;
  try {
    simulationResult = await client.simulateWriteContract({
      account,
      address: CORE,
      functionName: "bind_evaluator",
      args: [evaluatorArgument, VERSION, codeHash],
    });
  } catch (error) {
    manifest.binding_simulation = { ok: false, at_utc: new Date().toISOString(), error: String(error?.message || error) };
    await writeManifest(manifest);
    throw new Error(`SIMULATION FAILED — not broadcasting. ${String(error?.message || error)}`);
  }
  manifest.binding_simulation = {
    ok: true,
    at_utc: new Date().toISOString(),
    method: "gen_call/simulateWriteContract",
    function: "bind_evaluator",
    evaluator_address: EVALUATOR,
    version: VERSION,
    evaluator_code_hash: codeHash,
    decoded_return: safe(simulationResult ?? null),
  };
  await writeManifest(manifest);
  console.log(`SIMULATION_RESULT=PASS (bind_evaluator accepts Address ${EVALUATOR}, ${VERSION}, ${codeHash})`);

  if (!broadcastRequested) {
    console.log(`preflight-only: set TENDERCOUNCIL_BIND_CONFIRM=${CONFIRM} to broadcast the single recovery binding write`);
    return;
  }

  // Resume path: if a prior attempt-2 consensus tx was already persisted, poll
  // it instead of broadcasting a duplicate.
  let bindingTx = manifest.binding?.tx || null;
  let outerEvmTx = manifest.binding?.outer_evm_tx || null;
  let attempt2 = manifest.binding_attempts.find((a) => a.attempt === 2);

  if (!bindingTx) {
    // Guard: never double-broadcast if a prior attempt-2 record exists without a
    // finalized consensus tx (ambiguous partial). Require manual review — the
    // outer EVM tx can be reconciled from the persisted nonce instead.
    if (attempt2 && attempt2.status && attempt2.status !== "REVERTED") {
      throw new Error(`ambiguous prior attempt 2 (status=${attempt2.status}, genlayer_tx=${attempt2.genlayer_tx}); manual review required before re-broadcast`);
    }

    // Record the exact deployer nonce this write will consume, so the outer EVM
    // submission hash can be reconciled from chain deterministically. (The
    // pinned SDK's writeContract returns only the GenLayer consensus txId; the
    // local-account send path does not surface the outer EVM hash directly.)
    const nonce = Number(await client.getCurrentNonce({ address: account.address }));
    attempt2 = { attempt: 2, tool: "deploy/recover_v21_binding.mjs", encoding: "CalldataAddress(hexToBytes(EVALUATOR))", evm_nonce: nonce, outer_evm_tx: null, genlayer_tx: null, status: "BROADCASTING", broadcast_at_utc: new Date().toISOString() };
    manifest.binding_attempts.push(attempt2);
    await writeManifest(manifest);

    // Broadcast exactly ONE binding write with the correct Address encoding.
    bindingTx = await client.writeContract({
      account,
      address: CORE,
      functionName: "bind_evaluator",
      args: [evaluatorArgument, VERSION, codeHash],
      value: 0n,
      leaderOnly: false,
    });

    // Persist the GenLayer consensus tx id BEFORE polling.
    attempt2.genlayer_tx = bindingTx;
    attempt2.status = "CONSENSUS_SUBMITTED";
    manifest.binding = { tx: bindingTx, outer_evm_tx: null, evm_nonce: nonce, evaluator_address: EVALUATOR, version: VERSION, evaluator_code_hash: codeHash };
    await writeManifest(manifest);
    console.log(`RECOVERY_BINDING_GENLAYER_TX=${bindingTx}`);

    // Reconcile the outer EVM submission hash from the consumed nonce and record
    // it before polling. Non-fatal: the consensus tx is the authoritative id.
    try {
      outerEvmTx = await reconcileOuterEvmTx(client, account.address, nonce);
      if (outerEvmTx) {
        attempt2.outer_evm_tx = outerEvmTx;
        manifest.binding.outer_evm_tx = outerEvmTx;
        await writeManifest(manifest);
        console.log(`RECOVERY_BINDING_EVM_TX=${outerEvmTx}`);
      }
    } catch (error) {
      console.warn(`outer EVM tx reconciliation deferred: ${String(error?.message || error)}`);
    }
  } else {
    console.log(`resuming existing recovery binding consensus tx ${bindingTx}`);
  }

  // Poll to finalization and gate the outcome.
  const receipts = await waitFinal(client, bindingTx);
  if (attempt2) {
    attempt2.status = "FINALIZED";
    attempt2.result = resultName(receipts.finalized);
    attempt2.execution = executionName(receipts.finalized);
    attempt2.deterministic_violation = hasDV(receipts.finalized);
  }
  manifest.binding = { ...manifest.binding, tx: bindingTx, outer_evm_tx: manifest.binding?.outer_evm_tx || outerEvmTx, evaluator_address: EVALUATOR, version: VERSION, evaluator_code_hash: codeHash, ...receipts };
  if (!manifest.steps.includes("core_binding_finalized")) manifest.steps.push("core_binding_finalized");
  await writeManifest(manifest);

  // Fresh readback gate.
  const bindingAfter = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  const readyAfter = await read(client, CORE, "get_production_ready");
  const balanceAfter = String(await read(client, CORE, "get_contract_balance"));
  if (readyAfter !== true || bindingAfter.bound !== true || bindingAfter.address.toLowerCase() !== EVALUATOR.toLowerCase() || bindingAfter.version !== VERSION || bindingAfter.evaluator_code_hash !== codeHash || balanceAfter !== "0") {
    throw new Error(`post-binding readback failed: ready=${readyAfter} bound=${bindingAfter.bound} address=${bindingAfter.address} version=${bindingAfter.version} code_hash=${bindingAfter.evaluator_code_hash} balance=${balanceAfter}`);
  }
  manifest.final_readback = { get_production_ready: readyAfter, binding: bindingAfter, balance: balanceAfter, observed_at_utc: new Date().toISOString() };
  manifest.completed_at_utc = new Date().toISOString();
  await writeManifest(manifest);
  console.log(JSON.stringify({ core: CORE, evaluator: EVALUATOR, binding: bindingTx, outer_evm_tx: manifest.binding.outer_evm_tx, production_ready: readyAfter, code_hash: codeHash }, null, 2));
}

try {
  await main();
} catch (error) {
  try {
    const m = JSON.parse(await fs.readFile(MANIFEST, "utf8"));
    m.recovery_failed_at_utc = new Date().toISOString();
    m.recovery_failure = String(error?.stack || error);
    await writeManifest(m);
  } catch { /* preserve the original error if the manifest is unavailable */ }
  console.error(error?.stack || error);
  process.exitCode = 1;
}
