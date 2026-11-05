#!/usr/bin/env python3
"""One-time, journaled workspace layout migration. Default: plan only.

Moves preserve files/inodes. Only QCOW2 backing-path metadata is changed by
qemu-img rebase -u, after confirming the backing file itself was just renamed.
Source documents and all five overlays are backed up before any move.
Historical evidence JSON is never rewritten by this program.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'build/layout-migration-20261105'
FINAL = ROOT / 'emulator/evidence/layout-migration-20261105'
MOVES = [
    ('build/compat/vmvga-gtk-passport', 'emulator/state/vmvga-gtk-passport'),
    ('build/compat/vmvga-3d-zoom50', 'emulator/state/vmvga-3d-zoom50'),
    ('build/compat/vmvga-3d', 'emulator/state/vmvga-3d'),
    ('build/compat/vmvga-2d', 'emulator/state/vmvga-2d'),
    ('build/simulator', 'emulator/state/stock'),
    ('build/compat', 'emulator/evidence'),
    ('build/qemu-gui', 'emulator/build/qemu-gui'),
    ('sdk/simulator', 'emulator/images'),
    ('sdk/vmvga-dxvk', 'emulator/lib/dxvk'),
    ('downloads', 'emulator/downloads'),
    ('references/qemu-helios', 'emulator/references/qemu-helios'),
    ('references/qemu-vmvga', 'emulator/references/qemu-vmvga'),
    ('references/qemu-windows', 'emulator/references/qemu-windows'),
    ('tools/vmvga-runtime', 'emulator/runtime'),
    ('tools/research_guest', 'emulator/research/guest'),
    ('tools/audio-experiment', 'emulator/research/audio'),
    ('tools/prepare-simulator.py', 'emulator/tools/prepare-simulator.py'),
    ('config/simulator.lock.json', 'emulator/config/simulator.lock.json'),
    ('config/qemu-gui.lock.json', 'emulator/config/qemu-gui.lock.json'),
    ('docs/ANALYSIS.ko.md', 'docs/analysis/ANALYSIS.ko.md'),
    ('docs/DEVELOPMENT.ko.md', 'docs/development/DEVELOPMENT.ko.md'),
    ('docs/DEVICES.ko.md', 'docs/development/DEVICES.ko.md'),
    ('docs/VERIFICATION.ko.md', 'docs/verification/VERIFICATION.ko.md'),
    ('docs/SIMULATOR.ko.md', 'docs/emulator/SIMULATOR.ko.md'),
    ('docs/COMPATIBILITY.ko.md', 'docs/emulator/COMPATIBILITY.ko.md'),
    ('docs/NATIVE-QEMU.ko.md', 'docs/emulator/NATIVE-QEMU.ko.md'),
]
OVERLAYS = [
    'build/simulator/BB10.qcow2',
    'build/compat/vmvga-2d/BB10.qcow2',
    'build/compat/vmvga-3d/BB10.qcow2',
    'build/compat/vmvga-3d-zoom50/BB10.qcow2',
    'build/compat/vmvga-gtk-passport/BB10.qcow2',
]


def mapped(relative):
    for old, new in sorted(MOVES, key=lambda x: len(x[0]), reverse=True):
        if relative == old or relative.startswith(old + '/'):
            return new + relative[len(old):]
    return relative


def identity(path):
    s = path.lstat()
    r = {'device': s.st_dev, 'inode': s.st_ino, 'bytes': s.st_size,
         'mtimeNs': s.st_mtime_ns, 'mode': oct(s.st_mode & 0o777)}
    if path.is_symlink():
        r['symlink'] = os.readlink(path)
    return r


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def image_info(path):
    return json.loads(subprocess.check_output(['qemu-img', 'info', '--output=json', str(path)], text=True))


def save(name, value):
    (WORK / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if FINAL.exists():
        raise SystemExit('Migration was already applied; refusing to repeat it.')
    WORK.mkdir(parents=True, exist_ok=True)
    if (WORK / 'journal.json').exists():
        raise SystemExit('An apply journal already exists. Inspect it; do not retry blindly.')
    for old, new in MOVES:
        if not (ROOT / old).exists() or (ROOT / new).exists():
            raise SystemExit(f'Unexpected migration source/destination: {old} -> {new}')
    inventory = {}
    for old, _ in MOVES:
        src = ROOT / old
        entries = [src] + (list(src.rglob('*')) if src.is_dir() else [])
        for p in entries:
            if p.is_dir() and not p.is_symlink():
                continue
            rel = p.relative_to(ROOT).as_posix()
            inventory[rel] = identity(p)
    images = {}
    for rel in OVERLAYS:
        info = image_info(ROOT / rel)
        backing = Path(info['full-backing-filename'])
        backing_rel = backing.relative_to(ROOT).as_posix()
        images[rel] = {'info': info, 'sha256Before': sha(ROOT / rel),
                       'backingOld': backing_rel, 'backingNew': mapped(backing_rel),
                       'backingIdentity': identity(backing)}
    save('plan.json', {'createdAtUTC': datetime.now(timezone.utc).isoformat(),
                      'moves': MOVES, 'fileCount': len(inventory), 'overlays': images,
                      'historicalEvidenceRewrite': False})
    save('inventory-before.json', inventory)
    if not args.apply:
        print(json.dumps({'mode': 'plan-only', 'moves': len(MOVES),
                          'files': len(inventory), 'overlays': len(images),
                          'plan': str(WORK / 'plan.json')}))
        return
    for name in ['tools', 'docs', 'config', 'examples', 'README.md', 'package.json', '.gitignore']:
        p = ROOT / name
        dest = WORK / 'before' / name
        if p.is_dir():
            shutil.copytree(p, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    for rel in OVERLAYS:
        dest = WORK / 'overlay-backups' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
        if sha(dest) != images[rel]['sha256Before']:
            raise ValueError('Overlay backup hash mismatch')
    journal = {'moves': [], 'backingUpdates': [], 'complete': False}
    save('journal.json', journal)
    for old, new in MOVES:
        dest = ROOT / new
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.rename(ROOT / old, dest)
        journal['moves'].append([old, new])
        save('journal.json', journal)
    for rel, before in inventory.items():
        now = identity(ROOT / mapped(rel))
        if now != before:
            raise ValueError(f'Rename did not preserve file identity: {rel}')
    for old, report in images.items():
        new = ROOT / mapped(old)
        backing = ROOT / report['backingNew']
        if identity(backing) != report['backingIdentity']:
            raise ValueError('Backing data identity changed before metadata update')
        fmt = report['info'].get('backing-filename-format')
        if fmt not in ['vmdk', 'raw']:
            raise ValueError(f'Unexpected backing format: {fmt}')
        subprocess.run(['qemu-img', 'rebase', '-u', '-f', 'qcow2', '-F', fmt,
                        '-b', str(backing), str(new)], check=True)
        info = image_info(new)
        if info['full-backing-filename'] != str(backing):
            raise ValueError('Backing update verification failed')
        check = subprocess.run(['qemu-img', 'check', '-f', 'qcow2', str(new)], capture_output=True, text=True)
        if check.returncode:
            raise ValueError(check.stdout + check.stderr)
        journal['backingUpdates'].append({'old': old, 'new': mapped(old),
            'backing': str(backing), 'sha256After': sha(new), 'check': check.stdout})
        save('journal.json', journal)
    journal['complete'] = True
    journal['nonOverlayIdentityPreserved'] = True
    save('journal.json', journal)
    save('path-map.json', {'workspace': str(ROOT), 'moves': MOVES,
                          'rule': 'Longest matching old prefix maps to new prefix; old historical files are unchanged.'})
    os.rename(WORK, FINAL)
    print(json.dumps({'complete': True, 'journal': str(FINAL / 'journal.json'),
                      'filesPreserved': len(inventory), 'overlaysChecked': len(images)}))


if __name__ == '__main__':
    main()
