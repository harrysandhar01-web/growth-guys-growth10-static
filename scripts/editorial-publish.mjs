import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const profile = process.env.SITE_PROFILE;
const configs = {
  growth10: { site: 'GROWTH10', domain: 'growthguysgrowth10.ca' },
};
const cfg = configs[profile];
if (!cfg) throw new Error('unknown_profile');
if (process.env.GITHUB_ACTOR !== 'harrysandhar01-web' || process.env.OWNER_CONFIRMED !== 'true') {
  throw new Error('authenticated_owner_confirmation_required');
}
const route = (process.env.EDITORIAL_ROUTE || '/').trim();
const title = (process.env.EDITORIAL_TITLE || '').trim();
const reason = (process.env.OWNER_REASON || '').trim();
const contentPath = (process.env.EDITORIAL_CONTENT_FILE || '').trim();
if (!/^\/[a-z0-9][a-z0-9/_-]*\/?$/.test(route) || route.includes('..')) throw new Error('editorial_route_invalid');
if (title.length < 3 || title.length > 255) throw new Error('editorial_title_required');
if (reason.length < 8 || reason.length > 700) throw new Error('owner_reason_required');
if (!contentPath) throw new Error('editorial_content_file_required');
const content = fs.readFileSync(path.resolve(contentPath), 'utf8');
if (content.trim().length < 20 || content.length > 500000) throw new Error('editorial_content_invalid');
const sha256 = crypto.createHash('sha256').update(content, 'utf8').digest('hex');
const now = new Date().toISOString();
const publicationKey = process.env.PUBLICATION_KEY || `growth10-editorial-${now.replace(/[^0-9]/g, '').slice(0, 14)}-${sha256.slice(0, 12)}`;
const publicDir = path.resolve('public');
const manifestPath = path.join(publicDir, 'editorial-publications.json');
const statePath = path.join(publicDir, 'editorial-publication-state.json');
const readJson = file => fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : { publications: [] };
const manifest = readJson(manifestPath);
if (!Array.isArray(manifest.publications)) throw new Error('editorial_manifest_schema_invalid');
if (manifest.publications.some(item => item.publicationKey === publicationKey)) throw new Error('duplicate_editorial_publication');
manifest.publications.unshift({ publicationKey, site: cfg.site, domain: cfg.domain, route, title, contentSha256: sha256, publishedAt: now, actor: 'owner', reason });
const state = { site: cfg.site, latest: publicationKey, latestRoute: route, latestContentSha256: sha256, publishedAt: now, verificationArtifactsPreserved: true };
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(statePath, JSON.stringify(state, null, 2) + '\n');
console.log(JSON.stringify({ status: 'editorial_publication_staged', ...state, currentRecordPath: 'public/api/current-record.json', verificationRecordMutated: false }));
