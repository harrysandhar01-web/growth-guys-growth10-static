import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const source = process.cwd();
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'growth10-editorial-test-'));
fs.cpSync(source, temp, { recursive: true, filter: (name) => !name.includes(`${path.sep}.git${path.sep}`) && !name.endsWith(`${path.sep}.git`) });
const currentPath = path.join(temp, 'public/api/current-record.json');
const before = fs.readFileSync(currentPath, 'utf8');
const contentPath = path.join(temp, 'editorial-fixture.md');
fs.writeFileSync(contentPath, '# Editorial fixture\n\nA maintenance-only publication that does not describe a new verification event.\n');
execFileSync(process.execPath, ['scripts/editorial-publish.mjs'], {
  cwd: temp,
  env: {
    ...process.env,
    SITE_PROFILE: 'growth10',
    GITHUB_ACTOR: 'harrysandhar01-web',
    OWNER_CONFIRMED: 'true',
    OWNER_REASON: 'Test independent editorial maintenance lane.',
    EDITORIAL_ROUTE: '/editorials/maintenance-lane/',
    EDITORIAL_TITLE: 'Editorial maintenance lane test',
    EDITORIAL_CONTENT_FILE: contentPath,
    PUBLICATION_KEY: 'growth10-editorial-test-20261127',
  },
  stdio: 'pipe',
});
assert.equal(fs.readFileSync(currentPath, 'utf8'), before, 'current verification record must remain byte-identical');
const state = JSON.parse(fs.readFileSync(path.join(temp, 'public/editorial-publication-state.json'), 'utf8'));
assert.equal(state.site, 'GROWTH10');
assert.equal(state.verificationArtifactsPreserved, true);
assert.equal(JSON.parse(fs.readFileSync(path.join(temp, 'public/editorial-publications.json'), 'utf8')).publications.length, 1);
console.log('PASS editorial lane: publication succeeds without evidence or schedule and preserves current-record.json');
fs.rmSync(temp, { recursive: true, force: true });
