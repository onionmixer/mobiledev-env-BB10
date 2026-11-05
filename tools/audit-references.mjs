#!/usr/bin/env node
import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const webworks = join(root, 'references/bb10-webworks-framework');
if (!existsSync(join(webworks, 'package.json'))) {
  console.error('Reference checkout missing. See config/references.lock.json and docs/analysis/ANALYSIS.ko.md.');
  process.exit(1);
}
const removedApis = [
  { pattern: /\bpath\.existsSync\s*\(/g, module: 'node:path', member: 'existsSync', replacement: 'fs.existsSync' },
  { pattern: /\bpath\.exists\s*\(/g, module: 'node:path', member: 'exists', replacement: 'fs.access' },
  { pattern: /\butil\.puts\s*\(/g, module: 'node:util', member: 'puts', replacement: 'console.log' },
];
function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '.git' || entry.name === 'node_modules') continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.name.endsWith('.js')) yield path;
  }
}
const findings = [];
for (const dir of ['build', 'lib']) {
  for (const path of walk(join(webworks, dir))) {
    const text = readFileSync(path, 'utf8');
    for (const api of removedApis) {
      for (const match of text.matchAll(api.pattern)) {
        findings.push({ file: relative(webworks, path),
          line: text.slice(0, match.index).split('\n').length,
          api: `${api.module}.${api.member}`, available: typeof require(api.module)[api.member] === 'function',
          replacement: api.replacement });
      }
    }
  }
}
const repositories = JSON.parse(readFileSync(join(root, 'config/references.lock.json'))).repositories;
const checkouts = repositories.map(repo => {
  const result = spawnSync('git', ['-C', join(root, repo.path), 'rev-parse', 'HEAD'], { encoding: 'utf8' });
  return { ...repo, actualCommit: result.status === 0 ? result.stdout.trim() : null,
    matchesLock: result.status === 0 && result.stdout.trim() === repo.commit };
});
const report = { generatedAt: new Date().toISOString(), hostNode: process.version,
  scope: 'Static API scan of WebWorks build/lib only; does not test dependency installation or app runtime.',
  checkouts, webworksPackage: JSON.parse(readFileSync(join(webworks, 'package.json'))), findings };
mkdirSync(join(root, 'build'), { recursive: true });
writeFileSync(join(root, 'build/reference-audit.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(`Host Node: ${process.version}; removed API call sites: ${findings.filter(f => !f.available).length}`);
for (const checkout of checkouts) console.log(`${checkout.matchesLock ? 'OK' : 'MISMATCH'} ${checkout.path} ${checkout.actualCommit || '(missing)'}`);
console.log('Report: build/reference-audit.json');
if (checkouts.some(c => !c.matchesLock)) process.exitCode = 1;
