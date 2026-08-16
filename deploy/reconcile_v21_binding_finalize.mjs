/*
 * Reconcile + finalize the v2.1 recovery binding.
 *
 * The recovery binding (deploy/recover_v21_binding.mjs) DID broadcast and
 * succeed on chain: Core is bound and production_ready. However that script
 * crashed immediately after client.writeContract() returned, because its
 * sendRawTransaction interceptor did not fire for the local-account send path,
 * so attempt-2 was undefined when it tried to record the consensus tx. The
 * broadcast tx hashes were therefore never persisted.
 *
 * This step recovers those identifiers from chain (already reconciled: the
 * outer EVM tx at deployer nonce 97 -> the NewTransaction consensus txId),
 * persists them as binding attempt #2 alongside the preserved failed attempt
 * #1, waits for finalization, and records the final readback. It NEVER
 * broadcasts.
 */
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

const CORE = "0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd";
const EVALUATOR = "0x023AB3434761715a531884Ca0852aC14beE03acE";
const VERSION = "tendercouncil.evaluator.v2.1";
const EXPECTED_EVALUATOR_ARTIFACT_SHA256 = "e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b";
const CODE_HASH = `sha256:${EXPECTED_EVALUATOR_ARTIFACT_SHA256}`;
// Recovered + reconciled recovery-binding identifiers (attempt #2).
const RECOVERY_OUTER_EVM_TX = "0xb3c7be12c908f3141c06ffdfff597e83038e6c013768b06c31cacbf7778296fb";
const RECOVERY_GENLAYER_TX = "0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf";
const CHAIN_ID = 4221;
const DEPLOYER = "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7";
const MANIFEST = path.join(ROOT, "artifacts/tender_council_bradbury_v21_deployment.json");
const EVALUATOR_ARTIFACT = path.join(ROOT, "artifacts/tender_council_evaluator_v21_deployable.py");

const sha256 = (v) => crypto.createHash("sha256").update(v).digest("hex");
const safe = (v) => JSON.parse(JSON.stringify(v, (_, i) => typeof i === "bigint" ? i.toString() : i));
const statusName = (v) => v?.statusName || v?.status_name || v?.status || "UNKNOWN";
const resultName = (v) => v?.resultName || v?.result_name || v?.result || "UNKNOWN";
const executionName = (v) => v?.txExecutionResultName || v?.tx_execution_result_name || v?.txExecutionResult || v?.tx_execution_result || "UNKNOWN";
const hasDV = (v) => Boolean(v?.deterministicViolation || v?.deterministic_violation) || resultName(v) === "DETERMINISTIC_VIOLATION" || executionName(v) === "DETERMINISTIC_VIOLATION";
async function writeManifest(v) { await fs.writeFile(MANIFEST, `${JSON.stringify(v, null, 2)}\n`, "utf8"); }
async function read(client, address, fn, args = []) { return safe(await client.readContract({ address, functionName: fn, args })); }

async function main() {
  const artifactHash = sha256(await fs.readFile(EVALUATOR_ARTIFACT));
  if (artifactHash !== EXPECTED_EVALUATOR_ARTIFACT_SHA256) throw new Error(`frozen artifact hash mismatch: ${artifactHash}`);

  const key = await keytar.getPassword("genlayer-cli", "account:player3");
  if (!key) throw new Error("deployment account player3 missing");
  const account = sdk.createAccount(key);
  if (account.address.toLowerCase() !== DEPLOYER) throw new Error("account is not the deployer");
  const client = sdk.createClient({ chain: testnetBradbury, account });
  if (client.chain.id !== CHAIN_ID) throw new Error("wrong chain");

  const manifest = JSON.parse(await fs.readFile(MANIFEST, "utf8"));

  // Confirm on chain that the reconciled EVM tx maps to the consensus tx that
  // targets Core, so we persist the correct identifiers.
  const evmReceipt = await client.getTransactionReceipt({ hash: RECOVERY_OUTER_EVM_TX });
  if (evmReceipt.status !== "success" || evmReceipt.to?.toLowerCase() !== (testnetBradbury.consensusMainContract?.address || "").toLowerCase() || evmReceipt.from?.toLowerCase() !== DEPLOYER) {
    throw new Error("recovery outer EVM tx does not match expected consensus submission");
  }
  const gtx0 = await client.getTransaction({ hash: RECOVERY_GENLAYER_TX });
  if ((gtx0.recipient || "").toLowerCase() !== CORE.toLowerCase()) throw new Error("recovery consensus tx recipient is not Core");

  // Preserve failed attempt #1; add/refresh attempt #2 with both identifiers.
  if (!Array.isArray(manifest.binding_attempts)) manifest.binding_attempts = [];
  if (!manifest.binding_attempts.some((a) => a.attempt === 1)) {
    manifest.binding_attempts.unshift({
      attempt: 1,
      tool: "deploy/deploy_split_bradbury.mjs",
      outer_evm_tx: "0xf9526dcc579f2e4d143f69ba069f4182a2652f107d7aa4e8e4e29fa5cb2faa44",
      genlayer_tx: null,
      status: "REVERTED",
      cause: "ADDRESS_CALLDATA_ENCODING",
      detail: "bind_evaluator first argument passed as raw JS address string; GenVM received Python str where Core storage expected GenLayer Address ('str' object has no attribute 'as_bytes').",
      failed_at_utc: manifest.failed_at_utc || null,
      evm_revert_error: manifest.failure || null,
    });
  }
  let attempt2 = manifest.binding_attempts.find((a) => a.attempt === 2);
  if (!attempt2) {
    attempt2 = { attempt: 2 };
    manifest.binding_attempts.push(attempt2);
  }
  Object.assign(attempt2, {
    tool: "deploy/recover_v21_binding.mjs",
    encoding: "CalldataAddress(hexToBytes(EVALUATOR))",
    outer_evm_tx: RECOVERY_OUTER_EVM_TX,
    genlayer_tx: RECOVERY_GENLAYER_TX,
    hashes_recovered_from_chain: true,
    hash_recovery_note: "recover_v21_binding.mjs crashed after writeContract() returned (local-account sendRawTransaction interceptor did not fire); identifiers reconciled from deployer nonce 97 EVM tx -> NewTransaction consensus txId.",
  });
  manifest.binding = {
    ...(manifest.binding || {}),
    tx: RECOVERY_GENLAYER_TX,
    outer_evm_tx: RECOVERY_OUTER_EVM_TX,
    evaluator_address: EVALUATOR,
    version: VERSION,
    evaluator_code_hash: CODE_HASH,
  };
  // Persist identifiers BEFORE polling for finalization.
  await writeManifest(manifest);
  console.log(`persisted RECOVERY_BINDING_EVM_TX=${RECOVERY_OUTER_EVM_TX}`);
  console.log(`persisted RECOVERY_BINDING_GENLAYER_TX=${RECOVERY_GENLAYER_TX}`);

  // Wait for finalization and gate outcome.
  const accepted = await client.waitForTransactionReceipt({ hash: RECOVERY_GENLAYER_TX, status: "ACCEPTED", fullTransaction: true, retries: 240, interval: 5000 });
  const finalized = await client.waitForTransactionReceipt({ hash: RECOVERY_GENLAYER_TX, status: "FINALIZED", fullTransaction: true, retries: 720, interval: 5000 });
  if (statusName(finalized) !== "FINALIZED") throw new Error(`binding did not finalize: status=${statusName(finalized)}`);
  if (resultName(finalized) !== "AGREE" || executionName(finalized) !== "FINISHED_WITH_RETURN" || hasDV(finalized)) {
    throw new Error(`binding outcome gate failed: result=${resultName(finalized)} execution=${executionName(finalized)} dv=${hasDV(finalized)}`);
  }
  attempt2.status = "FINALIZED";
  attempt2.result = resultName(finalized);
  attempt2.execution = executionName(finalized);
  attempt2.deterministic_violation = hasDV(finalized);
  manifest.binding = { ...manifest.binding, accepted: safe(accepted), finalized: safe(finalized) };
  if (!Array.isArray(manifest.steps)) manifest.steps = [];
  if (!manifest.steps.includes("core_binding_finalized")) manifest.steps.push("core_binding_finalized");
  await writeManifest(manifest);

  // Fresh readback gate.
  const binding = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  const ready = await read(client, CORE, "get_production_ready");
  const balance = String(await read(client, CORE, "get_contract_balance"));
  if (ready !== true || binding.bound !== true || binding.address.toLowerCase() !== EVALUATOR.toLowerCase() || binding.version !== VERSION || binding.evaluator_code_hash !== CODE_HASH || balance !== "0") {
    throw new Error(`post-binding readback failed: ready=${ready} bound=${binding.bound} address=${binding.address} version=${binding.version} code_hash=${binding.evaluator_code_hash} balance=${balance}`);
  }
  manifest.final_readback = { get_production_ready: ready, binding, balance, observed_at_utc: new Date().toISOString() };
  manifest.completed_at_utc = new Date().toISOString();
  // Clear the transient recovery-crash markers now that the outcome is proven.
  delete manifest.recovery_failed_at_utc;
  delete manifest.recovery_failure;
  await writeManifest(manifest);
  console.log(JSON.stringify({ core: CORE, evaluator: EVALUATOR, binding: RECOVERY_GENLAYER_TX, outer_evm_tx: RECOVERY_OUTER_EVM_TX, production_ready: ready, code_hash: CODE_HASH, status: statusName(finalized), result: resultName(finalized), execution: executionName(finalized) }, null, 2));
}

try {
  await main();
} catch (error) {
  console.error(error?.stack || error);
  process.exitCode = 1;
}
