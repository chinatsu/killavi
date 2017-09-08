import struct
import tempfile
import shutil
from functools import partial

BUFFER_SIZE = 2 ** 24
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
            if self.temp.read(4) != b'RIFF': # if the first 4 bytes doesn't equal RIFF, we know this shit ain't avi
                return False
            l = struct.unpack('<I', self.temp.read(4))[0] # idk why i put this into a variable lol
            if self.temp.read(4) != b'AVI ': # if there's no avi here, it ain't no avi!!!
                return False
            while self.temp.read(4) in [b'LIST', b'JUNK']:
                s = struct.unpack('<I', self.temp.read(4))[0]
                self.temp.seek(s, 1)
            self.temp.seek(-4, 1)
            if self.temp.read(4) != b'idx1': # if there's no idx1 here it AINT NO AVI!!!!!!
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
                self.pos_of_movi = stream.tell() - 4 # get ourselves the 'movi' marker
            stream.seek(s - 4, 1)
        self.pos_of_idx1 = stream.tell() - 4 # get the 'idx1' marker
        s = struct.unpack('<I', stream.read(4))[0] + stream.tell()
        self.meta = []
        while stream.tell() < s: # build the list of meta which contains data for each frame
            chunk_id = stream.read(4)
            self.meta.append({
                "id": chunk_id,
                "flag": struct.unpack("<I", stream.read(4))[0],
                "offset": struct.unpack("<I", stream.read(4))[0],
                "size": struct.unpack("<I", stream.read(4))[0]
            })
        self.__fix_offsets(stream) # better try to realign this shit
        stream.seek(0) # let's go back to the beginning for future reads
        self.stream = stream

    def __len__(self):
        '''Returns the amount of frames'''
        return len(self.meta)

    def __iter__(self):
        for i in range(0, len(self)):
            yield self[i]

    def __getitem__(self, n):
        '''Return a Frame at n position'''
        m = self.meta[n]
        self.stream.seek(self.pos_of_movi + m['offset'] + 8, 0)
        frame = Frame(self.stream.read(m['size']), m['id'], m['flag'], m['offset'])
        self.stream.seek(0)
        return frame

    def as_temp(self, io=None, block=None):
        '''Rebuild the data stream into a TemporaryFile which is returned'''
        if io is None:
            io = tempfile.TemporaryFile()
        for m in self.meta:
            self.stream.seek(self.pos_of_movi + m['offset'] + 8, 0)
            frame = Frame(self.stream.read(m['size']), m['id'], m['flag'], m['offset'])
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
        '''Rebuild self.stream with frames from data, and metadata from meta'''
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

    def remove_keyframes(self):
        '''Remove all keyframes!!'''
        newmeta = []
        for frame in self:
            if frame.is_iframe():
                    lastpframe = frame.as_meta() # save the first pframe to use at the start of the video
                    break
        for frame in self:
            if frame.is_audioframe():
                newmeta.append(frame.as_meta()) # insert audio frames to keep them there
            if frame.is_pframe():
                newmeta.append(frame.as_meta()) # put all the pframes in where they're meant to be
                lastpframe = frame.as_meta()
            elif frame.is_iframe():
                newmeta.append(lastpframe) # if the frame is not a pframe, just insert the last pframe instead >:)
                                               # this is to keep the video synced with the audio, so to speak
        self.meta = newmeta

    def __fix_offsets(self, stream):
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
    def __init__(self, framedata, frameid, frameflag, offset):
        self.framedata = framedata
        self.frameid = frameid
        self.frameflag = frameflag
        self.frameoffset = offset

    def as_meta(self):
        '''Reverts the process from a Frame instance to an entry in Frames.meta'''
        return {'offset': self.frameoffset,
                'flag': self.frameflag,
                'id': self.frameid,
                'size': len(self.framedata)}

    def is_iframe(self):
        if self.is_videoframe():
            return self.frameflag & AVIIF_KEYFRAME != 0
        else:
            return False

    def is_pframe(self):
        if self.is_videoframe():
            return self.frameflag & AVIIF_KEYFRAME == 0
        else:
            return False

    def is_videoframe(self):
        return self.frameid[-2:] in [b'db', b'dc']

    def is_audioframe(self):
        return self.frameid[-2:] == b'wb'
