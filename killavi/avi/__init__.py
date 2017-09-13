import tempfile
import struct
import shutil

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
        self.file = tempfile.TemporaryFile()
        shutil.copyfileobj(file, self.file, BUFFER_SIZE)

        self.file.seek(4)
        self.size = struct.unpack('<I', self.file.read(4))[0]

        self.file.seek(32)
        self.header = Header(self.file.read(56))

        self.file.seek(0x5C)
        self.streams = []
        for i in range(0, self.header.streams):
            self.file.seek(12, 1)
            stream_header_size = struct.unpack('<I', self.file.read(4))[0]
            if self.file.read(4) in [b'vids', b'auds']:
                self.file.seek(-4, 1)
                type = self.file.read(4)

            if type == b'vids':
                video_header = video_stream_header(self.file.read(stream_header_size - 4))
                self.file.seek(4, 1)
                stream_format_size = struct.unpack('<I', self.file.read(4))[0]
                if stream_format_size == 40:
                    video_header["format"] = bitmapinfoheader(self.file.read(40))

                if self.file.read(4) == b'JUNK':
                    next = struct.unpack('<I', self.file.read(4))[0]
                    self.file.seek(next, 1)
                if self.file.read(4) == b'vprp':
                    properties_size = struct.unpack('<I', self.file.read(4))[0]
                    video_header["properties"] = vprp(self.file.read(properties_size))
                self.streams.append(video_header)
                self.file.seek(4, 1)
            elif type == b'auds':
                audio_header = audio_stream_header(self.file.read(stream_header_size - 4))
                self.streams.append(audio_header) # TODO: understand what audio headers really look like'
                self.file.seek(4, 1)
                stream_format_size = struct.unpack('<I', self.file.read(4))[0]
                audio_header["format"] = waveformatheader(self.file.read(stream_format_size))
                while self.file.read(4) == b'JUNK':
                    next = struct.unpack('<I', self.file.read(4))[0]
                    self.file.seek(next, 1)
                self.file.seek(4, 1)
        if self.file.read(4) == b'INFO':
            self.file.seek(4, 1)
            size = struct.unpack('<I', self.file.read(4))[0]
            self.info = str(self.file.read(size))[:-1]
        if self.file.read(4) == b'JUNK':
            next = struct.unpack('<I', self.file.read(4))[0]
            self.file.seek(next, 1)
        # we should now be near self.movi



class Header:
    def __init__(self, data):
        f = bytes_to_file(data)
        self.microsecond_per_frame = struct.unpack('<I', f.read(4))[0]
        self.max_bytes_per_sec =  struct.unpack('<I', f.read(4))[0]
        self.reserved1 = struct.unpack('<I', f.read(4))[0]
        self.flags = HeaderFlags(struct.unpack('<I', f.read(4))[0])
        self.total_frames = struct.unpack('<I', f.read(4))[0]
        self.initial_frames = struct.unpack('<I', f.read(4))[0]
        self.streams = struct.unpack('<I', f.read(4))[0]
        self.suggested_buffer_size = struct.unpack('<I', f.read(4))[0]
        self.width = struct.unpack('<I', f.read(4))[0]
        self.height = struct.unpack('<I', f.read(4))[0]
        self.reserved = struct.unpack('<IIII', f.read(16))[0]

class HeaderFlags:
    def __init__(self, input):
        self.has_index = input & AVIF_HASINDEX != 0
        self.must_use_index = input & AVIF_MUSTUSEINDEX != 0
        self.is_interleaved = input & AVIF_ISINTERLEAVED != 0
        self.was_capturefile = input & AVIF_WASCAPTUREFILE != 0
        self.copyrighted = input & AVIF_COPYRIGHTED != 0
        self.use_ck_type = input & AVIF_TRUSTCKTYPE != 0

def audio_stream_header(data):
    f = bytes_to_file(data)
    return {
        'type': 'auds',
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
        }
    }

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


def video_stream_header(data):
    f = bytes_to_file(data)
    return {
        'type': 'vids',
        'handler': str(f.read(4)),
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
        'sample_size': struct.unpack('<I', f.read(4))[0],
        'frame': {
            'left': struct.unpack('<H', f.read(2))[0],
            'top': struct.unpack('<H', f.read(2))[0],
            'right': struct.unpack('<H', f.read(2))[0],
            'bottom': struct.unpack('<H', f.read(2))[0]
        }
    }

def bitmapinfoheader(data):
    f = bytes_to_file(data)
    f.seek(4, 1)
    return {
        'width': struct.unpack('<l', f.read(4))[0],
        'height': struct.unpack('<l', f.read(4))[0],
        'planes': struct.unpack('<H', f.read(2))[0],
        'bit_count': struct.unpack('<H', f.read(2))[0],
        'compression': str(f.read(4)),
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
