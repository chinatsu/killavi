import tempfile
import struct
import shutil
import sys

AVIF_HASINDEX = 0x00000010
AVIF_MUSTUSEINDEX = 0x00000020
AVIF_ISINTERLEAVED = 0x00000100
AVIF_TRUSTCKTYPE = 0x00000800
AVIF_WASCAPTUREFILE = 0x00010000
AVIF_COPYRIGHTED = 0x00020000
MPEGLAYER3_FLAG_PADDING_ISO = 0x00000000
MPEGLAYER3_FLAG_PADDING_ON = 0x00000001
MPEGLAYER3_FLAG_PADDING_OFF = 0x00000002

BUFFER_SIZE = 2 ** 24

def bytes_to_file(data):
    f = tempfile.TemporaryFile()
    f.write(data)
    f.seek(0)
    return f

class AVI:
    def __init__(self, file):
        streams = []
        self.file = tempfile.TemporaryFile()
        shutil.copyfileobj(file, self.file, BUFFER_SIZE)

        while self.file.read(4) in [b'LIST', b'JUNK']:
            s = struct.unpack('<I', self.file.read(4))[0]
            if self.file.read(4) == b'movi':
                self.movi = self.file.tell() - 4 # get ourselves the 'movi' marker
            self.file.seek(s - 4, 1)
        self.idx1 = self.file.tell() - 4 # get the 'idx1' marker

        self.file.seek(0)
        check(self.file.read(4) == b'RIFF')
        self.size = struct.unpack('<I', self.file.read(4))[0]
        check(self.file.read(4) == b'AVI ')

        chunk = self.file.read(4)
        while chunk in [b'LIST', b'JUNK']:
            chunksize = struct.unpack('<I', self.file.read(4))[0]
            chunktype = self.file.read(4)
            if chunk == b'JUNK':
                self.file.seek(chunksize - 4, 1)
            if chunktype == b'hdrl':
                check(self.file.read(4) == b'avih')
                headersize = struct.unpack('<I', self.file.read(4))[0]
                self.header = header(self.file.read(56))
            elif chunktype == b'strl':
                check(self.file.read(4) == b'strh')
                streamsize = struct.unpack('<I', self.file.read(4))[0]
                streamtype = self.file.read(4)
                if streamtype == b'vids':
                    video_header = stream_header(self.file.read(streamsize - 4), streamtype)
                    check(self.file.read(4) == b'strf')
                    formatsize = struct.unpack('<I', self.file.read(4))[0]
                    if formatsize == 40:
                        video_header["format"] = bitmapinfoheader(self.file.read(formatsize))
                    # there's some junk here before an eventual video properties header
                    # so let's skip it
                    if self.file.read(4) == b'JUNK':
                        chunksize = struct.unpack('<I', self.file.read(4))[0]
                        self.file.seek(chunksize, 1)
                    else:
                        self.file.seek(-4, 1)
                    if self.file.read(4) == b'vprp':
                        propsize = struct.unpack('<I', self.file.read(4))[0]
                        video_header['properties'] = vprp(self.file.read(propsize))
                    else:
                        self.file.seek(-4, 1)
                    streams.append(video_header)
                elif streamtype == b'auds':
                    audio_header = stream_header(self.file.read(streamsize - 4), streamtype)
                    check(self.file.read(4) == b'strf')
                    formatsize = struct.unpack('<I', self.file.read(4))[0]
                    audio_header['format'] = waveformatheader(self.file.read(formatsize))
                    streams.append(audio_header)
                    if self.file.read(4) == b'JUNK':
                        chunksize = struct.unpack('<I', self.file.read(4))[0]
                        self.file.seek(chunksize, 1)
            elif chunktype == b'INFO':
                self.file.seek(4, 1)
                infosize = struct.unpack('<I', self.file.read(4))[0]
                self.header['info'] = self.file.read(infosize).decode()[:-1]
            elif chunktype == b'movi':
                self.movi = self.file.tell()
                self.file.seek(chunksize, 4)
            chunk = self.file.read(4)
        self.header['streams'] = streams

def check(statement):
    if statement == False:
        print("Unsupported file")
        sys.exit()

def header(data):
    f = bytes_to_file(data)
    return {
        'microsecond_per_frame': struct.unpack('<I', f.read(4))[0],
        'max_bytes_per_sec': struct.unpack('<I', f.read(4))[0],
        'reserved1': struct.unpack('<I', f.read(4))[0],
        'flags': header_flags(struct.unpack('<I', f.read(4))[0]),
        'total_frames': struct.unpack('<I', f.read(4))[0],
        'initial_frames': struct.unpack('<I', f.read(4))[0],
        'total_streams': struct.unpack('<I', f.read(4))[0],
        'suggested_buffer_size': struct.unpack('<I', f.read(4))[0],
        'width': struct.unpack('<I', f.read(4))[0],
        'height': struct.unpack('<I', f.read(4))[0],
        'reserved': struct.unpack('<IIII', f.read(16))[0]
    }

def header_flags(input):
    return {
        'AVIF_HASINDEX': input & AVIF_HASINDEX != 0,
        'AVIF_MUSTUSEINDEX': input & AVIF_MUSTUSEINDEX != 0,
        'AVIF_ISINTERLEAVED': input & AVIF_ISINTERLEAVED != 0,
        'AVIF_WASCAPTUREFILE': input & AVIF_WASCAPTUREFILE != 0,
        'AVIF_COPYRIGHTED': input & AVIF_COPYRIGHTED != 0,
        'AVIF_TRUSTCKTYPE': input & AVIF_TRUSTCKTYPE != 0,
    }

def stream_header(data, t):
    f = bytes_to_file(data)
    header = {}
    if t.decode() == 'vids':
        header["handler"] = f.read(4).decode()
    header.update({
        'type': t.decode(),
        'flags': struct.unpack('<I', f.read(4))[0],
        'priority': struct.unpack('<H', f.read(2))[0],
        'language': struct.unpack('<H', f.read(2))[0],
        'initial_frames': struct.unpack('<i', f.read(4))[0],
        'scale': struct.unpack('<I', f.read(4))[0],
        'rate': struct.unpack('<I', f.read(4))[0],
        'start': struct.unpack('<I', f.read(4))[0],
        'length': struct.unpack('<I', f.read(4))[0],
        'suggested_buffer_size': struct.unpack('<I', f.read(4))[0],
        'quality': struct.unpack('<i', f.read(4))[0],
        'sample_size': struct.unpack('<i', f.read(4))[0],
        'frame': {
            'left': struct.unpack('<H', f.read(2))[0],
            'top': struct.unpack('<H', f.read(2))[0],
            'right': struct.unpack('<H', f.read(2))[0],
            'bottom': struct.unpack('<H', f.read(2))[0]
        },
    })
    return header

def waveformatheader(data):
    f = bytes_to_file(data)
    header = {
        'format_tag': struct.unpack('<H', f.read(2))[0],
        'channels': struct.unpack('<H', f.read(2))[0],
        'samples_per_second': struct.unpack('<I', f.read(4))[0],
        'avg_bytes_per_sec': struct.unpack('<I', f.read(4))[0],
        'block_align': struct.unpack('<H', f.read(2))[0],
        'bits_per_sample': struct.unpack('<H', f.read(2))[0],
        'size': struct.unpack('<H', f.read(2))[0],
    }

    if header['size'] == 12:
        header['id'] = struct.unpack('<H', f.read(2))[0]
        flags = struct.unpack('<I', f.read(4))[0]
        header['flags'] = {
            'padding_iso': flags & MPEGLAYER3_FLAG_PADDING_ISO != 0,
            'padding_on': flags & MPEGLAYER3_FLAG_PADDING_ON != 0,
            'padding_off': flags & MPEGLAYER3_FLAG_PADDING_OFF != 0
        }
        header['block_size'] = struct.unpack('<H', f.read(2))[0]
        header['frames_per_block'] = struct.unpack('<H', f.read(2))[0]
        header['codec_delay'] = struct.unpack('<H', f.read(2))[0]

    return header


def bitmapinfoheader(data):
    f = bytes_to_file(data)
    f.seek(4, 1)
    return {
        'width': struct.unpack('<l', f.read(4))[0],
        'height': struct.unpack('<l', f.read(4))[0],
        'planes': struct.unpack('<H', f.read(2))[0],
        'bit_count': struct.unpack('<H', f.read(2))[0],
        'compression': f.read(4).decode(),
        'size_image': struct.unpack('<I', f.read(4))[0],
        'x_pixels_per_meter': struct.unpack('<l', f.read(4))[0],
        'y_pixels_per_meter': struct.unpack('<l', f.read(4))[0],
        'colors_used': struct.unpack('<I', f.read(4))[0],
        'colors_required': struct.unpack('<I', f.read(4))[0]
    }

def vprp(data):
    f = bytes_to_file(data)
    return {
        'video_format_token': struct.unpack('<I', f.read(4))[0],
        'video_standard': struct.unpack('<I', f.read(4))[0],
        'refresh_rate': struct.unpack('<I', f.read(4))[0],
        'horizontal_lines': struct.unpack('<I', f.read(4))[0],
        'vertical_lines': struct.unpack('<I', f.read(4))[0],
        'aspect_ratio_width': struct.unpack('<H', f.read(2))[0],
        'aspect_ratio_height': struct.unpack('<H', f.read(2))[0],
        'width': struct.unpack('<I', f.read(4))[0],
        'height': struct.unpack('<I', f.read(4))[0],
        'field_per_frame': struct.unpack('<I', f.read(4))[0],
        'field': {
            'compressed_bitmap_height': struct.unpack('<I', f.read(4))[0],
            'compressed_bitmap_width': struct.unpack('<I', f.read(4))[0],
            'valid_bitmap_height': struct.unpack('<I', f.read(4))[0],
            'valid_bitmap_width': struct.unpack('<I', f.read(4))[0],
            'valid_bitmap_x_offset': struct.unpack('<I', f.read(4))[0],
            'valid_bitmap_y_offset': struct.unpack('<I', f.read(4))[0],
            'video_x_offset': struct.unpack('<I', f.read(4))[0],
            'video_y_offset': struct.unpack('<I', f.read(4))[0],
        }
    }
