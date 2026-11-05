#!/usr/bin/env python3
"""Read-only, bounded RCFS inspection of the supplied simulator's fs-os partition.

On-disk field layout cross-checked against bb10root/bb10mt rcfs.pas
(commit 24c3edfe87310b38ed5c4abf348c2f2666f90fbc). Uses existing host liblzo2.
Does not modify source image or execute extracted binaries.
"""
import argparse
import ctypes
from pathlib import Path
import stat
import struct


class RCFS:
    def __init__(self, path, offset=65802240):
        self.f=Path(path).open('rb');self.base=offset
        header=self.read(0x1000,84)
        if header[32:40]!=b'r-c-f-s\0':raise ValueError('RCFS magic mismatch')
        self.image_size,self.count,self.inodes,self.inodes_size,self.names,self.names_size,self.data,self.data_size=struct.unpack_from('<8I',header,48)
        self.chunk_size=struct.unpack_from('<I',header,80)[0]
        if not 1 <= self.chunk_size <= 65536:raise ValueError('Invalid compression chunk size')
        self.lzo=ctypes.CDLL('liblzo2.so.2').lzo1x_decompress_safe
        self.lzo.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p]
        self.lzo.restype=ctypes.c_int

    def read(self,off,size):
        if off<0 or size<0 or size>128*1024*1024:raise ValueError('Invalid bounded read')
        if hasattr(self,'image_size') and off+size>self.image_size:raise ValueError('RCFS range outside image')
        self.f.seek(self.base+off);b=self.f.read(size)
        if len(b)!=size:raise ValueError('Short RCFS read')
        return b

    def name(self,off):return self.read(off,min(1024,self.image_size-off)).split(b'\0')[0].decode('utf8')

    def inode(self,off):
        x=struct.unpack('<4H6I',self.read(off,32))
        return dict(record=off,mode=x[2],emode=x[3],name=self.name(x[4]),offset=x[5],size=x[6],mtime=x[7])

    def ls(self,node):
        if not stat.S_ISDIR(node['mode']) or node['size']%32:raise ValueError('Not valid directory')
        return [self.inode(o) for o in range(node['offset'],node['offset']+node['size'],32)]

    def lookup(self,path):
        node=self.inode(self.inodes)
        for part in path.strip('/').split('/'):
            if part:node={n['name']:n for n in self.ls(node)}[part]
        return node

    def content(self,node):
        kind=(node['emode']>>7)&3
        if not kind:return self.read(node['offset'],node['size'])
        if kind!=1:raise ValueError(f'Unsupported compression kind {kind}')
        first=struct.unpack('<I',self.read(node['offset'],4))[0]
        if first<8 or first%4 or first>4*1024*1024:raise ValueError('Invalid compression offset table')
        offsets=struct.unpack('<%dI'%(first//4),self.read(node['offset'],first))
        out=[]
        for start,end in zip(offsets,offsets[1:]):
            if start==end:continue
            if end<start or end-start>65536:raise ValueError('Invalid compressed chunk')
            source=ctypes.create_string_buffer(self.read(node['offset']+start,end-start))
            dest=ctypes.create_string_buffer(self.chunk_size);length=ctypes.c_size_t(self.chunk_size)
            result=self.lzo(source,end-start,dest,ctypes.byref(length),None)
            if result:raise ValueError(f'LZO decompression error {result}')
            out.append(dest.raw[:length.value])
        data=b''.join(out)
        if len(data)!=node['size']:raise ValueError(f'RCFS file size mismatch {len(data)} != {node["size"]}')
        return data


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('disk');p.add_argument('path');p.add_argument('--extract');p.add_argument('--offset',type=int,default=65802240);a=p.parse_args()
    fs=RCFS(a.disk,a.offset);node=fs.lookup(a.path)
    if a.extract:
        Path(a.extract).write_bytes(fs.content(node));print(f'Extracted {a.path}: {node["size"]} bytes')
    elif stat.S_ISDIR(node['mode']):
        for n in fs.ls(node):print(oct(n['mode']),hex(n['emode']),n['size'],n['name'])
    else:print(fs.content(node).decode(errors='replace'))
