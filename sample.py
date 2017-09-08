import killavi

if __name__ == '__main__':
    a = killavi.Base('sample.avi') # load a file named sample.avi
    meta = [] # a list to store metadata (frame order, basically)
    for idx, _ in enumerate(a.frames):
        if idx+35 > len(a.frames):
            break
        for x in range(idx, idx+35):
            meta.append(a.frames[x].as_meta())
    a.frames.meta = meta
    a.frames.remove_keyframes() # remove its keyframes
    io = a.frames.as_temp() # build the bytestream
    a.frames.overwrite(io) # overwrite the Frames instance with the new shit
    a.output('sample2.avi') # output the things
