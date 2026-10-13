import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, extname, join, resolve } from "node:path";

const canonicalOrigin = (process.env.CANONICAL_ORIGIN ?? "https://growthguysgrowth10.ca").replace(/\/$/, "");
const expectedCode = process.env.EXPECTED_CODE ?? "GROWTH10";
const publicDir = resolve(process.argv[2] ?? "public");
const inventoryDir = resolve(process.argv[3] ?? "source-inventory");
const generatedAt = new Date().toISOString();
const inventoryDate = generatedAt.slice(0, 10);
const concurrency = 6;
const publicAssetPrefixes = ["/assets/", "/manus-storage/", "/__manus/"];

function decodeXml(value) {
  return value
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'");
}

function sitemapUrls(xml) {
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)]
    .map((match) => decodeXml(match[1].trim()))
    .filter((value) => value.startsWith(canonicalOrigin));
}

function safePathname(value) {
  const url = new URL(value, canonicalOrigin);
  if (url.origin !== canonicalOrigin) throw new Error(`unexpected_origin:${url.origin}`);
  const pathname = decodeURIComponent(url.pathname);
  if (!pathname.startsWith("/") || pathname.split("/").includes("..")) {
    throw new Error(`unsafe_path:${pathname}`);
  }
  return pathname;
}

function htmlFile(pathname) {
  return pathname === "/" ? "index.html" : `${pathname.replace(/^\/+|\/+$/g, "")}/index.html`;
}

function assetFile(pathname) {
  return pathname.replace(/^\/+/, "");
}

function isPublicAsset(pathname) {
  return publicAssetPrefixes.some((prefix) => pathname.startsWith(prefix));
}

function collectPublicAssets(text) {
  const assets = new Set();
  const consider = (candidate) => {
    try {
      if (!candidate || candidate.startsWith("data:") || candidate.startsWith("#")) return;
      const url = new URL(candidate, canonicalOrigin);
      if (url.origin !== canonicalOrigin || url.search || !isPublicAsset(url.pathname)) return;
      assets.add(url.pathname);
    } catch {
      // A malformed public attribute cannot become a snapshot file path.
    }
  };

  for (const match of text.matchAll(/(?:src|href)=["']([^"']+)["']/gi)) consider(match[1]);
  for (const match of text.matchAll(/url\((?:["'])?([^\s)"']+)(?:["'])?\)/gi)) consider(match[1]);
  return assets;
}

async function fetchRequired(url, responseType = "text") {
  const response = await fetch(url, {
    headers: {
      "cache-control": "no-cache",
      pragma: "no-cache",
      "user-agent": "GrowthGuysGrowth10PrivateSnapshot/1.0",
    },
  });
  if (!response.ok) throw new Error(`fetch_failed:${response.status}:${url}`);
  return responseType === "bytes" ? new Uint8Array(await response.arrayBuffer()) : response.text();
}

async function put(relativePath, body) {
  const destination = join(publicDir, relativePath);
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, body);
}

async function mapLimit(items, mapper) {
  let cursor = 0;
  const workers = Array.from({ length: Math.min(concurrency, Math.max(items.length, 1)) }, async () => {
    while (cursor < items.length) {
      const current = cursor;
      cursor += 1;
      await mapper(items[current], current);
    }
  });
  await Promise.all(workers);
}

const manifestPath = join(publicDir, "deployment-manifest.json");
let priorManifest = {};
try {
  priorManifest = JSON.parse(await readFile(manifestPath, "utf8"));
} catch {
  // The first full-snapshot build replaces the limited accepted-record snapshot.
}

const sitemap = await fetchRequired(`${canonicalOrigin}/sitemap.xml`);
const pageUrls = sitemapUrls(sitemap);
if (pageUrls.length === 0) throw new Error("empty_canonical_sitemap");

await rm(publicDir, { recursive: true, force: true });
await mkdir(publicDir, { recursive: true });
await mkdir(inventoryDir, { recursive: true });
await put(".nojekyll", "");
await writeFile(join(inventoryDir, `live-sitemap-${inventoryDate}.xml`), sitemap);

const routeMap = {};
const assetPaths = new Set();
await mapLimit(pageUrls, async (url, index) => {
  const html = await fetchRequired(url);
  const pathname = safePathname(url);
  const output = htmlFile(pathname);
  await put(output, html);
  routeMap[pathname === "/" ? "/" : `${pathname.replace(/\/+$/, "")}/`] = `/${output}`;
  for (const asset of collectPublicAssets(html)) assetPaths.add(asset);
  if ((index + 1) % 25 === 0 || index + 1 === pageUrls.length) {
    console.log(`pages=${index + 1}/${pageUrls.length}`);
  }
});

const capturedAssets = new Set();
for (;;) {
  const pendingAssets = [...assetPaths].filter((pathname) => !capturedAssets.has(pathname)).sort();
  if (pendingAssets.length === 0) break;
  await mapLimit(pendingAssets, async (pathname, index) => {
    const bytes = await fetchRequired(`${canonicalOrigin}${pathname}`, "bytes");
    await put(assetFile(pathname), bytes);
    capturedAssets.add(pathname);
    if (extname(pathname).toLowerCase() === ".css") {
      for (const asset of collectPublicAssets(Buffer.from(bytes).toString("utf8"))) assetPaths.add(asset);
    }
    if ((index + 1) % 25 === 0 || index + 1 === pendingAssets.length) {
      console.log(`assets=${capturedAssets.size}`);
    }
  });
}

const dataRoutes = {
  "/api/current-record": "/api/current-record.json",
  "/verification-feed.json": "/verification-feed.json",
  "/feed.xml": "/feed.xml",
  "/robots.txt": "/robots.txt",
  "/sitemap.xml": "/sitemap.xml",
};
for (const [route, output] of Object.entries(dataRoutes)) {
  await put(output.slice(1), await fetchRequired(`${canonicalOrigin}${route}`));
  routeMap[route] = output;
}

const currentRecord = JSON.parse(await readFile(join(publicDir, "api/current-record.json"), "utf8"));
const acceptedRecord = currentRecord?.record ?? currentRecord;
if (acceptedRecord?.code !== expectedCode) {
  throw new Error(`unexpected_current_record_code:${String(acceptedRecord?.code)}`);
}

const manifest = {
  ...priorManifest,
  schemaVersion: 2,
  profileId: "growth10",
  code: expectedCode,
  canonicalOrigin,
  generatedAt,
  source: "canonical_public_html_snapshot",
  deploymentState: "built_not_deployed",
  staticRoutes: Object.fromEntries(Object.entries(routeMap).sort(([a], [b]) => a.localeCompare(b))),
  canonicalSnapshot: {
    generatedAt,
    publicRouteCount: pageUrls.length,
    publicAssetCount: capturedAssets.size,
    currentRecordReference: acceptedRecord?.recordReference ?? acceptedRecord?.record_reference ?? null,
    currentRecordObservedAt: acceptedRecord?.observedAt ?? acceptedRecord?.observed_at ?? null,
    sourceOrigin: canonicalOrigin,
  },
  dynamicControlPlaneExcluded: [
    "owner authentication",
    "original-evidence retention",
    "validator acceptance",
    "verification publication",
    "scheduled verification",
    "database-backed current record",
  ],
};
await put("static-route-map.json", `${JSON.stringify(manifest.staticRoutes, null, 2)}\n`);
await put("deployment-manifest.json", `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({
  publicRouteCount: pageUrls.length,
  publicAssetCount: capturedAssets.size,
  mappedRouteCount: Object.keys(routeMap).length,
  deploymentState: manifest.deploymentState,
}));
