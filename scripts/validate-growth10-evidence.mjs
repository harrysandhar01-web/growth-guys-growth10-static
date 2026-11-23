import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export const REQUIRED_ROLES = new Set(["products", "cart_totals"]);
export const PROHIBITED_ACTIONS = ["login", "identity", "address", "payment", "checkout_submission", "order", "captcha_bypass"];

function fail(message) { throw new Error(message); }
function money(value, field) {
  if (typeof value !== "string" || !/^\d+(?:\.\d{1,2})?$/.test(value)) fail(`${field}_must_be_CAD_number`);
  const cents = Math.round(Number(value) * 100);
  if (!Number.isSafeInteger(cents) || cents < 0) fail(`${field}_invalid`);
  return cents;
}
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function torontoDate(iso) {
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) fail("observed_at_must_be_valid_iso_timestamp");
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const p = Object.fromEntries(parts.map(x => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}
function isImage(bytes, mime) {
  const actual = bytes.subarray(0, 12);
  return (mime === "image/webp" && actual.toString("ascii", 0, 4) === "RIFF" && actual.toString("ascii", 8, 12) === "WEBP") ||
    (mime === "image/png" && actual.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) ||
    (mime === "image/jpeg" && actual[0] === 0xff && actual[1] === 0xd8 && actual[2] === 0xff);
}

export function validateGrowth10Evidence(pkg, packageDir = process.cwd(), now = new Date()) {
  if (!pkg || typeof pkg !== "object") fail("evidence_package_required");
  if (pkg.site !== "GROWTH10" || pkg.code !== "GROWTH10") fail("site_or_code_identity_mismatch");
  if (typeof pkg.event_key !== "string" || !/^growth10-(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]{2,100}$/.test(pkg.event_key)) fail("canonical_growth10_event_key_required");
  const eventDate = pkg.event_key.match(/^growth10-(\d{4}-\d{2}-\d{2})-/)[1];
  if (pkg.evidence_date !== eventDate) fail("event_key_and_evidence_date_mismatch");
  const observed = new Date(pkg.observed_at);
  if (!Number.isFinite(observed.getTime()) || torontoDate(pkg.observed_at) !== pkg.evidence_date || observed > now) fail("observed_timestamp_invalid_future_or_wrong_toronto_day");
  if (typeof pkg.status !== "string" || /unaccepted|system[_ -]?error|failed|failure|rejected/i.test(pkg.status) || !/candidate_evidence_retained|candidate_accepted/i.test(pkg.status)) fail("evidence_package_is_not_an_accepted_candidate_state");
  if (pkg.currency !== "CAD") fail("currency_must_be_CAD");
  if (String(pkg.coupon ?? "").toUpperCase() !== "GROWTH10") fail("coupon_identity_mismatch");
  if (!/successfully|applied/i.test(String(pkg.merchant_response ?? "")) || /not applied|failed|invalid|rejected/i.test(String(pkg.merchant_response ?? ""))) fail("merchant_success_response_required");
  const scope = pkg.scope;
  if (!scope || ["account_or_identity_entered", "address_entered", "payment_entered", "checkout_submitted", "order_placed"].some(k => scope[k] === true)) fail("cart_only_scope_boundary_failed");
  if (pkg.payment_method_changed !== false) fail("payment_method_changed_must_be_false");
  const subtotal = money(pkg.subtotal, "subtotal");
  const discount = money(pkg.discount, "discount");
  const total = money(pkg.total, "total");
  const bitcoin = money(pkg.bitcoin ?? "0", "bitcoin");
  if (subtotal <= 0 || discount <= 0 || discount > subtotal) fail("positive_discount_within_subtotal_required");
  if (discount !== Math.round(subtotal * 0.1)) fail("GROWTH10_discount_must_equal_10_percent");
  if (total !== subtotal - discount - bitcoin) fail("displayed_total_does_not_reconcile_with_coupon_and_bitcoin_adjustment");
  if (!Number.isInteger(pkg.quantity) || pkg.quantity !== 1) fail("single_cart_quantity_required");
  if (!String(pkg.product ?? "").trim()) fail("product_required");
  if (!Array.isArray(pkg.originals) || pkg.originals.length < 2 || pkg.originals.length > 8) fail("multiple_originals_required");
  const roles = new Set(); const digests = new Set(); let maxCapture = -Infinity;
  for (const original of pkg.originals) {
    if (!original || !REQUIRED_ROLES.has(original.role) && original.role !== "checkout_boundary") fail("unsupported_original_role");
    if (roles.has(original.role)) fail("duplicate_original_role");
    roles.add(original.role);
    if (!original.captured_at || torontoDate(original.captured_at) !== pkg.evidence_date) fail("original_capture_day_mismatch");
    const captured = new Date(original.captured_at); if (!Number.isFinite(captured.getTime()) || Math.abs(captured - observed) > 15 * 60 * 1000) fail("original_capture_outside_observation_window");
    maxCapture = Math.max(maxCapture, captured.getTime());
    const file = path.resolve(packageDir, original.path); if (!fs.existsSync(file)) fail(`original_evidence_missing:${original.path}`);
    const bytes = fs.readFileSync(file); if (bytes.length === 0 || bytes.length > 8 * 1024 * 1024 || !isImage(bytes, original.mime_type)) fail(`original_evidence_invalid_image:${original.path}`);
    const digest = sha256(bytes); if (!/^[a-f0-9]{64}$/i.test(original.sha256) || digest !== original.sha256.toLowerCase()) fail(`original_evidence_hash_mismatch:${original.path}`);
    if (digests.has(digest)) fail("duplicate_original_bytes"); digests.add(digest);
  }
  if (!roles.has("products") || !roles.has("cart_totals")) fail("products_and_cart_totals_originals_required");
  if (maxCapture !== observed.getTime()) fail("observed_at_must_match_final_original_capture");
  if (!Array.isArray(pkg.prohibited_actions) || pkg.prohibited_actions.join("|") !== PROHIBITED_ACTIONS.join("|")) fail("prohibited_action_boundary_mismatch");
  return { status: "validated_candidate", site: "GROWTH10", code: "GROWTH10", event_key: pkg.event_key, evidence_date: pkg.evidence_date, observed_at: pkg.observed_at, product: pkg.product, quantity: pkg.quantity, subtotal: pkg.subtotal, discount: pkg.discount, bitcoin: pkg.bitcoin ?? "0.00", total: pkg.total, original_digests: [...digests], validated_at: new Date().toISOString() };
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const packagePath = process.argv[2]; if (!packagePath) fail("usage: node scripts/validate-growth10-evidence.mjs <package.json> [receipt.json]");
  const absolute = path.resolve(packagePath); const pkg = JSON.parse(fs.readFileSync(absolute, "utf8"));
  const receipt = validateGrowth10Evidence(pkg, path.dirname(absolute));
  const receiptPath = process.argv[3]; if (receiptPath) fs.writeFileSync(path.resolve(receiptPath), JSON.stringify(receipt, null, 2) + "\n");
  console.log(JSON.stringify(receipt));
}
