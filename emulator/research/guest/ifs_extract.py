#!/usr/bin/env python3
"""Read-only extraction of this simulator's UCL-compressed QNX IFS.

Uses only two pure decoder functions from a SHA-256 pinned qnxprobe source;
does not import/execute that tool's top-level code. See README.md for provenance.
Validates exact decompressed size and the independent QNX image checksum.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import struct


DECODER_SHA256 = '266f5503a0d84224ff8135371ec557b730350498e22134fdfeb8c0a8632e4940'


def extract(source, decoder_source, destination):
    raw = Path(source).read_bytes()
    if len(raw) > 32*1024*1024:
        raise ValueError('IFS input too large for this bounded research reader')
    signature = struct.pack('<I', 0x00ff7eeb)
    header = -1
    for candidate in range(min(len(raw)-256, 8192)):
        if raw[candidate:candidate+4] != signature:
            continue
        version = struct.unpack_from('<H', raw, candidate+4)[0]
        header_size, machine = struct.unpack_from('<HH', raw, candidate+8)
        if version == 1 and header_size == 256 and machine == 3 and raw[candidate+6] & 0x1e == 0x0c:
            header = candidate
            break
    if header < 0:
        raise ValueError('Expected little-endian UCL startup header')
    startup_size, stored_size = struct.unpack_from('<II', raw, header+32)
    image_size = struct.unpack_from('<I', raw, header+44)[0]
    if image_size > 64*1024*1024 or stored_size < startup_size or header+stored_size > len(raw):
        raise ValueError('Invalid bounded startup image size')
    decoder = Path(decoder_source).read_bytes()
    if hashlib.sha256(decoder).hexdigest() != DECODER_SHA256:
        raise ValueError('Decoder source SHA-256 mismatch; inspect source before changing pin')
    wanted = {'ucl_nrv2b_decompress', 'ifs_decompress_blocks'}
    tree = ast.parse(decoder)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    if {n.name for n in funcs} != wanted:
        raise ValueError('Decoder functions missing')
    namespace = {'struct': struct}
    exec(compile(ast.Module(body=funcs, type_ignores=[]), str(decoder_source), 'exec'), namespace)
    image = namespace['ifs_decompress_blocks'](raw[header+startup_size:header+stored_size], namespace['ucl_nrv2b_decompress'])
    if len(image) != image_size or image[:7] != b'imagefs' or image_size % 4:
        raise ValueError('Decompressed size/magic mismatch')
    checksum = sum(struct.unpack('<%dI' % (image_size//4), image)) & 0xffffffff
    if checksum:
        raise ValueError('QNX image 32-bit word checksum failed')
    embedded_size, directory_end, pos = struct.unpack_from('<III', image, 8)
    if embedded_size != image_size or not 0 <= pos <= directory_end <= image_size:
        raise ValueError('Invalid imagefs directory bounds')
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    files = []
    while pos+24 <= directory_end:
        length, _, inode, mode, _, _, _ = struct.unpack_from('<HH5I', image, pos)
        if length == 0:
            break
        if length < 24 or pos+length > directory_end:
            raise ValueError('Invalid imagefs entry length')
        if inode and stat.S_ISREG(mode):
            offset, size = struct.unpack_from('<II', image, pos+24)
            name = image[pos+32:pos+length].split(b'\0')[0].decode('utf8')
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or offset+size > image_size:
                raise ValueError('Unsafe imagefs path/range')
            data = image[offset:offset+size]
            out = dest / path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            files.append(dict(path=name, bytes=size, offset=offset, sha256=hashlib.sha256(data).hexdigest()))
        pos += length
    (dest.parent/'imagefs.bin').write_bytes(image)
    (dest.parent/'ifs-manifest.json').write_text(json.dumps(dict(imageBytes=image_size, wordChecksum=checksum, files=files), indent=2)+'\n')
    print(f'Extracted {len(files)} regular files, {image_size} image bytes, word checksum {checksum}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ifs')
    parser.add_argument('decoder_source')
    parser.add_argument('destination')
    args = parser.parse_args()
    extract(args.ifs, args.decoder_source, args.destination)
