#!/usr/bin/env python3
"""Stage pinned source independently of the reference repositories."""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'emulator/build/qemu-gui'
SOURCE = WORK / 'source'
PINS = {
    'qemu-helios': '6577af923eac07522b4a6879854f1469c48c5801',
    'qemu-vmvga': '073c4dc64e49dd082c70f249dd883cba7ea93f43',
    'qemu-windows': '21b0444a253624cf087d809e90f1c2caba392cc4',
}


def run(*args):
    subprocess.run(args, check=True)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    for name, commit in PINS.items():
        actual = subprocess.check_output(['git', '-C', str(ROOT / 'emulator/references' / name), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != commit:
            raise SystemExit(f'{name}: unexpected revision {actual}')
    marker = WORK / 'source.lock.json'
    if marker.exists():
        print('Pinned GUI source already prepared.')
        return
    if SOURCE.exists():
        raise SystemExit('Unmarked source directory exists; refusing to replace it.')
    SOURCE.mkdir()
    archive = WORK / 'qemu-source.tar'
    run('git', '-C', str(ROOT / 'emulator/references/qemu-helios'), 'archive', '--format=tar', f'--output={archive}', PINS['qemu-helios'])
    run('tar', '-xf', str(archive), '-C', str(SOURCE))
    shutil.copytree(ROOT / 'emulator/references/qemu-vmvga/hw', SOURCE / 'hw', dirs_exist_ok=True)
    patches = sorted((ROOT / 'emulator/references/qemu-windows/patches').glob('*.patch'))
    patches.append(ROOT / 'emulator/research/guest/pcnet-preserve-dwio-experiment.patch')
    for patch in patches:
        run('git', '-C', str(SOURCE), 'apply', '--recount', '--check', str(patch))
        run('git', '-C', str(SOURCE), 'apply', '--recount', str(patch))
    marker.write_text(json.dumps({'pins': PINS, 'patches': [p.name for p in patches],
        'display': ['gtk'], 'pcnet': 'preserve DWIO only across software reset'}, indent=2) + '\n')
    (WORK / 'out').mkdir(exist_ok=True)
    print(f'Prepared {SOURCE}')


if __name__ == '__main__':
    main()
