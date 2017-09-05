#!/usr/bin/env python3

import struct
import tempfile
import shutil
from functools import partial

BUFFER_SIZE = 1024
AVIIF_LIST = 0x00000001
AVIIF_KEYFRAME = 0x00000010
AVIIF_NO_TIME = 0x00000100
SAFE_FRAMES_COUNT = 150000

class Base(object):
    def __init__(self, path):
        with open(path, 'rb') as f:
            # copy path into a temporary file
            self.temp = tempfile.TemporaryFile()
            shutil.copyfileobj(f, self.temp, BUFFER_SIZE)
            self.temp.seek(0)
        if not self.is_formatted():
            print('Unsupported file.')
        # create a Frames object for all of the video's frames
        self.frames = Frames(self.temp)

    def output(self, path):
        self.frames.stream.seek(0)
        with open(path, 'wb') as f:
            shutil.copyfileobj(self.frames.stream, f, BUFFER_SIZE)

    def is_formatted(self, path=None):
        '''Parse file header and check for justavithings.tumblr.com'''
        try:
            self.temp.seek(0)
            is_io = True
        except AttributeError:
            self.temp = open(path, 'rb')
            is_io = False
        try:
            self.temp.seek(0, 0)
            if self.temp.read(4) != b'RIFF':
                return False
            len = struct.unpack('<I', self.temp.read(4))[0]
            if self.temp.read(4) != b'AVI ':
                return False
            while self.temp.read(4) in [b'LIST', b'JUNK']:
                s = struct.unpack('<I', self.temp.read(4))[0]
                self.temp.seek(s, 1)
            self.temp.seek(-4, 1)
            if self.temp.read(4) != b'idx1':
                return False
            s = struct.unpack('<I', self.temp.read(4))[0]
            self.temp.seek(s, 1)
        except:
            return False
        if not is_io:
            self.temp.close()
        return True


class Frames(object):
    def __init__(self, stream):
        '''Collect metadata and framedata from a stream.'''
        stream.seek(12, 0)
        while stream.read(4) in [b'LIST', b'JUNK']:
            s = struct.unpack('<I', stream.read(4))[0]
            if stream.read(4) == b'movi':
                self.pos_of_movi = stream.tell() - 4
            stream.seek(s - 4, 1)
        self.pos_of_idx1 = stream.tell() - 4
        s = struct.unpack('<I', stream.read(4))[0] + stream.tell()
        self.meta = []
        while stream.tell() < s:
            chunk_id = stream.read(4)
            self.meta.append({
                "id": chunk_id,
                "flag": struct.unpack("<I", stream.read(4))[0],
                "offset": struct.unpack("<I", stream.read(4))[0],
                "size": struct.unpack("<I", stream.read(4))[0]
            })
        self.fix_offsets(stream)
        stream.seek(0)
        self.stream = stream

    def as_temp(self, io=None, block=None):
        if io is None:
            io = tempfile.TemporaryFile()
        for m in self.meta:
            self.stream.seek(self.pos_of_movi + m['offset'] + 8, 0)
            frame = Frame(self.stream.read(m['size']), m['id'], m['flag'])
            if frame.framedata:
                m['offset'] = io.tell() + 4
                m['size'] = len(frame.framedata)
                m['flag'] = frame.frameflag
                m['id'] = frame.frameid
                io.write(m['id'])
                io.write(struct.pack("<I", len(frame.framedata)))
                io.write(frame.framedata)
                if len(frame.framedata) % 2 == 1:
                    io.write(b'\000')
        io.seek(0)
        return io

    def overwrite(self, data):
        '''Rebuild self.stream with frames and metadata from data'''
        self.stream.seek(self.pos_of_movi - 4)
        self.stream.write(struct.pack("<I", data.tell() + 4))
        self.stream.write(b'movi')
        data.seek(0)
        while True:
            d = data.read(BUFFER_SIZE)
            self.stream.write(bytes(d))
            if len(d) < BUFFER_SIZE:
                break
        self.stream.write(b'idx1')
        self.stream.write(struct.pack("<I", len(self.meta) * 16))
        for m in self.meta:
            self.stream.write(m['id'] + struct.pack("<III", m['flag'], m['offset'], m['size']))
        eof = self.stream.tell()
        self.stream.truncate(eof)
        self.stream.seek(4)
        self.stream.write(struct.pack("<I", eof - 8))
        self.stream.seek(48)
        count = 0
        for m in self.meta:
            if m['id'][-2:] in [b'db', b'dc']:
                count += 1
        self.stream.write(struct.pack("<I", count))
        self.stream.seek(0)

    def keyframes_to_deltaframes(self, range=None):
        '''Turn keyframes into deltaframes (incomplete)'''
        for i, _ in enumerate(self.meta):
            frame = self.at(i)
            if frame.is_keyframe:
                frame.flag = 0

    def at(self, n):
        '''Return a Frame at n position'''
        try:
            m = self.meta[n]
            self.stream.seek(self.pos_of_movi + m['offset'] + 8, 0)
            frame = Frame(self.stream.read(m['size']), m['id'], m['flag'])
            self.stream.seek(0)
            return frame
        except:
            return None

    def fix_offsets(self, stream):
        if len(self.meta) == 0:
            return
        position = stream.tell()
        m = self.meta[0]
        stream.seek(self.pos_of_movi + m['offset'], 0)
        if not stream.read(4) == m['id']:
            for x in self.meta:
                x['offset'] -= self.pos_of_movi
        stream.seek(position, 0)


class Frame(object):
    def __init__(self, framedata, frameid, frameflag):
        self.framedata = framedata
        self.frameid = frameid
        self.frameflag = frameflag

    def is_keyframe(self):
        if self.is_videoframe():
            return self.frameflag & AVIIF_KEYFRAME != 0

    def is_deltaframe(self):
        if self.is_videoframe():
            return self.frameflag & AVIIF_KEYFRAME == 0

    def is_videoframe(self):
        return self.frameid[-2:] in [b'db', b'dc']

    def is_audioframe(self):
        return self.frameid[-2:] == b'wb'

a = Base('drop.avi')
io = a.frames.as_temp()
a.frames.overwrite(io)
a.output("drop3.avi")
