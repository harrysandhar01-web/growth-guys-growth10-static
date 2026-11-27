import { spawnSync } from "node:child_process";

const steps = [
  ["current-record-projection", ["scripts/validate-current-record-projection.mjs", "public"]],
  ["canonical-public-snapshot", ["scripts/validate-canonical-snapshot.mjs", "public"]],
  ["customer-facing-site", ["scripts/validate-customer-facing-site.mjs", "public"]],
];

const results = [];
for (const [name, args] of steps) {
  const result = spawnSync(process.execPath, args, { encoding: "utf8" });
  if (result.stdout?.trim()) {
    try {
      results.push({ name, ...JSON.parse(result.stdout.trim().split("\n").at(-1)) });
    } catch {
      results.push({ name, output: result.stdout.trim().slice(-1000) });
    }
  }
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || "validation failed").trim().slice(-2000);
    throw new Error(`owner_publication_validation_failed:${name}:${detail}`);
  }
}

console.log(JSON.stringify({
  status: "owner_publication_validation_passed",
  checks: results,
}));
