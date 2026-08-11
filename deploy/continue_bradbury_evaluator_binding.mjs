/* Continue the reviewed Bradbury pair after a separately finalized Core deploy. */
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

const CORE = process.env.TENDERCOUNCIL_EXISTING_CORE || "";
const CORE_TX = process.env.TENDERCOUNCIL_EXISTING_CORE_TX || "";
const HEAD = process.env.TENDERCOUNCIL_EXPECTED_HEAD || "";
const CONFIRM = "CONTINUE_TENDERCOUNCIL_EVALUATOR_BINDING";
const VERSION = "tendercouncil.evaluator.v1";
const CHAIN_ID = 4221;
const DEPLOYER = "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7";
const MANIFEST = path.join(ROOT, "artifacts/tender_council_bradbury_replacement_deployment.json");

const file = {
  coreSource: path.join(ROOT, "contracts/tender_council_core.py"),
  coreArtifact: path.join(ROOT, "artifacts/tender_council_core_deployable.py"),
  evaluatorSource: path.join(ROOT, "contracts/tender_council_evaluator.py"),
  evaluatorArtifact: path.join(ROOT, "artifacts/tender_council_evaluator_deployable.py"),
  generator: path.join(ROOT, "tools/make_deployable.py"),
};

const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex");
const safe = (value) => JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const addressFrom = (receipt) => receipt?.data?.contract_address || receipt?.txDataDecoded?.contractAddress || receipt?.txDataDecoded?.contract_address || null;
const statusName = (value) => value?.statusName || value?.status || "UNKNOWN";
async function writeManifest(value) { await fs.writeFile(MANIFEST, `${JSON.stringify(value, null, 2)}\n`, "utf8"); }

async function hashes() {
  const entries = await Promise.all(Object.entries(file).map(async ([key, location]) => [key, await fs.readFile(location)]));
  const bytes = Object.fromEntries(entries);
  return {
    canonical_core_source_sha256: sha256(bytes.coreSource),
    deployable_core_artifact_sha256: sha256(bytes.coreArtifact),
    canonical_evaluator_source_sha256: sha256(bytes.evaluatorSource),
    deployable_evaluator_artifact_sha256: sha256(bytes.evaluatorArtifact),
    artifact_generator_sha256: sha256(bytes.generator),
    core_artifact_bytes: bytes.coreArtifact.length,
    evaluator_artifact_bytes: bytes.evaluatorArtifact.length,
    evaluatorArtifact: bytes.evaluatorArtifact,
  };
}

async function waitFinal(client, hash) {
  const accepted = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", fullTransaction: true, retries: 240, interval: 5000 });
  const finalized = await client.waitForTransactionReceipt({ hash, status: "FINALIZED", fullTransaction: true, retries: 720, interval: 5000 });
  if (statusName(finalized) !== "FINALIZED") throw new Error(`transaction did not finalize: ${hash}`);
  return { hash, accepted: safe(accepted), finalized: safe(finalized) };
}

async function read(client, address, functionName, args = []) {
  return safe(await client.readContract({ address, functionName, args }));
}

async function main() {
  if (process.env.TENDERCOUNCIL_CONTINUE_CONFIRM !== CONFIRM) throw new Error("explicit continuation confirmation missing");
  if (!HEAD || process.env.TENDERCOUNCIL_RELEASE_PREFLIGHT_OK !== HEAD) throw new Error("reviewed HEAD preflight token missing");
  if (!/^0x[0-9a-fA-F]{40}$/.test(CORE) || !/^0x[0-9a-fA-F]{64}$/.test(CORE_TX)) throw new Error("existing Core address/tx missing");
  const accountKey = await keytar.getPassword("genlayer-cli", "account:player3");
  if (!accountKey) throw new Error("deployment account player3 missing");
  const account = sdk.createAccount(accountKey);
  if (account.address.toLowerCase() !== DEPLOYER) throw new Error("deployment sender mismatch");
  const client = sdk.createClient({ chain: testnetBradbury, account });
  if (client.chain.id !== CHAIN_ID) throw new Error("wrong Bradbury chain");
  const h = await hashes();
  const bindingBefore = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  if (await read(client, CORE, "get_production_ready") !== false || bindingBefore.bound !== false || bindingBefore.address.toLowerCase() !== `0x${"0".repeat(40)}` || String(await read(client, CORE, "get_contract_balance")) !== "0") {
    throw new Error("Core is not in the expected finalized unbound state");
  }
  const coreTx = await client.getTransaction({ hash: CORE_TX });
  if (coreTx.statusName !== "FINALIZED" || coreTx.resultName !== "AGREE" || coreTx.txExecutionResultName !== "FINISHED_WITH_RETURN" || coreTx.txDataDecoded?.contractAddress?.toLowerCase() !== CORE.toLowerCase()) {
    throw new Error("existing Core finality/readback proof is insufficient");
  }
  const codeHash = `sha256:${h.deployable_evaluator_artifact_sha256}`;
  const manifest = JSON.parse(await fs.readFile(MANIFEST, "utf8"));
  manifest.core = { ...(manifest.core || {}), address: CORE, deployment_tx: CORE_TX, finality_recheck: { status: coreTx.statusName, result: coreTx.resultName, execution: coreTx.txExecutionResultName, created_timestamp: coreTx.createdTimestamp, finalized_observed_at_utc: new Date().toISOString(), contract_address: coreTx.txDataDecoded.contractAddress, validators: safe(coreTx.lastRound) } };
  manifest.steps = [...(manifest.steps || []), "core_finality_rechecked_after_runner_timeout"];
  await writeManifest(manifest);

  const evaluatorTx = await client.deployContract({ code: h.evaluatorArtifact, args: [CORE, VERSION], leaderOnly: false });
  const evaluatorReceipts = await waitFinal(client, evaluatorTx);
  const evaluator = addressFrom(evaluatorReceipts.finalized);
  if (!evaluator) throw new Error("Evaluator finalized receipt did not expose contract address");
  manifest.evaluator = { address: evaluator, deployment_tx: evaluatorTx, constructor_core: CORE, version: VERSION, artifact_bytes: h.evaluator_artifact_bytes, ...evaluatorReceipts };
  manifest.steps.push("evaluator_deployed_finalized");
  await writeManifest(manifest);
  const configuredCore = await read(client, evaluator, "get_core_address");
  const configuredVersion = await read(client, evaluator, "get_evaluator_version");
  if (configuredCore.toLowerCase() !== CORE.toLowerCase() || configuredVersion !== VERSION) throw new Error("Evaluator constructor readback failed");
  manifest.evaluator.constructor_readback = { core_address: configuredCore, version: configuredVersion };
  manifest.steps.push("evaluator_constructor_verified");
  await writeManifest(manifest);

  const bindEstimate = await client.simulateContract({ account, address: CORE, functionName: "bind_evaluator", args: [evaluator, VERSION, codeHash] });
  void bindEstimate;
  const bindingTx = await client.writeContract({ account, address: CORE, functionName: "bind_evaluator", args: [evaluator, VERSION, codeHash], value: 0n, leaderOnly: false });
  const bindingReceipts = await waitFinal(client, bindingTx);
  manifest.binding = { tx: bindingTx, evaluator_address: evaluator, version: VERSION, evaluator_code_hash: codeHash, ...bindingReceipts };
  manifest.steps.push("core_binding_finalized");
  const bindingAfter = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  const ready = await read(client, CORE, "get_production_ready");
  if (ready !== true || bindingAfter.bound !== true || bindingAfter.address.toLowerCase() !== evaluator.toLowerCase() || bindingAfter.version !== VERSION || bindingAfter.evaluator_code_hash !== codeHash) throw new Error("binding readback failed");
  manifest.final_readback = { get_production_ready: ready, binding: bindingAfter };
  manifest.completed_at_utc = new Date().toISOString();
  await writeManifest(manifest);
  console.log(JSON.stringify({ core: CORE, evaluator, binding: bindingTx, production_ready: ready, code_hash: codeHash }, null, 2));
}

try {
  await main();
} catch (error) {
  try {
    const manifest = JSON.parse(await fs.readFile(MANIFEST, "utf8"));
    manifest.failed_at_utc = new Date().toISOString();
    manifest.failure = String(error?.stack || error);
    await writeManifest(manifest);
  } catch { /* preserve the original failure if the manifest is unavailable */ }
  console.error(error?.stack || error);
  process.exitCode = 1;
}
