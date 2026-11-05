#!/usr/bin/env python3
"""Rewrite maintained code/docs only, never the historical evidence tree."""
import json
import os
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'emulator/evidence/layout-migration-20261105'
MOVES = json.loads((REPORT / 'path-map.json').read_text())['moves']
ORDERED = sorted(MOVES, key=lambda x: len(x[0]), reverse=True)
PATTERN = re.compile('|'.join(re.escape(a) for a, _ in ORDERED))
LOOKUP = dict(MOVES)


def mapped(path):
    for old, new in ORDERED:
        if path == old or path.startswith(old + '/'):
            return new + path[len(old):]
    return path


def old_name(path):
    rel = path.relative_to(ROOT).as_posix()
    for old, new in sorted(MOVES, key=lambda x: len(x[1]), reverse=True):
        if rel == new or rel.startswith(new + '/'):
            return old + rel[len(new):]
    return rel


def rewrite(path):
    text = path.read_text()
    old = old_name(path)
    new = path.relative_to(ROOT).as_posix()
    links = []
    if path.suffix == '.md':
        def protect(m):
            target = m.group(2)
            url = urlsplit(target)
            if not url.scheme and not target.startswith(('#', '/')):
                old_target = posixpath.normpath(posixpath.join(posixpath.dirname(old), url.path))
                dest = posixpath.relpath(mapped(old_target), posixpath.dirname(new))
                if url.fragment:
                    dest += '#' + url.fragment
                token = m.group(1) + dest + m.group(3)
            else:
                token = m.group(0)
            links.append(token)
            return f'@@BB10_LINK_{len(links)-1}@@'
        text = re.sub(r'(\[[^\]]*\]\()([^\s)]+)(\))', protect, text)
    text = PATTERN.sub(lambda m: LOOKUP[m.group(0)], text)
    for i, link in enumerate(links):
        text = text.replace(f'@@BB10_LINK_{i}@@', link)
    path.write_text(text)


def main():
    marker = REPORT / 'maintained-paths-updated.json'
    if marker.exists():
        raise SystemExit('Already rewritten; do not apply substitutions twice.')
    files = []
    for base in ['tools', 'docs', 'config', 'emulator/runtime', 'emulator/research', 'emulator/tools', 'emulator/config']:
        for p in (ROOT / base).rglob('*'):
            if p.suffix not in ['.mjs', '.py', '.sh', '.md', '.json', '.example']:
                continue
            if 'maintenance' in p.parts or '__pycache__' in p.parts:
                continue
            rewrite(p)
            files.append(str(p.relative_to(ROOT)))
    rewrite(ROOT / 'package.json')
    marker.write_text(json.dumps({'files': files, 'historicalEvidenceModified': False}, indent=2) + '\n')
    print(f'Updated {len(files)+1} maintained files; historical evidence untouched.')


if __name__ == '__main__':
    main()
