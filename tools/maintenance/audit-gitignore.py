#!/usr/bin/env python3
"""Read-only commit-candidate audit using the actual workspace ignore rules.

An isolated temporary Git directory makes this work even before git init.
It does not initialize or stage anything in the workspace's .git directory.
Reports contain paths/categories, never matching credential contents.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'emulator/evidence/git-preparation'
EXCLUDED = [
    'HANDOFF.md',
    'sdk/bbndk/.bb10-sdk.json',
    'references/bbtube/.git/config',
    'build/hello-cascades/HelloCascades-unsigned.bar',
    'emulator/images/10.3.1.2558/BlackBerry10Simulator.vmdk',
    'emulator/lib/dxvk/usr/lib/libdxvk_d3d9.so.0',
    'emulator/downloads/example.zip', 'emulator/references/qemu-helios/COPYING',
    'emulator/build/qemu-gui/qemu-system-x86_64-gtk',
    'emulator/state/vmvga-gtk-passport/Xauthority',
    'emulator/evidence/layout-migration-20261105/before/README.md',
    'emulator/runtime/qemu-system-x86_64',
    'config/device.json', 'config/local.env', '.env', '.env.production',
    '.aws/credentials', '.codex/config.toml', '.agents/local.json',
    'signing/author.p12', 'signing/author.csk', 'signing/bb.csk',
    'signing/device.csj', 'debugtoken.bar', 'keys/private.pem',
    'copy/firmware.bin', 'copy/disk.qcow2', 'copy/simulator.vmdk',
    'capture/network.pcap', 'capture/session.har',
    'scratch/Xauthority', 'scratch/id_ed25519', 'scratch/credentials.json',
]
REQUIRED = [
    '.gitignore', 'README.md', 'HOWROUSE.md', 'HISTORY.md', 'package.json',
    'start_emulator_bb10.sh', 'config/sdk.lock.json',
    'config/references.lock.json', 'config/local.env.example',
    'config/device.example.json', 'emulator/config/qemu-gui.lock.json',
    'emulator/config/simulator.lock.json', 'emulator/runtime/runtime.lock.json',
    'emulator/runtime/Dockerfile', 'emulator/runtime/Dockerfile.gui',
    'emulator/runtime/Dockerfile.gui-runtime', 'emulator/runtime/setup-gui.sh',
    'tools/bb10.mjs', 'tools/simulator.mjs',
    'emulator/research/audio/ak4531.c',
    'examples/hello-cascades/assets/main.qml',
    'examples/hello-cascades/bar-descriptor.xml',
]
SECRET_PATTERNS = {
    'private-key-marker': re.compile(rb'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----'),
    'aws-access-key-id': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github-token': re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    'github-fine-grained-token': re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    'slack-token': re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    actual = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--show-toplevel'],
                            capture_output=True, text=True)
    actual_repo = actual.returncode == 0 and Path(actual.stdout.strip()).resolve() == ROOT
    with tempfile.TemporaryDirectory(prefix='bb10-ignore-audit-') as temp:
        subprocess.run(['git', 'init', '--quiet', temp], check=True, capture_output=True)
        command = ['git', '-c', 'core.excludesFile=/dev/null',
                   f'--git-dir={temp}/.git', f'--work-tree={ROOT}']
        def ignored(path):
            status = subprocess.run(command + ['check-ignore', '--no-index', '--quiet', '--', path],
                                    cwd=ROOT, capture_output=True, text=True)
            if status.returncode not in [0, 1]:
                raise RuntimeError(status.stderr)
            p = subprocess.run(command + ['check-ignore', '--no-index', '-v', '--', path],
                               cwd=ROOT, capture_output=True, text=True)
            if p.returncode not in [0, 1]:
                raise RuntimeError(p.stderr)
            # Verbose check-ignore also returns a matching !unignore rule.
            # Its exit code alone therefore does not classify ignored status.
            return status.returncode == 0, p.stdout.strip()
        cases = []
        issues = []
        for path, expected in [(p, True) for p in EXCLUDED] + [(p, False) for p in REQUIRED]:
            value, rule = ignored(path)
            cases.append({'path': path, 'expectedIgnored': expected,
                          'ignored': value, 'rule': rule})
            if value != expected:
                issues.append({'path': path, 'reason': 'ignore rule mismatch'})
            if path in REQUIRED and not (ROOT / path).is_file():
                issues.append({'path': path, 'reason': 'required source file missing'})
        # No filesystem fixtures are created for these future source asset checks.
        for path in ['examples/app/icon.png', 'examples/app/tone.wav',
                     'package-lock.json', '.env.example', '.env.template']:
            value, rule = ignored(path)
            cases.append({'path': path, 'expectedIgnored': False, 'ignored': value, 'rule': rule})
            if value:
                issues.append({'path': path, 'reason': 'source asset unintentionally ignored'})
        output = subprocess.check_output(command + ['ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT)
        candidates = []
        for raw in output.split(b'\0'):
            if not raw:
                continue
            path = raw.decode('utf-8')
            file = ROOT / path
            if file.is_symlink():
                issues.append({'path': path, 'reason': 'symlink needs review'})
                continue
            data = file.read_bytes()
            candidates.append({'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            if len(data) > 1024 * 1024:
                issues.append({'path': path, 'reason': 'candidate exceeds 1 MiB; resource review required'})
            if data.startswith((b'\x7fELF', b'MZ', b'PK\x03\x04')) or b'\0' in data[:8192]:
                issues.append({'path': path, 'reason': 'binary/archive candidate needs review'})
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(data):
                    issues.append({'path': path, 'reason': name})
        tracked_ignored = None
        if actual_repo:
            tracked_ignored = subprocess.check_output(
                ['git', '-C', str(ROOT), 'ls-files', '-ci', '--exclude-standard', '-z'])
            tracked_ignored = [p.decode() for p in tracked_ignored.split(b'\0') if p]
            issues += [{'path': p, 'reason': 'already tracked despite ignore rule'} for p in tracked_ignored]
    result = {
        'checkedAtUTC': datetime.now(timezone.utc).isoformat(),
        'actualWorkspaceIsGitRepository': actual_repo,
        'workspaceGitMetadataModified': False, 'filesStaged': False,
        'validationUsesIsolatedTemporaryGitDirectory': True,
        'gitignoreSha256': hashlib.sha256((ROOT / '.gitignore').read_bytes()).hexdigest(),
        'candidateCount': len(candidates), 'candidateBytes': sum(p['bytes'] for p in candidates),
        'largestCandidates': sorted(candidates, key=lambda p: p['bytes'], reverse=True)[:10],
        'ruleChecks': cases, 'alreadyTrackedIgnoredFiles': tracked_ignored,
        'issues': issues, 'passed': not issues,
        'limits': 'Pattern and binary/size audit only; not a complete credential or license review. No commit/staging performed.',
    }
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    (OUT / 'candidates.json').write_text(json.dumps(candidates, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['actualWorkspaceIsGitRepository', 'candidateCount',
        'candidateBytes', 'filesStaged', 'issues', 'passed']}, indent=2, ensure_ascii=False))
    raise SystemExit(bool(issues))


if __name__ == '__main__':
    main()
