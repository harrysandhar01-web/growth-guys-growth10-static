import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { validateGrowth10Evidence, PROHIBITED_ACTIONS } from "./validate-growth10-evidence.mjs";

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "growth10-evidence-test-"));
const webp = Buffer.concat([Buffer.from("RIFF"), Buffer.alloc(4), Buffer.from("WEBP"), Buffer.from("fixture")]);
const file = path.join(dir, "cart.webp"); fs.writeFileSync(file, webp);
const digest = crypto.createHash("sha256").update(webp).digest("hex");
const base = () => ({
  site: "GROWTH10", code: "GROWTH10", event_key: "growth10-2026-11-22-isolated-cart-pass", evidence_date: "2026-11-22",
  observed_at: "2026-11-22T14:43:00.000Z", product: "TB-500 5mg - Single vial", quantity: 1,
  subtotal: "40.00", discount: "4.00", bitcoin: "0.00", total: "36.00", currency: "CAD", coupon: "GROWTH10",
  merchant_response: "Coupon code applied successfully.", status: "candidate_evidence_retained", payment_method_changed: false,
  scope: { account_or_identity_entered: false, address_entered: false, payment_entered: false, checkout_submitted: false, order_placed: false },
  prohibited_actions: PROHIBITED_ACTIONS,
  originals: [
    { role: "products", path: "cart.webp", mime_type: "image/webp", sha256: digest, captured_at: "2026-11-22T14:42:00.000Z" },
    { role: "cart_totals", path: "cart.webp", mime_type: "image/webp", sha256: digest, captured_at: "2026-11-22T14:43:00.000Z" }
  ]
});
function rejects(mutator, message) { const p = base(); mutator(p); assert.throws(() => validateGrowth10Evidence(p, dir, new Date("2026-11-23T00:00:00.000Z")), new RegExp(message)); }
// Duplicate bytes are rejected as non-independent originals; use a distinct second image for the valid fixture.
const second = Buffer.concat([Buffer.from("RIFF"), Buffer.alloc(4), Buffer.from("WEBP"), Buffer.from("products")]);
fs.writeFileSync(path.join(dir, "products.webp"), second);
const secondDigest = crypto.createHash("sha256").update(second).digest("hex");
const valid = base(); valid.originals[0] = { ...valid.originals[0], path: "products.webp", sha256: secondDigest };
assert.equal(validateGrowth10Evidence(valid, dir, new Date("2026-11-23T00:00:00.000Z")).status, "validated_candidate");
rejects(p => { p.site = "VIP10"; }, "site_or_code_identity_mismatch");
rejects(p => { p.originals[1].sha256 = "0".repeat(64); }, "original_evidence_hash_mismatch");
rejects(p => { p.observed_at = "2026-11-24T14:43:00.000Z"; }, "observed_timestamp_invalid");
rejects(p => { p.originals = [p.originals[1]]; }, "multiple_originals_required");
rejects(p => { p.scope.payment_entered = true; }, "cart_only_scope_boundary_failed");
rejects(p => { p.status = "Unaccepted private cart observation; not published"; }, "evidence_package_is_not_an_accepted");
rejects(p => { p.status = "system_error at guest_cart_execution"; }, "evidence_package_is_not_an_accepted");
console.log("GROWTH10 evidence validator tests passed");
