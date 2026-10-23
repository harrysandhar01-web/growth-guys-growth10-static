import { access, readFile } from "node:fs/promises";
import { join, resolve } from "node:path";

const publicDir = resolve(process.argv[2] ?? "public");
const routeMap = JSON.parse(await readFile(join(publicDir, "static-route-map.json"), "utf8"));
const manifest = JSON.parse(await readFile(join(publicDir, "deployment-manifest.json"), "utf8"));
const sitemap = await readFile(join(publicDir, "sitemap.xml"), "utf8");
const currentRecord = JSON.parse(await readFile(join(publicDir, "api/current-record.json"), "utf8"));
const record = currentRecord?.record ?? currentRecord;

await access(join(publicDir, ".nojekyll"));
if (manifest.deploymentState !== "built_not_deployed") throw new Error("unexpected_deployment_state");
if (manifest.source !== "canonical_public_html_snapshot") throw new Error("snapshot_source_missing");
if (manifest.code !== "GROWTH10" || record?.code !== "GROWTH10") throw new Error("growth10_identity_mismatch");
if (!manifest.canonicalSnapshot?.publicRouteCount) throw new Error("snapshot_metadata_missing");
if (!Number.isInteger(manifest.canonicalSnapshot?.publicAssetCount)) throw new Error("asset_metadata_missing");
if (!Array.isArray(manifest.dynamicControlPlaneExcluded) || manifest.dynamicControlPlaneExcluded.length === 0) {
  throw new Error("dynamic_boundary_missing");
}
if (Object.keys(routeMap).length < manifest.canonicalSnapshot.publicRouteCount) throw new Error("route_map_incomplete");
if ((sitemap.match(/<loc>/g) ?? []).length !== manifest.canonicalSnapshot.publicRouteCount) throw new Error("sitemap_count_mismatch");
for (const match of sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)) {
  const url = new URL(match[1]);
  const route = decodeURIComponent(url.pathname).replace(/^\/+|\/+$/g, "");
  if (!route || url.pathname.endsWith("/") || route.includes(".")) continue;
  try {
    await access(join(publicDir, route, "index.html"));
    throw new Error(`sitemap_noncanonical_route:${url.pathname}`);
  } catch (error) {
    if (error?.message?.startsWith("sitemap_noncanonical_route:")) throw error;
  }
}
for (const output of Object.values(routeMap)) {
  await access(join(publicDir, output.replace(/^\//, "")));
}
console.log(JSON.stringify({
  publicRouteCount: manifest.canonicalSnapshot.publicRouteCount,
  mappedRouteCount: Object.keys(routeMap).length,
  publicAssetCount: manifest.canonicalSnapshot.publicAssetCount,
  deploymentState: manifest.deploymentState,
}));
