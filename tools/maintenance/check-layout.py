#!/usr/bin/env python3
"""Check maintained links/entrypoints and relocated disk/evidence identities."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'emulator/evidence/layout-migration-20261105'


def main():
    failures = []
    documents = [ROOT / n for n in ['README.md', 'HOWROUSE.md', 'HISTORY.md']]
    documents += [ROOT / 'tools/README.md', ROOT / 'emulator/README.md']
    documents += list((ROOT / 'docs').rglob('*.md'))
    documents += list((ROOT / 'emulator/runtime').glob('*.md'))
    documents += list((ROOT / 'emulator/research').rglob('*.md'))
    links = 0
    for doc in documents:
        for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', doc.read_text()):
            u = urlsplit(target)
            if u.scheme or target.startswith('#'):
                continue
            links += 1
            path = doc.parent / unquote(u.path)
            if not path.exists():
                failures.append(f'Missing link: {doc.relative_to(ROOT)} -> {target}')
    scripts = json.loads((ROOT / 'package.json').read_text())['scripts']
    for name, command in scripts.items():
        for path in re.findall(r'(?:node|bash)\s+([^\s;&]+)', command):
            if not (ROOT / path).is_file():
                failures.append(f'Missing npm entrypoint: {name} -> {path}')
    inventory = json.loads((REPORT / 'inventory-before.json').read_text())
    moves = json.loads((REPORT / 'path-map.json').read_text())['moves']
    def mapped(path):
        for old, new in sorted(moves, key=lambda x: len(x[0]), reverse=True):
            if path == old or path.startswith(old + '/'):
                return new + path[len(old):]
        return path
    preserved = 0
    for old, before in inventory.items():
        if not old.startswith(('build/compat/', 'build/simulator/', 'sdk/simulator/', 'sdk/vmvga-dxvk/', 'downloads/')):
            continue
        if old.endswith('/BB10.qcow2'):
            continue
        path = ROOT / mapped(old)
        s = path.lstat()
        if (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, oct(s.st_mode & 0o777)) != (
                before['device'], before['inode'], before['bytes'], before['mtimeNs'], before['mode']):
            failures.append(f'Historical asset identity changed: {old}')
        preserved += 1
    lock = json.loads((ROOT / 'emulator/config/qemu-gui.lock.json').read_text())
    binary = ROOT / lock['binary']
    binary_matches = hashlib.sha256(binary.read_bytes()).hexdigest() == lock['binarySha256']
    if not binary_matches:
        failures.append('GUI binary SHA-256 differs from lock')
    disks = []
    plan = json.loads((REPORT / 'plan.json').read_text())
    for old, item in plan['overlays'].items():
        disk = ROOT / mapped(old)
        info = json.loads(subprocess.check_output(['qemu-img', 'info', '--output=json', str(disk)], text=True))
        expected = ROOT / item['backingNew']
        if info['full-backing-filename'] != str(expected):
            failures.append(f'Backing path differs: {disk}')
        check = subprocess.run(['qemu-img', 'check', '-f', 'qcow2', str(disk)], capture_output=True, text=True)
        if check.returncode:
            failures.append(f'Image check failed: {disk}')
        disks.append({'disk': str(disk.relative_to(ROOT)), 'backing': str(expected.relative_to(ROOT)),
                      'checkPassed': check.returncode == 0})
    result = {'documents': len(documents), 'localLinks': links, 'npmCommands': len(scripts),
              'historicalAssetIdentitiesChecked': preserved, 'guiBinarySha256Matches': binary_matches,
              'disks': disks, 'failures': failures, 'passed': not failures}
    (REPORT / 'layout-check.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
