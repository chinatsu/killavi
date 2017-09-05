#!/usr/bin/env python3

import os
import struct

def is_formatted(file):
    answer = True
    try:
        file.seekable()
        is_io = True
    except AttributeError:
        file = open(file, 'rb')
        is_io = False

    try:
        file.seek(0, 0)
        if file.read(4) != 'RIFF':
            return False
        len = struct.unpack('<I', file.read(4))[0]
        if file.read(4) != 'AVI ':
            return False
        while file.read(4) in ['LIST', 'JUNK']:
            s = struct.unpack('<I', file.read(4))[0]
            file.seek(s, 1)
        file.seek(-4, 1)
        if file.read(4) != 'idx1':
            return False
        s = struct.unpack('<I', file.read(4))[0]
        file.seek(s, 1)
    except:
        return False
    if not is_io:
        file.close()
    return answer

def init(stream):
    stream.seek(12, 0)
    while stream.read(4) in ['LIST', 'JUNK']:
        s = struct.unpack('<I', stream.read(4))[0]
        if stream.read(4) == 'movi':
            pos_of_movi = stream.seek(-4, 1)
        stream.seek(s-4, 1)
    pos_of_idx1 = stream.seek(-4, 1)
    s = struct.unpack('<I', stream.read(4))[0] + stream.tell()
    meta = []
    while stream.tell() <= s:
        chunk_id = stream.read(4)
        try:
            meta.append({
                "id": chunk_id,
                "flag": struct.unpack("<I", stream.read(4))[0],
                "offset": struct.unpack("<I", stream.read(4))[0],
                "size": struct.unpack("<I", stream.read(4))[0]
                })
        except:
            print('Last appended object:')
            print(meta[-1])
            break

if is_formatted('file.avi'):
    with open('file.avi', 'rb') as f:
        init(f)
