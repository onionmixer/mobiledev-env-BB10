#!/usr/bin/env python3
"""Bounded read-only QNX6 reader based on Linux fs/qnx6 and qnx6_fs.h.

Reads an already converted raw disk. Supports little-endian plain QNX6,
not the signed RIM filesystem wrapper. Never writes source disk bytes.
"""
import argparse
import functools
import hashlib
import json
from pathlib import Path
import stat
import struct


class QNX6:
    def __init__(self, path, offset):
        self.f = Path(path).open('rb')
        self.offset = offset
        sb = self.read_at(offset + 8192, 512)
        if struct.unpack_from('<I', sb)[0] != 0x68191122:
            raise ValueError('Not a plain little-endian QNX6 superblock')
        self.bs = struct.unpack_from('<I', sb, 48)[0]
        self.blocks = struct.unpack_from('<I', sb, 60)[0]
        if self.bs not in [512, 1024, 2048, 4096, 8192]:
            raise ValueError('Invalid block size')
        sb2 = self.read_at(offset + 8192 + 4096 + self.blocks*self.bs, 512)
        if struct.unpack_from('<I', sb2)[0] == 0x68191122 and struct.unpack_from('<Q', sb2, 8)[0] > struct.unpack_from('<Q', sb, 8)[0]:
            sb = sb2
        self.sb = sb
        self.data = offset + 8192 + 4096
        self.inodes = self.root_node(sb[72:152])
        self.longfile = self.root_node(sb[232:312])

    def read_at(self, offset, size):
        if offset < 0 or size < 0 or size > 128*1024*1024:
            raise ValueError('Invalid bounded read')
        self.f.seek(offset)
        data = self.f.read(size)
        if len(data) != size:
            raise ValueError('Truncated input')
        return data

    def root_node(self, data):
        return {'size': struct.unpack_from('<Q', data)[0],
                'ptr': struct.unpack_from('<16I', data, 8), 'level': data[72]}

    @functools.lru_cache(maxsize=4096)
    def block(self, n):
        if n == 0xffffffff:
            return bytes(self.bs)
        if n >= self.blocks:
            raise ValueError(f'Block out of bounds: {n}')
        return self.read_at(self.data+n*self.bs, self.bs)

    def block_no(self, node, n):
        levels = node['level']
        if levels > 5:
            raise ValueError('Invalid indirect levels')
        count = self.bs//4
        outer = n // (count**levels)
        if outer >= 16:
            raise ValueError('File block out of bounds')
        b = node['ptr'][outer]
        for level in range(levels-1, -1, -1):
            index = (n // (count**level)) % count
            b = struct.unpack_from('<I', self.block(b), index*4)[0]
        return b

    def file_range(self, node, offset=0, length=None):
        length = node['size']-offset if length is None else min(length, node['size']-offset)
        if length < 0 or length > 128*1024*1024:
            raise ValueError('Requested file range too large')
        chunks=[]
        while length:
            n, inside = divmod(offset, self.bs)
            take = min(length, self.bs-inside)
            chunks.append(self.block(self.block_no(node,n))[inside:inside+take])
            offset += take
            length -= take
        return b''.join(chunks)

    def inode(self, n):
        raw = self.file_range(self.inodes, (n-1)*128, 128)
        return {'inode': n, 'size': struct.unpack_from('<Q',raw)[0],
                'mode': struct.unpack_from('<H',raw,32)[0],
                'ptr': struct.unpack_from('<16I',raw,36),
                'level': raw[100], 'status': raw[101]}

    def inode_disk_offset(self, n):
        """Locate this active superblock generation's 128-byte inode record."""
        if n < 1 or n*128 > self.inodes['size']:
            raise ValueError('Inode number out of bounds')
        block_index, inside = divmod((n-1)*128, self.bs)
        block_number = self.block_no(self.inodes, block_index)
        if block_number == 0xffffffff:
            raise ValueError('Inode record maps to a hole')
        return self.data + block_number*self.bs + inside

    def ls(self, n):
        node = self.inode(n)
        if not stat.S_ISDIR(node['mode']):
            raise ValueError('Not a directory')
        data=self.file_range(node)
        entries=[]
        for at in range(0,len(data)-31,32):
            ino=struct.unpack_from('<I',data,at)[0]; length=data[at+4]
            if not ino or not length:continue
            if length <= 27:
                name=data[at+5:at+5+length]
            else:
                idx=struct.unpack_from('<I',data,at+8)[0]
                blob=self.file_range(self.longfile,idx*self.bs,self.bs)
                size=struct.unpack_from('<H',blob)[0]
                if size>510:raise ValueError('Invalid long filename')
                name=blob[2:2+size]
            entries.append((name.decode('utf-8',errors='surrogateescape'),ino))
        return entries

    def lookup(self,path):
        n=1
        for part in path.strip('/').split('/'):
            if not part:continue
            n=dict(self.ls(n))[part]
        return n


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('disk');parser.add_argument('offset',type=int)
    parser.add_argument('path',nargs='?',default='/')
    parser.add_argument('--extract')
    parser.add_argument('--map', action='store_true', help='Print read-only file-to-disk byte extent map as JSON')
    args=parser.parse_args()
    fs=QNX6(args.disk,args.offset)
    n=fs.lookup(args.path);node=fs.inode(n)
    if args.map:
        if not stat.S_ISREG(node['mode']):
            raise ValueError('Extent map requires a regular file')
        extents = []
        for block_index in range((node['size'] + fs.bs - 1)//fs.bs):
            block_number = fs.block_no(node, block_index)
            extents.append(dict(fileOffset=block_index*fs.bs,
                                bytes=min(fs.bs,node['size']-block_index*fs.bs),
                                filesystemBlock=block_number,
                                diskOffset=None if block_number==0xffffffff else fs.data+block_number*fs.bs))
        print(json.dumps(dict(path=args.path, inode=n, mode=oct(node['mode']),
                              inodeRecordDiskOffset=fs.inode_disk_offset(n),
                              size=node['size'], blockSize=fs.bs,
                              partitionOffset=fs.offset,
                              sha256=hashlib.sha256(fs.file_range(node)).hexdigest(),
                              extents=extents), indent=2))
    elif args.extract:
        Path(args.extract).write_bytes(fs.file_range(node))
        print(f'Extracted {args.path}: {node["size"]} bytes')
    elif stat.S_ISDIR(node['mode']):
        for name,ino in fs.ls(n):
            info=fs.inode(ino)
            print(oct(info['mode']),info['size'],ino,name)
    else:
        print(fs.file_range(node).decode('utf-8',errors='replace'))
