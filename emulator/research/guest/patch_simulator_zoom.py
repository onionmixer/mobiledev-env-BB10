#!/usr/bin/env python3
"""EXPERIMENTAL: patch one stopped, disposable simulator disk copy only.

No allocation, directory or superblock changes: append one PPS attribute inside
the already allocated 4096-byte data block and update the existing inode size.
The fixed destination prevents accidental use on the source or live overlay.
Default is a read-only plan; --apply is required for the two bounded writes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import time

from qnx6_read import QNX6


ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / 'emulator/evidence/guest'
SOURCE = DIRECTORY / 'current-user.raw'
DESTINATION = DIRECTORY / 'passport-zoom50.raw'
MANIFEST = DIRECTORY / 'passport-zoom50-manifest.json'
OBJECT = '/var/pps/services@0.0.775/mesa@99.0.660'
PARTITION = 616896000
INODE = 28371
INODE_OFFSET = 637189888
DATA_OFFSET = 2197366272
ORIGINAL = b'@mesa\nx86pc_BB10DevAlpha_zoom_factor::0.70\n'
ORIGINAL_SHA = '078b3b6b1e2ecdc4e1913229d6bff8a6fa74ff1b1a31fd1b5229308bc4640ae4'
REPLACEMENT = ORIGINAL + b'x86pc_BB10Keyboard1440x1440_zoom_factor::0.50\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path):
    fs = QNX6(path, PARTITION)
    number = fs.lookup(OBJECT)
    node = fs.inode(number)
    if number != INODE or node['size'] != len(ORIGINAL) or node['mode'] != stat.S_IFREG | 0o660:
        raise ValueError('Unexpected mesa inode identity, mode or size')
    if fs.bs != 4096 or node['level'] != 0 or node['ptr'][0] != 385854:
        raise ValueError('Unexpected mesa allocation')
    if any(p != 0xffffffff for p in node['ptr'][1:]):
        raise ValueError('Expected exactly one allocated data block')
    if fs.inode_disk_offset(number) != INODE_OFFSET or fs.data+node['ptr'][0]*fs.bs != DATA_OFFSET:
        raise ValueError('Unexpected active inode or data extent')
    data = fs.file_range(node)
    if data != ORIGINAL or digest(data) != ORIGINAL_SHA:
        raise ValueError('Unexpected mesa content/hash; this patch is version-specific')
    if fs.read_at(INODE_OFFSET,8) != struct.pack('<Q',len(ORIGINAL)):
        raise ValueError('Unexpected inode size field')
    return fs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = args.destination.absolute()
    if path.is_symlink() or SOURCE.is_symlink() or path.resolve() != DESTINATION:
        raise ValueError(f'Only the pre-existing disposable copy {DESTINATION} is permitted')
    if not path.is_file() or not SOURCE.is_file():
        raise ValueError('Source and pre-created disposable copy must exist')
    if os.path.samefile(path,SOURCE):
        raise ValueError('Destination must be a different file/inode from the source')
    for protected in [DIRECTORY/'disk.raw', DIRECTORY/'vmware-sdk.bin']:
        if protected.exists() and os.path.samefile(path,protected):
            raise ValueError('Destination aliases a protected source artifact')
    if path.stat().st_size != 8589934592 or SOURCE.stat().st_size != path.stat().st_size:
        raise ValueError('Unexpected raw disk size')
    source = inspect(SOURCE)
    target = inspect(path)
    if source.sb != target.sb or source.read_at(0,512) != target.read_at(0,512):
        raise ValueError('Source/copy active superblock or MBR mismatch')
    before_inode = target.read_at(INODE_OFFSET,128)
    before_block = target.read_at(DATA_OFFSET,4096)
    if before_inode != source.read_at(INODE_OFFSET,128) or before_block != source.read_at(DATA_OFFSET,4096):
        raise ValueError('Source/copy target ranges differ')
    writes = [(DATA_OFFSET,before_block[:len(REPLACEMENT)],REPLACEMENT),
              (INODE_OFFSET,before_inode[:8],struct.pack('<Q',len(REPLACEMENT)))]
    plan = dict(experimental=True, source=str(SOURCE), destination=str(path),
                diskBytes=path.stat().st_size, partitionOffset=PARTITION, object=OBJECT,
                inode=INODE, inodeRecordDiskOffset=INODE_OFFSET, dataDiskOffset=DATA_OFFSET,
                before=dict(fileBytes=len(ORIGINAL),fileSha256=digest(ORIGINAL),
                            inodeRecordSha256=digest(before_inode),dataBlockSha256=digest(before_block)),
                after=dict(fileBytes=len(REPLACEMENT),fileSha256=digest(REPLACEMENT)),
                writes=[dict(offset=o,bytes=len(new),beforeHex=old.hex(),afterHex=new.hex()) for o,old,new in writes])
    if not args.apply:
        print(json.dumps(dict(status='read-only-plan',**plan),indent=2))
        return
    if MANIFEST.exists():
        raise ValueError('Manifest already exists; refusing to overwrite an earlier experiment')
    source_identity = SOURCE.stat()
    target_identity = path.stat()
    fd = os.open(path,os.O_RDWR|os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev,opened.st_ino,opened.st_mtime_ns) != (target_identity.st_dev,target_identity.st_ino,target_identity.st_mtime_ns):
            raise ValueError('Destination changed between inspection and opening')
        if (opened.st_dev,opened.st_ino) == (source_identity.st_dev,source_identity.st_ino):
            raise ValueError('Opened destination aliases source')
        for offset,old,_ in writes:
            if os.pread(fd,len(old),offset) != old:
                raise ValueError('Destination bytes changed after inspection')
        try:
            for offset,_,new in writes:
                if os.pwrite(fd,new,offset) != len(new):
                    raise OSError('Short patch write')
            os.fsync(fd)
            after = QNX6(path,PARTITION)
            after_node = after.inode(after.lookup(OBJECT))
            if after_node['size'] != len(REPLACEMENT) or after.file_range(after_node) != REPLACEMENT:
                raise ValueError('QNX6 reader verification failed')
            after_inode = after.read_at(INODE_OFFSET,128)
            after_block = after.read_at(DATA_OFFSET,4096)
            expected_inode = struct.pack('<Q',len(REPLACEMENT))+before_inode[8:]
            expected_block = REPLACEMENT+before_block[len(REPLACEMENT):]
            if after_inode != expected_inode or after_block != expected_block or after.sb != source.sb:
                raise ValueError('Unexpected bytes changed in target ranges')
            inspect(SOURCE)  # Re-read immutable reference content after patching.
            if source.read_at(INODE_OFFSET,128) != before_inode or source.read_at(DATA_OFFSET,4096) != before_block:
                raise ValueError('Source changed during experiment')
            plan['after'].update(inodeRecordSha256=digest(after_inode),dataBlockSha256=digest(after_block))
            plan.update(status='applied-and-readback-verified',recordedAtUTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
            temporary = MANIFEST.with_suffix('.json.tmp')
            with temporary.open('x') as report:
                report.write(json.dumps(plan,indent=2)+'\n')
            os.replace(temporary,MANIFEST)
        except BaseException:
            for offset,old,_ in reversed(writes):
                os.pwrite(fd,old,offset)
            os.fsync(fd)
            raise
    finally:
        os.close(fd)
    print(json.dumps(dict(status=plan['status'],manifest=str(MANIFEST),fileSha256=plan['after']['fileSha256'])))


if __name__ == '__main__':
    main()
