/* Resolve the installed GenLayer CLI/SDK without embedding a developer path. */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";


const require = createRequire(import.meta.url);

function packageRootFromRequire() {
  try {
    return path.dirname(require.resolve("genlayer/package.json"));
  } catch {
    return null;
  }
}

function globalPackageRoot() {
  try {
    const npm = process.platform === "win32" ? "npm.cmd" : "npm";
    const root = execFileSync(npm, ["root", "-g"], {
      encoding: "utf8", windowsHide: true,
    }).trim();
    return root ? path.join(root, "genlayer") : null;
  } catch {
    return null;
  }
}

function platformPackageRoot() {
  if (process.platform === "win32" && process.env.APPDATA) {
    return path.join(process.env.APPDATA, "npm", "node_modules", "genlayer");
  }
  return null;
}

export function resolveGenlayerModulePaths() {
  const candidates = [
    process.env.GENLAYER_PACKAGE_ROOT || null,
    packageRootFromRequire(),
    platformPackageRoot(),
    globalPackageRoot(),
  ].filter(Boolean).map((value) => path.resolve(value));
  const packageRoot = candidates.find((value) =>
    fs.existsSync(path.join(value, "dist", "index.js"))
  );
  if (!packageRoot) {
    throw new Error(
      "GenLayer CLI package not found; install genlayer or set GENLAYER_PACKAGE_ROOT",
    );
  }
  const sdkRoot = path.join(packageRoot, "node_modules", "genlayer-js", "dist");
  const viem = path.join(packageRoot, "node_modules", "viem", "_esm", "index.js");
  for (const required of [path.join(sdkRoot, "index.js"), viem]) {
    if (!fs.existsSync(required)) {
      throw new Error(`required GenLayer dependency is missing: ${required}`);
    }
  }
  return {
    packageRoot,
    cliEntry: path.join(packageRoot, "dist", "index.js"),
    sdkRoot,
    viem,
    repositoryRoot: path.resolve(
      path.dirname(fileURLToPath(import.meta.url)), "..",
    ),
  };
}
