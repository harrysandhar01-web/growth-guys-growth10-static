# Permanent owner-controlled content publishing directive

For ordinary owner-supplied content—screenshots, text, guides, announcements, editorial material, metadata, structured data, internal links, or other site-maintenance content—use the independent owner-content lane. Identify the publication as owner-submitted, not independently verified checkout evidence.

Do not require automated verification acceptance, previous verification dates, duplicate-verification restrictions, merchant observations, external validators, WebDAV, Manus WebDev, or external acceptance APIs for ordinary owner-content publication. Automated verification failure must not block this lane.

The current GROWTH10 repository implementation of the requested owner-content workflow is `.github/workflows/owner-editorial-publish.yml`, backed by `scripts/editorial-publish.mjs`. Do not create a competing verification publisher. The workflow is owner-only, preserves `public/api/current-record.json`, current-record aliases, owner records, verification feeds, and historical evidence, and records a content hash and owner publication manifest.

Future maintenance of this lane must use the existing owner editorial workflow and must update applicable canonical URLs, metadata, structured data, internal links, sitemap last-modified dates, archives, and live no-cache read-back. Any content that is not a merchant checkout observation must remain clearly labeled owner-submitted and must never be represented as independently verified evidence.
