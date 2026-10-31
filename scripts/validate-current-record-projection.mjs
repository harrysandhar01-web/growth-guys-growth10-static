import { existsSync, readFileSync } from "node:fs";
import { join as joinFile, resolve as resolveDir } from "node:path";
const ownerDir = resolveDir(process.argv[2] ?? "public");
if (existsSync(joinFile(ownerDir,"owner-publication-state.json"))) {
  const j = f => JSON.parse(readFileSync(joinFile(ownerDir,f),"utf8"));
  const record=j("api/current-record.json");
  const alias=j("api/current-record");
  const state=j("owner-publication-state.json");
  const cfg={vip10:{code:"VIP10",route:"vip10"},growth10:{code:"GROWTH10",route:"growth10"}}[state.profile];
  if (!cfg || record.code!==cfg.code || state.latest!==record.record_reference || alias.record_reference!==state.latest) throw Error("owner_current_record_identity_mismatch");
  const feed=j("verification-feed.json");
  const has=state.profile==="vip10" ? feed.records.some(x=>x.recordReference===state.latest) : feed.items.some(x=>x.id===state.latest);
  if (!has) throw Error("owner_record_absent_from_public_feed");
  const displayDate=new Intl.DateTimeFormat("en-US",{timeZone:"America/Toronto",month:"long",day:"numeric",year:"numeric"}).format(new Date(record.observed_at));
  for (const file of ["index.html",cfg.route+"/index.html","verification-archive/index.html"]) {
    const html=readFileSync(joinFile(ownerDir,file),"utf8");
    // Public pages use the customer-facing current-record block; an internal
    // owner banner is not required and must not be the publication contract.
    if (!html.includes(record.product_name) || !html.includes(displayDate)) throw Error("current_public_projection_missing:"+file);
  }
  if (!existsSync(joinFile(ownerDir,"owner-records",state.latest,"index.html"))) throw Error("owner_record_archive_missing");
  if (!readFileSync(joinFile(ownerDir,"sitemap.xml"),"utf8").includes("/owner-records/"+state.latest+"/")) throw Error("owner_record_sitemap_missing");
  if (new Date(record.observed_at).toISOString()!==state.observedAt) throw Error("owner_time_not_consistent");
  console.log(JSON.stringify({ownerPublishedRecord:state.latest,profile:state.profile,status:"source_consistent"}));
  process.exit(0);
}
import { readFile } from "node:fs/promises";
import { join, resolve } from "node:path";

const publicDir = resolve(process.argv[2] ?? "public");
const record = JSON.parse(await readFile(join(publicDir, "api/current-record.json"), "utf8"));
const observedAt = new Date(record.observed_at);
if (Number.isNaN(observedAt.getTime())) throw new Error("invalid_current_record_observed_at");
const displayDate = new Intl.DateTimeFormat("en-US", { timeZone: "America/Toronto", month: "long", day: "numeric", year: "numeric" }).format(observedAt);
const pages = ["index.html","growth10/index.html","discount-codes/index.html","verification-archive/index.html","verification-history/index.html","how-we-verify/index.html"];
for (const relative of pages) {
  const html = (await readFile(join(publicDir, relative), "utf8")).replace(/\$\s+/g, "$").replace(/\s+/g, " ");
  if (relative === "index.html" || relative === "growth10/index.html") {
    for (const [label, value] of [["current display date", displayDate],["current evidence route", record.evidence_url],["current product", record.product_name]]) {
      if (!html.includes(value)) throw new Error(`${relative}: current record ${label} missing: ${value}`);
    }
  } else {
    for (const [label, value] of [["display date", displayDate],["record reference", record.record_reference],["product", record.product_name],["total", `$${record.total_cad} CAD`],["evidence route", record.evidence_url]]) {
      if (!html.includes(value)) throw new Error(`${relative}: current record ${label} missing: ${value}`);
    }
  }
}

const currentBlockPattern = /<section\b[^>]*(?:current-record-refresh|current-verification-banner|verification-record-summary|current-verification-summary-title)[^>]*>[\s\S]*?<\/section>/gi;
for (const relative of pages) {
  const html = (await readFile(join(publicDir, relative), "utf8")).replace(/\s+/g, " ");
  if (/Current documented record[^<]{0,220}October 27, 2026|Latest GROWTH10 verified checkout record[^<]{0,220}October 27, 2026/i.test(html)) {
    throw new Error(`${relative}: stale October 27 current metadata`);
  }
  for (const block of html.match(currentBlockPattern) ?? []) {
    if (/\bCurrent\b|\bLatest\b/i.test(block) && !block.includes(displayDate)) {
      throw new Error(`${relative}: stale dated current projection`);
    }
  }
}

console.log(JSON.stringify({ pagesChecked: pages.length, displayDate, product: record.product, total: record.total_cad }));
