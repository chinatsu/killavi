AVIIF_KEYFRAME = 0x00000010

class Frame(object):
    def __init__(self, framedata, frameid, frameflag):
        self.framedata = framedata
        self.frameid = frameid
        self.frameflag = frameflag

    def is_iframe(self):
        if self.is_videoframe():
            return self.frameflag & AVIIF_KEYFRAME != 0

    def is_pframe(self):
        if self.is_videoframe():
            return self.frameflag & AVIIF_KEYFRAME == 0

    def is_videoframe(self):
        return self.frameid[-2:] in [b'db', b'dc']

    def is_audioframe(self):
        return self.frameid[-2:] == b'wb'
