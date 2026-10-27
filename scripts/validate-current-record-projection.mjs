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
    for (const [label, value] of [["latest observation date", "October 27, 2026"],["latest observation route", "/observations/2026-10-27/"],["latest observation product", "TB-500 5mg"]]) {
      if (!html.includes(value)) throw new Error(`${relative}: latest observation ${label} missing: ${value}`);
    }
  } else {
    for (const [label, value] of [["display date", displayDate],["record reference", record.record_reference],["product", record.product],["total", `$${record.total_cad} CAD`],["cart observation scope", "Documented pre-payment cart observation"]]) {
      if (!html.includes(value)) throw new Error(`${relative}: current record ${label} missing: ${value}`);
    }
  }
}
console.log(JSON.stringify({ pagesChecked: pages.length, displayDate, product: record.product, total: record.total_cad }));
