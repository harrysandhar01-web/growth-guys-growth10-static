# GROWTH10 evidence gate

The GROWTH10 owner publication lane now requires a site-specific retained evidence package before `owner-manual-publish.mjs` can write any record. This is a validation gate, not an acceptance receipt and not a publication receipt.

## Required path

1. A GROWTH10 candidate package is supplied through the owner workflow's `evidence_package` input.
2. `scripts/validate-growth10-evidence.mjs` verifies the exact GROWTH10 identity, canonical event key and Toronto evidence day, non-future timestamp, cart-only scope, exact 10% discount arithmetic, separate Bitcoin discount, successful merchant response, independent original evidence roles, original bytes, MIME signatures, SHA-256 digests, bounded capture timing, and the complete prohibited-action boundary.
3. The validator emits `status: validated_candidate`; it never emits `accepted` or `published`.
4. The owner publisher requires the validator receipt and compares its event timestamp, product, subtotal, discount, Bitcoin discount, and total with the owner inputs before staging any files.
5. Owner confirmation, the authoritative acceptance receipt, deployment, and no-cache live read-back remain separate required records. A projection or customer-facing QA pass cannot substitute for evidence acceptance.

The isolated owner preflight runs focused rejection tests and exercises both correction and new-record branches against synthetic fixtures. The fixtures are not merchant evidence and are never used for production publication.

## Current retained package

The retained November 23 package remains blocked. Its provenance explicitly says `Unaccepted private cart observation; not published`, and its original package does not contain the candidate lifecycle fields required for promotion. The validator therefore rejects it before publication. The public GROWTH10 record remains unchanged until a genuine retained candidate is accepted through the authoritative owner path.

This gate does not open checkout, enter payment or personal information, submit an order, change schedules, modify VIP10, or modify Peptide Index.
