/* Bind one already-finalized replacement Evaluator to one already-finalized Core. */
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
const EVALUATOR = process.env.TENDERCOUNCIL_EXISTING_EVALUATOR || "";
const EVALUATOR_TX = process.env.TENDERCOUNCIL_EXISTING_EVALUATOR_TX || "";
const EVALUATOR_EVM_TX = process.env.TENDERCOUNCIL_EXISTING_EVALUATOR_EVM_TX || "";
const HEAD = process.env.TENDERCOUNCIL_EXPECTED_HEAD || "";
const VERSION = "tendercouncil.evaluator.v1";
const CHAIN_ID = 4221;
const DEPLOYER = "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7";
const MANIFEST = path.join(ROOT, "artifacts/tender_council_bradbury_replacement_deployment.json");
const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex");
const safe = (value) => JSON.parse(JSON.stringify(value, (_, item) => typeof item === "bigint" ? item.toString() : item));
const statusName = (value) => value?.statusName || value?.status || "UNKNOWN";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function writeManifest(value) { await fs.writeFile(MANIFEST, `${JSON.stringify(value, null, 2)}\n`, "utf8"); }
async function read(client, address, functionName, args = []) { return safe(await client.readContract({ address, functionName, args })); }
async function waitFinal(client, hash) {
  const accepted = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", fullTransaction: true, retries: 240, interval: 5000 });
  const finalized = await client.waitForTransactionReceipt({ hash, status: "FINALIZED", fullTransaction: true, retries: 720, interval: 5000 });
  if (statusName(finalized) !== "FINALIZED") throw new Error(`transaction did not finalize: ${hash}`);
  return { hash, accepted: safe(accepted), finalized: safe(finalized) };
}
async function main() {
  if (process.env.TENDERCOUNCIL_BIND_CONFIRM !== "BIND_TENDERCOUNCIL_EXISTING_PAIR") throw new Error("explicit binding confirmation missing");
  if (!HEAD || process.env.TENDERCOUNCIL_RELEASE_PREFLIGHT_OK !== HEAD) throw new Error("reviewed HEAD preflight token missing");
  for (const [name, value, pattern] of [["Core", CORE, /^0x[0-9a-fA-F]{40}$/], ["Core tx", CORE_TX, /^0x[0-9a-fA-F]{64}$/], ["Evaluator", EVALUATOR, /^0x[0-9a-fA-F]{40}$/], ["Evaluator tx", EVALUATOR_TX, /^0x[0-9a-fA-F]{64}$/], ["Evaluator EVM tx", EVALUATOR_EVM_TX, /^0x[0-9a-fA-F]{64}$/]]) if (!pattern.test(value)) throw new Error(`${name} is missing or malformed`);
  const privateKey = await keytar.getPassword("genlayer-cli", "account:player3");
  if (!privateKey) throw new Error("deployment account player3 missing");
  const account = sdk.createAccount(privateKey);
  if (account.address.toLowerCase() !== DEPLOYER) throw new Error("deployment sender mismatch");
  const client = sdk.createClient({ chain: testnetBradbury, account });
  if (client.chain.id !== CHAIN_ID) throw new Error("wrong chain");
  const artifact = await fs.readFile(path.join(ROOT, "artifacts/tender_council_evaluator_deployable.py"));
  const codeHash = `sha256:${sha256(artifact)}`;
  const coreTx = await client.getTransaction({ hash: CORE_TX });
  const evaluatorTx = await client.getTransaction({ hash: EVALUATOR_TX });
  if (coreTx.statusName !== "FINALIZED" || coreTx.txDataDecoded?.contractAddress?.toLowerCase() !== CORE.toLowerCase()) throw new Error("Core finality mismatch");
  if (evaluatorTx.statusName !== "FINALIZED" || evaluatorTx.txDataDecoded?.contractAddress?.toLowerCase() !== EVALUATOR.toLowerCase() || evaluatorTx.resultName !== "AGREE" || evaluatorTx.txExecutionResultName !== "FINISHED_WITH_RETURN") throw new Error("Evaluator finality mismatch");
  const binding = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  if (await read(client, CORE, "get_production_ready") !== false || binding.bound !== false || binding.address.toLowerCase() !== `0x${"0".repeat(40)}` || String(await read(client, CORE, "get_contract_balance")) !== "0") throw new Error("Core is not unbound and empty");
  if ((await read(client, EVALUATOR, "get_core_address")).toLowerCase() !== CORE.toLowerCase() || await read(client, EVALUATOR, "get_evaluator_version") !== VERSION) throw new Error("Evaluator constructor mismatch");
  const manifest = JSON.parse(await fs.readFile(MANIFEST, "utf8"));
  manifest.evaluator = { ...(manifest.evaluator || {}), address: EVALUATOR, deployment_tx: EVALUATOR_TX, evm_deployment_tx: EVALUATOR_EVM_TX, constructor_core: CORE, version: VERSION, finalized_recheck: { status: evaluatorTx.statusName, result: evaluatorTx.resultName, execution: evaluatorTx.txExecutionResultName, created_timestamp: evaluatorTx.createdTimestamp, observed_at_utc: new Date().toISOString(), contract_address: evaluatorTx.txDataDecoded.contractAddress, validators: safe(evaluatorTx.lastRound) } };
  manifest.steps = [...(manifest.steps || []), "evaluator_finality_rechecked"];
  await writeManifest(manifest);
  await client.simulateContract({ account, address: CORE, functionName: "bind_evaluator", args: [EVALUATOR, VERSION, codeHash] });
  const bindingTx = await client.writeContract({ account, address: CORE, functionName: "bind_evaluator", args: [EVALUATOR, VERSION, codeHash], value: 0n, leaderOnly: false });
  const receipts = await waitFinal(client, bindingTx);
  const finalBinding = JSON.parse(await read(client, CORE, "get_evaluator_binding"));
  const ready = await read(client, CORE, "get_production_ready");
  if (ready !== true || finalBinding.bound !== true || finalBinding.address.toLowerCase() !== EVALUATOR.toLowerCase() || finalBinding.version !== VERSION || finalBinding.evaluator_code_hash !== codeHash) throw new Error("binding readback failed");
  manifest.binding = { tx: bindingTx, evaluator_address: EVALUATOR, version: VERSION, evaluator_code_hash: codeHash, ...receipts };
  manifest.steps.push("core_binding_finalized");
  manifest.final_readback = { get_production_ready: ready, binding: finalBinding };
  manifest.completed_at_utc = new Date().toISOString();
  await writeManifest(manifest);
  console.log(JSON.stringify({ core: CORE, evaluator: EVALUATOR, binding: bindingTx, production_ready: ready, code_hash: codeHash }, null, 2));
}
try { await main(); } catch (error) { try { const m = JSON.parse(await fs.readFile(MANIFEST, "utf8")); m.failed_at_utc = new Date().toISOString(); m.failure = String(error?.stack || error); await writeManifest(m); } catch {} console.error(error?.stack || error); process.exitCode = 1; }
