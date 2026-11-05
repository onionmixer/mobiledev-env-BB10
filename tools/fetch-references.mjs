import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repos = JSON.parse(readFileSync(join(root, 'config/references.lock.json'))).repositories;
function git(args, capture = false) {
  const r = spawnSync('git', args, { cwd: root, stdio: capture ? 'pipe' : 'inherit', encoding: 'utf8' });
  if (r.error || r.status !== 0) throw new Error(`git failed: ${r.error?.message || r.stderr || r.status}`);
  return r.stdout?.trim();
}
try {
  for (const repo of repos) {
    const path = join(root, repo.path);
    if (existsSync(path)) {
      if (git(['-C', path, 'rev-parse', 'HEAD'], true) !== repo.commit) {
        throw new Error(`Existing ${repo.path} differs from the lock. Preserve or move it before retrying.`);
      }
      console.log(`Already pinned: ${repo.path}`);
      continue;
    }
    git(['clone', '--no-checkout', '--depth', '1', repo.url, path]);
    git(['-C', path, 'fetch', '--depth', '1', 'origin', repo.commit]);
    git(['-C', path, 'checkout', '--detach', repo.commit]);
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
