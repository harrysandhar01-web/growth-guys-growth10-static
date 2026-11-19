import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] ?? "public");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const record = JSON.parse(read("api/current-record.json"));
const state = JSON.parse(read("owner-publication-state.json"));

const requiredPages = [
  "index.html",
  "growth10/index.html",
  "verification-archive/index.html",
  "verification-history/index.html",
  "how-we-verify/index.html",
  "guides/growth-guys-growth10-promo-code-savings/index.html",
];
const fail = (message) => { throw new Error(`customer_facing_qa_failed:${message}`); };

if (record.code !== "GROWTH10") fail("wrong_site_code");
if (state.latest !== record.record_reference) fail("current_record_state_mismatch");
if (!record.product_name || !record.observed_at || !record.evidence_url) fail("incomplete_current_record");

for (const file of requiredPages) {
  const html = read(file);
  if (!/<html\b/i.test(html) || !/<body\b/i.test(html)) fail(`${file}:not_html_document`);
  if (!/<title>[^<]+<\/title>/i.test(html)) fail(`${file}:missing_title`);
  if (!/<h1\b[^>]*>[\s\S]*?<\/h1>/i.test(html)) fail(`${file}:missing_h1`);
  if (file === "index.html") {
    if (!html.includes('rel="canonical"') || !html.includes("https://growthguysgrowth10.ca/")) fail(`${file}:canonical_missing_or_wrong`);
    if (!html.includes(record.product_name)) fail(`${file}:current_product_missing`);
    if (!html.includes(record.evidence_url)) fail(`${file}:current_evidence_missing`);
    if (!html.includes(record.record_reference)) fail(`${file}:current_reference_missing`);
    if (!html.includes("growth10-evidence-gallery")) fail(`${file}:evidence_gallery_missing`);
    const ownerBlock = html.match(/<!-- OWNER_RECORD_START -->([\s\S]*?)<!-- OWNER_RECORD_END -->/i)?.[1] ?? "";
    if (!ownerBlock.includes(record.record_reference) || !ownerBlock.includes(record.product_name)) fail(`${file}:current_owner_block_stale`);
  }
}

const evidencePath = record.evidence_url.replace(/^\//, "");
if (!fs.existsSync(path.join(root, evidencePath))) fail("current_evidence_file_missing");
const homepage = read("index.html");
const imageSources = [...homepage.matchAll(/(?:src|href)="(\/evidence\/[^"#?]+)"/g)].map((m) => m[1]);
for (const src of new Set(imageSources)) {
  if (!fs.existsSync(path.join(root, src.replace(/^\//, "")))) fail(`linked_evidence_missing:${src}`);
}

console.log(JSON.stringify({
  status: "customer_facing_qa_passed",
  checkedPages: requiredPages,
  currentRecord: record.record_reference,
  currentProduct: record.product_name,
  currentEvidence: record.evidence_url,
  linkedEvidenceFiles: [...new Set(imageSources)].length,
}));
