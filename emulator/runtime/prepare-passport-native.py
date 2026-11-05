#!/usr/bin/env python3
"""Prepare a separate Passport USER configuration at full internal scale."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'emulator/research/guest'))
from qnx6_read import QNX6

BASE = ROOT / 'emulator/evidence/guest/passport-zoom50.raw'
OUTPUT = ROOT / 'emulator/evidence/guest/passport-zoom100.raw'
OBJECT = '/var/pps/services@0.0.775/mesa@99.0.660'
OLD = b'x86pc_BB10Keyboard1440x1440_zoom_factor::0.50\n'
NEW = b'x86pc_BB10Keyboard1440x1440_zoom_factor::1.00\n'
EXPECTED = 'e178dd231fcbbc95d46acbed966a49929ab5e46916c27afc335eaf94eac2446c'


def inspect(path):
    fs = QNX6(path, 616896000)
    node = fs.inode(fs.lookup(OBJECT))
    value = fs.file_range(node)
    if node['size'] > fs.bs or node['level'] != 0:
        raise ValueError('Expected a single-block PPS object')
    offset = fs.data + fs.block_no(node, 0) * fs.bs
    fs.f.close()
    return value, offset


def main():
    original, offset = inspect(BASE)
    if hashlib.sha256(original).hexdigest() != EXPECTED or original.count(OLD) != 1:
        raise SystemExit('Unsupported source PPS configuration')
    replacement = original.replace(OLD, NEW)
    if OUTPUT.exists():
        if OUTPUT.is_symlink() or os.path.samefile(BASE, OUTPUT) or inspect(OUTPUT)[0] != replacement:
            raise SystemExit('Existing native backing differs; refusing to replace it')
    else:
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', str(BASE), str(OUTPUT)], check=True)
        with OUTPUT.open('r+b') as f:
            f.seek(offset)
            if f.read(len(original)) != original:
                raise ValueError('Copied PPS content mismatch')
            f.seek(offset)
            f.write(replacement)
            f.flush()
            os.fsync(f.fileno())
        if inspect(OUTPUT)[0] != replacement or inspect(BASE)[0] != original:
            raise ValueError('Native backing verification failed')
        OUTPUT.chmod(0o444)
    report = {'source': str(BASE), 'output': str(OUTPUT), 'object': OBJECT,
              'dataDiskOffset': offset, 'fileBytes': len(original),
              'beforeSha256': EXPECTED, 'afterSha256': hashlib.sha256(replacement).hexdigest(),
              'guestZoom': 1.0, 'hostGtkScale': 0.5,
              'logicalAppResolution': [1440, 1440], 'expectedFullFramebuffer': [1536, 1560],
              'inodeSizeChanged': False, 'originalWritten': False}
    state_name = os.environ.get('BB10_STATE_NAME', 'vmvga-gtk-passport')
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', state_name):
        raise ValueError('Invalid BB10_STATE_NAME')
    state = ROOT / 'emulator/state' / state_name
    state.mkdir(exist_ok=True)
    (state / 'backing-preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    disk = state / 'BB10.qcow2'
    if not disk.exists():
        subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'raw', '-b', str(OUTPUT), str(disk)], check=True)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
