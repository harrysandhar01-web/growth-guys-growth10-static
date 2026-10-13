# GROWTH10 static-site staging

This private GitHub repository is the route-parity staging target for the **public GROWTH10 site**. The canonical snapshot builder collects the public sitemap routes, public site assets, and read-only current-record/feed files from the canonical site into `public/`.

## Current state

- **Private staging only** — no GitHub Pages deployment
- **No custom domain, CNAME, DNS, redirects, or live traffic changes**
- **No validation, owner, evidence, database, or scheduling workflow runs from this repository**
- Snapshot files are a controlled recovery/parity artifact, not a production replacement

## Local refresh and validation

```bash
node scripts/capture-canonical-snapshot.mjs public
node scripts/validate-canonical-snapshot.mjs public
```

The builder verifies the current public record is GROWTH10 before writing a snapshot. The validator requires the full sitemap route count to be represented, checks every mapped local artifact, and requires the non-deployment boundary in the manifest.

## Cutover boundary

A static snapshot cannot replace the dynamic verification control plane. This repository must **not** receive a Pages configuration, custom-domain file, or DNS cutover until a separately hosted replacement has parity for owner authentication, retained original evidence, validator-gated acceptance, publication, scheduled work, API behavior, canonical/alias redirects, crawler HTML, and rollback.
