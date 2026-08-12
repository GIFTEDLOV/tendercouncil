/* Guarded direct programmatic runner for the reviewed corrected Bradbury deployer. */
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const SDK_ROOT = "C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist";
const sdk = await import(pathToFileURL(`${SDK_ROOT}/index.js`));
const { testnetBradbury } = await import(pathToFileURL(`${SDK_ROOT}/chains/index.js`));
const { default: deploySplitBradbury } = await import("./deploy_split_bradbury.mjs");
const keytar = createRequire(pathToFileURL("C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/dist/index.js"))("keytar");

const expectedHead = process.env.TENDERCOUNCIL_EXPECTED_HEAD || "";
if (!expectedHead || process.env.TENDERCOUNCIL_RELEASE_PREFLIGHT_OK !== expectedHead) {
  throw new Error("release preflight token is missing or does not match reviewed HEAD");
}
if (process.env.TENDERCOUNCIL_BROADCAST_CONFIRM !== "DEPLOY_TWO_CONTRACTS_TO_BRADBURY") {
  throw new Error("broadcast confirmation is missing");
}
const privateKey = await keytar.getPassword("genlayer-cli", "account:player3");
if (!privateKey) throw new Error("keychain account missing: player3");
const account = sdk.createAccount(privateKey);
const client = sdk.createClient({ chain: testnetBradbury, account });
if (client.chain.id !== 4221 || account.address.toLowerCase() !== "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7") {
  throw new Error("live deployment network or sender mismatch");
}
await deploySplitBradbury(client);
