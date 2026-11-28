# GROWTH10 independent editorial publication lane

`node scripts/editorial-publish.mjs` is the owner-authorized editorial/site-maintenance lane for GROWTH10. It is separate from `owner-manual-publish.mjs` and `owner-checkout-publish.mjs`.

The command requires the owner actor and `OWNER_CONFIRMED=true`, plus an editorial route, title, reason, and content file. It validates and hashes the content, then writes only:

- `public/editorial-publications.json`
- `public/editorial-publication-state.json`

It does not read or write `public/api/current-record.json`, `public/api/current-record`, `public/owner-records/current.json`, `public/verification-feed.json`, `public/api/verification-feed.json`, checkout evidence, verification history, or the checkout publication state. The state file records `verificationArtifactsPreserved: true` so a deployment receipt can distinguish editorial publication from verification publication.

Use the existing Pages deployment workflow after the generated editorial artifacts pass static validation. The current accepted verification record remains the source for all verification surfaces until a separate evidence package passes the evidence validator and owner acceptance workflow.

## Example

```bash
SITE_PROFILE=growth10 \
GITHUB_ACTOR=harrysandhar01-web \
OWNER_CONFIRMED=true \
OWNER_REASON='Refresh seasonal editorial guidance.' \
EDITORIAL_ROUTE='/editorials/seasonal-guide/' \
EDITORIAL_TITLE='Seasonal discount-code guide' \
EDITORIAL_CONTENT_FILE='/tmp/seasonal-guide.md' \
node scripts/editorial-publish.mjs
```

## Editorial dates and publishing independence

Owner-authorized editorial HTML, features, FAQs and ordinary corrections must not depend on a new checkout run or checkout-specific acceptance. The editorial publication date and a merchant promotion's end date are separate from any verification observation timestamp. Projection scripts must preserve editorial blocks, source attribution and historical evidence. Payment-method wording in current summaries must come from the current record; omit absent USD card charges. Keep current-record APIs and evidence immutable during an editorial-only change.

Historical checkout results must remain in their dated archive pages. Do not reinsert the October 22, 2026 historical record or its individual preview on the homepage or current GROWTH10 page. Current pages should emphasize the latest observation and link to the archive for older individual records. Retain original archive pages and evidence unchanged.
