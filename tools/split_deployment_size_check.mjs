/* Local, no-RPC deployment encoding and safety-envelope check. */
import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { resolveGenlayerModulePaths } from "./genlayer_module_paths.mjs";

const {
  repositoryRoot: ROOT, sdkRoot: GENLAYER_JS, viem: VIEM,
} = resolveGenlayerModulePaths();
const OUTPUT = process.env.TENDERCOUNCIL_SPLIT_SIZE_OUTPUT || "artifacts/tender_council_split-size-budget.json";
const PREFERRED_TARGET = 40000;
const TARGET = Number(process.env.TENDERCOUNCIL_OUTER_SIZE_TARGET || 42000);
const SENDER = "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7";
const ZERO = "0x0000000000000000000000000000000000000000";
const [{ testnetBradbury }, genlayer, viem] = await Promise.all([
  import(pathToFileURL(`${GENLAYER_JS}/chains/index.js`)),
  import(pathToFileURL(`${GENLAYER_JS}/index.js`)),
  import(pathToFileURL(VIEM)),
]);
const add = testnetBradbury.consensusMainContract.abi.find((item) => item.type === "function" && item.name === "addTransaction");
const calldata = genlayer.abi.calldata;
const transactions = genlayer.abi.transactions;
function stats(hex) {
  const bytes = Buffer.from(hex.slice(2), "hex");
  const zero = bytes.reduce((sum, item) => sum + (item === 0 ? 1 : 0), 0);
  return { bytes: bytes.length, zero_bytes: zero, nonzero_bytes: bytes.length - zero };
}
function encode(source, args) {
  const ctor = calldata.encode(calldata.makeCalldataObject(undefined, args, undefined));
  const app = transactions.serialize([source, ctor, false]);
  const txArgs = [SENDER, ZERO, BigInt(testnetBradbury.defaultNumberOfInitialValidators), BigInt(testnetBradbury.defaultConsensusMaxRotations), app];
  if (add.inputs.length >= 6) txArgs.push(0n);
  const outer = viem.encodeFunctionData({ abi: [add], functionName: "addTransaction", args: txArgs });
  return { app, outer };
}
const componentsToEncode = [
  { path: "artifacts/tender_council_core_v21_deployable.py", args: [] },
  { path: "artifacts/tender_council_evaluator_v21_deployable.py", args: [SENDER, "tendercouncil.evaluator.v2.1"] },
];
const components = [];
for (const { path, args } of componentsToEncode) {
  const source = await fs.readFile(`${ROOT}/${path}`, "utf8");
  const encoded = encode(source, args);
  components.push({ path, constructor_args: args, source_utf8_bytes: Buffer.byteLength(source, "utf8"), app_data: stats(encoded.app), outer_deployment_data: stats(encoded.outer), preferred_target_outer_bytes: PREFERRED_TARGET, safety_target_outer_bytes: TARGET, within_preferred_target: stats(encoded.outer).bytes < PREFERRED_TARGET, within_target: stats(encoded.outer).bytes < TARGET });
}
const result = { generated_at_utc: new Date().toISOString(), chain: { name: testnetBradbury.name, chain_id: testnetBradbury.id }, preferred_target_outer_bytes: PREFERRED_TARGET, target_outer_bytes: TARGET, measured_historical_boundary: { accepted: 53316, failed: 53348 }, components };
await fs.writeFile(OUTPUT, `${JSON.stringify(result, null, 2)}\n`, "utf8");
for (const component of components) console.log(JSON.stringify(component));
if (components.some((component) => !component.within_target)) process.exitCode = 1;
