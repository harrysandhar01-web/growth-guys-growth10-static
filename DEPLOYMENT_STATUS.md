# Deployment status

| Field | Value |
|---|---|
| State | static snapshot deployed; dynamic control plane unchanged |
| Static content directory | public/ |
| Snapshot source | Canonical public HTML, public assets, and read-only public feeds |
| Intended canonical domain | growthguysgrowth10.ca |
| Current public domain | unchanged |
| GitHub Pages | deployment workflow succeeded for commit `24faad0` |
| Custom domain / CNAME | not configured |
| DNS / redirects | unchanged |

## Boundary

This repository is a **static route-parity deployment artifact**. Its canonical snapshot captures the crawlable public site and read-only record/feed projections, while the manifest explicitly excludes the dynamic control plane.

It does **not** replace owner authentication, original-evidence retention, validator acceptance, verification publication, scheduled verification, or the database-backed current record. No DNS or hosting cutover is permitted until the dynamic replacement, route/content/metadata/JSON-LD parity, canonical and alias redirects, sitemap/feed behavior, crawler readback, and rollback are independently proven.
