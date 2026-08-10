/*
 * No-broadcast Bradbury deployment-envelope probe.
 *
 * This deliberately uses the installed genlayer-js calldata/transaction
 * encoders and the Bradbury ConsensusMain ABI. It only calls read methods and
 * eth_estimateGas; it never signs, sends, or submits a transaction.
 */

import fs from "node:fs/promises";
import { pathToFileURL } from "node:url";

const GENLAYER_ROOT = "C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer";
const GENLAYER_JS = `${GENLAYER_ROOT}/node_modules/genlayer-js`;
const VIEM = `${GENLAYER_ROOT}/node_modules/viem/_esm/index.js`;
const RPC = process.env.BRADBURY_RPC || "https://rpc-bradbury.genlayer.com";
const SENDER = (process.env.BRADBURY_PROBE_SENDER ||
  "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7").toLowerCase();
const OUTPUT = process.env.BRADBURY_PROBE_OUTPUT ||
  "artifacts/bradbury-deployment-envelope-probe.json";
const STOP_WIDTH = Number(process.env.BRADBURY_PROBE_STOP_WIDTH || 16);
const CURRENT_SOURCES = [
  "contracts/tender_council_production.py",
  "artifacts/tender_council_production_deployable.py",
];
const ZERO_ADDRESS = "0x0000000000000000000000000000000000000000";
const DEPENDS =
  '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }';
const INITIAL_SIZES = [
  10_000, 20_000, 30_000, 40_000, 45_000, 50_000, 52_000,
  54_000, 56_000, 58_000, 60_000, 65_000, 70_000,
];
const READ_METHODS = new Set([
  "eth_chainId",
  "eth_blockNumber",
  "eth_getBlockByNumber",
  "eth_gasPrice",
  "eth_estimateGas",
]);

const [{ testnetBradbury }, genlayer, viem] = await Promise.all([
  import(pathToFileURL(`${GENLAYER_JS}/dist/chunk-XCQTIUTU.js`)),
  import(pathToFileURL(`${GENLAYER_JS}/dist/index.js`)),
  import(pathToFileURL(VIEM)),
]);

const calldata = genlayer.abi.calldata;
const transactions = genlayer.abi.transactions;
const addTransaction = testnetBradbury.consensusMainContract.abi.find(
  (item) => item.type === "function" && item.name === "addTransaction",
);
if (!addTransaction) throw new Error("Bradbury addTransaction ABI not found");

async function rpc(method, params = []) {
  if (!READ_METHODS.has(method)) {
    throw new Error(`probe attempted a non-read RPC method: ${method}`);
  }
  const response = await fetch(RPC, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params }),
  });
  const body = await response.json();
  return { http_status: response.status, ...body };
}

function sourceForBytes(target) {
  const base = `${DEPENDS}\nfrom genlayer import *\n\nclass SizeProbe(gl.Contract):\n    def __init__(self):\n        pass\n`;
  const baseBytes = Buffer.byteLength(base, "utf8");
  if (target < baseBytes) {
    throw new Error(`target ${target} is below minimal source size ${baseBytes}`);
  }
  return base + "#".repeat(target - baseBytes);
}

function encodeDeployment(source) {
  const constructorBytes = calldata.encode(
    calldata.makeCalldataObject(undefined, [], undefined),
  );
  const appData = transactions.serialize([source, constructorBytes, false]);
  const args = [
    SENDER,
    ZERO_ADDRESS,
    BigInt(testnetBradbury.defaultNumberOfInitialValidators),
    BigInt(testnetBradbury.defaultConsensusMaxRotations),
    appData,
  ];
  if (addTransaction.inputs.length >= 6) {
    args.push(BigInt(Math.floor(Date.now() / 1000) + 3600));
  }
  const data = viem.encodeFunctionData({
    abi: [addTransaction],
    functionName: "addTransaction",
    args,
  });
  return { constructorBytes, appData, data };
}

function byteStats(hex) {
  const bytes = Buffer.from(hex.slice(2), "hex");
  let zero = 0;
  for (const value of bytes) if (value === 0) zero += 1;
  return {
    bytes: bytes.length,
    zero_bytes: zero,
    nonzero_bytes: bytes.length - zero,
  };
}

function exactError(response) {
  return response.error ? JSON.stringify(response.error) : null;
}

async function probe(target) {
  const source = sourceForBytes(target);
  const sourceBytes = Buffer.byteLength(source, "utf8");
  const encoded = encodeDeployment(source);
  const request = {
    from: SENDER,
    to: testnetBradbury.consensusMainContract.address,
    data: encoded.data,
    value: "0x0",
  };
  const [chainId, blockNumber, gasPrice, block, estimate] = await Promise.all([
    rpc("eth_chainId"),
    rpc("eth_blockNumber"),
    rpc("eth_gasPrice"),
    rpc("eth_getBlockByNumber", ["latest", false]),
    rpc("eth_estimateGas", [request]),
  ]);
  const dataStats = byteStats(encoded.data);
  const appStats = byteStats(encoded.appData);
  return {
    captured_at_utc: new Date().toISOString(),
    requested_source_bytes: target,
    source_utf8_bytes: sourceBytes,
    app_data: {
      ...appStats,
      hex_prefix: encoded.appData.slice(2, 50),
    },
    encoded_deployment_data: dataStats,
    request: {
      ...request,
      gas: null,
      gas_price: gasPrice.result || null,
    },
    chain_id: chainId.result || null,
    block_number: blockNumber.result || null,
    block: block.result
      ? {
          number: block.result.number,
          timestamp: block.result.timestamp,
          gas_limit: block.result.gasLimit,
          gas_used: block.result.gasUsed,
          size: block.result.size,
          extra_fields: Object.fromEntries(
            Object.entries(block.result).filter(([key]) =>
              /pub|data|blob|l1|batch|gas/i.test(key),
            ),
          ),
        }
      : null,
    estimate: {
      result: estimate.result || null,
      error: exactError(estimate),
      http_status: estimate.http_status,
    },
  };
}

async function payloadStats(path) {
  const source = await fs.readFile(path, "utf8");
  const encoded = encodeDeployment(source);
  return {
    path,
    source_utf8_bytes: Buffer.byteLength(source, "utf8"),
    app_data: byteStats(encoded.appData),
    encoded_deployment_data: byteStats(encoded.data),
  };
}

async function main() {
  const results = [];
  const seen = new Set();
  const run = async (target) => {
    if (seen.has(target)) return results.find((item) => item.requested_source_bytes === target);
    seen.add(target);
    const result = await probe(target);
    results.push(result);
    console.log(JSON.stringify({
      source_bytes: result.source_utf8_bytes,
      encoded_data_bytes: result.encoded_deployment_data.bytes,
      estimate: result.estimate,
    }));
    return result;
  };

  for (const size of INITIAL_SIZES) await run(size);
  const successful = () => results.filter((item) => item.estimate.result);
  const failed = () => results.filter((item) => item.estimate.error);
  let low = successful().sort((a, b) => a.source_utf8_bytes - b.source_utf8_bytes).at(-1)?.requested_source_bytes;
  let high = failed().sort((a, b) => a.source_utf8_bytes - b.source_utf8_bytes)[0]?.requested_source_bytes;
  if (low === undefined) {
    await run(1_000);
    low = successful().at(-1)?.requested_source_bytes;
  }
  if (high === undefined) {
    await run(80_000);
    high = failed().sort((a, b) => a.source_utf8_bytes - b.source_utf8_bytes)[0]?.requested_source_bytes;
  }
  if (low !== undefined && high !== undefined && low < high) {
    while (high - low > STOP_WIDTH) {
      const middle = Math.floor((low + high) / 2);
      const result = await run(middle);
      if (result.estimate.result) low = middle;
      else high = middle;
    }
  }
  results.sort((a, b) => a.source_utf8_bytes - b.source_utf8_bytes);
  const successfulResults = results.filter((item) => item.estimate.result);
  const failedResults = results.filter((item) => item.estimate.error);
  const output = {
    probe_type: "Bradbury deployment envelope; estimate-only, no signing or broadcast",
    rpc: RPC,
    cli_path_reference: "genlayer CLI deploy -> genlayer-js deployContract -> ConsensusMain.addTransaction -> eth_estimateGas",
    genlayer_cli_version: "0.39.1",
    genlayer_js_version: "1.1.8",
    chain: {
      name: testnetBradbury.name,
      chain_id: testnetBradbury.id,
      rpc_url: RPC,
      consensus_main: testnetBradbury.consensusMainContract.address,
      initial_validators: testnetBradbury.defaultNumberOfInitialValidators,
      max_rotations: testnetBradbury.defaultConsensusMaxRotations,
      add_transaction_input_count: addTransaction.inputs.length,
    },
    encoding: {
      constructor: "calldata.makeCalldataObject(undefined, [], undefined) -> calldata.encode",
      transaction: "transactions.serialize([source, constructorBytes, false]) -> RLP",
      outer_call: "ConsensusMain.addTransaction(sender, zeroAddress, 5, 3, appData, validUntil)",
      source_encoding: "UTF-8",
    },
    tendercouncil_payloads: await Promise.all(CURRENT_SOURCES.map(payloadStats)),
    initial_sizes_decimal_bytes: INITIAL_SIZES,
    boundary_search_stop_width_bytes: STOP_WIDTH,
    results,
    summary: {
      largest_success_source_bytes: successfulResults.at(-1)?.source_utf8_bytes || null,
      smallest_failure_source_bytes: failedResults[0]?.source_utf8_bytes || null,
      largest_success_encoded_data_bytes: successfulResults.at(-1)?.encoded_deployment_data.bytes || null,
      smallest_failure_encoded_data_bytes: failedResults[0]?.encoded_deployment_data.bytes || null,
    },
  };
  await fs.writeFile(OUTPUT, `${JSON.stringify(output, null, 2)}\n`, "utf8");
  console.log(`wrote ${OUTPUT}`);
}

await main();
