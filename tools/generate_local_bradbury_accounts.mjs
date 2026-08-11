import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = path.join(root, ".local", "tendercouncil_bradbury_accounts.json");
const sdk = await import(pathToFileURL("C:/Users/DELL/AppData/Roaming/npm/node_modules/genlayer/node_modules/genlayer-js/dist/index.js"));

const accounts = [];
for (const label of ["bidder_a", "bidder_b", "bidder_c", "bidder_d", "bidder_e"]) {
  const privateKey = sdk.generatePrivateKey();
  accounts.push({ label, private_key: privateKey, address: sdk.createAccount(privateKey).address });
}
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, `${JSON.stringify({ generated_at_utc: new Date().toISOString(), accounts }, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
console.log(JSON.stringify({ path: out, addresses: accounts.map(({ label, address }) => ({ label, address })) }, null, 2));
