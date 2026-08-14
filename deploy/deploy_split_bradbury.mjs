/*
 * Reviewed, broadcast-capable Bradbury release entrypoint.
 *
 * This file is intentionally separate from deploy_split.py, which remains a
 * no-broadcast dry-run plan. It is invoked through the installed GenLayer CLI
 * script runner so the configured active account is used by GenLayer's own
 * programmatic client. It cannot broadcast without the explicit confirmation
 * environment variable below.
 */
import fs from "node:fs/promises";
import fsSync from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const VERSION = "tendercouncil.evaluator.v2";
const NETWORK = "testnet-bradbury";
const CHAIN_ID = 4221;
const RPC = "https://rpc-bradbury.genlayer.com";
const CONFIRM = "DEPLOY_TWO_CONTRACTS_TO_BRADBURY";
// The v2 pair gets its own manifest. writeManifest also runs from the failure
// path, so pointing this at an existing manifest would overwrite append-only
// historical deployment evidence on the first error.
const MANIFEST_PATH = path.join(ROOT, "artifacts/tender_council_bradbury_v2_deployment.json");

const files = {
  coreSource: path.join(ROOT, "contracts/tender_council_core.py"),
  coreArtifact: path.join(ROOT, "artifacts/tender_council_core_deployable.py"),
  evaluatorSource: path.join(ROOT, "contracts/tender_council_evaluator.py"),
  evaluatorArtifact: path.join(ROOT, "artifacts/tender_council_evaluator_deployable.py"),
  generator: path.join(ROOT, "tools/make_deployable.py"),
};

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function jsonSafe(value) {
  return JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
}

function statusName(receipt) {
  return receipt?.statusName || receipt?.status || "UNKNOWN";
}

function contractAddress(receipt) {
  return receipt?.data?.contract_address || receipt?.txDataDecoded?.contractAddress || receipt?.txDataDecoded?.contract_address || null;
}

async function readBytes(file) {
  return fs.readFile(file);
}

async function localHashes() {
  const [coreSource, coreArtifact, evaluatorSource, evaluatorArtifact, generator] = await Promise.all([
    readBytes(files.coreSource), readBytes(files.coreArtifact), readBytes(files.evaluatorSource),
    readBytes(files.evaluatorArtifact), readBytes(files.generator),
  ]);
  return {
    canonical_core_source_sha256: sha256(coreSource),
    deployable_core_artifact_sha256: sha256(coreArtifact),
    canonical_evaluator_source_sha256: sha256(evaluatorSource),
    deployable_evaluator_artifact_sha256: sha256(evaluatorArtifact),
    artifact_generator_sha256: sha256(generator),
    core_artifact_bytes: coreArtifact.length,
    evaluator_artifact_bytes: evaluatorArtifact.length,
    coreSource,
    evaluatorSource,
    coreArtifact,
    evaluatorArtifact,
  };
}

function runPreflight(sender, hashes) {
  const expectedHead = process.env.TENDERCOUNCIL_EXPECTED_HEAD || "";
  if (!expectedHead || process.env.TENDERCOUNCIL_RELEASE_PREFLIGHT_OK !== expectedHead) {
    throw new Error("release preflight token is missing or does not match reviewed HEAD");
  }
  if (sender.toLowerCase() !== "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7") throw new Error("release preflight sender mismatch");
  const header = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }';
  for (const [key, file] of Object.entries({ coreSource: files.coreSource, coreArtifact: files.coreArtifact, evaluatorSource: files.evaluatorSource, evaluatorArtifact: files.evaluatorArtifact })) {
    const bytes = fsSync.readFileSync(file);
    if (key.endsWith("Source") && bytes.toString("utf8").split(/\r?\n/, 1)[0] !== header) throw new Error(`${key} runner header mismatch`);
    if (sha256(bytes) !== hashes[key]) throw new Error(`${key} hash mismatch`);
    if (key.endsWith("Artifact") && bytes.length + 1024 >= 42000) throw new Error(`${key} exceeds conservative size envelope`);
  }
}

function gitHead() {
  const head = process.env.TENDERCOUNCIL_EXPECTED_HEAD || "";
  if (!head) throw new Error("reviewed Git HEAD token is missing");
  return head;
}

async function waitFinal(client, hash) {
  const accepted = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", retries: 240, interval: 5000 });
  const finalized = await client.waitForTransactionReceipt({ hash, status: "FINALIZED", retries: 720, interval: 5000 });
  if (statusName(finalized) !== "FINALIZED") throw new Error(`transaction did not finalize: ${hash}`);
  return { accepted: jsonSafe(accepted), finalized: jsonSafe(finalized) };
}

async function read(client, address, functionName, args = []) {
  return client.readContract({ address, functionName, args });
}

async function writeManifest(manifest) {
  await fs.writeFile(MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(`deployment_manifest=${MANIFEST_PATH}`);
}

export default async function deploySplitBradbury(client) {
  const account = client.account;
  const sender = account?.address;
  if (!sender) throw new Error("configured GenLayer client has no signing account");
  if (client.chain?.id !== CHAIN_ID) throw new Error("client chain is not Bradbury 4221");
  if ((client.chain?.name || "").toLowerCase().includes("bradbury") === false) throw new Error("client network is not Bradbury");
  if (process.env.TENDERCOUNCIL_BROADCAST_CONFIRM !== CONFIRM) {
    throw new Error(`broadcast disabled; set TENDERCOUNCIL_BROADCAST_CONFIRM=${CONFIRM}`);
  }

  const hashes = await localHashes();
  runPreflight(sender, {
    coreSource: hashes.canonical_core_source_sha256,
    coreArtifact: hashes.deployable_core_artifact_sha256,
    evaluatorSource: hashes.canonical_evaluator_source_sha256,
    evaluatorArtifact: hashes.deployable_evaluator_artifact_sha256,
  });
  const manifest = {
    mode: "BROADCAST_TWO_CONTRACTS",
    network: NETWORK,
    chain_id: CHAIN_ID,
    rpc: RPC,
    sender,
    git_commit: gitHead(),
    canonical_core_source_sha256: hashes.canonical_core_source_sha256,
    deployable_core_artifact_sha256: hashes.deployable_core_artifact_sha256,
    canonical_evaluator_source_sha256: hashes.canonical_evaluator_source_sha256,
    deployable_evaluator_artifact_sha256: hashes.deployable_evaluator_artifact_sha256,
    artifact_generator_sha256: hashes.artifact_generator_sha256,
    evaluator_schema_version: VERSION,
    steps: [],
  };

  try {
    const coreHash = await client.deployContract({ code: hashes.coreArtifact, args: [], leaderOnly: false });
    const coreReceipts = await waitFinal(client, coreHash);
    const coreAddress = contractAddress(coreReceipts.finalized);
    if (!coreAddress) throw new Error("Core finalized receipt did not expose contract address");
    manifest.core = { address: coreAddress, deployment_tx: coreHash, artifact_bytes: hashes.coreArtifact.length, ...coreReceipts };
    manifest.steps.push("core_deployed_finalized");

    const initialReady = await read(client, coreAddress, "get_production_ready");
    const initialBinding = JSON.parse(await read(client, coreAddress, "get_evaluator_binding"));
    const initialBalance = await read(client, coreAddress, "get_contract_balance");
    if (initialReady !== false || initialBinding.bound !== false || initialBinding.address.toLowerCase() !== "0x" + "0".repeat(40) || initialBinding.version !== "" || initialBinding.evaluator_code_hash !== "" || String(initialBalance) !== "0") {
      throw new Error("Core initial unconfigured readback failed");
    }
    manifest.core.initial_readback = { get_production_ready: initialReady, binding: initialBinding, balance: String(initialBalance) };
    manifest.steps.push("core_initial_state_verified");

    const evaluatorHash = await client.deployContract({ code: hashes.evaluatorArtifact, args: [coreAddress, VERSION], leaderOnly: false });
    const evaluatorReceipts = await waitFinal(client, evaluatorHash);
    const evaluatorAddress = contractAddress(evaluatorReceipts.finalized);
    if (!evaluatorAddress) throw new Error("Evaluator finalized receipt did not expose contract address");
    manifest.evaluator = { address: evaluatorAddress, deployment_tx: evaluatorHash, constructor_core: coreAddress, version: VERSION, artifact_bytes: hashes.evaluatorArtifact.length, ...evaluatorReceipts };
    manifest.steps.push("evaluator_deployed_finalized");

    const configuredCore = await read(client, evaluatorAddress, "get_core_address");
    const configuredVersion = await read(client, evaluatorAddress, "get_evaluator_version");
    if (configuredCore.toLowerCase() !== coreAddress.toLowerCase() || configuredVersion !== VERSION) throw new Error("Evaluator constructor readback failed");
    manifest.evaluator.constructor_readback = { core_address: configuredCore, version: configuredVersion };
    manifest.steps.push("evaluator_constructor_verified");

    const codeHash = `sha256:${hashes.deployable_evaluator_artifact_sha256}`;
    const bindHash = await client.writeContract({ address: coreAddress, functionName: "bind_evaluator", args: [evaluatorAddress, VERSION, codeHash], value: 0n, leaderOnly: false });
    const bindReceipts = await waitFinal(client, bindHash);
    manifest.binding = { tx: bindHash, evaluator_address: evaluatorAddress, version: VERSION, evaluator_code_hash: codeHash, ...bindReceipts };
    manifest.steps.push("core_binding_finalized");

    const finalBinding = JSON.parse(await read(client, coreAddress, "get_evaluator_binding"));
    const finalReady = await read(client, coreAddress, "get_production_ready");
    if (finalReady !== true || finalBinding.bound !== true || finalBinding.address.toLowerCase() !== evaluatorAddress.toLowerCase() || finalBinding.version !== VERSION || finalBinding.evaluator_code_hash !== codeHash) throw new Error("Core binding readback failed");
    manifest.final_readback = { get_production_ready: finalReady, binding: finalBinding };
    manifest.completed_at_utc = new Date().toISOString();
    await writeManifest(manifest);
    console.log(JSON.stringify(manifest, null, 2));
  } catch (error) {
    manifest.failed_at_utc = new Date().toISOString();
    manifest.failure = String(error?.stack || error);
    await writeManifest(manifest);
    throw error;
  }
}
