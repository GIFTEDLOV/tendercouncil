/* Estimate-only probe for the two generated TenderCouncil deployments. */
import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { resolveGenlayerModulePaths } from "./genlayer_module_paths.mjs";

const {
  repositoryRoot: ROOT, sdkRoot: GENLAYER_JS, viem: VIEM,
} = resolveGenlayerModulePaths();
const RPC = process.env.BRADBURY_RPC || "https://rpc-bradbury.genlayer.com";
const SENDER = (process.env.BRADBURY_PROBE_SENDER ||
  "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7").toLowerCase();
const OUTPUT = process.env.BRADBURY_SPLIT_PROBE_OUTPUT ||
  "artifacts/bradbury-split-deployment-probe.json";
const COMPONENTS = [
  { path: "artifacts/tender_council_core_deployable.py", args: [] },
  {
    path: "artifacts/tender_council_evaluator_deployable.py",
    args: [SENDER, "tendercouncil.evaluator.v2"],
  },
];
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const [{ testnetBradbury }, genlayer, viem] = await Promise.all([
  import(pathToFileURL(`${GENLAYER_JS}/chains/index.js`)),
  import(pathToFileURL(`${GENLAYER_JS}/index.js`)),
  import(pathToFileURL(VIEM)),
]);
const calldata = genlayer.abi.calldata;
const transactions = genlayer.abi.transactions;
const addTransaction = testnetBradbury.consensusMainContract.abi.find(
  (item) => item.type === "function" && item.name === "addTransaction",
);
const READ_METHODS = new Set(["eth_chainId", "eth_blockNumber", "eth_gasPrice", "eth_getBlockByNumber", "eth_estimateGas"]);

async function rpc(method, params = []) {
  if (!READ_METHODS.has(method)) throw new Error(`non-read method attempted: ${method}`);
  const response = await fetch(RPC, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params }),
  });
  return { http_status: response.status, ...(await response.json()) };
}

function stats(hex) {
  const bytes = Buffer.from(hex.slice(2), "hex");
  const zero = bytes.reduce((sum, value) => sum + (value === 0 ? 1 : 0), 0);
  return { bytes: bytes.length, zero_bytes: zero, nonzero_bytes: bytes.length - zero };
}

function encode(source, args) {
  const constructorBytes = calldata.encode(calldata.makeCalldataObject(undefined, args, undefined));
  const appData = transactions.serialize([source, constructorBytes, false]);
  const txArgs = [SENDER, ZERO_ADDRESS,
    BigInt(testnetBradbury.defaultNumberOfInitialValidators),
    BigInt(testnetBradbury.defaultConsensusMaxRotations), appData];
  if (addTransaction.inputs.length >= 6) txArgs.push(BigInt(Math.floor(Date.now() / 1000) + 3600));
  const data = viem.encodeFunctionData({ abi: [addTransaction], functionName: "addTransaction", args: txArgs });
  return { appData, data };
}

async function probe({ path, args }) {
  const source = await fs.readFile(`${ROOT}/${path}`, "utf8");
  const encoded = encode(source, args);
  const request = { from: SENDER, to: testnetBradbury.consensusMainContract.address, data: encoded.data, value: "0x0" };
  const [chainId, blockNumber, gasPrice, block, estimate] = await Promise.all([
    rpc("eth_chainId"), rpc("eth_blockNumber"), rpc("eth_gasPrice"),
    rpc("eth_getBlockByNumber", ["latest", false]), rpc("eth_estimateGas", [request]),
  ]);
  return {
    path,
    constructor_args: args,
    captured_at_utc: new Date().toISOString(),
    source_utf8_bytes: Buffer.byteLength(source, "utf8"),
    app_data: stats(encoded.appData),
    outer_deployment_data: stats(encoded.data),
    request: { ...request, gas: null, gas_price: gasPrice.result || null },
    chain_id: chainId.result || null,
    block_number: blockNumber.result || null,
    block: block.result ? { number: block.result.number, timestamp: block.result.timestamp, gas_limit: block.result.gasLimit, extra_fields: Object.fromEntries(Object.entries(block.result).filter(([key]) => /pub|data|blob|l1|batch|gas/i.test(key))) } : null,
    estimate: { result: estimate.result || null, error: estimate.error || null, http_status: estimate.http_status },
  };
}

const results = [];
for (const component of COMPONENTS) {
  results.push(await probe(component));
  const latest = results.at(-1);
  console.log(JSON.stringify({ path: component.path, source_bytes: latest.source_utf8_bytes, outer_bytes: latest.outer_deployment_data.bytes, estimate: latest.estimate }));
}
const output = {
  probe_type: "TenderCouncil two-contract Bradbury deployment estimate; no signing or broadcast",
  rpc: RPC,
  cli_path_reference: "genlayer-js deploy encoding -> ConsensusMain.addTransaction -> eth_estimateGas",
  genlayer_cli_version: "0.39.1",
  genlayer_js_version: "1.1.8",
  chain: { name: testnetBradbury.name, chain_id: testnetBradbury.id, consensus_main: testnetBradbury.consensusMainContract.address, add_transaction_input_count: addTransaction.inputs.length },
  encoding: { source_encoding: "UTF-8", transaction: "transactions.serialize([source, constructorBytes, false])", constructor: "Core []; Evaluator [nonzero placeholder Core address, tendercouncil.evaluator.v2]", outer_call: "ConsensusMain.addTransaction(sender, zeroAddress, 5, 3, appData, validUntil)" },
  measured_boundary: { largest_known_success_outer_bytes: 53316, smallest_known_failure_outer_bytes: 53348 },
  results,
};
await fs.writeFile(OUTPUT, `${JSON.stringify(output, null, 2)}\n`, "utf8");
console.log(`wrote ${OUTPUT}`);
